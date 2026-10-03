# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "requests",
#     "msgspec",
#     "orjson",
#     "pydantic",
#     "rich",
# ]
# ///

"""
Compare JSON decode and encode speed on 200,000 records.
Decoders: json, orjson, msgspec (typed + validated), pydantic v2 (validated).
Encoders: json, orjson, msgspec.
"""
import json
import time
import statistics

import orjson
import msgspec

from pydantic import BaseModel, TypeAdapter

N_RECORDS = 200_000
RUNS = 7

class UserMsgspec(msgspec.Struct):
    id: int
    name: str
    tags: list[str]
    score: float

class UserPydantic(BaseModel):
    id: int
    name: str
    tags: list[str]
    score: float

def median_seconds(fn) -> float:
    fn()  # warm-up
    times = []
    for _ in range(RUNS):
        start = time.perf_counter()
        fn()
        times.append(time.perf_counter() - start)
    return statistics.median(times)

def build_rows() -> list[dict]:
    return [
        {"id": i, "name": f"user{i}", "tags": ["a", "b", "c"], "score": i / 7}
        for i in range(N_RECORDS)
    ]

def main() -> None:
    rows = build_rows()
    raw = json.dumps(rows).encode()
    adapter = TypeAdapter(list[UserPydantic])
    typed = msgspec.json.decode(raw, type=list[UserMsgspec])
    decode = {
        "json.loads": median_seconds(lambda: json.loads(raw)),
        "orjson.loads": median_seconds(lambda: orjson.loads(raw)),
        "msgspec typed": median_seconds(lambda: msgspec.json.decode(raw, type=list[UserMsgspec])),
        "pydantic v2 typed": median_seconds(lambda: adapter.validate_json(raw)),
    }
    encode = {
        "json.dumps": median_seconds(lambda: json.dumps(rows)),
        "orjson.dumps": median_seconds(lambda: orjson.dumps(rows)),
        "msgspec encode": median_seconds(lambda: msgspec.json.encode(typed)),
    }

    print(f"=== decode {N_RECORDS:,} records ===")
    for name, seconds in decode.items():
        print(f"{name:<20}{seconds * 1000:8.1f} ms")

    print(f"=== encode {N_RECORDS:,} records ===")
    for name, seconds in encode.items():
        print(f"{name:<20}{seconds * 1000:8.1f} ms")

    # Validation is the other half of the story: bad data must be rejected.
    bad = b'{"id": "not-a-number", "name": "x", "tags": [], "score": 1.0}'
    try:
        msgspec.json.decode(bad, type=UserMsgspec)
    except msgspec.ValidationError as err:
        print("msgspec rejected bad data:", err)
    json.dump(decode, open("js.json", "w"))
    json.dump(encode, open("enc.json", "w"))

if __name__ == "__main__":
    main()