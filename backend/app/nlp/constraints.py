"""English constraint grammar. Place/category identities remain database-owned."""

import re


def constraints(text):
    text = text.casefold()
    values = {}
    non_ac = bool(re.search(r"\b(?:non[ -]?ac|no ac|not ac|without ac)\b", text))
    positive_text = re.sub(r"\b(?:non[ -]?ac|no ac|not ac|without ac)\b", "", text)
    positive_ac = bool(re.search(r"\b(?:only ac|ac only|with ac)\b", positive_text))
    if non_ac and positive_ac:
        raise ValueError("Contradictory AC preferences; choose AC or non-AC.")
    if non_ac:
        values["ac"] = False
    elif re.search(r"\bac\b", text):
        values["ac"] = True
    no_sleeper = bool(
        re.search(r"\b(?:not (?:a )?sleeper|no sleeper|without sleeper|seater)\b", text)
    )
    yes_sleeper = bool(re.search(r"\b(?:only sleeper|sleeper only)\b", text))
    if no_sleeper and yes_sleeper:
        raise ValueError("Contradictory sleeper preferences.")
    if no_sleeper:
        values["sleeper"] = False
    elif re.search(r"\bsleeper\b", text):
        values["sleeper"] = True
    return values
