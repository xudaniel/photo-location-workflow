"""Client state regression without launching a browser or requiring Node at runtime."""

from pathlib import Path
import shutil
import subprocess

import pytest


def test_background_completion_enables_start_while_viewing_history():
    node = shutil.which('node')
    if not node:
        pytest.skip('Node is optional; CI checks client state when available.')
    script = Path(__file__).parents[1]/'src/photo_location_workflow/static/geosleuth.js'
    code = r'''
import fs from 'node:fs';
import assert from 'node:assert/strict';
const {GeoWorkbench} = await import('data:text/javascript;base64,' + fs.readFileSync(process.argv[1]).toString('base64'));
const start = {disabled:true}, option={value:'new',textContent:''};
const container = {querySelector:selector=>selector.includes('geo-run')?{options:[option]}:start};
const history = {id:'old',status:'completed',result_token:'same',created_at:'earlier'};
const latest = {id:'new',status:'completed',created_at:'now'};
const value={configured:true,runs:[history,latest]};
const workbench = new GeoWorkbench({container,request:async()=>value});
Object.assign(workbench,{caseId:'demo',selected:'old',language:'en',renderKey:'old:false:same',
  value:{configured:true,runs:[history,{...latest,status:'processing'}]}});
workbench.drawProgress=()=>{};
workbench.render=()=>{throw new Error('Do not discard the history form draft.');};
workbench.poll=()=>{};
await workbench.reload();
assert.equal(start.disabled,false,'Completed background work must re-enable start while history is selected.');
assert.match(option.textContent,/Results saved/);
'''
    result = subprocess.run([node, '--input-type=module', '-e', code, str(script)],
                            capture_output=True, text=True, timeout=15)
    assert result.returncode == 0, result.stderr
