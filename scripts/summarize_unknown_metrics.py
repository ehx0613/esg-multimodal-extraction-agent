import csv
from collections import Counter, defaultdict
from config.settings import REPORTS_DIR, OUTPUT_DIR
from utils.json_utils import load_json

counter = Counter(); examples = defaultdict(list)
for p in REPORTS_DIR.glob("*/unknown_metrics.json"):
    report = p.parent.name
    for item in load_json(p):
        name = item.get("metric_name")
        if not name:
            continue
        counter[name] += 1
        if len(examples[name]) < 5:
            examples[name].append(report)

out = OUTPUT_DIR / "unknown_metric_summary.csv"
with open(out, "w", encoding="utf-8-sig", newline="") as f:
    w = csv.DictWriter(f, fieldnames=["metric_name", "count", "example_reports"])
    w.writeheader()
    for name, count in counter.most_common():
        w.writerow({"metric_name": name, "count": count, "example_reports": ";".join(examples[name])})
print(f"Saved to: {out}")
