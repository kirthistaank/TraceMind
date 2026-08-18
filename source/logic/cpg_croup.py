"""
Croup (Laryngotracheobronchitis) triage using AAP CPG.

Croup is a viral illness (usually parainfluenza) with characteristic barky cough & stridor.
Severity based on Westley Croup Score (stridor + retractions + air entry + alertness + cyanosis).

Dispositions:
- ER_NOW: Severe croup (severe stridor at rest, significant distress, hypoxia, altered mental)
- URGENT_SAME_DAY: Moderate croup (moderate stridor, mild-moderate distress) → dexamethasone
- HOME_MANAGEMENT: Mild croup (barky cough, mild stridor with agitation/cry, good air entry)
"""

from __future__ import annotations

from typing import Any

from source.state import Disposition, TriageDecision


def evaluate_croup_triage(case: dict[str, Any], missing_required: list[str]) -> TriageDecision:
    """
    Triage croup severity using modified Westley score concept.

    Reference: AAP Croup Management CPG
    """
    disposition: Disposition = "HOME_MANAGEMENT"
    rule_ids: list[str] = []
    med_flags: list[str] = []

    # Severe croup → ER_NOW
    if _is_severe_croup(case):
        disposition = "ER_NOW"
        rule_ids.append("R_CROUP_SEVERE_ER")

        if case.get("stridor") == "yes" and case.get("stridor_type") in ("biphasic", "expiratory"):
            rule_ids.append("R_CROUP_BIPHASIC_STRIDOR_ER")

        if case.get("oxygen_saturation") is not None and case["oxygen_saturation"] < 92:
            rule_ids.append("R_CROUP_HYPOXIA_ER")

        if case.get("retractions") == "severe":
            rule_ids.append("R_CROUP_SEVERE_RETRACTIONS_ER")

        if case.get("breathing") == "distress":
            rule_ids.append("R_CROUP_RESPIRATORY_DISTRESS_ER")

        med_flags.append("consider_racemic_epinephrine")

    # Moderate croup → URGENT_SAME_DAY
    elif _is_moderate_croup(case):
        disposition = "URGENT_SAME_DAY"
        rule_ids.append("R_CROUP_MODERATE_URGENT")

        if case.get("retractions") in ("mild", "moderate"):
            rule_ids.append("R_CROUP_RETRACTIONS_URGENT")

        if case.get("breathing") == "tachypnea_concern":
            rule_ids.append("R_CROUP_TACHYPNEA_URGENT")

        med_flags.append("dexamethasone_0.6mg_per_kg")

    # Mild croup → HOME_MANAGEMENT
    else:
        disposition = "HOME_MANAGEMENT"
        rule_ids.append("R_CROUP_MILD_HOME")

        if case.get("barky_cough") == "yes":
            rule_ids.append("R_CROUP_BARKY_COUGH_HOME")

        if case.get("stridor") == "yes" and case.get("stridor_type") == "inspiratory":
            rule_ids.append("R_CROUP_INSPIRATORY_STRIDOR_HOME")

    # Medication flags
    med_flags.extend(_check_croup_medication_flags(case))

    # Supportive care
    if disposition == "HOME_MANAGEMENT" or disposition == "URGENT_SAME_DAY":
        med_flags.append("humidified_air_supportive_care")

    return TriageDecision(
        disposition=disposition,
        rule_ids=rule_ids,
        missing_required=missing_required,
        med_flags=med_flags,
        out_of_scope_reason=None,
    )


def _is_severe_croup(case: dict[str, Any]) -> bool:
    """Severe croup criteria (any one = severe)."""

    # Hypoxia
    if case.get("oxygen_saturation") is not None and case["oxygen_saturation"] < 92:
        return True

    # Stridor at rest with significant retractions
    if case.get("stridor") == "yes" and case.get("retractions") in ("moderate", "severe"):
        return True

    # Biphasic or expiratory stridor (suggests lower airway involvement)
    if case.get("stridor_type") in ("biphasic", "expiratory"):
        return True

    # Respiratory distress
    if case.get("breathing") == "distress":
        return True

    # Severe retractions
    if case.get("retractions") == "severe":
        return True

    # Altered mental status / lethargy
    if case.get("alertness") == "altered":
        return True

    # Severely limited speech (only single words)
    if case.get("ability_to_speak") == "single_words":
        return True

    # Drooling + stridor (may indicate epiglottitis; treat as emergency)
    if case.get("drooling") == "yes" and case.get("stridor") == "yes":
        rule_alert = "possible_epiglottitis_not_simple_croup"
        return True

    # Very high respiratory rate
    rr = case.get("respiratory_rate")
    age_mo = case.get("age_months")
    if rr is not None and age_mo is not None:
        if age_mo < 12 and rr >= 60:
            return True
        elif rr >= 50:
            return True

    return False


def _is_moderate_croup(case: dict[str, Any]) -> bool:
    """Moderate croup criteria."""

    # Moderate retractions
    if case.get("retractions") == "moderate":
        return True

    # Stridor at rest (without severe retractions)
    if case.get("stridor") == "yes" and case.get("retractions") not in ("severe", "moderate"):
        return True

    # Tachypnea
    if case.get("breathing") == "tachypnea_concern":
        return True

    # Moderate respiratory rate
    rr = case.get("respiratory_rate")
    age_mo = case.get("age_months")
    if rr is not None and age_mo is not None:
        if age_mo < 12 and 50 <= rr < 60:
            return True
        elif 45 <= rr < 50:
            return True

    # Inspiratory stridor with mild retractions
    if case.get("stridor_type") == "inspiratory" and case.get("retractions") == "mild":
        return True

    return False


def _check_croup_medication_flags(case: dict[str, Any]) -> list[str]:
    """Check for medication considerations in croup."""
    flags = []

    age_mo = case.get("age_months")

    # Dexamethasone dosing
    if age_mo is not None and age_mo < 6:
        flags.append("dexamethasone_caution_infants_under_6mo")

    # Fever present? Rule out epiglottitis
    if case.get("temp_f") is not None and case.get("temp_f") > 103:
        flags.append("high_fever_with_croup_consider_epiglottitis")

    return flags
