"""Live loopback-only DEMO import/publish/passenger/rollback smoke; no token logging."""

import base64
import json
import os
from pathlib import Path
from uuid import uuid4

import httpx


def run():
    root = {"Authorization": "Bearer " + os.environ["RTC_ADMIN_TOKEN"]}
    alias = "DEMO Phase5A verification " + uuid4().hex[:10]
    report = {"application": "http://127.0.0.1:8000", "alias": alias, "checks": {}}
    reviewer = None
    batch = None
    with httpx.Client(
        base_url="http://127.0.0.1:8000/api/v1", trust_env=False, timeout=180
    ) as client:

        def request(method, path, headers=root, body=None):
            assert path.startswith("/") and not path.startswith("//")
            response = client.request(method, path, headers=headers, json=body)
            response.raise_for_status()
            return response.json().get("data", response.json())

        try:
            bootstrap = request("GET", "/app/bootstrap")
            station = request("GET", "/stations/resolve?value=Tirupati")["candidates"][
                0
            ]
            operator = bootstrap["operators"][0]["id"]
            reviewer = request(
                "POST",
                "/admin/data/users",
                body={
                    "username": "phase5a-smoke-reviewer-" + uuid4().hex[:8],
                    "role": "APPROVER",
                    "operator_ids": [],
                    "global_scope": True,
                },
            )
            reviewer_headers = {"Authorization": "Bearer " + reviewer["token"]}
            csv = f"station_id,name,dataset_source\n{station['id']},{alias},DEMO\n"
            batch = request(
                "POST",
                "/admin/imports/files/station-aliases",
                body={
                    "filename": "DEMO-live-smoke-alias.csv",
                    "operator_id": operator,
                    "content_base64": base64.b64encode(csv.encode()).decode(),
                },
            )
            report["batch_id"] = batch["id"]

            def search():
                response = client.get("/stations/search", params={"q": alias})
                response.raise_for_status()
                return response.json()["data"]

            report["checks"]["draft_hidden"] = not search()
            for verb, headers in (
                ("validate", root),
                ("approve", reviewer_headers),
                ("publish", root),
            ):
                batch = request(
                    "POST",
                    f"/admin/imports/batches/{batch['id']}/{verb}",
                    headers,
                    {
                        "revision": batch["revision"],
                        "reason": "DEMO live application verification",
                    },
                )
                report["checks"][verb] = batch["workflow_state"]
                assert not batch.get("validation_report", {}).get("errors")
            matches = search()
            report["checks"]["published_search"] = bool(
                matches and matches[0]["id"] == station["id"]
            )
            conversation = client.post(
                "/conversation/message",
                json={
                    "text": f"Next bus to {alias}?",
                    "language": "en",
                    "station_context": bootstrap["default_station"]["id"],
                },
            )
            conversation.raise_for_status()
            result = conversation.json()
            report["checks"]["passenger_enquiry_resolves_imported_alias"] = (
                result["context"]["destination"] == station["id"]
            )
            report["passenger_response_status"] = result.get("status")
            batch = request(
                "POST",
                f"/admin/imports/batches/{batch['id']}/rollback",
                body={
                    "revision": batch["revision"],
                    "reason": "Restore DEMO smoke test state",
                },
            )
            report["checks"]["rollback_archived"] = (
                batch["workflow_state"] == "ARCHIVED"
            )
            report["checks"]["rolled_back_alias_hidden"] = not search()
            assert all(report["checks"].values()), report
        finally:
            if batch and batch["workflow_state"] == "PUBLISHED":
                request(
                    "POST",
                    f"/admin/imports/batches/{batch['id']}/rollback",
                    body={
                        "revision": batch["revision"],
                        "reason": "Cleanup live DEMO smoke test",
                    },
                )
            elif batch and batch["workflow_state"] in {"DRAFT", "VALIDATED"}:
                request(
                    "POST",
                    f"/admin/imports/batches/{batch['id']}/archive",
                    body={
                        "revision": batch["revision"],
                        "reason": "Cleanup interrupted DEMO verification",
                    },
                )
            if reviewer:
                request("DELETE", f"/admin/data/users/{reviewer['id']}")
                report["reviewer_revoked"] = True
        path = Path(__file__).resolve().parents[1] / "docs/phase5a-live-smoke.json"
        path.write_text(json.dumps(report, indent=2), encoding="utf-8")
        print(json.dumps(report, indent=2))


if __name__ == "__main__":
    run()
