import argparse
import json
from pathlib import Path
from .generator import generate,dump,SEED,NOW
from .validators import validate
from .benchmark import run
from .event_replay import replay
from .reports import report

def main():
    parser=argparse.ArgumentParser(description="Independent SYNTHETIC RTC laboratory, never live bus data")
    parser.add_argument("command",choices=["generate","validate","replay","benchmark","report"])
    parser.add_argument("--root",type=Path,default=Path(__file__).resolve().parent.parent)
    parser.add_argument("--config",type=Path,help="JSON with categories and operators arrays")
    parser.add_argument("--seed",type=int,default=SEED)
    parser.add_argument("--category",choices=list("ABCDEFGHIJ"))
    parser.add_argument("--now",help="Timezone-aware frozen ISO timestamp")
    parser.add_argument("--adapter",help="Importable module:function")
    parser.add_argument("--mode",choices=["functional","nlp"],default="functional")
    args=parser.parse_args()
    try:
        if args.command=="generate": result=generate(args.root,args.seed,json.loads(args.config.read_text(encoding="utf-8")) if args.config else None)
        elif args.command=="validate": result=validate(args.root)
        elif args.command=="benchmark":
            result=run(args.root,args.category,args.adapter,args.now,args.mode)
            print(json.dumps({k:v for k,v in result.items() if k!="results"},indent=2))
            return 0 if result["failed"]==0 else 1
        elif args.command=="report": result=report(args.root)
        else:
            state=json.loads((args.root/"fixtures/network.v1.json").read_text(encoding="utf-8"))
            events=json.loads((args.root/"fixtures/events.v1.json").read_text(encoding="utf-8"))["events"]
            result=replay(state,events,args.now or "2026-11-08T08:07:00+05:30")
            dump(args.root/"reports/replay.json",result)
            result={"events_replayed":len(result["event_log"]),"live_positions":False,"source_label":"SYNTHETIC"}
        print(json.dumps(result,indent=2))
        return 1 if result.get("passed") is False else 0
    except (OSError,ValueError,KeyError) as exc:
        print(json.dumps({"passed":False,"error":str(exc)}));return 2
if __name__=="__main__": raise SystemExit(main())
