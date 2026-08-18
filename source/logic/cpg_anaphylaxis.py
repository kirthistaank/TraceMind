"""
Allergic reaction / Anaphylaxis triage using AAP & AAAAI guidelines.

Anaphylaxis is a life-threatening reaction requiring immediate epinephrine.
Key: Any systemic involvement (skin + airway/breathing/GI/cardiovascular) = suspect anaphylaxis.

Dispositions:
- ER_NOW: Anaphylaxis (any airway involvement, stridor, wheezing, hypotension, altered mental status, multi-system)
- URGENT_SAME_DAY: Allergic reaction without anaphylaxis (localized angioedema, significant urticaria, mild GI)
- HOME_MANAGEMENT: Mild localized reaction (isolated urticaria/itching, known resolved trigger)
"""

from __future__ import annotations

from typing import Any

from source.state import Disposition, TriageDecision


def evaluate_anaphylaxis_triage(case: dict[str, Any], missing_required: list[str]) -> TriageDecision:
    """
    Triage allergic reaction vs anaphylaxis.

    Reference: AAP Anaphylaxis Management, AAAAI Guidelines
    """
    disposition: Disposition = "HOME_MANAGEMENT"
    rule_ids: list[str] = []
    med_flags: list[str] = []

    # Anaphylaxis → ER_NOW (medical emergency)
    if _is_anaphylaxis(case):
        disposition = "ER_NOW"
        rule_ids.append("R_ANAPHYLAXIS_ER")

        # Identify which systems involved
        if case.get("breathing") == "distress" or case.get("stridor") == "yes" or case.get("wheeze") == "yes":
            rule_ids.append("R_ANAPHYLAXIS_AIRWAY_ER")

        if case.get("hypotension") == "yes" or case.get("syncope_or_presyncope") == "yes":
            rule_ids.append("R_ANAPHYLAXIS_CARDIOVASCULAR_ER")

        if case.get("angioedema") in ("airway", "systemic"):
            rule_ids.append("R_ANAPHYLAXIS_ANGIOEDEMA_AIRWAY_ER")

        if case.get("alertness") == "altered":
            rule_ids.append("R_ANAPHYLAXIS_ALTERED_MENTAL_ER")

        med_flags.append("CALL_911_IMMEDIATE_EPINEPHRINE")

    # Significant allergic reaction (not anaphylaxis) → URGENT_SAME_DAY
    elif _is_significant_allergic_reaction(case):
        disposition = "URGENT_SAME_DAY"
        rule_ids.append("R_ALLERGIC_REACTION_URGENT")

        if case.get("angioedema") in ("face", "lips"):
            rule_ids.append("R_ALLERGIC_ANGIOEDEMA_FACE_URGENT")

        if case.get("gi_symptoms") in ("vomiting", "abdominal_pain", "diarrhea"):
            rule_ids.append("R_ALLERGIC_GI_SYMPTOMS_URGENT")

        med_flags.append("monitor_for_biphasic_reaction")

    # Mild localized reaction → HOME_MANAGEMENT
    else:
        disposition = "HOME_MANAGEMENT"
        rule_ids.append("R_ALLERGIC_MILD_HOME")
        med_flags.append("antihistamine_and_monitor")

    # Known severe allergy history
    if case.get("known_allergy_history") and "severe" in case.get("known_allergy_history", "").lower():
        med_flags.append("known_severe_allergy_history")

    # Allergen still present?
    allergen = case.get("allergen_exposure")
    if allergen:
        med_flags.append(f"allergen_exposure:{allergen}")

    return TriageDecision(
        disposition=disposition,
        rule_ids=rule_ids,
        missing_required=missing_required,
        med_flags=med_flags,
        out_of_scope_reason=None,
    )


def _is_anaphylaxis(case: dict[str, Any]) -> bool:
    """
    Anaphylaxis criteria (AAP/AAAAI):
    - Multi-system involvement (skin + airway/breathing/GI/CV), OR
    - Any airway compromise (stridor, wheezing, breathing distress), OR
    - Hypotension / syncope, OR
    - Angioedema of airway/lips + any systemic sign
    """

    # Airway compromise = anaphylaxis until proven otherwise
    if case.get("stridor") == "yes":
        return True
    if case.get("breathing") == "distress":
        return True
    if case.get("wheeze") == "yes":
        return True

    # Cardiovascular compromise
    if case.get("hypotension") == "yes":
        return True
    if case.get("syncope_or_presyncope") == "yes":
        return True

    # Severe angioedema (airway or systemic)
    if case.get("angioedema") in ("airway", "systemic"):
        return True

    # Multi-system involvement: skin + airway/GI/CV
    has_skin = case.get("urticaria") == "yes" or case.get("angioedema") != "none"
    has_airway = case.get("stridor") == "yes" or case.get("breathing") == "distress"
    has_gi = case.get("gi_symptoms") in ("vomiting", "abdominal_pain", "diarrhea")
    has_cv = case.get("hypotension") == "yes"
    has_neuro = case.get("alertness") == "altered"

    # Skin + any one systemic = anaphylaxis
    system_count = sum([has_airway, has_gi, has_cv, has_neuro])
    if has_skin and system_count >= 1:
        return True

    # Any two systemic systems even without rash
    if system_count >= 2:
        return True

    return False


def _is_significant_allergic_reaction(case: dict[str, Any]) -> bool:
    """
    Allergic reaction (not anaphylaxis) warrants urgent evaluation:
    - Significant localized angioedema (lips, face)
    - Widespread urticaria
    - Mild GI symptoms (not multi-system)
    """

    # Localized but significant angioedema
    if case.get("angioedema") in ("lips", "face"):
        return True

    # Extensive urticaria + not just isolated rash
    if case.get("urticaria") == "yes":
        # If urticaria + any other symptom besides mild itch, escalate
        if case.get("gi_symptoms") != "none":
            return True
        if case.get("angioedema") != "none":
            return True

    return False
