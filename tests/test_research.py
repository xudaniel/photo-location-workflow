import io
import json
import threading
import time
from urllib.error import HTTPError

from PIL import Image
import pytest

from photo_location_workflow.core import init_case, load, save
from photo_location_workflow.research import OpenAIResearch, ResearchError, ResearchManager, settings


class FakeResearch:
    configured = True
    model = 'test-model'
    def __init__(self):
        self.plans=0
        self.searches=0
        self.fail=True
    def plan(self, case, run):
        self.plans+=1
        return {'summary':'Observed scene', 'observations':['Three windows'], 'queries':['distinctive building'], 'questions':['Does the entrance match?']}, {'response_id':'plan'}
    def search(self, run):
        self.searches+=1
        if self.fail:
            raise ResearchError('rate_limit','Try later')
        return {'summary':'Unverified hypothesis','observations':[], 'queries':['building address'],'questions':['Check official address'], 'sources':[{'url':'https://example.org/','title':'Example'}], 'candidates':[{'name':'Example building','address':'Unverified address','reason':'Similar facade','source_urls':['https://example.org/'],'review_status':'unreviewed'}]}, {'response_id':'search'}


@pytest.fixture
def case(tmp_path):
    image=tmp_path/'source.png';Image.new('RGB',(100,90),'green').save(image)
    root=tmp_path/'case';init_case(image,root)
    return root


def wait_for(manager,case,status):
    deadline=time.monotonic()+5
    while time.monotonic()<deadline:
        with manager.lock:
            state=manager.snapshot(case)
            if state['runs'][-1]['status']==status and not manager.jobs:
                return state
        time.sleep(.01)
    raise AssertionError('Research did not finish')


def test_checkpoint_retry_progress_and_explicit_adoption(case):
    client=FakeResearch();manager=ResearchManager(client)
    try:
        manager.progress(case,'Checked the roof',['older-question'])
        manager.start(case,['assets/source.png'],'en',True)
        state=wait_for(manager,case,'failed')
        assert state['runs'][0]['plan']['observations']==['Three windows']
        assert not load(case)['candidates'] and not load(case)['evidence']
        manager.progress(case,'More local notes',['r1-q1'])
        client.fail=False
        manager.start(case,None,'en',True,resume=state['runs'][0]['id'])
        state=wait_for(manager,case,'completed')
        assert client.plans==1 and client.searches==2
        assert state['runs'][0]['notes']=='Checked the roof'
        assert state['notes']=='More local notes'
        assert state['resolved']==['r1-q1']
        assert load(case)['conclusion']['level']=='unknown'
        manager.adopt(case,state['runs'][0]['id'],0)
        manager.adopt(case,state['runs'][0]['id'],0)
        assert len(load(case)['candidates'])==1
        assert load(case)['conclusion']['level']=='candidate'
        assert load(case)['evidence']==[]
    finally:manager.close()


def test_interrupted_run_recovered_without_network(case):
    client=FakeResearch();manager=ResearchManager(client)
    data=load(case);data['research']={'notes':'Saved','resolved':[], 'runs':[{'id':'r1','status':'searching','plan':{'summary':'Saved'}}]};save(case,data)
    try:
        assert manager.snapshot(case)['runs'][0]['status']=='interrupted'
        assert manager.snapshot(case)['notes']=='Saved'
        assert client.plans==client.searches==0
    finally:manager.close()


def test_consent_integrity_and_inflight_duplicate_guard(case):
    client=FakeResearch();entered=threading.Event();release=threading.Event()
    original=client.plan
    def blocking(*args):entered.set();release.wait(5);return original(*args)
    client.plan=blocking;manager=ResearchManager(client)
    try:
        with pytest.raises(ValueError):manager.start(case,['assets/source.png'],'en')
        with pytest.raises(ValueError):manager.start(case,['../source.png'],'en',True)
        manager.start(case,['assets/source.png'],'en',True)
        assert entered.wait(3)
        with pytest.raises(ValueError):manager.start(case,['assets/source.png'],'en',True)
        release.set();wait_for(manager,case,'failed')
        (case/'assets/source.png').write_bytes(b'changed')
        with pytest.raises(ValueError):manager.start(case,['assets/source.png'],'en',True)
    finally:release.set();manager.close()


def test_search_candidates_require_returned_sources(monkeypatch):
    client=OpenAIResearch('test-key')
    value={'summary':'Hypothesis','queries':['building'],'questions':['check'], 'candidates':[
        {'name':'Cited','address':'Unknown','reason':'shape','source_urls':['https://example.org/']},
        {'name':'Invented','address':'Fake','reason':'guess','source_urls':['https://invented.test/']}]}
    raw={'id':'r','output':[{'type':'web_search_call','status':'completed','action':{'sources':[{'url':'https://example.org/','title':'Source'}]}}]}
    monkeypatch.setattr(client,'_request',lambda *a,**k:(value,raw))
    result,_=client.search({'language':'en','notes':'','plan':{}})
    assert [c['name'] for c in result['candidates']]==['Cited']
    raw['output'][0]['status']='failed'
    with pytest.raises(ResearchError):client.search({'language':'en','notes':'','plan':{}})


def test_transport_settings_and_error_redaction(tmp_path,monkeypatch):
    path=tmp_path/'.env';path.write_text('OPENAI_API_KEY="not-a-real-key"\nOPENAI_MODEL=test-model\nUNRELATED=ignored\n')
    monkeypatch.delenv('OPENAI_API_KEY',raising=False);monkeypatch.delenv('OPENAI_MODEL',raising=False)
    key,model=settings(path);assert key=='not-a-real-key' and model=='test-model'
    def fail(request,**kwargs):
        assert request.full_url=='https://api.openai.com/v1/responses'
        body=json.loads(request.data)
        assert body['store'] is False
        raise HTTPError(request.full_url,429,'secret detail',{},io.BytesIO(b'{"error":{"code":"insufficient_quota","message":"SECRET"}}'))
    monkeypatch.setattr('photo_location_workflow.research.urlopen',fail)
    with pytest.raises(ResearchError) as error:OpenAIResearch(key)._request([],{},False)
    assert error.value.code=='quota' and 'SECRET' not in str(error.value)


def test_research_http_routes_and_no_automatic_candidate(tmp_path):
    from photo_location_workflow.ui import create_server
    from urllib.request import Request,urlopen
    import base64
    client=FakeResearch();client.fail=False
    server,token=create_server(tmp_path/'cases',research_client=client)
    thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
    def request(path,body=None):
        headers={'X-Local-Token':token}
        if body is not None:headers['Content-Type']='application/json'
        req=Request(f'http://127.0.0.1:{server.server_port}'+path,data=json.dumps(body).encode() if body is not None else None,headers=headers)
        with urlopen(req,timeout=5) as response:return json.load(response)
    try:
        assert request('/api/research')['configured'] is True
        image=io.BytesIO();Image.new('RGB',(80,60),'green').save(image,format='PNG')
        state=request('/api/cases',{'image':base64.b64encode(image.getvalue()).decode()})
        route='/api/cases/'+state['id']
        request(route+'/progress',{'notes':'Inspect window','resolved':[]})
        with pytest.raises(HTTPError):request(route+'/research',{'assets':['assets/source.png']})
        request(route+'/research',{'assets':['assets/source.png'],'consent':True,'language':'en'})
        deadline=time.monotonic()+5
        while time.monotonic()<deadline:
            research=request(route+'/research')
            if research['runs'][-1]['status']=='completed':break
            time.sleep(.01)
        assert research['runs'][-1]['status']=='completed'
        assert request(route)['data']['candidates']==[]
        adopted=request(route+'/adopt',{'run':research['runs'][-1]['id'],'index':0})
        assert adopted['data']['conclusion']['level']=='candidate'
        assert adopted['data']['evidence']==[]
    finally:server.shutdown();server.server_close();thread.join(timeout=5)


def test_openai_payload_contains_only_selected_prepared_images(case,monkeypatch):
    import base64
    import photo_location_workflow.research as module
    payloads=[]
    plan={'summary':'Observed','observations':['Green image'],'queries':['green scene'],'questions':['Check source']}
    result={'summary':'Unverified','queries':[],'questions':[],'candidates':[]}
    def respond(request,**kwargs):
        body=json.loads(request.data);payloads.append(body)
        output=[{'type':'message','content':[{'type':'output_text','text':json.dumps(plan if len(payloads)==1 else result),'annotations':[]}]}]
        if len(payloads)==2:output.insert(0,{'type':'web_search_call','status':'completed','action':{'sources':[]}})
        return io.BytesIO(json.dumps({'id':'test-response','status':'completed','output':output,'usage':{'input_tokens':10,'output_tokens':10}}).encode())
    monkeypatch.setattr(module,'urlopen',respond)
    client=OpenAIResearch('not-a-real-key')
    run={'assets':['assets/source.png'],'notes':'Only these notes','language':'en'}
    run['plan'],_=client.plan(case,run)
    client.search(run)
    first=payloads[0];second=payloads[1]
    image=first['input'][0]['content'][1]['image_url']
    assert image.startswith('data:image/jpeg;base64,')
    with Image.open(io.BytesIO(base64.b64decode(image.split(',')[1]))) as im:
        assert max(im.size)<=1600 and not im.getexif()
    serialized=json.dumps(payloads)
    assert str(case) not in serialized and 'not-a-real-key' not in serialized
    assert second['tools'][0]['type']=='web_search' and second['tool_choice']=='required'
    assert second['max_tool_calls']==2
    assert all(item['type']!='input_image' for item in second['input'][0]['content'])


@pytest.mark.parametrize('api_error', [
    {'code':'credit_balance_exhausted','type':'insufficient_quota'},
    {'code':None,'type':'insufficient_quota'},
])
def test_credit_exhaustion_is_not_treated_as_transient_rate_limit(monkeypatch,api_error):
    def fail(request,**kwargs):raise HTTPError(request.full_url,429,'error',{},io.BytesIO(json.dumps({'error':api_error}).encode()))
    monkeypatch.setattr('photo_location_workflow.research.urlopen',fail)
    with pytest.raises(ResearchError) as error:OpenAIResearch('test')._request([],{},False)
    assert error.value.code=='quota'
