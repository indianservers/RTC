"""Offline English terminal conversation: python -m app.cli.chat."""

import argparse
import json
import os
import sys
from datetime import datetime
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..domain import Operator, database
from ..nlp.pipeline import NLPRequest, RTCNLPEngine


def main():
    parser = argparse.ArgumentParser(description="Offline English RTC text chat")
    parser.add_argument(
        "--database",
        help="SQLAlchemy URL; defaults to DATABASE_URL or sqlite:///rtc.db",
    )
    parser.add_argument("--station", help="Default boarding station code or name")
    parser.add_argument("--operator", help="Default operator code")
    parser.add_argument("--session", help="Resume a conversation session ID")
    parser.add_argument("--debug", action="store_true")
    args = parser.parse_args()
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    owner_token = os.getenv("RTC_SESSION_TOKEN")
    history = []
    db = database(args.database) if args.database else database()
    with Session(db) as session:
        operators = list(
            session.scalars(select(Operator).where(Operator.active.is_(True)))
        )
        if not operators:
            parser.error(
                "No operator records. Initialize a separate demo database using the README instructions."
            )
        operator = args.operator or (
            operators[0].code
            if len(operators) == 1
            else input("Operator code: ").strip()
        )
        if operator not in {o.code for o in operators} | {o.id for o in operators}:
            parser.error("Unknown operator code")
        station = (
            args.station or input("Boarding bus stand (station name or code): ").strip()
        )
        engine = RTCNLPEngine(session)
        resolved = engine.orchestrator.engine.resolver.resolve(station)
        if resolved["status"] != "KNOWN":
            parser.error(
                "Boarding station is unknown or ambiguous; use its station code."
            )
        sid = args.session
        debug = args.debug
        print(
            "Offline English RTC text chat. /help lists commands. Timetable records may be demonstration data."
        )
        while True:
            try:
                text = input("You: ").strip()
            except (EOFError, KeyboardInterrupt):
                print("\nGoodbye.")
                break
            if not text:
                continue
            if text == "/exit":
                print("Goodbye.")
                break
            if text == "/help":
                print(
                    "/help /reset /context /results /select N /history /debug /station [name or code] /exit\nAsk about timings, fares, stops, seats, platforms or facilities."
                )
                continue
            if text == "/debug":
                debug = not debug
                print("Debug " + ("enabled." if debug else "disabled."))
                continue
            if text == "/history":
                for role, message in history[-50:]:
                    print(role + ": " + message)
                continue
            if text.startswith("/select "):
                number = text.removeprefix("/select ").strip()
                if not number.isdigit() or int(number) < 1:
                    print("Use /select followed by a positive result number.")
                    continue
                text = "the " + number + " one"
            if text == "/context" or text == "/results":
                if not sid:
                    print("No active conversation.")
                    continue
                _, _, context = engine.conversations.load(
                    sid, datetime.now(ZoneInfo("Asia/Kolkata")), owner_token
                )
                if text == "/results":
                    for i, row in enumerate(context.get("candidates", []), 1):
                        print(
                            f"{i}. {row.get('service_number', 'unknown')} | {row.get('departure', 'unknown')} | fare {row.get('fare', 'unknown')} | {row.get('result_id', '')}"
                        )
                else:
                    print(
                        json.dumps(
                            {k: v for k, v in context.items() if k != "_owner_hash"},
                            indent=2,
                            ensure_ascii=False,
                        )
                    )
                session.rollback()
                continue
            if text.startswith("/station"):
                value = (
                    text.removeprefix("/station").strip()
                    or input("Boarding station: ").strip()
                )
                match = engine.orchestrator.engine.resolver.resolve(value)
                if match["status"] != "KNOWN":
                    print("Which station do you mean? Use a unique station code.")
                    continue
                station = match["candidates"][0]["id"]
                text = "from " + match["candidates"][0]["code"]
            if text == "/reset":
                if sid:
                    engine.process(
                        NLPRequest(
                            session_id=sid,
                            text="reset",
                            language="en",
                            owner_token=owner_token,
                        ),
                        datetime.now(ZoneInfo("Asia/Kolkata")),
                    )
                    session.commit()
                sid = None
                print("Conversation reset.")
                continue
            if text.startswith("/"):
                print("Unknown command. Use /help.")
                continue
            try:
                result = engine.process(
                    NLPRequest(
                        text=text,
                        session_id=sid,
                        language="en",
                        station_context=station,
                        operator=operator,
                        debug=debug,
                        owner_token=owner_token,
                    ),
                    datetime.now(ZoneInfo("Asia/Kolkata")),
                )
                session.commit()
            except Exception:
                session.rollback()
                if debug:
                    raise
                print(
                    "The local enquiry could not be completed. Check the database setup or enable /debug."
                )
                continue
            history.extend([("You", text), ("RTC", result.answer)])
            history = history[-50:]
            sid = result.session_id
            print("RTC: " + result.answer)
            if debug:
                print(json.dumps(result.debug, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
