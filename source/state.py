from __future__ import annotations

from typing import Any, Literal, TypedDict, cast

Disposition = Literal["ER_NOW", "URGENT_SAME_DAY", "HOME_MANAGEMENT", "OUT_OF_SCOPE"]


class CaseFields(TypedDict, total=False):
    """Canonical clinical fields after interpretation + optional KG normalization."""

    # Condition selector
    chief_complaint: Literal["fever", "asthma", "anaphylaxis", "croup", "unknown"]

    # Demographics & vital signs
    age_years: float | None
    age_months: float | None  # if set, takes precedence over age_years for infant rules
    weight_kg: float | None
    temp_f: float | None
    temp_unknown: bool

    # Shared / fever-related fields
    vomiting: Literal["none", "once", "repeated", "unknown"]
    alertness: Literal["normal", "sleepy_ok", "altered", "unknown"]
    breathing: Literal["normal", "tachypnea_concern", "distress", "unknown"]
    fluid_intake: Literal["good", "some", "poor", "none", "unknown"]
    urine_last_8h: Literal["yes", "no", "unknown"]
    current_meds: list[str]
    last_antibiotic_dose_hours_ago: float | None
    local_outbreak_context: str | None  # probabilistic prior only; never overrides gates
    seizure: Literal["yes", "no", "unknown"]
    fever_duration_hours: float | None  # for CPG ">3 days" / prolonged fever triggers
    intake_declined: bool

    # Asthma exacerbation fields
    wheeze: Literal["yes", "no", "unknown"]
    peak_expiratory_flow: float | None  # liters/min or % predicted
    respiratory_rate: float | None  # breaths/min
    oxygen_saturation: float | None  # % (0-100)
    stridor: Literal["yes", "no", "unknown"]
    retractions: Literal["none", "mild", "moderate", "severe", "unknown"]
    ability_to_speak: Literal["full_sentences", "short_phrases", "words_only", "no_speech", "unknown"]
    cough_type: Literal["dry", "wet", "barking", "productive", "unknown"]
    prior_intubation: Literal["yes", "no", "unknown"]

    # Allergic reaction / Anaphylaxis fields
    urticaria: Literal["yes", "no", "unknown"]
    angioedema: Literal["none", "lips", "face", "airway", "systemic", "unknown"]
    allergen_exposure: str | None  # text description (food, insect, medication, etc.)
    known_allergy_history: str | None
    gi_symptoms: Literal["none", "nausea", "vomiting", "abdominal_pain", "diarrhea", "unknown"]
    hypotension: Literal["yes", "no", "unknown"]
    syncope_or_presyncope: Literal["yes", "no", "unknown"]

    # Croup fields
    stridor_type: Literal["inspiratory", "expiratory", "biphasic", "unknown"]
    stridor_onset: Literal["gradual", "sudden", "unknown"]
    barky_cough: Literal["yes", "no", "unknown"]
    drooling: Literal["yes", "no", "unknown"]
    difficulty_swallowing: Literal["yes", "no", "unknown"]
    croup_duration_hours: float | None


class TriageDecision(TypedDict, total=False):
    disposition: Disposition
    rule_ids: list[str]
    missing_required: list[str]
    med_flags: list[str]
    out_of_scope_reason: str | None


class CareTraceState(TypedDict, total=False):
    """LangGraph state."""

    messages: list[dict[str, str]]  # {"role": "user"|"assistant", "content": str}
    raw_user_text: str
    case: CaseFields
    kg_annotations: list[dict[str, Any]]
    decision: TriageDecision
    assistant_reply: str
    turn: int


REQUIRED_FOR_SAFE_PLAN: tuple[str, ...] = (
    "temp_f_or_unknown_ack",
    "alertness",
    "breathing",
    "fluid_intake",
    "urine_last_8h",
)


def default_case() -> CaseFields:
    return cast(
        CaseFields,
        {
            "chief_complaint": "unknown",
            "age_years": None,
            "age_months": None,
            "weight_kg": None,
            "temp_f": None,
            "temp_unknown": False,
            "vomiting": "unknown",
            "alertness": "unknown",
            "breathing": "unknown",
            "fluid_intake": "unknown",
            "urine_last_8h": "unknown",
            "current_meds": [],
            "last_antibiotic_dose_hours_ago": None,
            "local_outbreak_context": None,
            "seizure": "unknown",
            "fever_duration_hours": None,
            "intake_declined": False,
            "wheeze": "unknown",
            "peak_expiratory_flow": None,
            "respiratory_rate": None,
            "oxygen_saturation": None,
            "stridor": "unknown",
            "retractions": "unknown",
            "ability_to_speak": "unknown",
            "cough_type": "unknown",
            "prior_intubation": "unknown",
            "urticaria": "unknown",
            "angioedema": "none",
            "allergen_exposure": None,
            "known_allergy_history": None,
            "gi_symptoms": "none",
            "hypotension": "unknown",
            "syncope_or_presyncope": "unknown",
            "stridor_type": "unknown",
            "stridor_onset": "unknown",
            "barky_cough": "unknown",
            "drooling": "unknown",
            "difficulty_swallowing": "unknown",
            "croup_duration_hours": None,
        },
    )
