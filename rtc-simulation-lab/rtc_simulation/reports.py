"""Machine-readable and Markdown coverage, with explicit missing coverage."""
import json
from collections import Counter
from pathlib import Path
from .generator import dump,CATEGORIES
from .validators import read_jsonl,validate

def report(root):
    root=Path(root);net=json.loads((root/"fixtures/network.v1.json").read_text(encoding="utf-8"))
    cases=read_jsonl(root/"scenarios/functional.v1.jsonl")
    counts={k:len(net[k]) for k in ("cities","stations","routes","trips")}
    counts.update(scenarios=len(cases),questions=len(read_jsonl(root/"benchmarks/english.evaluation.v1.jsonl")))
    coverage={"intent":dict(Counter(c["enquiry"]["intent"] for c in cases)),
        "category":dict(Counter(c["category"] for c in cases)),
        "bus_category":dict(Counter(c["bus_category"] for c in cases)),
        "date_time_case":dict(Counter(c["time_case"] for c in cases)),
        "error_unknown_case":dict(Counter(w for c in cases for w in c["expected_warnings"]))}
    missing=["Production integration and real classifier evaluation have not been run.",
             "Bus-category labels measure fixture distribution, not category-specific production policy.",
             "Synthetic coverage does not validate official tariffs, schedules or concessions."]
    for key in CATEGORIES:
        if key not in coverage["bus_category"]:missing.append("Missing bus category: "+key)
    check=validate(root)
    benchmark_path=root/"reports/benchmark.functional.json"
    bench=json.loads(benchmark_path.read_text(encoding="utf-8")) if benchmark_path.exists() else None
    data=dict(source_label="SYNTHETIC",counts=counts,coverage=coverage,validation=check,
        scenario_validation_pass_rate=bench["pass_rate"] if bench else None,
        benchmark_summary={k:bench[k] for k in ("total","passed","failed","elapsed_seconds")} if bench else None,missing_coverage=missing)
    dump(root/"reports/coverage.json",data)
    lines=["# SYNTHETIC RTC laboratory report","","All information is generated DEMO data, never official APSRTC information.",""]
    lines += [f"- {k}: {v}" for k,v in counts.items()]
    lines += ["",f"Artifact validation: {'PASS' if check['passed'] else 'FAIL'}"]
    if bench: lines += [f"Gold scenario pass rate: {bench['passed']}/{bench['total']} ({bench['pass_rate']:.1%}); {bench['elapsed_seconds']:.6f} seconds."]
    for name,values in coverage.items():
        lines += ["", "## "+name,""]+[f"- {k}: {v}" for k,v in sorted(values.items())]
    lines += ["","## Missing coverage and limits",""]+["- "+m for m in missing]
    (root/"reports/coverage.md").write_text("\n".join(lines)+"\n",encoding="utf-8")
    return data
