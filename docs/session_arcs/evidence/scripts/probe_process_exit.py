#!/usr/bin/env python3
"""Does shutdown(wait=False) let the PROCESS exit while a worker runs?

Claim under test (#73 r9, OpenAI attacker-smuggle seat): ThreadPoolExecutor
workers are non-daemon and joined by concurrent.futures' atexit hook, so the
caller's raise is immediate but the PROCESS is not.

Run:  python docs/session_arcs/evidence/scripts/probe_process_exit.py
Then compare the printed raise time against the shell's own wall clock:
      time python docs/session_arcs/evidence/scripts/probe_process_exit.py
"""
import concurrent.futures as cf
import time

t0 = time.time()
pool = cf.ThreadPoolExecutor(max_workers=2)
hang = pool.submit(time.sleep, 6)          # stands in for a hung model call
fast = pool.submit(lambda: 1)
try:
    fast.result()
    raise RuntimeError("lens failed")       # the first error
except RuntimeError:
    hang.cancel()                           # cannot cancel a RUNNING future
    pool.shutdown(wait=False)
print(f"raise returned at t={time.time() - t0:.2f}s")
