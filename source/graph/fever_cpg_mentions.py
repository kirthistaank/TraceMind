"""
Map structured CaseFields → short clinical phrases for KG lookup.

Phrases are chosen to overlap with preferred terms (`pt`) in the Fever CPG mini-KG
loaded by ``KG_implementation/Scaffold_KG_FeverCPG_Text_to_AuraDB.ipynb``
(Snowstorm search seeds such as "Vomiting", "Fever", "Dyspnea").
"""

from __future__ import annotations

from typing import Any


def kg_mentions_from_case(case: dict[str, Any]) -> list[str]:
    mentions: list[str] = []
    seen: set[str] = set()
    complaint = case.get("chief_complaint", "fever")

    def add(term: str) -> None:
        t = term.strip()
        if not t or t.lower() in seen:
            return
        seen.add(t.lower())
        mentions.append(t)

    # Fever-related mentions
    if case.get("temp_f") is not None or case.get("temp_unknown"):
        add("fever")

    v = case.get("vomiting")
    if v not in (None, "unknown", "none"):
        add("vomiting")

    if case.get("seizure") == "yes":
        add("seizure")

    breath = case.get("breathing")
    if breath == "distress":
        add("dyspnea")
    elif breath == "tachypnea_concern":
        add("tachypnea")

    alert = case.get("alertness")
    if alert == "altered":
        add("lethargy")
    elif alert == "sleepy_ok":
        add("drowsiness")

    if case.get("urine_last_8h") == "no":
        add("oliguria")

    fluid = case.get("fluid_intake")
    if fluid in ("poor", "none"):
        add("dehydration")

    fd = case.get("fever_duration_hours")
    if isinstance(fd, (int, float)) and fd >= 72:
        add("fever")

    # Asthma mentions
    if complaint == "asthma":
        if case.get("wheeze") == "yes":
            add("asthma exacerbation")
            add("wheezing")
        if case.get("stridor") == "yes":
            add("stridor")
        if case.get("cough_type"):
            add("cough")
        if case.get("retractions") in ("mild", "moderate", "severe"):
            add("retractions")

    # Anaphylaxis mentions
    if complaint == "anaphylaxis":
        if case.get("urticaria") == "yes":
            add("urticaria")
            add("hives")
        if case.get("angioedema") != "none":
            add("angioedema")
        if case.get("stridor") == "yes":
            add("anaphylaxis")
        if case.get("breathing") == "distress":
            add("anaphylaxis")
        if case.get("hypotension") == "yes":
            add("shock")
        allergen = case.get("allergen_exposure")
        if allergen:
            add("allergic reaction")

    # Croup mentions
    if complaint == "croup":
        if case.get("barky_cough") == "yes":
            add("croup")
        if case.get("stridor") == "yes":
            add("stridor")
        if case.get("cough_type") == "barking":
            add("laryngotracheobronchitis")

    return mentions


def kg_mentions_from_case_and_text(case: dict[str, Any], raw_user_text: str) -> list[str]:
    """
    Same as ``kg_mentions_from_case``, plus light substring cues from the latest user
    utterance so early turns (e.g. \"fever and vomiting\" before a temp is given) still
    retrieve mini-KG concepts. Does not change ``CaseFields`` or triage required fields.
    """
    mentions = kg_mentions_from_case(case)
    seen = {m.lower() for m in mentions}
    t = (raw_user_text or "").lower()

    def add(term: str) -> None:
        x = term.strip()
        if not x or x.lower() in seen:
            return
        seen.add(x.lower())
        mentions.append(x)

    # Fever/shared mentions
    if "fever" in t:
        add("fever")
    if "vomit" in t or "throwing up" in t or "threw up" in t:
        add("vomiting")
    if "seizure" in t or "convulsion" in t:
        add("seizure")
    if "rash" in t:
        add("skin rash")
    if "breathing fast" in t or "rapid breathing" in t or "tachypnea" in t:
        add("tachypnea")
    if ("trouble breathing" in t or "shortness of breath" in t or "gasping" in t) and "no trouble" not in t:
        add("dyspnea")
    if "lethargic" in t or "barely responding" in t or "won't wake" in t:
        add("lethargy")
    if "dehydration" in t or "dry mouth" in t or "dry lips" in t:
        add("dehydration")
    if "pee" in t or "urin" in t:
        if any(x in t for x in ("hasn't", "has not", "no pee", "not peed", "not since", "don't think")):
            add("oliguria")

    # Asthma mentions
    if "wheez" in t or "asthma" in t:
        add("wheezing")
        add("asthma exacerbation")
    if "stridor" in t:
        add("stridor")
    if "cough" in t or "barking" in t:
        add("cough")
    if "breath" in t and "work" in t:
        add("retractions")

    # Anaphylaxis mentions
    if "hive" in t or "urticaria" in t:
        add("urticaria")
    if "swell" in t or "angioedema" in t:
        add("angioedema")
    if "allerg" in t:
        add("allergic reaction")
    if "anaphyl" in t:
        add("anaphylaxis")

    # Croup mentions
    if "croup" in t or "barking cough" in t or "barky cough" in t:
        add("croup")
    if "laryngeal" in t or "larynx" in t:
        add("laryngotracheobronchitis")

    return mentions
