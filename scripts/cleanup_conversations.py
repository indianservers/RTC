"""Bounded local idle-session redaction. Dry run unless --apply is explicit."""

import argparse
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))
from app.catalog import Context
from app.domain import database
from app.nlp.pipeline import ConversationManager
from sqlalchemy import select
from sqlalchemy.orm import Session


def run(apply=False, limit=1000, after=""):
    engine = database()
    now = datetime.now(UTC)
    expired = []
    with Session(engine) as session, session.begin():
        rows = list(
            session.scalars(
                select(Context)
                .where(Context.id > after)
                .order_by(Context.id)
                .limit(limit)
            )
        )
        for row in rows:
            try:
                deadline = datetime.fromisoformat(
                    row.values.get("expires_at", "1970-01-01T00:00:00+00:00")
                )
                if deadline.tzinfo is None:
                    continue
            except (TypeError, ValueError):
                continue
            if deadline <= now:
                expired.append(row.id)
                if apply:
                    ConversationManager(session).expire(row)
        print(
            json.dumps(
                {
                    "apply": apply,
                    "scanned": len(rows),
                    "expired": len(expired),
                    "next_cursor": rows[-1].id if len(rows) == limit else None,
                }
            )
        )
    engine.dispose()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--limit", type=int, default=1000)
    parser.add_argument("--after", default="")
    args = parser.parse_args()
    if not 1 <= args.limit <= 10000:
        parser.error("limit must be between 1 and 10000")
    run(args.apply, args.limit, args.after)
