# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "hypothesis",
#     "rich",
# ]
# ///

"""
Use Hypothesis to test two slugify() implementations.

A valid slug has no spaces, no uppercase, no doubled dashes and no dashes at
either end. We never write a single example by hand: Hypothesis generates
500 strings per run and shrinks any failure to the smallest input.
"""
import re
from hypothesis import given, settings, strategies as st

def slugify_buggy(text: str) -> str:
    """The version most of us write first."""
    return "-".join(text.lower().split())

def slugify_fixed(text: str) -> str:
    """Keep only letters and digits, join the words with single dashes."""
    words = re.findall(r"[a-z0-9]+", text.lower())
    return "-".join(words)

def is_valid_slug(slug: str) -> bool:
    return (
        slug == slug.strip("-")
        and "--" not in slug
        and slug == slug.lower()
        and " " not in slug
    )

def run_property(slugify, label: str) -> None:
    @settings(max_examples=500, database=None, derandomize=True)
    @given(st.text())
    def property_is_valid(text):
        assert is_valid_slug(slugify(text))
    try:
        property_is_valid()
        print(f"{label}: passed 500 generated cases")
    except AssertionError as err:
        print(f"{label}: FAILED")
        for note in getattr(err, "__notes__", []):
            print(note)

def main() -> None:
    run_property(slugify_buggy, "slugify_buggy")
    run_property(slugify_fixed, "slugify_fixed")

if __name__ == "__main__":
    main()