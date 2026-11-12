"""Linux direct-child supervisor. Sampling failure never substitutes for wait().

All writes must stay in the project. Only processes in the new job session,
matching the launching UID and observed (PID, start ticks), may be signalled.
Signal delivery uses pidfds, never an unverified/reused numeric PID.
This is not a service surviving SIGKILL or a power failure; those remain UNKNOWN.
"""
from dataclasses import dataclass, asdict
from pathlib import Path
import json
import ctypes
import os
import re
import resource
import shutil
import signal
import subprocess
import time

ROOT = Path(__file__).resolve().parents[2]

def inside(path):
    path = Path(path).resolve()
    path.relative_to(ROOT)
    return path

@dataclass(frozen=True)
class Identity:
    pid: int
    start_ticks: int
    uid: int
    pgid: int
    sid: int

@dataclass(frozen=True)
class Limits:
    wall_s: float
    rss_bytes: int
    free_disk_bytes: int
    output_bytes: int
    volume_bytes: int
    sample_s: float = .2
    term_grace_s: float = 1.
    max_sampling_failures: int = 3
    log_stall_s: float = 120.
    total_output_bytes: int | None = None

class ProcReader:
    def names(self):
        # Enumeration and per-PID inspection are deliberately separate.
        return os.listdir('/proc')

    def read(self, pid):
        base = Path('/proc') / str(pid)
        first = (base / 'stat').read_text().rsplit(')', 1)[1].split()
        uid = base.stat().st_uid
        second = (base / 'stat').read_text().rsplit(')', 1)[1].split()
        if first[19] != second[19]:
            raise ProcessLookupError('PID identity changed during read')
        ident = Identity(pid, int(second[19]), uid, int(second[2]), int(second[3]))
        return ident, second[0], int(second[21]) * os.sysconf('SC_PAGE_SIZE')

    def sample(self, root):
        races = 0
        members = {}
        for name in self.names():
            if not name.isdigit():
                continue
            try:
                ident, state, rss = self.read(int(name))
            except (OSError, ValueError, IndexError):
                races += 1
                continue
            if ident.uid == root.uid and ident.sid == root.sid:
                members[ident.pid] = (ident, state, rss)
        actual = members.get(root.pid)
        if actual is not None and actual[0] != root:
            return dict(rss_bytes=None, members={}, races=races,
                        issue='root_identity_changed')
        if actual is None:
            return dict(rss_bytes=None, members=members, races=races,
                        issue='root_unreadable')
        return dict(rss_bytes=sum(v[2] for v in members.values()), members=members,
                    races=races, issue=None)


def outcome(returncode, reason=None):
    if returncode is None:
        return dict(exit_kind='UNKNOWN', returncode=None, signal=None)
    if reason == 'wall_timeout':
        kind = 'TIMEOUT'
    elif reason:
        kind = 'CONTROLLED_STOP'
    elif returncode < 0:
        kind = 'SIGNAL'
    else:
        kind = 'NORMAL' if returncode == 0 else 'NONZERO'
    return dict(exit_kind=kind, returncode=returncode,
                signal=-returncode if returncode < 0 else None)


def validate_identity(identity, root):
    return (identity.uid == root.uid and identity.sid == root.sid
            and root.pgid == root.pid and root.sid == root.pid)


def pidfd_open(pid):
    if hasattr(os, 'pidfd_open'):
        return os.pidfd_open(pid)
    libc = ctypes.CDLL(None, use_errno=True)
    function = libc.pidfd_open
    function.argtypes = [ctypes.c_int, ctypes.c_uint]
    function.restype = ctypes.c_int
    value = function(pid, 0)
    if value < 0:
        error = ctypes.get_errno()
        raise OSError(error, os.strerror(error))
    return value


def pidfd_signal(fd, sig):
    if hasattr(signal, 'pidfd_send_signal'):
        return signal.pidfd_send_signal(fd, sig)
    libc = ctypes.CDLL(None, use_errno=True)
    function = libc.pidfd_send_signal
    function.argtypes = [ctypes.c_int, ctypes.c_int, ctypes.c_void_p, ctypes.c_uint]
    function.restype = ctypes.c_int
    if function(fd, int(sig), None, 0) < 0:
        error = ctypes.get_errno()
        raise OSError(error, os.strerror(error))


def send_verified(identity, root, sig, reader):
    """Pin target by pidfd, then validate its birth/session before signalling."""
    if not validate_identity(identity, root):
        return False
    try:
        fd = pidfd_open(identity.pid)
    except ProcessLookupError:
        return False
    try:
        try:
            actual_root, _, _ = reader.read(root.pid)
            if actual_root != root:
                return False
        except (ProcessLookupError, FileNotFoundError):
            pass  # A previously observed child can outlive its reaped launcher.
        actual, state, _ = reader.read(identity.pid)
        if actual != identity or state == 'Z':
            return False
        pidfd_signal(fd, sig)
        return True
    except (ProcessLookupError, FileNotFoundError):
        return False
    finally:
        os.close(fd)


def _file_sizes(directory):
    sizes = []
    for base, dirs, files in os.walk(directory, followlinks=False):
        for name in dirs:
            inside(Path(base) / name)
        for name in files:
            path = inside(Path(base) / name)
            try:
                sizes.append((path, path.stat().st_size))
            except FileNotFoundError:
                # Unknown sample rather than silently imputing zero.
                raise OSError('Output file disappeared during resource sampling')
    return sizes


def resource_snapshot(reader, identity, cwd, log_path, total_dir=None):
    snap = reader.sample(identity)
    files = _file_sizes(cwd)
    snap.update(output_bytes=sum(n for _, n in files),
                largest_volume_bytes=max((n for p, n in files if p.suffix == '.nc'), default=0),
                free_disk_bytes=shutil.disk_usage(cwd).free,
                total_output_bytes=sum(n for _, n in _file_sizes(total_dir)) if total_dir else None)
    # Read only the appended stdout, using an offset held by the supervisor below.
    snap['log_size'] = log_path.stat().st_size
    return snap


def limit_reason(snap, limits):
    checks = [('rss_limit', snap.get('rss_bytes'), limits.rss_bytes, False),
              ('disk_floor', snap.get('free_disk_bytes'), limits.free_disk_bytes, True),
              ('output_limit', snap.get('output_bytes'), limits.output_bytes, False),
              ('volume_limit', snap.get('largest_volume_bytes'), limits.volume_bytes, False),
              ('total_output_limit', snap.get('total_output_bytes'), limits.total_output_bytes, False)]
    for name, value, bound, below in checks:
        if value is not None and bound is not None and (value < bound if below else value > bound):
            return name
    return None


def supervise(argv, cwd, limits, *, env=None, reader=None, sampler=None,
              validator=None, total_dir=None, input_files=None):
    """Run once in a NEW directory; durable JSONL + status, direct wait ownership.

    validator(cwd, final) is a model-specific read-only closed-volume validator.
    Exceptions fail closed without losing wait ownership. No shell, no retry.
    Limits are sampled controls, not OS-wide instantaneous resource guarantees.
    """
    cwd = inside(cwd)
    if any(cwd.iterdir()):
        raise FileExistsError('Supervisor requires a fresh, empty run directory')
    if limits.wall_s <= 0 or limits.sample_s <= 0:
        raise ValueError('Positive timing limits required')
    for name, data in (input_files or {}).items():
        target = inside(cwd / name)
        if target.parent != cwd or target.name in ['stdout.log', 'events.jsonl', 'status.json', 'launch_once.json']:
            raise ValueError('Invalid staged input path')
        with target.open('xb') as staged:
            staged.write(data)
    total_dir = inside(total_dir) if total_dir else None
    reader = reader or ProcReader()
    sampler = sampler or resource_snapshot
    log_path = cwd / 'stdout.log'
    event_path = cwd / 'events.jsonl'
    status_path = cwd / 'status.json'
    reason = None
    rc = None
    identity = None
    proc = None
    known = {}
    records = []
    errors = []
    peak = None
    requested_signal = []
    old_handlers = {}
    start = time.monotonic()
    usage0 = resource.getrusage(resource.RUSAGE_CHILDREN)
    log_offset = 0
    log_tail = ''
    changed = start
    previous_size = 0
    failures = 0
    cleanup_ok = True
    fatal = re.compile(r'(?im)^.*(?:\bNaN\b|\bInf\b|\bERROR\b|MPI_ABORT|bad isec_req).*$', re.M)

    with event_path.open('x', buffering=1) as events, log_path.open('xb') as log:
        def emit(kind, **data):
            event = dict(wall_s=time.monotonic()-start, event=kind, **data)
            try:
                events.write(json.dumps(event, allow_nan=False)+'\n')
                events.flush()
                os.fsync(events.fileno())
            except OSError as exc:
                errors.append(dict(error='journal persistence failed: '+repr(exc)))

        def terminate_group(sig):
            nonlocal cleanup_ok
            if identity is None:
                cleanup_ok = False
                emit('cleanup_refused', reason='No verified launch identity; direct owned child only')
                if proc is not None and proc.returncode is None:
                    proc.terminate() if sig == signal.SIGTERM else proc.kill()
                return
            # Refresh safe session membership; keep prior birth identities if read fails.
            try:
                known.update({pid: v[0] for pid, v in reader.sample(identity)['members'].items()})
            except Exception as exc:
                emit('cleanup_sampling_error', error=repr(exc))
            for member in sorted(known.values(), key=lambda x: x.pid == identity.pid):
                try:
                    sent = send_verified(member, identity, sig, reader)
                    emit('signal_delivery', identity=asdict(member), signal=int(sig), delivered=sent)
                except Exception as exc:
                    cleanup_ok = False
                    emit('signal_error', error=repr(exc))

        def handle(sig, frame):
            requested_signal.append(sig)

        try:
            (cwd / 'launch_once.json').write_text(json.dumps(dict(argv=list(argv), launch_count=1, limits=asdict(limits))))
            proc = subprocess.Popen(list(argv), cwd=cwd, env=env, stdout=log,
                                    stderr=subprocess.STDOUT, start_new_session=True)
            # The owned child remains waitable even if it exits immediately.
            identity, _, _ = reader.read(proc.pid)
            if identity.uid != os.getuid() or identity.pgid != proc.pid or identity.sid != proc.pid:
                raise RuntimeError('Child is not the expected isolated session')
            known[identity.pid] = identity
            emit('launched', identity=asdict(identity), direct_parent=os.getpid())
            for sig in (signal.SIGINT, signal.SIGTERM):
                old_handlers[sig] = signal.signal(sig, handle)
            while True:
                # wait(), not a process-list observation, is authoritative.
                try:
                    rc = proc.wait(timeout=min(limits.sample_s, max(.001, limits.wall_s-(time.monotonic()-start))))
                    emit('wait_returned', returncode=rc)
                    break
                except subprocess.TimeoutExpired:
                    pass
                if requested_signal:
                    reason = 'supervisor_signal_'+str(requested_signal[0])
                elif time.monotonic()-start >= limits.wall_s:
                    reason = 'wall_timeout'
                if reason:
                    break
                try:
                    snap = sampler(reader, identity, cwd, log_path, total_dir)
                    known.update({pid: v[0] for pid, v in snap.pop('members').items()})
                    if snap['rss_bytes'] is None:
                        raise OSError(snap.get('issue', 'Unknown RSS sample'))
                    peak = max(peak or 0, snap['rss_bytes'])
                    records.append(dict(wall_s=time.monotonic()-start, **snap))
                    emit('sample', **snap)
                    reason = limit_reason(snap, limits)
                    size = snap['log_size']
                    if size != previous_size:
                        changed = time.monotonic()
                        previous_size = size
                    if time.monotonic()-changed > limits.log_stall_s:
                        reason = reason or 'log_stall'
                    with log_path.open('rb') as inp:
                        inp.seek(log_offset); chunk = inp.read();log_offset = inp.tell()
                    text = log_tail+chunk.decode('utf8', errors='replace')
                    if fatal.search(text):
                        reason = reason or 'fatal_log_pattern'
                    log_tail = text[-1024:]
                    if validator:
                        validator(cwd, False)
                    failures = 0
                except Exception as exc:
                    failures += 1
                    errors.append(dict(wall_s=time.monotonic()-start, error=repr(exc)))
                    emit('sampling_gap', error=repr(exc), consecutive=failures)
                    if failures >= limits.max_sampling_failures:
                        reason = 'monitoring_unavailable'
                if reason:
                    break
        except Exception as exc:
            reason = 'launcher_error' if proc is None else 'supervisor_error'
            errors.append(dict(wall_s=time.monotonic()-start, error=repr(exc)))
            emit(reason, error=repr(exc))
        finally:
            # No sampler, parser or model-validator exception can skip child wait.
            if proc is not None:
                if rc is None:
                    terminate_group(signal.SIGTERM)
                    try:
                        rc = proc.wait(timeout=limits.term_grace_s)
                    except subprocess.TimeoutExpired:
                        terminate_group(signal.SIGKILL)
                        try:
                            rc = proc.wait(timeout=limits.term_grace_s+1)
                        except Exception as exc:
                            errors.append(dict(error='wait unavailable: '+repr(exc)))
                    except Exception as exc:
                        errors.append(dict(error='wait unavailable: '+repr(exc)))
                # The launcher may exit leaving ranks. Clean only identity-verified members.
                try:
                    remaining = reader.sample(identity)['members'] if identity else {}
                    live = [v[0] for v in remaining.values() if v[1] != 'Z']
                    if live:
                        reason = reason or 'surviving_descendants'
                        known.update({x.pid:x for x in live})
                        terminate_group(signal.SIGTERM)
                        time.sleep(limits.term_grace_s)
                        terminate_group(signal.SIGKILL)
                    remaining = reader.sample(identity)['members'] if identity else {}
                    cleanup_ok &= not any(v[1] != 'Z' for v in remaining.values())
                except Exception as exc:
                    cleanup_ok = False
                    emit('cleanup_unverified', error=repr(exc))
                emit('child_wait_final', returncode=rc, cleanup_verified=cleanup_ok)
            for sig, handler in old_handlers.items():
                signal.signal(sig, handler)
        if proc is not None and rc == 0 and reason is None:
            try:
                text = log_path.read_text(errors='replace')
                if fatal.search(text):
                    reason = 'fatal_log_pattern'
                final_sizes = _file_sizes(cwd)
                final_snap = dict(output_bytes=sum(n for _, n in final_sizes),
                                  largest_volume_bytes=max((n for p,n in final_sizes if p.suffix=='.nc'),default=0),
                                  free_disk_bytes=shutil.disk_usage(cwd).free,
                                  total_output_bytes=sum(n for _,n in _file_sizes(total_dir)) if total_dir else None)
                reason = reason or limit_reason(final_snap, limits)
                if validator:
                    validator(cwd, True)
            except Exception as exc:
                reason = 'final_validation_error'
                errors.append(dict(error=repr(exc)))
        usage = resource.getrusage(resource.RUSAGE_CHILDREN)
        exit_info = outcome(rc, reason)
        if proc is None:
            exit_info['exit_kind'] = 'LAUNCH_ERROR'
        qualification = 'PARTIAL' if rc is None or errors or not cleanup_ok else ('PASS' if rc == 0 and reason is None else 'FAIL')
        status = dict(**exit_info, qualification=qualification, stop_reason=reason,
                      elapsed_s=time.monotonic()-start, identity=asdict(identity) if identity else None,
                      wait_source='direct subprocess.Popen.wait' if rc is not None else 'UNKNOWN',
                      peak_sampled_tree_rss_bytes=peak, samples=records, gaps=errors,
                      cleanup_verified=cleanup_ok, children_cpu_user_s=usage.ru_utime-usage0.ru_utime,
                      children_cpu_system_s=usage.ru_stime-usage0.ru_stime,
                      resource_definition='sampled same-UID new session; shared RSS counted repeatedly; no continuous-peak guarantee')
        with status_path.open('x') as out:
            json.dump(status, out, indent=2, allow_nan=False);out.flush();os.fsync(out.fileno())
        return status
