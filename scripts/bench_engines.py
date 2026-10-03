# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "requests",
#	  "duckdb",
#	  "polars",
#	  "pandas",
#	  "pyarrow",
#	  "numpy",
#	  "msgspec",
#	  "orjson",
#	  "pydantic",
#	  "hypothesis",
#	  "diskcache",
#	  "tenacity"
#     "rich",
# ]
# ///


"""Benchmark pandas, Polars and DuckDB on the same group-by query.

Question asked of every engine: which 3 users generated the most revenue?
Each timing is the median of 5 runs after one warm-up run.
"""
import json
import statistics
import subprocess
import sys
import time
import duckdb
import numpy as np
import pandas as pd
import polars as pl
SIZES = [1_000_000, 5_000_000, 20_000_000]
FILE = "s.parquet"
RUNS = 5
SQL = f"SELECT user, SUM(amt) AS s FROM '{FILE}' GROUP BY user ORDER BY s DESC LIMIT 3"

def make_file(n_rows: int) -> None:
    """Write a Parquet file with n_rows of fake sales."""
    rng = np.random.default_rng(7)
    frame = pd.DataFrame({
        "user": rng.integers(1, 100_000, n_rows),
        "amt": rng.random(n_rows) * 100,
    })
    frame.to_parquet(FILE)

def run_pandas():
    return pd.read_parquet(FILE).groupby("user").amt.sum().nlargest(3)

def run_polars():
    return (
        pl.scan_parquet(FILE)
        .group_by("user")
        .agg(pl.col("amt").sum())
        .sort("amt", descending=True)
        .head(3)
        .collect()
    )

def run_duckdb():
    return duckdb.sql(SQL).df()

ENGINES = {"pandas": run_pandas, "polars": run_polars, "duckdb": run_duckdb}

def median_seconds(fn) -> float:
    fn()  # warm-up so file cache and imports do not skew run 1
    times = []
    for _ in range(RUNS):
        start = time.perf_counter()
        fn()
        times.append(time.perf_counter() - start)
    return statistics.median(times)

# Each engine runs alone in a fresh process, importing only what it needs,
# so the peak-memory numbers are not polluted by the other libraries.
# VmHWM in /proc is the peak resident memory of that process (reset on exec).
MEMORY_SNIPPETS = {
    "pandas": f"import pandas as pd; pd.read_parquet('{FILE}').groupby('user').amt.sum().nlargest(3)",
    "polars": f"import polars as pl; pl.scan_parquet('{FILE}').group_by('user').agg(pl.col('amt').sum()).sort('amt', descending=True).head(3).collect()",
    "duckdb": f"import duckdb; duckdb.sql(\"{SQL}\").df()",
}

def peak_memory_mb(name: str) -> int:
    code = MEMORY_SNIPPETS[name] + "; print(next(int(l.split()[1]) // 1024 for l in open('/proc/self/status') if l.startswith('VmHWM')))"
    out = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, check=True)
    return int(out.stdout.strip())

def main() -> None:
    results = {}
    for n_rows in SIZES:
        print(f"=== {n_rows:,} rows ===", flush=True)
        make_file(n_rows)
        results[n_rows] = {}
        for name, fn in ENGINES.items():
            results[n_rows][name] = median_seconds(fn)
            print(f"{name:<8}{results[n_rows][name] * 1000:8.1f} ms", flush=True)
    print("=== peak memory, 20M rows ===", flush=True)
    memory = {}
    for name in ENGINES:
        memory[name] = peak_memory_mb(name)
        print(f"{name:<8}{memory[name]:8d} MB", flush=True)
    json.dump(results, open("scale.json", "w"))
    json.dump(memory, open("mem.json", "w"))

if __name__ == "__main__":
    main()