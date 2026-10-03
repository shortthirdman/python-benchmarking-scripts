# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "rich",
# ]
# ///

"""
Turn the benchmark numbers into a table your teammates will enjoy reading.


Reads scale.json written by bench_engines.py and prints one Rich table with
a speedup column, plus a short verdict panel.
"""
import json
from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

console = Console(width=72)
results = json.load(open("scale.json"))
largest = max(results, key=int)
table = Table(
    title=f"Top-3 query, {int(largest):,} rows",
    box=box.SIMPLE_HEAVY,
    show_lines=False,
)
table.add_column("library", style="bold")
table.add_column("time (ms)", justify="right")
table.add_column("vs pandas", justify="right")
baseline = results[largest]["pandas"]
for name, seconds in sorted(results[largest].items(), key=lambda kv: kv[1]):
    speedup = baseline / seconds
    table.add_row(name, f"{seconds * 1000:,.0f}", f"{speedup:.2f}x")
console.print(table)
winner = min(results[largest], key=results[largest].get)
verdict = (
    f"[bold green]{winner}[/] finished first at {int(largest):,} rows.\n"
    "Re-run on your own data before you rewrite anything."
)
console.print(Panel(verdict, title="verdict", expand=False))
console.rule("smaller sizes")
for size, row in results.items():
    best = min(row, key=row.get)
    console.print(f"{int(size):>12,} rows -> fastest: [bold]{best}[/]")