"""Bounded subprocess logs, process-tree cancellation and OS-owned workspace locks."""

from contextlib import contextmanager
import json
import os
from pathlib import Path
import signal
import subprocess
import tempfile
import threading
import time

LOG_LIMIT = 100_000
_held = threading.local()


class TaskStopped(ValueError):
    def __init__(self, reason):
        self.reason = reason
        super().__init__(f"Task {reason}; saved checkpoints and logs are retained.")


def atomic_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    name = None
    try:
        with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', dir=path.parent,
                                         prefix='.checkpoint-', delete=False) as stream:
            name = stream.name
            json.dump(value, stream, ensure_ascii=False, indent=2)
            stream.write('\n')
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(name, path)
    finally:
        if name and os.path.exists(name):
            os.unlink(name)


@contextmanager
def workspace_lock(workspace):
    """Nonblocking OS lock; releasing a crashed process needs no stale-file deletion."""
    root = Path(workspace).resolve()
    root.parent.mkdir(parents=True, exist_ok=True)
    with (root.parent / (root.name + '.lock')).open('a+b') as stream:
        if stream.tell() == 0:
            stream.write(b'0')
            stream.flush()
        stream.seek(0)
        try:
            if os.name == 'nt':
                import msvcrt
                msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(stream.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError as exc:
            raise ValueError('Workspace is busy in another task or process.') from exc
        held = getattr(_held, 'fds', [])
        _held.fds = held + [stream.fileno()]
        try:
            yield
        finally:
            _held.fds = held
            if os.name == 'nt':
                stream.seek(0)
                msvcrt.locking(stream.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(stream.fileno(), fcntl.LOCK_UN)


class WindowsJob:
    """Kill-on-close containment, including when the workbench itself crashes."""
    def __init__(self):
        import ctypes as ct
        from ctypes import wintypes as wt

        class Basic(ct.Structure):
            _fields_ = [('process_time', ct.c_longlong), ('job_time', ct.c_longlong),
                        ('flags', wt.DWORD), ('minimum', ct.c_size_t), ('maximum', ct.c_size_t),
                        ('active_limit', wt.DWORD), ('affinity', ct.c_size_t),
                        ('priority', wt.DWORD), ('scheduling', wt.DWORD)]

        class IO(ct.Structure):
            _fields_ = [(name, ct.c_ulonglong) for name in ('reads', 'writes', 'other', 'read_bytes', 'write_bytes', 'other_bytes')]

        class Limits(ct.Structure):
            _fields_ = [('basic', Basic), ('io', IO), ('process_memory', ct.c_size_t),
                        ('job_memory', ct.c_size_t), ('peak_process', ct.c_size_t), ('peak_job', ct.c_size_t)]

        self.ct = ct
        self.api = ct.WinDLL('kernel32', use_last_error=True)
        self.api.CreateJobObjectW.argtypes = [wt.LPVOID, wt.LPCWSTR]
        self.api.CreateJobObjectW.restype = wt.HANDLE
        self.api.SetInformationJobObject.argtypes = [wt.HANDLE, ct.c_int, wt.LPVOID, wt.DWORD]
        self.api.SetInformationJobObject.restype = wt.BOOL
        self.api.AssignProcessToJobObject.argtypes = [wt.HANDLE, wt.HANDLE]
        self.api.AssignProcessToJobObject.restype = wt.BOOL
        self.api.TerminateJobObject.argtypes = [wt.HANDLE, wt.UINT]
        self.api.TerminateJobObject.restype = wt.BOOL
        self.api.CloseHandle.argtypes = [wt.HANDLE]
        self.api.CloseHandle.restype = wt.BOOL
        self.handle = self.api.CreateJobObjectW(None, None)
        if not self.handle:
            raise ct.WinError(ct.get_last_error())
        limits = Limits()
        limits.basic.flags = 0x2000  # JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
        if not self.api.SetInformationJobObject(self.handle, 9, ct.byref(limits), ct.sizeof(limits)):
            self.close()
            raise ct.WinError(ct.get_last_error())

    def attach(self, process):
        if not self.api.AssignProcessToJobObject(self.handle, int(process._handle)):
            raise self.ct.WinError(self.ct.get_last_error())

    def stop(self):
        if not self.api.TerminateJobObject(self.handle, 1):
            raise self.ct.WinError(self.ct.get_last_error())

    def close(self):
        if self.handle:
            self.api.CloseHandle(self.handle)
            self.handle = None


def _stop_tree(process):
    if os.name == 'nt':
        # Keep the parent alive until taskkill has enumerated its descendants.
        subprocess.run(['taskkill', '/PID', str(process.pid), '/T', '/F'],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=10)
    else:
        try:
            os.killpg(process.pid, signal.SIGTERM)
        except ProcessLookupError:
            return
        except PermissionError:
            if process.poll() is None:
                raise
            return  # macOS may retain an already-dead group briefly.
        time.sleep(.15)
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        except PermissionError:
            if process.poll() is None:
                raise


def run_process(command, *, cwd, env, log_path, timeout, cancel=None):
    """Drain output continuously; bounded RAM/disk even for an unlimited producer."""
    if cancel and cancel.is_set():
        raise TaskStopped('cancelled')
    log_path = Path(log_path)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    log_path.write_bytes(b'')
    options = {'start_new_session': True} if os.name != 'nt' else {
        'creationflags': subprocess.CREATE_NEW_PROCESS_GROUP}
    if os.name != 'nt':
        # A surviving tool retains the workspace lock after a server crash.
        options['pass_fds'] = tuple(getattr(_held, 'fds', []))
    job = WindowsJob() if os.name == 'nt' else None
    try:
        process = subprocess.Popen(command, cwd=cwd, env=env, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                                   stderr=subprocess.STDOUT, **options)
        if job:
            job.attach(process)
    except BaseException:
        if 'process' in locals():
            _stop_tree(process)
            process.wait(timeout=10)
            process.stdout.close()
        if job:
            job.close()
        raise
    errors = []

    def drain():
        tail = bytearray()
        try:
            with log_path.open('r+b', buffering=0) as stream:
                while True:
                    chunk = os.read(process.stdout.fileno(), 8192)
                    if not chunk:
                        break
                    tail.extend(chunk)
                    del tail[:-LOG_LIMIT]
                    stream.seek(0)
                    stream.write(tail)
                    stream.truncate()
        except OSError as exc:
            errors.append(exc)

    reader = threading.Thread(target=drain, daemon=True, name='photo-task-log')
    reader.start()
    deadline = time.monotonic() + timeout
    stopped = None
    try:
        while process.poll() is None:
            if cancel and cancel.is_set():
                stopped = 'cancelled'
                break
            if time.monotonic() >= deadline:
                stopped = 'timed_out'
                break
            if errors:
                raise OSError('Could not write the task log.')
            time.sleep(.04)
    except KeyboardInterrupt:
        stopped = 'cancelled'
    finally:
        # On POSIX this also terminates descendants left behind by an exited parent.
        if job:
            try:
                job.stop()
            finally:
                job.close()
        else:
            _stop_tree(process)
        process.wait(timeout=10)
        reader.join(timeout=3)
        process.stdout.close()
    if reader.is_alive() or errors:
        raise OSError('Task output could not be drained completely.')
    if stopped:
        raise TaskStopped(stopped)
    return subprocess.CompletedProcess(command, process.returncode,
                                       log_path.read_bytes().decode('utf-8', errors='replace'))
