"""Deterministic Telugu enquiry vocabulary and fact-based passenger replies."""

import re
from datetime import datetime


STATIONS = {
    "గుంటూరు": "Guntur", "విజయవాడ": "Vijayawada", "బెజవాడ": "Vijayawada",
    "తిరుపతి": "Tirupati", "తిరుమల": "Tirumala", "నెల్లూరు": "Nellore",
    "హైదరాబాద్": "Hyderabad", "విశాఖపట్నం": "Visakhapatnam", "వైజాగ్": "Visakhapatnam",
    "ఒంగోలు": "Ongole", "కడప": "Kadapa", "కర్నూలు": "Kurnool",
    "ఏలూరు": "Eluru", "కాకినాడ": "Kakinada", "అనంతపురం": "Anantapur",
    "శ్రీకాకుళం": "Srikakulam", "విజయనగరం": "Vizianagaram",
    "మచిలీపట్నం": "Machilipatnam", "భీమవరం": "Bhimavaram",
}


def normalize_enquiry(text):
    """Translate known vocabulary only; station resolution still validates local records."""
    if not re.search(r"[\u0c00-\u0c7f]", text):
        return text
    for native, english in sorted(STATIONS.items(), key=lambda item: -len(item[0])):
        text = text.replace(native, f" {english.casefold()} ")
    replacements = {
        "మొదటి బస్సు": "first bus", "మొదటి": "first bus",
        "చివరి బస్సు": "last bus", "చివరి": "last bus",
        "తర్వాతి": "next bus", "తదుపరి": "next bus",
        "టికెట్ ధర": "ticket fare", "టికెట్ ఎంత": "ticket fare",
        "చార్జీ": "fare", "ఛార్జీ": "fare", "ధర": "fare",
        "ప్లాట్‌ఫామ్": "platform", "ప్లాట్ ఫామ్": "platform", "ప్లాట్ఫారం": "platform",
        "ప్రయాణ సమయం": "journey duration", "ఎంతసేపు": "journey duration",
        "స్టాపులు": "route stops", "స్టాప్‌లు": "route stops",
        "నాన్ ఏసీ": "non ac", "ఏసీ": "ac", "స్లీపర్": "sleeper",
        "రేపు": "tomorrow", "ఈరోజు": "today", "ఉదయం": "morning",
        "సాయంత్రం": "evening", "రాత్రి": "night", "నుంచి": "from", "నుండి": "from",
    }
    for native, english in sorted(replacements.items(), key=lambda item: -len(item[0])):
        text = text.replace(native, f" {english} ")
    if re.search(r"బస్సు|బస్|ఎప్పుడు|ఎన్నింటికి", text) and not re.search(
        r"first bus|last bus|next bus|fare|platform|duration|stops", text
    ):
        text += " next bus"
    return " ".join(text.split())


def clock(value):
    try:
        timestamp = datetime.fromisoformat(str(value))
        return timestamp.strftime("%H:%M")
    except (ValueError, TypeError):
        return str(value)


def render_results(results):
    """Never invent platform, live status, price, or departure details."""
    parts = []
    for result in results:
        rows = result.get("results", [])
        if not rows:
            parts.append("సరిపోలే సమాచారం అందుబాటులో లేదు.")
            continue
        row = rows[0]
        intent = result["intent"]
        if row.get("dataset_source") in ("DEMO", "SYNTHETIC"):
            parts.append("ఇది ప్రదర్శన సమాచారం.")
        if intent == "BUS_PLATFORM":
            parts.append(f"ప్లాట్‌ఫామ్ నంబర్ {row['bay']}." if row.get("bay") else "ప్లాట్‌ఫామ్ ఇంకా నిర్ధారించబడలేదు.")
        elif row.get("departure"):
            kind = "అంచనా" if row.get("departure_kind") == "estimated" else "షెడ్యూల్ ప్రకారం"
            parts.append(f"సర్వీస్ {row.get('service_number', '')}. {kind} బయలుదేరే సమయం {clock(row['departure'])}.")
            if row.get("fare") is not None:
                parts.append(f"టికెట్ ధర {row['fare']} రూపాయలు.")
            if row.get("arrival"):
                parts.append(f"చేరుకునే సమయం {clock(row['arrival'])}.")
            if len(rows) > 1:
                times = ", ".join(clock(r["departure"]) for r in rows[1:3] if r.get("departure"))
                if times:
                    parts.append(f"ఇతర సర్వీసుల సమయాలు: {times}.")
        elif intent in ("TICKET_FARE", "GET_FARE"):
            amount = row.get("amount", row.get("fare"))
            parts.append(f"టికెట్ ధర {amount} రూపాయలు." if amount is not None else "టికెట్ ధర అందుబాటులో లేదు.")
        elif intent == "JOURNEY_DURATION" and row.get("minutes") is not None:
            parts.append(f"ప్రయాణ సమయం {row['minutes']} నిమిషాలు.")
        elif intent == "ARRIVAL_TIME" and row.get("arrival"):
            parts.append(f"చేరుకునే సమయం {clock(row['arrival'])}.")
        else:
            parts.append("ఈ వివరాలు క్రింద ఉన్న ఫలితాలలో చూడండి. నిర్ధారించని సమాచారాన్ని ప్రయాణానికి ముందు బస్ స్టేషన్‌లో తనిఖీ చేయండి.")
    return " ".join(parts) or "సరిపోలే సమాచారం అందుబాటులో లేదు."


def localize_dialogue(answer, state, clarify, results):
    if re.search(r"[\u0c00-\u0c7f]", answer):
        return answer
    prompts = {
        "AWAITING_ORIGIN": "మీరు ఏ బస్ స్టేషన్‌లో ఎక్కుతారు?",
        "AWAITING_DESTINATION": "మీరు ఎక్కడికి వెళ్లాలి?",
        "AWAITING_STATION_CLARIFICATION": "మీరు ఏ బస్ స్టేషన్ గురించి అడుగుతున్నారు? క్రింద ఉన్న స్టేషన్‌ను ఎంచుకోండి.",
        "AWAITING_CATEGORY": "మీకు ఏ రకమైన బస్సు కావాలి? క్రింద ఉన్న ఎంపికలను చూడండి.",
        "NO_RESULTS": "మీరు ఎంచుకున్న పరిమితులకు సరిపోయే బస్సు సమాచారం అందుబాటులో లేదు. పరిమితులు అలాగే ఉన్నాయి.",
        "OUT_OF_SCOPE": "నేను ఆర్టీసీ బస్సు సమాచారం కోసం సహాయం చేస్తాను. బస్సు సమయాలు, ధర లేదా మార్గం గురించి అడగండి.",
    }
    if state in prompts:
        return prompts[state]
    if clarify:
        return "దయచేసి మీ ప్రశ్నను మరింత స్పష్టంగా చెప్పండి. గమ్యం, బస్సు సమయం, టికెట్ ధర లేదా ప్లాట్‌ఫామ్ గురించి అడగవచ్చు. క్రింద ఉన్న ఎంపికలను కూడా చూడండి."
    if results:
        return render_results(results)
    return "మీ అభ్యర్థన నమోదు అయింది. బస్సు గమ్యం, సమయం లేదా టికెట్ ధర గురించి అడగండి."
