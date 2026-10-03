# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "functools",
#	  "diskcache",
#     "rich",
# ]
# ///

"""
Show why diskcache beats functools.lru_cache for slow, repeatable work.
fake_api() stands in for a slow HTTP call (0.8 s each). We call it for five
inputs, twice, then again from a brand-new Python process.
"""
import functools
import json
import subprocess
import sys
import time
import diskcache

DELAY = 0.8
INPUTS = range(5)
cache = diskcache.Cache("/tmp/dc_demo_final")
cache.clear()

def fake_api(x: int) -> int:
    time.sleep(DELAY)
    return x * x

@cache.memoize()
def disk_cached(x: int) -> int:
    return fake_api(x)

@functools.lru_cache(maxsize=None)
def memory_cached(x: int) -> int:
    return fake_api(x)

def timed_ms(fn) -> float:
    start = time.perf_counter()
    for i in INPUTS:
        fn(i)
    return (time.perf_counter() - start) * 1000

# Code run in a fresh process: both caches get one chance to help.
CHILD = """
import time, diskcache
cache = diskcache.Cache('/tmp/dc_demo_final')
@cache.memoize()
def disk_cached(x):
    time.sleep(0.8); return x * x
t = time.perf_counter(); [disk_cached(i) for i in range(5)]
print(round((time.perf_counter() - t) * 1000, 2))
"""

def main() -> None:
    first = timed_ms(disk_cached)
    second = timed_ms(disk_cached)
    print(f"diskcache run 1 (cold):   {first:9.2f} ms")
    print(f"diskcache run 2 (warm):   {second:9.2f} ms")
    lru_first = timed_ms(memory_cached)
    lru_second = timed_ms(memory_cached)
    print(f"lru_cache run 1 (cold):   {lru_first:9.2f} ms")
    print(f"lru_cache run 2 (warm):   {lru_second:9.2f} ms")
    print("=== new Python process ===")
    out = subprocess.run([sys.executable, "-c", CHILD], capture_output=True, text=True, check=True)
    restart = float(out.stdout.strip())
    print(f"diskcache after restart:  {restart:9.2f} ms")
    print("lru_cache after restart:  cold again (memory is gone)")
    json.dump({"cold": first, "warm": second, "restart": restart}, open("cache.json", "w"))

if __name__ == "__main__":
    main()