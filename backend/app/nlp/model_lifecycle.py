"""Pure lifecycle gate. Candidate training scores cannot authorize deployment."""


def transition(entry, target):
    allowed = {
        "CANDIDATE": {"EVALUATED"},
        "EVALUATED": {"APPROVED"},
        "APPROVED": {"ACTIVE"},
        "ACTIVE": {"ROLLED_BACK"},
        "ROLLED_BACK": set(),
    }
    current = entry.get("deployment_status", "CANDIDATE")
    if target not in allowed.get(current, set()):
        raise ValueError("Invalid model lifecycle transition")
    if target in ("EVALUATED", "APPROVED", "ACTIVE") and (
        not entry.get("independent_evaluation")
        or not entry.get("validation_metrics")
        or not entry.get("test_metrics")
    ):
        raise ValueError(
            "Separate validation and independent-test reports are required"
        )
    if target in ("APPROVED", "ACTIVE"):
        if entry.get("reviewed_dataset_examples", 0) < 10000:
            raise ValueError("Reviewed dataset target is unmet")
        if entry["test_metrics"].get("macro_f1", 0) < 0.95:
            raise ValueError("Independent intent macro-F1 target is unmet")
        if entry.get("threshold_source") != "validation":
            raise ValueError("Validation-calibrated uncertainty threshold required")
        if not entry.get("os_offline_verified"):
            raise ValueError("OS-isolated inference verification required")
    return {
        **entry,
        "deployment_status": target,
        "approved": target in ("APPROVED", "ACTIVE"),
    }
