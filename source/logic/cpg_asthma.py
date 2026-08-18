"""
Asthma exacerbation triage using NIH NAEPP CPG criteria.

Dispositions based on severity assessment:
- ER_NOW: Severe exacerbation (severe distress, hypoxia, altered mental status)
- URGENT_SAME_DAY: Moderate exacerbation (moderate symptoms, work of breathing)
- HOME_MANAGEMENT: Mild exacerbation (minimal distress, normal O2, speaks full sentences)
"""

from __future__ import annotations

from typing import Any

from source.state import Disposition, TriageDecision


def evaluate_asthma_triage(case: dict[str, Any], missing_required: list[str]) -> TriageDecision:
    """
    Triage asthma exacerbation based on NIH NAEPP severity assessment.

    Reference: https://www.nhlbi.nih.gov/asthma/action-plan.pdf
    """
    disposition: Disposition = "HOME_MANAGEMENT"
    rule_ids: list[str] = []
    med_flags: list[str] = []

    # Severe exacerbation → ER_NOW
    if _is_severe_exacerbation(case):
        disposition = "ER_NOW"
        rule_ids.append("R_ASTHMA_SEVERE_ER")
        if case.get("oxygen_saturation") is not None and case["oxygen_saturation"] < 90:
            rule_ids.append("R_ASTHMA_HYPOXIA_ER")
        if case.get("ability_to_speak") == "words_only" or case.get("ability_to_speak") == "no_speech":
            rule_ids.append("R_ASTHMA_SPEECH_IMPAIRMENT_ER")
        if case.get("altered_mental_status"):
            rule_ids.append("R_ASTHMA_ALTERED_MENTAL_ER")
    # Moderate exacerbation → URGENT_SAME_DAY
    elif _is_moderate_exacerbation(case):
        disposition = "URGENT_SAME_DAY"
        rule_ids.append("R_ASTHMA_MODERATE_URGENT")
        if case.get("retractions") in ("moderate", "severe"):
            rule_ids.append("R_ASTHMA_RETRACTIONS_URGENT")
    # Mild exacerbation → HOME_MANAGEMENT
    else:
        disposition = "HOME_MANAGEMENT"
        rule_ids.append("R_ASTHMA_MILD_HOME")
        if case.get("wheeze") == "yes":
            rule_ids.append("R_ASTHMA_MILD_WHEEZE_HOME")

    # Medication flags
    med_flags.extend(_check_medication_flags(case))

    # Prior intubation flag
    if case.get("prior_intubation") == "yes":
        med_flags.append("prior_intubation_history")

    return TriageDecision(
        disposition=disposition,
        rule_ids=rule_ids,
        missing_required=missing_required,
        med_flags=med_flags,
        out_of_scope_reason=None,
    )


def _is_severe_exacerbation(case: dict[str, Any]) -> bool:
    """Severe exacerbation criteria (any one = severe)."""
    # Hypoxia
    if case.get("oxygen_saturation") is not None and case["oxygen_saturation"] < 90:
        return True

    # Severe respiratory distress
    if case.get("breathing") == "distress":
        return True

    # Severe retractions
    if case.get("retractions") == "severe":
        return True

    # Altered mental status / confused
    if case.get("alertness") == "altered":
        return True

    # Inability to speak full sentences (only words or no speech)
    if case.get("ability_to_speak") in ("words_only", "no_speech"):
        return True

    # Very high respiratory rate (age-specific)
    rr = case.get("respiratory_rate")
    age_mo = case.get("age_months")
    if rr is not None and age_mo is not None:
        if age_mo < 6 and rr >= 60:
            return True
        elif age_mo < 12 and rr >= 55:
            return True
        elif rr >= 45:
            return True

    # Prior intubation + current wheezing = elevated risk
    if case.get("prior_intubation") == "yes" and case.get("wheeze") == "yes":
        return True

    return False


def _is_moderate_exacerbation(case: dict[str, Any]) -> bool:
    """Moderate exacerbation criteria (some distress, abnormal vitals)."""
    # Moderate retractions
    if case.get("retractions") == "moderate":
        return True

    # Tachypnea concern (elevated RR but not severe)
    if case.get("breathing") == "tachypnea_concern":
        return True

    # Moderate hypoxia (91-94%)
    ox = case.get("oxygen_saturation")
    if ox is not None and 90 < ox < 95:
        return True

    # Reduced peak expiratory flow (50-80% predicted)
    pef = case.get("peak_expiratory_flow")
    if pef is not None and 50 <= pef <= 80:
        return True

    # Moderate respiratory rate (age-dependent)
    rr = case.get("respiratory_rate")
    age_mo = case.get("age_months")
    if rr is not None and age_mo is not None:
        if age_mo < 6 and 50 <= rr < 60:
            return True
        elif age_mo < 12 and 45 <= rr < 55:
            return True
        elif 40 <= rr < 45:
            return True

    # Speaks short phrases (reduced compared to normal)
    if case.get("ability_to_speak") == "short_phrases":
        return True

    return False


def _check_medication_flags(case: dict[str, Any]) -> list[str]:
    """Check for medication-related safety issues."""
    flags = []

    meds = case.get("current_meds", [])
    if meds and any("beta" in med.lower() for med in meds):
        flags.append("beta_blocker_contraindicated")

    return flags
