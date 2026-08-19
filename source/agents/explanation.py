"""
Explanation Agent: decision object → clinician-style rationale + safety netting.

Uses an LLM when configured; deterministic template fallback for auditability.

Extra Investigation — Approach 2: Logic-Augmented Generation (LAG)
  Enable with TRACEMIND_USE_LAG=1.  Instead of dumping raw dicts, the LLM
  receives a fully-structured symbolic context block: patient state, KG evidence,
  every rule evaluated (fired ✓ or cleared ✗), med flags, and the final decision.
  This constrains the LLM to express the symbolic reasoning rather than generate
  its own, producing more trustworthy and consistent explanations.
"""

from __future__ import annotations

from source.agents.medication import (
    acetaminophen_note,
    ibuprofen_note,
    seattle_childrens_fever_cpg_summary,
)
from source.config import Settings
from source.state import CaseFields, TriageDecision


def _heading(title: str, underline: bool = False) -> str:
    """Format heading text for markdown output (used in Streamlit)."""
    if underline:
        return f"\n\n**{title}**\n"
    return f"**{title}**"


# ---------------------------------------------------------------------------
# LAG: rule metadata — (human_label, condition_description, cpg_basis)
# Keep in sync with triage_rules.py rule IDs.
# ---------------------------------------------------------------------------
_RULE_META: dict[str, tuple[str, str, str]] = {
    "R_ER_ALERTNESS": (
        "Altered alertness",
        "alertness == altered",
        "Seattle Children's CPG: child not alert when awake → ER immediately",
    ),
    "R_ER_BREATHING": (
        "Breathing distress",
        "breathing == distress",
        "CPG: trouble breathing → ER immediately",
    ),
    "R_ER_DEHYDRATION_SEVERE": (
        "Severe dehydration",
        "dehydration_severe == yes  (poor/no fluid AND no urine)",
        "CPG: no wet diaper/urine in 8 h + poor intake → ER immediately",
    ),
    "R_ER_NO_FLUID_NO_URINE": (
        "No fluid intake and no urine output",
        "fluid_intake == none AND urine_last_8h == no",
        "CPG: unable to keep fluids down + no urine → ER immediately",
    ),
    "R_CPG_SEIZURE": (
        "Febrile seizure",
        "seizure == yes",
        "CPG: febrile convulsion → ER immediately",
    ),
    "R_CPG_INFANT_UNDER_3MO_FEVER": (
        "Infant under 3 months with fever",
        "age < 3 months AND temp_f > 100.4°F",
        "CPG: fever in infant < 3 months → ER immediately",
    ),
    "R_URGENT_VERY_HIGH_FEVER": (
        "Very high fever",
        "temp_f >= 104°F AND NOT er_now",
        "CPG: fever ≥ 104°F → same-day urgent evaluation",
    ),
    "R_URGENT_REPEATED_VOMIT_POOR_FLUID": (
        "Repeated vomiting with poor fluid intake",
        "vomiting == repeated AND fluid_intake == poor AND NOT er_now",
        "CPG: vomits often + poor intake → same-day urgent evaluation",
    ),
    "R_URGENT_TACHYPNEA_CONCERN": (
        "Tachypnea concern",
        "breathing == tachypnea_concern AND NOT er_now",
        "CPG: fast breathing concern → same-day urgent evaluation",
    ),
    "R_URGENT_FEVER_OVER_3_DAYS": (
        "Fever lasting more than 3 days",
        "fever_duration_hours >= 72 AND NOT er_now",
        "CPG: fever > 3 days → same-day urgent evaluation",
    ),
    "R_HOME_CONSERVATIVE": (
        "Conservative home management",
        "alertness in {normal, sleepy_ok} AND breathing == normal "
        "AND fluid_intake != none AND NOT er_now AND NOT urgent_same_day",
        "CPG: alert, breathing normally, taking some fluids — no red flags met",
    ),
    # Asthma CPG rules
    "R_ASTHMA_MILD_HOME": (
        "Mild asthma exacerbation",
        "wheeze present with normal oxygen and full speech ability",
        "NIH NAEPP CPG: minimal distress, normal O2, full sentences → home management",
    ),
    "R_ASTHMA_MILD_WHEEZE_HOME": (
        "Mild wheeze without distress",
        "wheeze == yes AND minimal distress",
        "CPG: isolated wheeze without respiratory distress → home management",
    ),
    "R_ASTHMA_MODERATE_URGENT": (
        "Moderate asthma exacerbation",
        "moderate symptoms with work of breathing",
        "NIH NAEPP CPG: moderate retractions or short phrases → urgent same-day",
    ),
    "R_ASTHMA_RETRACTIONS_URGENT": (
        "Moderate retractions with asthma",
        "retractions in (mild, moderate)",
        "CPG: moderate retractions indicate moderate exacerbation → urgent care",
    ),
    "R_ASTHMA_SEVERE_ER": (
        "Severe asthma exacerbation",
        "severe distress, hypoxia, or altered mental status",
        "NIH NAEPP CPG: severe exacerbation with single words or low SpO2 → ER now",
    ),
    "R_ASTHMA_HYPOXIA_ER": (
        "Asthma with hypoxia",
        "oxygen_saturation < 90%",
        "CPG: SpO2 < 90% in asthma → ER immediately",
    ),
    "R_ASTHMA_SPEECH_IMPAIRMENT_ER": (
        "Asthma with speech impairment",
        "ability_to_speak in (single_words, no_speech)",
        "CPG: inability to speak full sentences → severe exacerbation → ER",
    ),
    "R_ASTHMA_ALTERED_MENTAL_ER": (
        "Asthma with altered mental status",
        "altered_mental_status == yes",
        "CPG: altered mental status in asthma → severe → ER immediately",
    ),
    # Anaphylaxis CPG rules
    "R_ANAPHYLAXIS_ER": (
        "Anaphylaxis - multi-system involvement",
        "multi-system involvement detected",
        "AAP/AAAAI: anaphylaxis (skin + airway/GI/CV) → CALL 911",
    ),
    "R_ANAPHYLAXIS_AIRWAY_ER": (
        "Anaphylaxis with airway involvement",
        "breathing == distress OR wheeze == yes OR stridor == yes",
        "CPG: airway involvement in anaphylaxis → ER immediately",
    ),
    "R_ANAPHYLAXIS_CARDIOVASCULAR_ER": (
        "Anaphylaxis with cardiovascular collapse",
        "hypotension == yes OR syncope_or_presyncope == yes",
        "CPG: hypotension/syncope in anaphylaxis → ER immediately",
    ),
    "R_ANAPHYLAXIS_ANGIOEDEMA_AIRWAY_ER": (
        "Anaphylaxis with airway angioedema",
        "angioedema == airway",
        "CPG: airway angioedema → severe anaphylaxis → ER immediately",
    ),
    "R_ANAPHYLAXIS_ALTERED_MENTAL_ER": (
        "Anaphylaxis with altered mental status",
        "alertness == altered",
        "CPG: altered mental status in anaphylaxis → ER immediately",
    ),
    "R_ALLERGIC_REACTION_URGENT": (
        "Significant allergic reaction",
        "localized angioedema or widespread urticaria",
        "AAP: significant reaction without anaphylaxis → same-day urgent care",
    ),
    "R_ALLERGIC_ANGIOEDEMA_FACE_URGENT": (
        "Facial/lip angioedema",
        "angioedema in (face, lips)",
        "CPG: localized facial swelling → urgent evaluation needed",
    ),
    "R_ALLERGIC_GI_SYMPTOMS_URGENT": (
        "Allergic reaction with GI symptoms",
        "gi_symptoms in (vomiting, abdominal_pain, diarrhea)",
        "CPG: allergic reaction with GI involvement → urgent care",
    ),
    "R_ALLERGIC_MILD_HOME": (
        "Mild localized allergic reaction",
        "isolated urticaria/itching only",
        "CPG: mild isolated rash without systemic involvement → home management",
    ),
    # Croup CPG rules
    "R_CROUP_MILD_HOME": (
        "Mild croup",
        "barky cough with mild stridor (crying only)",
        "AAP: mild croup with good air entry and normal O2 → home management",
    ),
    "R_CROUP_BARKY_COUGH_HOME": (
        "Barky cough without stridor",
        "barky_cough == yes AND no significant stridor",
        "CPG: seal-like cough alone → mild croup → home care",
    ),
    "R_CROUP_INSPIRATORY_STRIDOR_HOME": (
        "Inspiratory stridor only",
        "stridor_type == inspiratory",
        "CPG: inspiratory stridor (not biphasic) → mild croup → home management",
    ),
    "R_CROUP_MODERATE_URGENT": (
        "Moderate croup",
        "stridor at rest or moderate retractions",
        "AAP: moderate croup with stridor at rest → dexamethasone + urgent care",
    ),
    "R_CROUP_RETRACTIONS_URGENT": (
        "Croup with moderate retractions",
        "retractions in (mild, moderate)",
        "CPG: retractions indicate moderate severity → urgent evaluation needed",
    ),
    "R_CROUP_TACHYPNEA_URGENT": (
        "Croup with tachypnea concern",
        "breathing == tachypnea_concern",
        "CPG: elevated respiratory rate in croup → urgent same-day care",
    ),
    "R_CROUP_SEVERE_ER": (
        "Severe croup",
        "severe stridor at rest + significant distress",
        "AAP: severe croup (Westley score ≥ 6) → ER immediately",
    ),
    "R_CROUP_BIPHASIC_STRIDOR_ER": (
        "Croup with biphasic/expiratory stridor",
        "stridor_type in (biphasic, expiratory)",
        "CPG: biphasic stridor (lower airway) → ER immediately",
    ),
    "R_CROUP_HYPOXIA_ER": (
        "Croup with hypoxia",
        "oxygen_saturation < 92%",
        "CPG: SpO2 < 92% in croup → ER immediately",
    ),
    "R_CROUP_SEVERE_RETRACTIONS_ER": (
        "Croup with severe retractions",
        "retractions == severe",
        "CPG: severe retractions → severe croup → ER immediately",
    ),
    "R_CROUP_RESPIRATORY_DISTRESS_ER": (
        "Croup with respiratory distress",
        "breathing == distress",
        "CPG: respiratory distress in croup → severe → ER immediately",
    ),
}


def _format_case_summary(case: CaseFields) -> str:
    lines: list[str] = []

    age_y = case.get("age_years")
    age_m = case.get("age_months")
    if age_m is not None:
        lines.append(f"- Age: {age_m:.0f} months")
    elif age_y is not None:
        lines.append(f"- Age: {age_y:.0f} years")
    else:
        lines.append("- Age: unknown")

    wt = case.get("weight_kg")
    if wt is not None:
        lines.append(f"- Weight: {wt} kg")

    tf = case.get("temp_f")
    if tf is not None:
        tier = "very_high (≥104°F)" if tf >= 104 else "high (≥103°F)" if tf >= 103 else "non_extreme (<103°F)"
        lines.append(f"- Temperature: {tf}°F  [classified: {tier}]")
    elif case.get("temp_unknown"):
        lines.append("- Temperature: unknown (acknowledged by caregiver)")
    else:
        lines.append("- Temperature: not yet reported")

    _label = {
        "normal": "normal (awake, responsive)",
        "sleepy_ok": "sleepy but rousable (acceptable)",
        "altered": "ALTERED — not responding normally",
        "unknown": "unknown",
    }
    lines.append(f"- Alertness: {_label.get(str(case.get('alertness', 'unknown')), str(case.get('alertness', 'unknown')))}")

    _blabel = {
        "normal": "normal",
        "tachypnea_concern": "faster than normal (concern)",
        "distress": "DISTRESS — labored or very fast",
        "unknown": "unknown",
    }
    lines.append(f"- Breathing: {_blabel.get(str(case.get('breathing', 'unknown')), str(case.get('breathing', 'unknown')))}")

    _flabel = {
        "good": "good",
        "some": "some (sipping)",
        "poor": "poor (minimal)",
        "none": "NONE (not drinking)",
        "unknown": "unknown",
    }
    lines.append(f"- Fluid intake: {_flabel.get(str(case.get('fluid_intake', 'unknown')), str(case.get('fluid_intake', 'unknown')))}")

    _ulabel = {"yes": "yes", "no": "NO (dry for 8+ hours)", "unknown": "unknown"}
    lines.append(f"- Urination last 8h: {_ulabel.get(str(case.get('urine_last_8h', 'unknown')), str(case.get('urine_last_8h', 'unknown')))}")

    _vlabel = {
        "none": "none",
        "once": "once",
        "repeated": "repeated (multiple times)",
        "unknown": "unknown",
    }
    lines.append(f"- Vomiting: {_vlabel.get(str(case.get('vomiting', 'unknown')), str(case.get('vomiting', 'unknown')))}")

    fd = case.get("fever_duration_hours")
    if fd is not None:
        lines.append(f"- Fever duration: {fd:.0f} hours")

    sz = case.get("seizure", "unknown")
    if sz != "unknown":
        lines.append(f"- Seizure reported: {sz}")

    meds = [str(m).strip() for m in (case.get("current_meds") or []) if str(m).strip()]
    lines.append(f"- Current medications: {', '.join(meds) if meds else 'none reported'}")

    ctx = case.get("local_outbreak_context")
    if ctx:
        lines.append(f"- Local outbreak context: {ctx} (probabilistic prior only; never overrides safety gates)")

    return "\n".join(lines)


def _format_rules_section(rule_ids: list[str]) -> str:
    fired_set = set(rule_ids)
    lines: list[str] = []
    for rid, (label, condition, cpg) in _RULE_META.items():
        if rid in fired_set:
            lines.append(f"✓ FIRED: {rid}")
            lines.append(f"  Label: {label}")
            lines.append(f"  Condition: {condition}")
            lines.append(f"  CPG basis: {cpg}")
        else:
            lines.append(f"✗ NOT FIRED: {rid}  ({label})")
    return "\n".join(lines)


def _kg_annotation_display_name(ann: dict) -> str:
    """Resolve preferred term from flat or nested ``annotate_case_mentions`` shape."""
    c = ann.get("concept")
    if isinstance(c, dict):
        name = (
            c.get("term")
            or c.get("pt")
            or c.get("preferred_term")
            or c.get("label")
            or c.get("name")
        )
        if name:
            return str(name)
    return (
        str(ann.get("preferred_term") or ann.get("label") or ann.get("name") or "")
        or "unknown"
    )


def _kg_annotation_concept_id(ann: dict) -> str:
    """SNOMED / concept id from flat fields or nested ``concept`` dict."""
    top = ann.get("sctid") or ann.get("concept_id")
    if top:
        return str(top)
    c = ann.get("concept")
    if isinstance(c, dict):
        cid = c.get("id") or c.get("sctid") or c.get("conceptId")
        if cid is not None:
            return str(cid)
    return ""


def _format_kg_evidence(kg_annotations: list[dict]) -> str:
    if not kg_annotations:
        return "KG evidence: none retrieved (Neo4j offline or no mentions mapped)"
    lines = ["KG concepts annotated from caregiver text:"]
    for ann in kg_annotations:
        name = _kg_annotation_display_name(ann)
        sctid = _kg_annotation_concept_id(ann)
        phrase = ann.get("phrase") or ann.get("mention") or ""
        entry = f"  - {name}"
        if sctid:
            entry += f" [SNOMED {sctid}]"
        if phrase:
            entry += f"  ← matched phrase: \"{phrase}\""
        lines.append(entry)
    return "\n".join(lines)


def _format_lag_context(
    case: CaseFields,
    decision: TriageDecision,
    kg_annotations: list[dict],
) -> str:
    disp = decision.get("disposition", "UNKNOWN")
    rule_ids = decision.get("rule_ids") or []
    med_flags = decision.get("med_flags") or []
    missing = decision.get("missing_required") or []
    sections = [
        "=== SYMBOLIC TRIAGE CONTEXT ===",
        "",
        "PATIENT STATE (structured from caregiver reports):",
        _format_case_summary(case),
        "",
        "KNOWLEDGE GRAPH EVIDENCE:",
        _format_kg_evidence(kg_annotations),
        "",
        "TRIAGE RULES EVALUATED (all rules in scope):",
        _format_rules_section(rule_ids),
    ]
    if med_flags:
        sections += ["", "MEDICATION SAFETY FLAGS:"]
        sections += [f"  - {f}" for f in med_flags]

    if missing:
        sections += ["", "MISSING REQUIRED FIELDS (disposition cannot be finalised):"]
        sections += [f"  - {m}" for m in missing]

    sections += [
        "",
        f"FINAL SYMBOLIC DECISION: {disp}",
        "",
        "=== YOUR TASK ===",
        "Express the above symbolic reasoning as a clear, trustworthy caregiver-facing explanation.",
        "You MUST follow these constraints:",
        "1. State the disposition first (exactly as given above — do NOT change it).",
        "2. Explain WHY using the specific rules that fired (cite their labels).",
        "3. Acknowledge which red-flag rules were explicitly evaluated and NOT fired (i.e., what was ruled out).",
        "4. List any medication flags and what the caregiver should do about them.",
        "5. Give concrete home care steps (if disposition is HOME_MANAGEMENT).",
        "6. State explicit escalation triggers — specific, not vague.",
        "7. Do NOT add clinical content not supported by the symbolic context above.",
        "8. Do NOT invent diagnoses, dosages, or conditions not present in the state.",
    ]

    return "\n".join(sections)


def _template_reply(case: CaseFields, decision: TriageDecision) -> str:
    disp = decision.get("disposition")
    rules = ", ".join(decision.get("rule_ids") or [])
    missing = decision.get("missing_required") or []
    mflags = decision.get("med_flags") or []

    if missing:
        return (
            "I can help you decide what's safest tonight. I need a few more specifics before I recommend a plan:\n"
            + "\n".join(f"• {m}" for m in missing)
        )

    if disp == "OUT_OF_SCOPE":
        if decision.get("out_of_scope_reason") == "intake_declined":
            return (
                "Without the key details we need (temperature or confirmation you don't have one, alertness, breathing, "
                "fluids, and urination), I can't produce a safe triage plan in this tool. "
                "Please call your pediatric clinician, an after-hours line, or local urgent/emergency services if you're worried."
            )
        return (
            "Based on what I can responsibly cover in this scoped tool, I'm not able to select a single safe disposition. "
            "Please contact your clinician or an urgent line for individualized guidance."
        )

    # Dehydration signal for med text
    fi = case.get("fluid_intake", "unknown")
    ur = case.get("urine_last_8h", "unknown")
    dehydration_risk = fi in ("poor", "none") or ur == "no"

    acet = acetaminophen_note(case)
    ibu = ibuprofen_note(case, dehydration_risk)

    if disp == "ER_NOW":
        return (
            "🚨 EMERGENCY DEPARTMENT — GO NOW.\n\n"
            f"{_heading('Why (rule trace):')} "
            + (rules or "red-flag / severe-dehydration gate")
            + ".\n\n"
            f"{_heading('Key positives/concerns:')}\n"
            "• I'm weighing reduced responsiveness, breathing, hydration, and urine output as hard safety signals\n"
            "• Local outbreak context (if mentioned) can raise suspicion for viral illness but does not override these gates.\n\n"
            f"{_heading('What to do now:')}\n"
            "• Go to the ER now; do not wait overnight.\n"
            "• Bring temperature log, medication list, and recent fluid intake notes if possible.\n\n"
            f"{_heading('Disclaimer:')} THIS IS NOT A DIAGNOSIS; IT IS AN ESCALATION BASED ON RISK THRESHOLDS.\n"
        )

    if disp == "URGENT_SAME_DAY":
        return (
            "⚠️ URGENT — Same-Day Evaluation Needed\n\n"
            "Please contact your pediatrician or urgent care clinic today.\n\n"
            f"{_heading('Why (rule trace):')} "
            + rules
            + ".\n\n"
            f"{_heading('What to do now:')}\n"
            "• Arrange same-day urgent evaluation based on local access.\n"
            "• Continue small frequent fluids while monitoring alertness and breathing.\n\n"
            "Overnight: if symptoms worsen before you can be seen, use the ER thresholds your clinician provides; "
            "if in doubt with rapidly worsening symptoms, choose the ER.\n"
        )

    # HOME_MANAGEMENT
    body = (
        "🏠 HOME MANAGEMENT\n\n"
        "Monitor closely at home. Return immediately if symptoms worsen.\n\n"
        f"{_heading('Why (rule trace):')} "
        + rules
        + ".\n\n"
        + seattle_childrens_fever_cpg_summary()
        + "\n\n"
        f"{_heading('What to do now:')}\n"
        "• Encourage frequent small sips of oral rehydration solution or water; prioritize hydration.\n"
        "• Light clothing, rest, and comfort care.\n"
        "• Track temperatures and vomiting episodes.\n\n"
        "Medication safety (authoritative sources required in production):\n"
        f"• Acetaminophen: {acet.text}\n  Provenance: {acet.provenance}\n"
        f"• Ibuprofen/NSAIDs: {ibu.text}\n  Provenance: {ibu.provenance}\n"
    )
    if mflags:
        body += f"\n{_heading('Medication Safety Flags:')}\n"
        for flag in mflags:
            body += f"  • {flag}\n"
    body += (
        "\nEscalate to urgent care / ER if any of the following occur:\n"
        "• Hard to wake, confusion, or not responding normally.\n"
        "• Breathing becomes fast, noisy, or labored.\n"
        "• Repeated vomiting or unable to keep fluids down.\n"
        "• No urination for ~8 hours or signs of severe dehydration.\n"
        "• Fever persists and you are worried, or fever is very high and the child looks ill.\n\n"
        f"{_heading('Disclaimer:')} If new information emerges (worsening alertness, breathing, or intake), disposition may change.\n"
    )
    return body


def _llm_explain(settings: Settings, case: CaseFields, decision: TriageDecision) -> str:
    from langchain_openai import ChatOpenAI

    if not settings.openai_api_key:
        raise RuntimeError("OPENAI_API_KEY not set")

    llm = ChatOpenAI(
        model=settings.openai_model,
        temperature=0.2,
        api_key=settings.openai_api_key,
    )
    sys = (
        "You are a cautious pediatric triage explainer. Output must:\n"
        "• State disposition and why (reference rule IDs provided).\n"
        "• List key positives/negatives.\n"
        "• Give explicit escalation thresholds.\n"
        "• Separate known vs unknown vs local-context prior.\n"
        "• Never claim you examined the child. Never invent doses without weight.\n"
    )
    payload = {
        "case": case,
        "decision": decision,
    }
    return str(
        llm.invoke(
            [
                {"role": "system", "content": sys},
                {"role": "user", "content": str(payload)},
            ]
        ).content
    )


def _lag_explain(
    settings: Settings,
    case: CaseFields,
    decision: TriageDecision,
    kg_annotations: list[dict],
) -> str:
    """Logic-Augmented Generation: LLM receives the full symbolic reasoning chain."""
    #print("--------------------------------")
    #print("Triggered Logic-Augmented Generation: lag explanations active: ", True)
    #print("--------------------------------")
    from langchain_openai import ChatOpenAI

    if not settings.openai_api_key:
        raise RuntimeError("OPENAI_API_KEY not set")

    llm = ChatOpenAI(
        model=settings.openai_model,
        temperature=0.2,
        api_key=settings.openai_api_key,
    )
    sys = (
        "You are a pediatric triage explainer operating in Logic-Augmented Generation mode.\n"
        "A symbolic triage system has already evaluated the case and produced a structured reasoning chain.\n"
        "Your ONLY job is to express that reasoning as a clear, trustworthy, caregiver-facing explanation.\n"
        "You must NOT change the disposition, invent new reasoning, or add clinical content "
        "not present in the symbolic context you are given.\n"
        "Never claim you examined the child. Never invent dosages without weight.\n"
    )
    context = _format_lag_context(case, decision, kg_annotations)
    print("--------------------------------")
    print("Extnded Context: ", context)
    print("--------------------------------")
    return str(
        llm.invoke(
            [
                {"role": "system", "content": sys},
                {"role": "user", "content": context},
            ]
        ).content
    )


def explain(
    settings: Settings,
    case: CaseFields,
    decision: TriageDecision,
    kg_annotations: list[dict] | None = None,
) -> str:
    if settings.use_mock_llm or not settings.openai_api_key:
        return _template_reply(case, decision)
    kg = kg_annotations or []
    try:
        if settings.use_lag:
            return _lag_explain(settings, case, decision, kg)
        return _llm_explain(settings, case, decision)
    except Exception:
        return _template_reply(case, decision)
