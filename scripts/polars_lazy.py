# /// script
# requires-python = ">=3.12"
# dependencies = [
#	  "polars",
#	  "numpy",
#     "rich",
# ]
# ///

"""
Show what Polars' lazy engine does with a query before running it.

We join orders to users, then filter to one country AFTER the join. A naive
engine joins everything first. Polars pushes the filter down so far fewer
rows are joined. explain() prints the plan so we can see it.
"""
import time
import numpy as np
import polars as pl

rng = np.random.default_rng(3)
N_USERS = 200_000
N_ORDERS = 3_000_000

users = pl.DataFrame({
    "user_id": np.arange(N_USERS),
    "country": rng.choice(["PK", "US", "DE", "IN", "BR"], N_USERS),
})

orders = pl.DataFrame({
    "user_id": rng.integers(0, N_USERS, N_ORDERS),
    "amount": rng.random(N_ORDERS) * 100,
})

query = (
    orders.lazy()
    .join(users.lazy(), on="user_id")
    .filter(pl.col("country") == "PK")
    .group_by("country")
    .agg(pl.col("amount").sum().alias("revenue"))
)
print("=== optimized plan (what Polars will really run) ===")
print(query.explain())

def timed(label: str, **flags) -> pl.DataFrame:
    start = time.perf_counter()
    result = query.collect(**flags)
    print(f"{label:<28}{(time.perf_counter() - start) * 1000:8.1f} ms")
    return result

timed("warm-up")
timed("optimizations ON")
timed("optimizations OFF", optimizations=pl.QueryOptFlags.none())
print(query.collect())