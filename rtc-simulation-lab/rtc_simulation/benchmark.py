"""Gold comparison and explicit external adapter protocol."""
import importlib
import time
from pathlib import Path
from .generator import dump
from .reference_engine import evaluate
from .validators import read_jsonl

def run(root, category=None, adapter=None, now=None, mode="functional"):
    root=Path(root)
    cases=read_jsonl(root/"scenarios/functional.v1.jsonl")
    questions={q["scenario_id"]:q for q in read_jsonl(root/"benchmarks/english.evaluation.v1.jsonl")}
    if category: cases=[c for c in cases if c["category"]==category]
    if not cases: raise ValueError("No matching scenarios")
    if mode=="nlp" and not adapter: raise ValueError("NLP evaluation requires an external adapter; no classifier is bundled")
    function=None
    if adapter:
        module,name=adapter.split(":",1)
        function=getattr(importlib.import_module(module),name)
    results=[];start=time.perf_counter()
    for c in cases:
        clock=now or c["frozen_now"]
        payload=dict(scenario_id=c["id"],fixture=c["fixture"],frozen_now=clock,
            enquiry=c["enquiry"] if mode=="functional" else None,
            question=questions[c["id"]]["question"] if mode=="nlp" else None,
            conversation_context=questions[c["id"]]["conversation_context"] if mode=="nlp" else None)
        expected=c["expected_result"] if mode=="functional" else dict(intent=questions[c["id"]]["expected_intent"],
            entity_constraints=questions[c["id"]]["entity_constraints"],database_query=questions[c["id"]]["expected_database_query"],
            result=c["expected_result"])
        try:
            actual=function(payload) if function else evaluate(c["fixture"],c["enquiry"],clock)
            error=None
        except Exception as exc:
            actual=None;error=f"{type(exc).__name__}: {exc}"
        results.append(dict(id=c["id"],category=c["category"],passed=actual==expected,error=error,
            expected=expected,actual=actual))
    passed=sum(r["passed"] for r in results)
    report=dict(source_label="SYNTHETIC",mode=mode,adapter=adapter or "standalone reference engine (self-check against authored gold)",
        clock_override=now,clock_note="Gold remains tied to authored frozen time; overrides may intentionally fail.",
        total=len(results),passed=passed,failed=len(results)-passed,pass_rate=passed/len(results),
        elapsed_seconds=time.perf_counter()-start,results=results)
    dump(root/f"reports/benchmark.{mode}.json",report)
    return report
