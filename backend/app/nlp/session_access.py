"""Optional owner-bound sessions; legacy random-ID sessions retain compatibility."""

import hashlib
import hmac


class SessionAccessError(PermissionError):
    pass


def token_hash(token):
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def check_owner(values, token):
    stored = values.get("_owner_hash")
    if stored and (not token or not hmac.compare_digest(stored, token_hash(token))):
        raise SessionAccessError("Session access denied")


def public_context(values):
    result = {k: v for k, v in values.items() if not k.startswith("_")}
    result.update(
        current_station_id=values.get("current_station_id", values.get("origin")),
        operator_id=values.get(
            "operator_id", values.get("filters", {}).get("operator")
        ),
        origin_id=values.get("origin"),
        destination_id=values.get("destination"),
        current_result_set=values.get("candidates", []),
        current_ranking=values.get("journey_ranking", values.get("last_intent")),
        state_version=values.get("revision", 0),
    )
    return result
