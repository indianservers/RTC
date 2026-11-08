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
    return {k: v for k, v in values.items() if k != "_owner_hash"}
