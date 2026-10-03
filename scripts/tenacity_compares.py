"""tenacity demo: retry a flaky API with exponential backoff.

FlakyService fails the first three calls with a ConnectionError. The
decorator retries with waits of 0.5 s, 1 s and 2 s. A ValueError (a bug in
our own code, not a network blip) must NOT be retried.
"""
import logging
import sys
import time
from tenacity import (
    before_sleep_log,
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)
logging.basicConfig(
    stream=sys.stdout,
    level=logging.INFO,
    format="%(asctime)s.%(msecs)03d  %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("api")

class FlakyService:
    def __init__(self, failures: int) -> None:
        self.failures = failures
        self.calls = 0
    def get_prices(self) -> dict:
        self.calls += 1
        log.info("attempt %d: calling API", self.calls)
        if self.calls <= self.failures:
            raise ConnectionError("503 upstream unavailable")
        return {"BTC": 64000}

service = FlakyService(failures=3)

@retry(
    stop=stop_after_attempt(5),
    wait=wait_exponential(multiplier=0.5, max=4),
    retry=retry_if_exception_type(ConnectionError),
    before_sleep=before_sleep_log(log, logging.WARNING),
)
def fetch_prices() -> dict:
    return service.get_prices()

@retry(stop=stop_after_attempt(5), retry=retry_if_exception_type(ConnectionError))
def parse_payload() -> None:
    raise ValueError("bad payload")  # a bug, retrying will never fix it

def main() -> None:
    start = time.perf_counter()
    prices = fetch_prices()
    elapsed = time.perf_counter() - start
    print(f"{prices} after {service.calls} attempts in {elapsed:.1f}s")
    try:
        parse_payload()
    except ValueError as err:
        log.info("ValueError raised immediately, not retried: %s", err)

if __name__ == "__main__":
    main()