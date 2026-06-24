#!/usr/bin/env python3
"""mutation_lock.py — deep-init's half of the torn-tree commit guard (single source of truth).

The mutation meta-harness (tests-fixtures-v1/_mutation_harness.py) plants a known-bad edit, runs the
suite, then RESTORES the file. If a commit (agent or human) lands WHILE a mutation is planted, it
snapshots a TORN TREE — broken content gets committed. This corrupted 3 releases before the fix.

This module is the PRODUCER + the liveness oracle for both guards:
  - PRODUCER:  the mutation harness calls acquire() at startup → writes <root>/.oss-kit/.mutation-running
               with this process's PID on the FIRST line, and registers cleanup on atexit AND on
               SIGINT/SIGTERM (a `finally` does NOT run on SIGTERM/kill — exactly how the 3rd recurrence
               stranded a run).
  - READER:    is_blocking()/--check answers "is a file-mutating run in flight?" READ-ONLY (never deletes).
               FAIL CLOSED — an unparseable/empty PID BLOCKS; only a PROVABLY-dead PID auto-clears (so a
               crashed run can't wedge commits forever).

Contract pinned to oss-kit's commit-guard.sh so both guards agree byte-for-byte:
  - lock path: <git-toplevel>/.oss-kit/.mutation-running  (override: $OSS_KIT_MUTATION_LOCK_PATH)
  - PID parse: first line, ASCII digits only (matches `head -1 | tr -dc '0-9'`)
  - blocking exit code: 2     (skip the whole guard with $OSS_KIT_NO_MUTATION_LOCK=1)

Windows note (THE key correctness point): a bash `kill -0 <pid>` reader CANNOT see a Python os.getpid()
process — os.getpid() returns the WINDOWS pid, but MSYS `kill` uses the MSYS pid namespace, so it reports
a live process as dead. So liveness here is namespace-correct: ctypes OpenProcess on Windows (NEVER
os.kill on Windows — CPython maps os.kill→TerminateProcess and would actually KILL the process), os.kill(,0)
on POSIX. A hard TerminateProcess/kill can't run the SIGTERM handler on Windows — acceptable, because the
reader auto-clears a provably-dead PID.

CLI:  python tools/mutation_lock.py --check   # exit 2 if a live run holds the lock, else 0
"""
from __future__ import annotations

import argparse
import atexit
import os
import signal
import subprocess
import sys

LOCK_RELPATH = ".oss-kit/.mutation-running"      # under the git toplevel; matches oss-kit's commit-guard
ENV_PATH = "OSS_KIT_MUTATION_LOCK_PATH"          # path override (the seam shared with oss-kit + the §73 gate)
ENV_DISABLE = "OSS_KIT_NO_MUTATION_LOCK"         # set to "1" to disable the guard entirely
BLOCK_EXIT = 2                                    # oss-kit's commit-guard convention


# ── path + PID contract ──────────────────────────────────────────────────────
def _git_toplevel() -> str:
    try:
        out = subprocess.run(["git", "rev-parse", "--show-toplevel"],
                             capture_output=True, text=True, encoding="utf-8", errors="replace")
        if out.returncode == 0 and out.stdout.strip():
            return out.stdout.strip()
    except (OSError, subprocess.SubprocessError):
        pass
    return os.getcwd()


def _resolve_path(lock_path=None) -> str:
    """Resolve the lock path: an explicit arg wins (the gate passes temp paths), then $OSS_KIT_MUTATION_LOCK_PATH,
    then <git-toplevel>/.oss-kit/.mutation-running."""
    if lock_path:
        return str(lock_path)
    env = os.environ.get(ENV_PATH)
    if env:
        return env
    return os.path.join(_git_toplevel(), *LOCK_RELPATH.split("/"))


def _read_text(path: str) -> str:
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        return f.read()


def _first_line_pid(text: str):
    """First line, ASCII digits only, as an int (or None). Mirrors oss-kit's `head -1 | tr -dc '0-9'` exactly —
    so a CRLF-terminated or whitespace-padded PID parses identically on both sides of the contract."""
    lines = text.splitlines()
    first = lines[0] if lines else ""
    digits = "".join(ch for ch in first if ch in "0123456789")
    return int(digits) if digits else None


# ── liveness (PID-namespace-correct) ─────────────────────────────────────────
def _is_alive_windows(pid: int) -> bool:
    import ctypes
    from ctypes import wintypes
    PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
    SYNCHRONIZE = 0x00100000          # WaitForSingleObject needs this; QUERY_LIMITED alone does not grant it
    WAIT_OBJECT_0 = 0x00000000        # signaled = the process has exited
    STILL_ACTIVE = 259                # GetExitCodeProcess sentinel for a running process (ambiguous if a real exit code)
    ERROR_INVALID_PARAMETER = 87      # no such pid → dead
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel32.OpenProcess.restype = wintypes.HANDLE
    kernel32.OpenProcess.argtypes = (wintypes.DWORD, wintypes.BOOL, wintypes.DWORD)
    kernel32.GetExitCodeProcess.restype = wintypes.BOOL
    kernel32.GetExitCodeProcess.argtypes = (wintypes.HANDLE, ctypes.POINTER(wintypes.DWORD))
    kernel32.WaitForSingleObject.restype = wintypes.DWORD
    kernel32.WaitForSingleObject.argtypes = (wintypes.HANDLE, wintypes.DWORD)
    kernel32.CloseHandle.argtypes = (wintypes.HANDLE,)
    # Request SYNCHRONIZE too (lets WaitForSingleObject disambiguate a genuine 259 exit); fall back without it.
    handle = kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION | SYNCHRONIZE, False, pid)
    if not handle:
        handle = kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
    if not handle:
        err = ctypes.get_last_error()
        if err == ERROR_INVALID_PARAMETER:
            return False              # provably dead (no such pid)
        return True                   # ACCESS_DENIED or anything else → fail closed (assume alive)
    try:
        code = wintypes.DWORD()
        if not kernel32.GetExitCodeProcess(handle, ctypes.byref(code)):
            return True               # query failed → fail closed
        if code.value != STILL_ACTIVE:
            return False              # has a real exit code → exited
        # STILL_ACTIVE (259) is ambiguous (a process CAN exit with 259); confirm via the wait handle.
        if kernel32.WaitForSingleObject(handle, 0) == WAIT_OBJECT_0:
            return False              # actually signaled/exited
        return True                   # WAIT_TIMEOUT (alive) or wait unavailable → fail closed
    finally:
        kernel32.CloseHandle(handle)


def _is_alive(pid) -> bool:
    """True if pid names a live process. Fail-closed (True) on anything we can't disprove."""
    if pid is None or pid <= 0:
        return True                   # never os.kill(0,...) (a whole process group) — treat as alive/blocking
    if os.name == "nt":
        return _is_alive_windows(pid)
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False                  # ESRCH — no such process
    except PermissionError:
        return True                   # EPERM — exists, just not ours
    except OSError:
        return True                   # any other error → fail closed
    return True


# ── reader (READ-ONLY — never deletes a lock) ────────────────────────────────
def is_blocking(lock_path=None) -> bool:
    """True iff a commit should be BLOCKED: a lock file exists and a live (or unverifiable) PID holds it.
    READ-ONLY — 'auto-clear' means 'do not block', NOT 'delete the file' (only acquire()'s own handlers delete)."""
    path = _resolve_path(lock_path)
    if not os.path.exists(path):
        return False
    try:
        text = _read_text(path)
    except OSError:
        return True   # an existing lock we cannot read → fail closed
    pid = _first_line_pid(text)
    if pid is None:
        return True   # fail-closed: an unparseable or empty PID BLOCKS — a torn lock must never pass a commit
    if _is_alive(pid):
        return True   # a live holder is running the mutation harness — BLOCK the commit
    return False      # the PID is provably dead — auto-clear (a crashed run cannot wedge commits forever)


# ── producer (writer + cleanup) ──────────────────────────────────────────────
def _write_pid(path: str) -> str:
    """Write THIS process's PID as the first line of `path` (LF-terminated), creating the dir."""
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(f"{os.getpid()}\n")   # PID as the FIRST line — the exact contract oss-kit's commit-guard reads
    return path


def _write_lock(root) -> str:
    """Pure root-relative writer (no env override): <root>/.oss-kit/.mutation-running. Used by the §73 gate."""
    return _write_pid(os.path.join(str(root), *LOCK_RELPATH.split("/")))


def _lock_path_for(root) -> str:
    """Where acquire() writes — honors $OSS_KIT_MUTATION_LOCK_PATH so producer + reader agree under the seam."""
    env = os.environ.get(ENV_PATH)
    return env if env else os.path.join(str(root), *LOCK_RELPATH.split("/"))


def _register_cleanup(path: str) -> None:
    """Remove OUR lock on atexit AND on SIGINT/SIGTERM — a `finally` alone misses SIGTERM/kill."""
    def _cleanup():
        try:
            if os.path.exists(path) and _first_line_pid(_read_text(path)) == os.getpid():
                os.remove(path)   # only ever delete the lock WE wrote (it carries our PID)
        except OSError:
            pass

    atexit.register(_cleanup)

    def _on_signal(signum, frame):
        _cleanup()
        signal.signal(signum, signal.SIG_DFL)
        try:
            os.kill(os.getpid(), signum)   # re-raise with default disposition → preserve killed-by-signal status
        except Exception:
            raise SystemExit(128 + signum)

    for _sig in (signal.SIGINT, signal.SIGTERM):
        try:
            signal.signal(_sig, _on_signal)
        except (ValueError, OSError):
            pass   # not in the main thread, or the signal is unsupported here — atexit still covers normal exit


def acquire(root):
    """Acquire the mutation lock for THIS run. Refuses to start if a foreign LIVE PID already holds it (that would
    be the concurrent-run footgun this whole feature prevents); overwrites an absent/dead/own-stale lock."""
    if os.environ.get(ENV_DISABLE) == "1":
        return None
    target = _lock_path_for(root)
    if os.path.exists(target):
        try:
            holder = _first_line_pid(_read_text(target))
        except OSError:
            holder = None
        if holder is not None and holder != os.getpid() and _is_alive(holder):
            sys.stderr.write(
                f"ABORT: another file-mutating run holds the lock (pid {holder}).\n"
                f"  Lock: {target}\n"
                f"  Wait for it to finish, or if NO run is active the lock is stale; remove it: rm \"{target}\"\n")
            raise SystemExit(BLOCK_EXIT)
    _write_pid(target)
    _register_cleanup(target)
    return target


# ── CLI (the pre-commit hook calls `--check`) ────────────────────────────────
def _main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="deep-init mutation-lock guard")
    ap.add_argument("--check", action="store_true",
                    help="exit 2 if a live mutation-lock is held (the pre-commit guard), else 0")
    args = ap.parse_args(argv)
    if os.environ.get(ENV_DISABLE) == "1":
        return 0
    path = _resolve_path(None)
    if args.check:
        if is_blocking(path):
            sys.stderr.write(
                "ABORT: a file-mutating test run is in flight; wait for it.\n"
                f"  Lock: {path}\n"
                f"  If NO run is active, this lock is stale; remove it: rm \"{path}\"\n")
            return BLOCK_EXIT
        return 0
    print("blocking" if is_blocking(path) else "clear")
    return 0


if __name__ == "__main__":
    raise SystemExit(_main())
