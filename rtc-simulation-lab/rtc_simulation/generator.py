"""Seeded network plus independently authored scenario expectations."""
import csv
import hashlib
import json
import random
from datetime import datetime, timedelta
from pathlib import Path

SEED = 73129
META = {"schema_version": "1.0", "fixture_version": "1.0.0", "source_label": "SYNTHETIC", "random_seed": SEED}
CITIES = "Vijayawada Guntur Ongole Nellore Tirupati Chittoor Kadapa Kurnool Anantapur Hindupur Madanapalle Proddatur Nandyal Adoni Tenali Bapatla Chirala Narasaraopet Macherla Vinukonda Markapur Kavali Gudur Srikalahasti Puttur Palamaner Rayachoti Rajampet Pulivendula Dharmavaram Tadipatri Guntakal Visakhapatnam Vizianagaram Srikakulam Anakapalle Tuni Kakinada Rajamahendravaram Amalapuram Eluru Bhimavaram Tanuku Tadepalligudem Narsapur Machilipatnam Gudivada Nuzvid Hyderabad Warangal Khammam Nizamabad Karimnagar Bengaluru Chennai Vellore Ballari Hosapete Raichur Bidar".split()
CATEGORIES = ["Pallevelugu", "Express", "Ultra Deluxe", "Super Luxury", "Indra AC", "Garuda", "Amaravathi AC"]
NOW = "2026-11-08T08:00:00+05:30"
def dump(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False)+"\n", encoding="utf-8")

def network(seed, categories=None, operators=None):
    categories = categories or CATEGORIES
    operators = operators or ["DEMO APSRTC-style", "DEMO TSRTC-style", "DEMO KSRTC-style"]
    if not all(isinstance(x,str) and x for x in categories+operators):
        raise ValueError("Categories and operators must be nonempty strings")
    rng = random.Random(seed)
    cities = [dict(id=f"C{i:03}", name=n, source_label="SYNTHETIC") for i,n in enumerate(CITIES)]
    stations = [dict(id=f"S{i:03}", city_id=c["id"], name=c["name"]+suffix, source_label="SYNTHETIC")
                for i,(c,suffix) in enumerate((c,s) for c in cities for s in (" Bus Station", " Bypass"))]
    routes, trips, fares = [], [], []
    for i in range(600):
        ids = rng.sample([s["id"] for s in stations], rng.randint(3, 6))
        routes.append(dict(id=f"R{i:04}", stations=ids, one_way=True, source_label="SYNTHETIC"))
        fares.append(dict(id=f"F{i:04}", route_id=f"R{i:04}", mode="distance", rate=str(rng.randint(100,250)/100),
            valid_from="2026-01-01", valid_to="2026-12-31", source_label="SYNTHETIC"))
        for j in range(4):
            start = datetime.fromisoformat(NOW).replace(hour=(i+j*6)%24, minute=(i*7)%60)
            stops = []
            for k, sid in enumerate(ids):
                arrival = start+timedelta(minutes=k*75)
                stops.append(dict(station=sid, arrival=arrival.isoformat(), departure=(arrival+timedelta(minutes=5)).isoformat()))
            trips.append(dict(id=f"T{i*4+j:05}", route_id=f"R{i:04}", operator=operators[i%len(operators)],
                category=categories[(i+j)%len(categories)], stops=stops, weekdays=list(range(7)) if j%2 else [0,2,4,6],
                exceptions={"2026-11-08": True} if i%13==0 else {}, valid_from="2026-11-01", valid_to="2026-11-30",
                festival_special=i%13==0, additional_service=j==3, cancelled=i%29==0 and j==0,
                delay_minutes=15 if i%11==0 else 0, platform=str(i%12+1), amenities=["reclining seats"]+(["AC"] if (i+j)%7>=4 else []),
                seat_snapshot=None if i%5==0 else dict(available=rng.randint(0,40), observed_at=NOW, source_label="SYNTHETIC"),
                fare_override="450.00" if i%17==0 else None, source_label="SYNTHETIC"))
    return dict(**dict(META,random_seed=seed), cities=cities, stations=stations, routes=routes, trips=trips, fares=fares, categories=categories)

def stamp(day, hour, minute=0):
    return f"2026-11-{day:02}T{hour:02}:{minute:02}:00+05:30"
def trip(tid, stations, hours, day=8):
    return dict(id=tid, stops=[dict(station=s, arrival=stamp(day,h,m), departure=stamp(day,h,m)) for s,(h,m) in zip(stations,hours)],
                weekdays=list(range(7)), source_label="SYNTHETIC", amenities=["AC", "charging"], capacity=50)

def cases():
    """60 explicit case patterns x 10 parameter sets. Expectations never call the oracle."""
    scenarios, questions = [], []
    def add(group, label, state, query, value, warnings, text, variant, rule):
        sid=f"{group}-{len(scenarios)+1:04}"
        scenarios.append(dict(**META, id=sid, category=group, description=label+f" (variant {variant})", frozen_now=NOW,
            fixture=state, enquiry=query, expected_result=dict(value=value,warnings=warnings,source_label="SYNTHETIC"),
            expected_warnings=warnings, data_provenance="Authored synthetic gold fixture; literal/arithmetically derived expectation, independent of reference_engine",
            business_rule=rule, time_case="overnight" if "midnight" in label else "calendar" if "calendar" in label else "daytime",
            bus_category=CATEGORIES[variant%7]))
        styles=["short English", "Indian English", "ambiguous", "correction", "multiple intents", "context dependent"]
        style=styles[variant%6]
        prefixes=["", "Please tell me, ", "For that bus, ", "Sorry, I mean this service: ", "I am planning my journey. ", "And for this one, "]
        questions.append(dict(**META,id="Q-"+sid,scenario_id=sid,question=prefixes[variant%6]+text,
            style=style,conversation_context={"selected_enquiry":query,"fixture_ref":sid,"previous_turn":"Use the selected synthetic service and stations."},
            expected_intent=query["intent"],entity_constraints={k:v for k,v in query.items() if k!="intent"},
            expected_database_query={"operation":query["intent"],"filters":{k:v for k,v in query.items() if k!="intent"},"frozen_now":NOW,"fixture_ref":sid},
            final_factual_result=dict(value=value,warnings=warnings,source_label="SYNTHETIC"),evaluation_only=True))
    for v in range(10):
        a,b,c,d=[f"{name}-{v}" for name in ("Ongole","Guntur","Nellore","Tirupati")]
        t=trip(f"DEMO-{v}",[a,b],[(9,v),(10,v)])
        def put(g,label,state,q,value,warnings,text,rule):
            add(g,label,state,q,value,warnings,text,v,rule)
        for intent,value,text in [("departure",[stamp(8,9,v),stamp(8,10,v)],f"When does DEMO-{v} depart?"),("arrival",stamp(8,10,v),f"When will DEMO-{v} reach {b}?")]:
            put("A",intent,{"trips":[t]},dict(intent=intent,service_id=t["id"]),value,[],text,"Absolute scheduled times; future departures include equality")
        past=trip(t["id"],[a,b],[(6,v),(7,v)])
        put("A","past departure",{"trips":[past]},dict(intent="departure",service_id=t["id"]),[],[],f"Has DEMO-{v} already departed?","Past departures excluded")
        for amen in (["AC","charging"],["reclining seats"],[],["AC","sleeper"],["wheelchair space"]):
            put("B","amenities",{"trips":[dict(t,amenities=amen)]},dict(intent="amenities",service_id=t["id"]),amen,[],f"Does DEMO-{v} offer {', '.join(amen) or 'any listed amenities'}?","Only explicitly recorded amenities")
        x=trip("X",[a,b],[(9,v),(10,v)])
        y=trip("Y",[b,c],[(10,20+v),(11,20+v)])
        z=trip("Z",[c,d],[(11,40+v),(12,40+v)])
        route_cases=[("direct",[x],a,b,[["X"]]),("one transfer",[x,y],a,c,[["X","Y"]]),
            ("two transfers",[x,y,z],a,d,[["X","Y","Z"]]),("wrong direction",[x],b,a,[]),
            ("intermediate boarding",[trip("I",[a,b,c],[(9,v),(10,v),(11,v)])],b,c,[["I"]]),
            ("intermediate alighting",[trip("I",[a,b,c],[(9,v),(10,v),(11,v)])],a,b,[["I"]]),
            ("cancelled connection",[x,dict(y,cancelled=True)],a,c,[]),
            ("missed connection",[x,trip("Y",[b,c],[(9,50),(11,0)])],a,c,[]),
            ("minimum transfer insufficient",[x,trip("Y",[b,c],[(10,v+9),(11,0)])],a,c,[]),
            ("minimum transfer equality",[x,trip("Y",[b,c],[(10,v+10),(11,0)])],a,c,[["X","Y"]]),
            ("impossible itinerary",[x],a,d,[])]
        for label,ts,o,dest,expected in route_cases:
            put("C",label,{"trips":ts},dict(intent="journey",origin=o,destination=dest),expected,[],f"Can I travel from {o} to {dest} ({label})?","Directed stop order; 10 minute transfer; exclude cancellations")
        base=dict(mode="fixed",amount=str(100+v),valid_from="2026-01-01",valid_to="2026-12-31",source_label="SYNTHETIC")
        fq=dict(intent="fare",date="2026-11-08",origin=a,destination=b)
        fare_cases=[("fixed",base,{},f"{100+v}.00",[]),
            ("stop-to-stop",dict(base,mode="stop",pairs={a+":"+b:str(120+v)}),{},f"{120+v}.00",[]),
            ("stage",dict(base,mode="stage",rate="10.25"),{"stages":v+1},f"{10.25*(v+1):.2f}",[]),
            ("distance",dict(base,mode="distance",rate="1.50"),{"distance_km":20+v},f"{1.5*(20+v):.2f}",[]),
            ("date-effective",dict(base,valid_from="2026-11-08"),{},f"{100+v}.00",[]),
            ("trip override",base,{"trip_override":str(80+v)},f"{80+v}.00",[]),
            ("surcharge",dict(base,surcharge="12.50"),{},f"{112.5+v:.2f}",[]),
            ("concession",dict(base,concessions={"student":"0.25"}),{"concession":"student"},f"{(100+v)*.75:.2f}",[]),
            ("missing",None,{},None,["FARE_UNKNOWN"]),
            ("expired",dict(base,valid_to="2026-11-07"),{},None,["FARE_EXPIRED"]),
            ("not yet effective",dict(base,valid_from="2026-11-09"),{},None,["FARE_EXPIRED"]),
            ("inapplicable concession",base,{"concession":"student"},f"{100+v}.00",[])]
        for label,r,extra,expected,warn in fare_cases:
            put("D",label+" fare",{"fare_rule":r},dict(fq,**extra),expected,warn,f"What is the {label} fare from {a} to {b}?","Effective tariff then override then surcharge then eligible concession; Decimal half-up")
        put("D","unknown price not cheapest",{"prices":[{"id":"unknown","amount":None},{"id":"known","amount":str(v+1)}]},dict(intent="cheapest"),"known",[],f"Which priced option is cheapest for journey {v}?","Unknown price excluded")
        for label,snap,expected,warn in [("unknown",None,None,["SEATS_UNKNOWN"]),("fresh",dict(available=v,observed_at=NOW),v,[]),("stale",dict(available=40,observed_at=stamp(8,7)),None,["SEATS_STALE"]),("sold out",dict(available=0,observed_at=NOW),0,[])]:
            put("E",label+" seats",{"trips":[dict(t,seat_snapshot=snap)]},dict(intent="seats",service_id=t["id"]),expected,warn,f"How many {label} seats are recorded for DEMO-{v}?","Never infer seats from capacity; snapshots older than 15 minutes stale")
        for cancelled,delay in [(False,0),(False,15+v),(True,0),(True,30+v)]:
            put("F","operational status",{"trips":[dict(t,cancelled=cancelled,delay_minutes=delay)]},dict(intent="status",service_id=t["id"]),dict(cancelled=cancelled,delay_minutes=delay),[],f"Is DEMO-{v} cancellation recorded as {cancelled}, and is its delay {delay} minutes?","Cancellation and delay separately preserved")
        for platform in (None,str(v+1),str(v+11)):
            put("G","platform assignment",{"trips":[dict(t,platform=platform)]},dict(intent="platform",service_id=t["id"]),platform,["PLATFORM_UNKNOWN"] if platform is None else [],f"Is the platform for DEMO-{v} still {platform or 'unknown'}?","Unknown platform must remain unknown")
        put("H","unknown service",{"trips":[]},dict(intent="status",service_id=t["id"]),None,["SERVICE_UNKNOWN"],f"Where is unlisted service DEMO-{v}?","Unknown service returns warning")
        for stale in (False,True):
            put("H","stale GPS",{"trips":[dict(t,gps_stale=stale)]},dict(intent="gps",service_id=t["id"]),None,["GPS_STALE" if stale else "GPS_UNKNOWN"],f"Is the location of DEMO-{v} fresh (stale={stale})?","No actual live bus positions")
        night=trip("N",[a,b],[(23,v),(23,50)])
        nxt=trip("M",[b,c],[(0,10+v),(1,10+v)],day=9)
        put("I","cross-midnight transfer",{"trips":[night,nxt]},dict(intent="journey",origin=a,destination=c),[["N","M"]],[],f"Can I change at {b} after midnight?","Compare full dates across midnight")
        for label,weekdays,exceptions,expected in [("calendar inactive",[0],{},[]),("calendar added",[0],{"2026-11-08":True},[["X"]]),("calendar removed",list(range(7)),{"2026-11-08":False},[])]:
            put("I",label,{"trips":[dict(x,weekdays=weekdays,exceptions=exceptions)]},dict(intent="journey",origin=a,destination=b),expected,[],f"Does the {label} service run from {a} on Sunday?","Date exception overrides weekly calendar")
        for candidates in ([a,b],[f"DEMO-{v}",f"EXPRESS-{v}"],[a],[]):
            put("J","station/service selection",{"candidates":candidates},dict(intent="selection",text=f"Guntur service {v}"),candidates,["AMBIGUOUS_SELECTION"] if len(candidates)>1 else [],f"Which Guntur service {v} do you mean among {candidates}?","Return candidates; do not silently choose ambiguous entity")
    return scenarios, questions

def generate(root, seed=SEED, config=None):
    root=Path(root)
    net=network(seed, **(config or {}))
    meta=dict(META,random_seed=seed)
    scenarios, questions=cases()
    for row in scenarios+questions: row["random_seed"]=seed
    dump(root/"fixtures/network.v1.json",net)
    events=[]
    kinds=[("delayed",{"minutes":25}),("arrived",{}),("departed",{}),("cancelled",{}),("platform_changed",{"platform":"9"}),("gps_stale",{}),("seats_updated",{"available":12}),("diversion",{"description":"DEMO bypass via alternate road"})]
    for i,(kind,payload) in enumerate(kinds):
        events.append(dict(**meta,id=f"E{i:03}",at=stamp(8,8,i),kind=kind,payload=payload,service_id=net["trips"][i]["id"]))
    dump(root/"fixtures/events.v1.json",dict(**meta,events=events))
    for name,rows in [("scenarios/functional.v1.jsonl",scenarios),("benchmarks/english.evaluation.v1.jsonl",questions)]:
        p=root/name;p.parent.mkdir(parents=True,exist_ok=True)
        p.write_text("".join(json.dumps(row,sort_keys=True)+"\n" for row in rows),encoding="utf-8")
    for name in ("cities","stations","routes","trips","fares"):
        p=root/f"fixtures/{name}.v1.csv"
        rows=net[name]
        fields=sorted({k for row in rows for k in row}|set(meta))
        with p.open("w",newline="",encoding="utf-8") as f:
            writer=csv.DictWriter(f,fieldnames=fields);writer.writeheader()
            for row in rows:
                writer.writerow({k:json.dumps(v,sort_keys=True) if isinstance(v,(dict,list)) else v for k,v in dict(meta,**{k:v for k,v in row.items() if k not in meta}).items()})
    for name, rows in [("events",events),("functional",scenarios),("english_evaluation",questions)]:
        folder="fixtures" if name=="events" else "scenarios" if name=="functional" else "benchmarks"
        with (root/f"{folder}/{name}.v1.csv").open("w",newline="",encoding="utf-8") as f:
            writer=csv.DictWriter(f,fieldnames=list(rows[0]));writer.writeheader()
            for row in rows:
                writer.writerow({k:json.dumps(v,sort_keys=True) if isinstance(v,(dict,list)) or v is None else v for k,v in row.items()})
    paths=sorted([*root.glob("fixtures/*"),*root.glob("scenarios/*"),*root.glob("benchmarks/*")])
    dump(root/"manifest.v1.json",dict(**meta,files={p.relative_to(root).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in paths if p.is_file()}))
    return {"cities":len(net["cities"]),"stations":len(net["stations"]),"routes":len(net["routes"]),"trips":len(net["trips"]),"scenarios":len(scenarios),"questions":len(questions)}
