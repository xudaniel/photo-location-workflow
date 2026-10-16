import os
from pathlib import Path
import subprocess
import sys
import threading
import time

import pytest

from photo_location_workflow.tasks import LOG_LIMIT, TaskStopped, run_process, workspace_lock


def wait_for(test, timeout=8):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if test():
            return
        time.sleep(.03)
    raise AssertionError('Expected state was not reached.')


def test_real_process_output_is_streamed_and_bounded(tmp_path):
    result = run_process([sys.executable, '-c', "import sys; sys.stdout.buffer.write(b'x'*2000000); print('final marker')"],
                         cwd=tmp_path, env=os.environ, log_path=tmp_path / 'out.log', timeout=8)
    assert result.returncode == 0
    assert 'final marker' in result.stdout
    assert (tmp_path / 'out.log').stat().st_size <= LOG_LIMIT
    assert len(result.stdout.encode()) <= LOG_LIMIT


@pytest.mark.parametrize('reason', ['cancelled', 'timed_out'])
def test_stop_cleans_actual_child_process_and_retains_live_log(tmp_path, reason):
    child = "from pathlib import Path; import time\np=Path('heartbeat')\nwhile True:\n p.write_text(str(time.time_ns())); time.sleep(.03)"
    parent = f"import subprocess,sys,time; subprocess.Popen([sys.executable,'-c',{child!r}]); print('running',flush=True); time.sleep(60)"
    cancel = threading.Event()
    errors = []
    log = tmp_path / 'live.log'

    def run():
        try:
            run_process([sys.executable, '-c', parent], cwd=tmp_path, env=os.environ,
                        log_path=log, timeout=1.5 if reason == 'timed_out' else 10, cancel=cancel)
        except TaskStopped as exc:
            errors.append(exc.reason)

    thread = threading.Thread(target=run)
    thread.start()
    try:
        wait_for(lambda: log.is_file() and 'running' in log.read_text() and (tmp_path / 'heartbeat').is_file())
        assert thread.is_alive()  # The log is visible before process completion.
        if reason == 'cancelled':
            cancel.set()
        thread.join(timeout=12)
        assert not thread.is_alive()
        assert errors == [reason]
        heartbeat = (tmp_path / 'heartbeat').read_bytes()
        time.sleep(.2)
        assert (tmp_path / 'heartbeat').read_bytes() == heartbeat
    finally:
        cancel.set()
        thread.join(timeout=12)


def test_workspace_lock_is_cross_process_and_releases_after_exit(tmp_path):
    workspace = tmp_path / 'work'
    code = "from photo_location_workflow.tasks import workspace_lock; from pathlib import Path; import time\nwith workspace_lock('work'):\n Path('ready').write_text('yes'); time.sleep(20)"
    proc = subprocess.Popen([sys.executable, '-c', code], cwd=tmp_path)
    try:
        wait_for(lambda: (tmp_path / 'ready').exists())
        with pytest.raises(ValueError, match='busy'):
            with workspace_lock(workspace):
                pytest.fail('A second writer acquired the lock.')
    finally:
        proc.kill()
        proc.wait(timeout=5)
    with workspace_lock(workspace):
        pass


def test_pre_cancelled_task_never_launches(tmp_path):
    event = threading.Event()
    event.set()
    with pytest.raises(TaskStopped, match='cancelled'):
        run_process([sys.executable, '-c', "open('should-not-exist','w').close()"],
                    cwd=tmp_path, env=os.environ, log_path=tmp_path / 'out.log', timeout=5, cancel=event)
    assert not (tmp_path / 'should-not-exist').exists()


def test_controller_crash_cannot_leave_an_unlocked_writer(tmp_path):
    child = "from pathlib import Path; import time\np=Path('heartbeat')\nend=time.monotonic()+2\nwhile time.monotonic()<end:\n p.write_text(str(time.time_ns())); time.sleep(.03)\nPath('done').write_text('yes')"
    controller = ("from photo_location_workflow.tasks import workspace_lock, run_process; "
                  "import os,sys\nwith workspace_lock('work'):\n "
                  f"run_process([sys.executable,'-c',{child!r}],cwd='.',env=os.environ,log_path='crash.log',timeout=8)")
    proc = subprocess.Popen([sys.executable, '-c', controller], cwd=tmp_path)
    try:
        wait_for(lambda: (tmp_path / 'heartbeat').exists())
        proc.kill()
        proc.wait(timeout=5)
        if os.name == 'nt':
            time.sleep(.2)
            heartbeat = (tmp_path / 'heartbeat').read_bytes()
            time.sleep(.2)
            assert (tmp_path / 'heartbeat').read_bytes() == heartbeat
        else:
            with pytest.raises(ValueError, match='busy'):
                with workspace_lock(tmp_path / 'work'):
                    pytest.fail('An orphan writer lost its workspace protection.')
            wait_for(lambda: (tmp_path / 'done').exists())
        # The lock is released once the retained POSIX tool ends / Windows job dies.
        def available():
            try:
                with workspace_lock(tmp_path / 'work'):
                    return True
            except ValueError:
                return False
        wait_for(available)
    finally:
        if proc.poll() is None:
            proc.kill()
        proc.wait(timeout=5)
