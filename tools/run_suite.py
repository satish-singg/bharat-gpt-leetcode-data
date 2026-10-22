#!/usr/bin/env python3
"""Run one unittest suite and EXIT, whatever the suite leaves behind.

A release audit saw the combined runner print "Ran 37 tests ... OK" and then not terminate: the interpreter was waiting at
shutdown (a non-daemon thread, a pool finalizer or a child process). This wrapper runs the tests, records any threads or
child processes still alive, kills the children, and leaves with os._exit(), so a finished suite always ends. If the
tests themselves hang, a traceback of every thread is written to the log after SUITE_DUMP_AFTER seconds (diagnosis).

  python tools/run_suite.py test_master test_merge_part2        (module names, run in the current directory)
  python tools/run_suite.py discover -p 'test_*.py'
"""
import faulthandler, os, signal, sys, threading, unittest


def children(pid):
    out = []
    for d in os.listdir("/proc"):
        if d.isdigit():
            try:
                with open(f"/proc/{d}/stat") as f:
                    if int(f.read().rsplit(")", 1)[1].split()[1]) == pid:
                        out.append(int(d))
            except (OSError, IndexError, ValueError):
                pass
    return out


def main():
    # hang diagnosis without a watchdog THREAD (a thread would make every fork() in the tests a fork of a threaded process)
    signal.signal(signal.SIGALRM, lambda *_: faulthandler.dump_traceback(all_threads=True))
    signal.alarm(int(os.environ.get("SUITE_DUMP_AFTER", "840")))
    sys.path.insert(0, os.getcwd())
    prog = unittest.main(module=None, argv=["unittest"] + sys.argv[1:], exit=False)
    ok = prog.result.wasSuccessful() and prog.result.testsRun > 0
    signal.alarm(0)
    threads = [t.name for t in threading.enumerate() if t is not threading.main_thread() and t.is_alive()]
    kids = children(os.getpid()) if os.path.isdir("/proc") else []
    if threads or kids:
        print(f"[run_suite] still alive after the tests: threads {threads}, child processes {kids} (children killed)", file=sys.stderr)
    for k in kids:
        try:
            os.kill(k, signal.SIGKILL)
        except OSError:
            pass
    if os.environ.get("SUITE_JSON"):                           # machine-readable result for the release test report
        import json
        with open(os.environ["SUITE_JSON"], "w") as f:
            json.dump({"ok": ok, "run": prog.result.testsRun, "skipped": len(prog.result.skipped), "failures": len(prog.result.failures),
                       "errors": len(prog.result.errors), "lingering_threads": threads, "lingering_children": kids}, f)
    print(f"[run_suite] {'OK' if ok else 'FAILED'}: {prog.result.testsRun} tests run, {len(prog.result.skipped)} skipped, "
          f"{len(prog.result.failures)} failures, {len(prog.result.errors)} errors", flush=True)
    sys.stdout.flush(); sys.stderr.flush()
    os._exit(0 if ok else 1)


if __name__ == "__main__":
    main()
