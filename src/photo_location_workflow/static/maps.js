const esc = (s) => String(s ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const tools = ['google_streetview','google_satellite','google_terrain','google_earth','mapillary','openstreetmap','other'];
const names = {google_streetview:'Google Street View',google_satellite:'Google Satellite',google_terrain:'Google Terrain',google_earth:'Google Earth',mapillary:'Mapillary',openstreetmap:'OpenStreetMap',other:'Other / 其他'};
export class MapsWorkbench {
  constructor({container, request, mutate, run, notify, fileBase64, download}) {
    Object.assign(this, {container, request, mutate, run, notify, fileBase64, download});
    container.addEventListener('submit', event => {
      event.preventDefault();
      this.run(async () => {
        const form = event.target, f = Object.fromEntries(new FormData(form));
        if (form.id === 'map-location-form') {
          await this.mutate('map-location', {candidate:this.chosen, location:f});
        } else if (form.id === 'map-view-form') {
          const view = Object.fromEntries(['tool','availability','original_url','latitude','longitude','pano','heading','pitch','fov'].map(k => [k, f[k]]));
          if (f.evidence) {
            await this.mutate('map-view', {evidence:f.evidence, view, captured:f.captured, provider:f.provider});
          } else {
            await this.mutate('evidence', {candidate:this.chosen, kind:f.tool === 'google_streetview' ? 'streetview' : 'reference',
              url:f.original_url, verdict:f.verdict, notes:f.notes, captured:f.captured, provider:f.provider,
              image:f.image?.size ? await this.fileBase64(f.image) : null, map_view:view});
          }
        }
        this.notify(this.T('已保存，结论需重新审阅。','Saved. Review the conclusion again.'));
      });
    });
    container.addEventListener('change', event => {
      if (event.target.name === 'evidence') this.fillView(event.target.value);
      if (event.target.name === 'tool') this.cameraState();
    });
    container.addEventListener('click', event => {
      const button = event.target.closest('[data-map-action]');
      if (!button) return;
      this.run(async () => {
        if (button.dataset.mapAction === 'kml') {
          this.download(await this.request(`/cases/${this.active.id}/kml`, undefined, true), 'candidate-places.kml');
          return;
        }
        const form = button.closest('form'), field = form.id === 'map-location-form' ? 'shared_url' : 'original_url';
        const parsed = await this.request('/maps/parse', {url:form.elements[field].value});
        // Clear stale location/camera values before importing; unsupported links retain only their URL.
        const isViewpoint = form.id === 'map-location-form' && parsed.fields.tool === 'google_streetview';
        const keys = form.id === 'map-location-form' ? ['latitude','longitude','place_id'] : ['latitude','longitude','pano','heading','pitch','fov'];
        for (const key of keys) form.elements[key].value = isViewpoint ? '' : (parsed.fields[key] ?? '');
        if (form.id === 'map-view-form') {
          if (parsed.fields.tool) form.elements.tool.value = parsed.fields.tool;
          this.cameraState();
        }
        this.notify(isViewpoint ? this.T('这是街景相机位置，不自动作为候选地点坐标；请人工核对。','This is a panorama camera position, not an inferred place coordinate. Check manually.') : parsed.status === 'parsed' ? this.T('已填入链接明确包含的字段，请核对后保存。','Prefilled explicit URL fields. Check them before saving.') : this.T('此链接仅保留原文。请人工填写坐标和视角；不会展开短链接或猜测参数。','Link retained only. Enter coordinates/view manually; short links are not expanded or guessed.'));
      });
    });
  }
  mode(value) {
    return ({panorama_id:this.T('指定全景（可能失效）','Specified panorama (can expire)'),nearest_panorama:this.T('附近全景（可能变化）','Nearby panorama (can change)'),map_center:this.T('地图中心','Map center'),saved_link:this.T('原始链接','Original link')})[value] || value;
  }
  status(value) {
    return ({unreviewed:this.T('未检查','Not checked'),available:this.T('可查看','Available'),unavailable:this.T('无影像 / 无法查看','No imagery / unavailable')})[value] || this.T('未检查','Not checked');
  }
  T(zh,en) { return this.language === 'zh' ? zh : en; }
  input(name,label,value='',extra='') { return `<label>${esc(label)}<input name="${name}" value="${esc(value)}" ${extra}></label>`; }
  coordinateFields(value={}) {
    return `<div class="form-row">${this.input('latitude',this.T('纬度','Latitude'),value.latitude ?? '', 'type="number" step="any" min="-90" max="90"')}${this.input('longitude',this.T('经度','Longitude'),value.longitude ?? '', 'type="number" step="any" min="-180" max="180"')}</div>`;
  }
  link(label,url) { return `<a class="button secondary" href="${esc(url)}" target="_blank" rel="noreferrer">${esc(label)} ↗</a>`; }
  update(active,chosen,language) {
    Object.assign(this, {active,chosen,language});
    const c = active.data.candidates.find(c=>c.id===chosen);
    this.container.hidden = !c;
    if (!c) return;
    const context = c.map_location || {}, T = (zh,en)=>this.T(zh,en);
    const evidence = active.data.evidence.filter(e=>e.candidate_id===chosen && ['streetview','reference'].includes(e.kind));
    const links = active.maps.candidates[chosen] || [];
    this.container.innerHTML = `<div class="card-heading"><div><span class="eyebrow">MAPS · STREET VIEW · CROSS-CHECK</span><h2>${T('地图核对','Map investigation')} · ${esc(c.name)}</h2></div><span class="pill">${T('无需地图密钥','NO MAP KEY')}</span></div>
      <p class="hint">${T('打开外部地图查看，再保存实际观察。这里不会自动上传照片、获取影像或判定匹配。','Inspect external maps, then record what you actually observed. No photo upload, imagery fetching or automatic match judgment.')}</p>
      <div class="map-grid">
      <div><h3>1 · ${T('保存街景与对照视角','Save an inspected viewpoint')}</h3>
      <form id="map-view-form">
      <label>${T('证据记录','Evidence record')}<select name="evidence"><option value="">${T('新建地图核对证据','New map evidence')}</option>${evidence.map(e=>`<option value="${esc(e.id)}">${esc(e.id)} · ${esc(e.notes.slice(0,55))}</option>`).join('')}</select></label>
      <label>${T('地图工具','Map tool')}<select name="tool">${tools.map(k=>`<option value="${k}">${names[k]}</option>`).join('')}</select></label>
      <label>${T('实际查看状态（人工记录）','Imagery status (manually checked)')}<select name="availability"><option value="unreviewed">${T('未检查','Not checked')}</option><option value="available">${T('可查看','Available')}</option><option value="unavailable">${T('无影像 / 无法查看','No imagery / unavailable')}</option></select></label>
      ${this.input('original_url',T('实际查看的来源链接','Inspected source URL'),'', 'type="url" required maxlength="2000" placeholder="https://"')}
      <button type="button" class="quiet" data-map-action="parse">${T('从标准 Google 链接填入参数','Prefill from a standard Google URL')}</button>
      ${this.coordinateFields()}
      <div class="camera-fields">${this.input('pano',T('全景 ID（知道时填写）','Panorama ID (if known)'),'', 'maxlength="500"')}
      <div class="map-camera">${this.input('heading',T('朝向 °','Heading °'),'', 'type="number" step="any" min="-180" max="360"')}${this.input('pitch',T('俯仰 °','Pitch °'),'', 'type="number" step="any" min="-90" max="90"')}${this.input('fov',T('水平视野 °','Horizontal FOV °'),'', 'type="number" step="any" min="10" max="100"')}</div></div>
      <div class="form-row">${this.input('captured',T('影像日期：年 / 月 / unknown','Capture date: year / month / unknown'),'unknown','required placeholder="2025 / 2025-10 / unknown"')}${this.input('provider',T('影像提供者 / 署名','Provider / attribution'),'', 'maxlength="1000"')}</div>
      <div class="new-view-fields"><label>${T('核对结果','Observation')}<select name="verdict"><option value="unclear">${T('暂不确定','Unclear')}</option><option value="match">${T('吻合','Match')}</option><option value="contradiction">${T('存在矛盾','Contradiction')}</option></select></label>
      <label>${T('建筑、道路、挡墙、树带、山形或湖岸：哪些吻合 / 不符？','Buildings, roads, walls, trees, terrain or shoreline: what matches / differs?')}<textarea name="notes" rows="3" required></textarea></label>
      <label>${T('对照截图（可选，保存后可做编号双图对照）','Reference capture (optional; enables numbered comparison)')}<input name="image" type="file" accept="image/*"></label></div>
      <p class="hint">${T('全景 ID 可能失效；仅坐标会打开附近全景，可能与原影像不同。拍摄日期与保存时间分别记录，未知月份不补全。','Panorama IDs can expire. Coordinates reopen nearby imagery, which can change. Capture date is separate from save time; missing months stay unknown.')}</p>
      <button type="submit">${T('保存核对视角','Save viewpoint')}</button></form></div>
      <div><h3>2 · ${T('固定候选位置','Pin the candidate location')}</h3><form id="map-location-form">
      ${this.input('shared_url',T('地图分享链接（可选）','Map sharing URL (optional)'),context.shared_url,'type="url" maxlength="2000"')}
      <button type="button" class="quiet" data-map-action="parse">${T('从标准 Google 链接填入位置','Prefill from a standard Google URL')}</button>
      ${this.coordinateFields(context)}${this.input('place_id','Google Place ID',context.place_id,'maxlength="300"')}
      ${this.input('notes',T('位置来源 / 尚未确认之处','Location provenance / uncertainty'),context.notes,'maxlength="2000"')}
      <button type="submit">${T('保存候选位置','Save candidate location')}</button></form>
      <h3>3 · ${T('跨地图核对','Compare across maps')}</h3><div class="map-links">${links.map(([label,url])=>this.link(label,url)).join('')}</div>
      <p class="hint">${T('卫星与地形图以已存坐标为中心；Earth 和 Mapillary 打开工具首页，请定位后保存实际分享链接。不同平台可能使用同源影像，不自动视为独立证据。','Satellite/terrain links use saved coordinates. Earth and Mapillary open their home pages; locate the view and save its actual share link. Multiple platforms can reuse imagery; sources are not automatically independent.')}</p>
      <div class="map-links"><button type="button" class="secondary" data-map-action="kml">${T('导出全部候选 KML → Earth','Export all candidates as KML → Earth')}</button>${active.maps.shortlist_url ? this.link(T('Google 候选清单（有 Place ID 的地点）','Google shortlist (places with IDs)'), active.maps.shortlist_url):''}</div>
      <div class="map-view-log">${active.data.evidence.filter(e=>e.candidate_id===chosen && e.map_view).map(e=>`<article class="evidence-item"><strong>${esc(e.id)} · ${esc(names[e.map_view.tool])}</strong><p>${esc(e.captured || 'unknown')} · ${esc(e.provider || T('未记录署名','Attribution not recorded'))}</p><span class="pill ${esc(e.verdict)}">${esc(e.verdict)}</span> ${this.link(T('重开已存视角','Reopen saved view'),e.map_view.replay_url)}<p class="hint">${esc(this.status(e.map_view.availability))} · ${esc(this.mode(e.map_view.replay_mode))}<br>${T('保存于','Saved at')}: ${esc(e.map_view.saved_at)}</p></article>`).join('')}</div>
      </div></div>`;
    this.cameraState();
  }
  fillView(id) {
    const form = this.container.querySelector('#map-view-form');
    const e = this.active.data.evidence.find(e=>e.id===id), view = e?.map_view || {};
    for (const key of ['latitude','longitude','pano','heading','pitch','fov']) form.elements[key].value = view[key] ?? '';
    form.elements.availability.value = view.availability || 'unreviewed';
    form.elements.tool.value = view.tool || (e?.kind === 'reference' ? 'other' : 'google_streetview');
    form.elements.original_url.value = view.original_url || e?.url || '';
    form.elements.captured.value = e?.captured || 'unknown';
    form.elements.provider.value = e?.provider || '';
    const section = form.querySelector('.new-view-fields');
    section.hidden = !!id;
    section.querySelectorAll('input,select,textarea').forEach(el=>el.disabled=!!id);
    this.cameraState();
  }
  cameraState() {
    const form = this.container.querySelector('#map-view-form'), enabled = form.elements.tool.value === 'google_streetview';
    form.querySelector('.camera-fields').hidden = !enabled;
    for (const key of ['pano','heading','pitch','fov']) {
      form.elements[key].disabled = !enabled;
      if (!enabled) form.elements[key].value = '';
    }
  }
}
