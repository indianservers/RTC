"""Structural, referential, semantic and checksum validation."""
import hashlib
import json
from decimal import Decimal
from pathlib import Path
from .reference_engine import dt

def read_jsonl(path):
    return [json.loads(line) for line in Path(path).read_text(encoding="utf-8").splitlines() if line.strip()]

def validate(root):
    root=Path(root); errors=[]
    def check(condition,message):
        if not condition: errors.append(message)
    try:
        manifest=json.loads((root/"manifest.v1.json").read_text(encoding="utf-8"))
        for name,digest in manifest["files"].items():
            p=root/name
            check(p.resolve().is_relative_to(root.resolve()),"Manifest path escapes laboratory")
            if p.resolve().is_relative_to(root.resolve()):
                check(p.is_file() and hashlib.sha256(p.read_bytes()).hexdigest()==digest,"Checksum: "+name)
        net=json.loads((root/"fixtures/network.v1.json").read_text(encoding="utf-8"))
        for collection,minimum in [("cities",50),("stations",100),("routes",500),("trips",2000)]:
            rows=net[collection]
            check(len(rows)>=minimum,"Insufficient "+collection)
            check(len({r["id"] for r in rows})==len(rows),"Duplicate "+collection)
            check(all(r["source_label"]=="SYNTHETIC" for r in rows),"Provenance "+collection)
        stations={r["id"] for r in net["stations"]}
        cities={r["id"] for r in net["cities"]}
        routes={r["id"]:r for r in net["routes"]}
        for s in net["stations"]:check(s["city_id"] in cities,"Station city FK")
        for r in routes.values():
            check(len(r["stations"])==len(set(r["stations"])) and set(r["stations"])<=stations,"Invalid route sequence")
        for t in net["trips"]:
            check(t["route_id"] in routes,"Trip route FK")
            check([s["station"] for s in t["stops"]]==routes[t["route_id"]]["stations"],"Trip route direction")
            previous=None
            for s in t["stops"]:
                a,d=dt(s["arrival"]),dt(s["departure"])
                check(a<=d and (previous is None or previous<a),"Trip chronology "+t["id"])
                previous=d
            snap=t.get("seat_snapshot")
            check(snap is None or isinstance(snap["available"],int) and snap["available"]>=0,"Seat snapshot")
        for f in net["fares"]:
            check(f["route_id"] in routes and Decimal(f["rate"])>=0,"Fare FK/amount")
        cases=read_jsonl(root/"scenarios/functional.v1.jsonl")
        questions=read_jsonl(root/"benchmarks/english.evaluation.v1.jsonl")
        check(len(cases)>=500 and len(questions)>=500,"Minimum evaluation counts")
        check(len({c["id"] for c in cases})==len(cases),"Scenario IDs")
        check(len({q["question"] for q in questions})==len(questions),"Distinct English questions")
        index={c["id"]:c for c in cases}
        required={"id","description","frozen_now","fixture","enquiry","expected_result","expected_warnings","data_provenance","business_rule","schema_version","fixture_version","random_seed","source_label"}
        for c in cases:
            check(required<=c.keys(),"Scenario schema "+c["id"])
            dt(c["frozen_now"])
            check(c["source_label"]=="SYNTHETIC" and c["expected_result"]["source_label"]=="SYNTHETIC","Scenario provenance")
            check(c["expected_result"]["warnings"]==c["expected_warnings"],"Warning contract")
        for q in questions:
            check(q["scenario_id"] in index and q["evaluation_only"] is True,"Question linkage/isolation")
            check(q["final_factual_result"]==index[q["scenario_id"]]["expected_result"],"Question gold mismatch")
        check(set("ABCDEFGHIJ")<={c["category"] for c in cases},"Missing scenario category")
    except (ValueError,KeyError,TypeError,OSError,StopIteration) as exc:
        errors.append(f"Malformed artifact: {exc}")
    return {"passed":not errors,"errors":errors,"error_count":len(errors),"source_label":"SYNTHETIC"}
