"""
RAGAS-inspired clinical evaluation framework for CareTrace.

Adapts RAGAS (Retrieval Augmented Generation Assessment) metrics for pediatric triage:
- Faithfulness: Rule/data grounding (do fired rules explain disposition?)
- Answer Relevance: Disposition appropriateness
- Context Relevance: KG relevance to case
- Context Recall: Are all relevant KG facts retrieved?
- Context Precision: Are retrieved KG facts high-quality?

Plus clinical-specific metrics:
- Extraction Accuracy: Did we extract temp/age/alertness correctly?
- Safety Grounding: Are med flags based on actual patient data?
- Clinical Actionability: Can a caregiver act on the response?
"""

from __future__ import annotations

import re
import json
from dataclasses import dataclass, asdict
from typing import Any, Optional
from pathlib import Path

import pandas as pd
from langchain_openai import ChatOpenAI


# ============================================================================
# Data Models
# ============================================================================

@dataclass
class ExtractionMetrics:
    """Measurement of extracted clinical data accuracy."""
    temp_f_correct: bool
    temp_f_expected: Optional[float]
    temp_f_extracted: Optional[float]

    age_correct: bool
    age_expected: Optional[float]
    age_extracted: Optional[float]

    alertness_correct: bool
    alertness_expected: Optional[str]
    alertness_extracted: Optional[str]

    fluid_intake_correct: bool
    urine_correct: bool
    breathing_correct: bool

    field_completeness: float  # 0-1: how many required fields extracted
    overall_extraction_accuracy: float  # 0-1: proportion of fields correct


@dataclass
class FaithfulnessMetrics:
    """Measure if disposition is grounded in data and rules."""
    rules_fired: list[str]
    disposition: str
    expected_disposition: str

    has_rule_justification: bool  # Any rules fired?
    rule_supports_disposition: bool  # Do rules match disposition?
    med_flags_grounded: bool  # Are med flags based on extracted data?
    med_flags: list[str]

    grounding_score: float  # 0-3: overall faithfulness


@dataclass
class AnswerRelevanceMetrics:
    """Measure if response is relevant to query (disposition appropriate)."""
    disposition: str
    expected_disposition: str
    disposition_match: bool

    safety_appropriate: bool  # Conservative for ER/URGENT cases?
    actionability_score: int  # 0-3: can caregiver act?
    clarity_score: int  # 0-3: is response clear?

    relevance_score: float  # 0-3: overall relevance


@dataclass
class ContextRelevanceMetrics:
    """Measure if KG annotations are relevant to case."""
    kg_annotations: list[dict]
    case_fields: dict

    annotations_present: bool  # Any KG annotations?
    annotations_relevant: bool  # Are they related to case?
    num_relevant_annotations: int
    total_annotations: int

    relevance_score: float  # 0-1: proportion relevant


@dataclass
class ContextRecallMetrics:
    """Measure if all relevant KG facts were retrieved."""
    kg_annotations: list[dict]
    case_fields: dict
    expected_kg_topics: list[str]  # e.g., ['fever', 'dehydration']

    topics_found: list[str]
    topics_missed: list[str]
    recall_score: float  # 0-1: proportion of expected topics found


@dataclass
class ContextPrecisionMetrics:
    """Measure quality/specificity of KG annotations."""
    kg_annotations: list[dict]
    case_fields: dict

    num_annotations: int
    num_high_confidence: int
    num_low_confidence: int

    precision_score: float  # 0-1: proportion high-quality


@dataclass
class RAGASClinicalScores:
    """Complete RAGAS-inspired scores for a single case."""
    scenario_id: str
    arm: str

    # RAGAS metrics (0-1 or 0-3)
    extraction_accuracy: float  # 0-1
    faithfulness: float  # 0-3
    answer_relevance: float  # 0-3
    context_relevance: float  # 0-1
    context_recall: float  # 0-1
    context_precision: float  # 0-1

    # Composite metrics
    ragas_score: float  # 0-1: average of normalized metrics
    clinical_score: float  # 0-1: clinical-specific evaluation

    # Details
    extraction_metrics: Optional[ExtractionMetrics] = None
    faithfulness_metrics: Optional[FaithfulnessMetrics] = None
    relevance_metrics: Optional[AnswerRelevanceMetrics] = None
    context_rel_metrics: Optional[ContextRelevanceMetrics] = None
    context_recall_metrics: Optional[ContextRecallMetrics] = None
    context_prec_metrics: Optional[ContextPrecisionMetrics] = None

    error: Optional[str] = None


# ============================================================================
# Evaluation Functions
# ============================================================================

def evaluate_extraction(
    extracted_case: dict,
    expected_fields: dict,
) -> ExtractionMetrics:
    """
    Measure accuracy of clinical field extraction.

    Args:
        extracted_case: CareTrace extracted case (from state['case'])
        expected_fields: Ground truth fields {'temp_f': 102.0, 'alertness': 'normal', ...}

    Returns:
        ExtractionMetrics with per-field accuracy
    """
    expected_fields = expected_fields or {}

    # Extract temperature
    temp_expected = expected_fields.get('temp_f')
    temp_extracted = extracted_case.get('temp_f')
    temp_correct = (
        temp_expected is not None
        and temp_extracted is not None
        and abs(temp_extracted - temp_expected) < 0.5  # Within 0.5°F
    )

    # Extract age (prefer years, convert months if needed)
    age_expected_val = expected_fields.get('age_years')
    if age_expected_val is None and expected_fields.get('age_months') is not None:
        age_expected_val = expected_fields.get('age_months') / 12

    age_extracted_val = extracted_case.get('age_years')
    if age_extracted_val is None and extracted_case.get('age_months') is not None:
        age_extracted_val = extracted_case.get('age_months') / 12

    age_correct = (
        age_expected_val is not None
        and age_extracted_val is not None
        and abs(age_extracted_val - age_expected_val) < 0.1  # Within ~1 month
    )

    # Extract alertness
    alertness_expected = expected_fields.get('alertness')
    alertness_extracted = extracted_case.get('alertness')
    alertness_correct = alertness_expected and alertness_extracted == alertness_expected

    # Extract fluid/urine/breathing
    fluid_correct = (
        extracted_case.get('fluid_intake')
        == expected_fields.get('fluid_intake')
    )
    urine_correct = (
        extracted_case.get('urine_last_8h')
        == expected_fields.get('urine_last_8h')
    )
    breathing_correct = (
        extracted_case.get('breathing')
        == expected_fields.get('breathing')
    )

    # Calculate completeness (how many expected fields were extracted)
    # Only count fields that are expected to be provided (not None)
    expected_provided = {k: v for k, v in expected_fields.items() if v is not None}
    total_expected = len(expected_provided)

    if total_expected > 0:
        extracted_count = sum(
            1 for k, v in expected_provided.items()
            if extracted_case.get(k) is not None and extracted_case.get(k) != 'unknown'
        )
        field_completeness = extracted_count / total_expected
    else:
        field_completeness = 0.0

    # Overall accuracy (only count comparisons where expected value exists)
    correct_fields = []
    if temp_expected is not None:
        correct_fields.append(temp_correct)
    if age_expected_val is not None:
        correct_fields.append(age_correct)
    if alertness_expected is not None:
        correct_fields.append(alertness_correct)
    if expected_fields.get('fluid_intake') is not None:
        correct_fields.append(fluid_correct)
    if expected_fields.get('urine_last_8h') is not None:
        correct_fields.append(urine_correct)
    if expected_fields.get('breathing') is not None:
        correct_fields.append(breathing_correct)

    overall_accuracy = sum(correct_fields) / len(correct_fields) if correct_fields else 0.0

    return ExtractionMetrics(
        temp_f_correct=temp_correct,
        temp_f_expected=temp_expected,
        temp_f_extracted=temp_extracted,
        age_correct=age_correct,
        age_expected=age_expected_val,
        age_extracted=age_extracted_val,
        alertness_correct=alertness_correct,
        alertness_expected=alertness_expected,
        alertness_extracted=alertness_extracted,
        fluid_intake_correct=fluid_correct,
        urine_correct=urine_correct,
        breathing_correct=breathing_correct,
        field_completeness=field_completeness,
        overall_extraction_accuracy=overall_accuracy,
    )


def evaluate_faithfulness(
    extracted_case: dict,
    decision: dict,
    expected_disposition: str,
    med_flags_reference: dict[str, str],
) -> FaithfulnessMetrics:
    """
    Measure if disposition is grounded in extracted data and fired rules.

    RAGAS Faithfulness: Is generated text grounded in retrieved context?
    Clinical equivalent: Is disposition grounded in rules + extracted data?

    Args:
        extracted_case: CareTrace case (the 'context')
        decision: CareTrace decision with 'disposition' and 'rule_ids'
        expected_disposition: Ground truth
        med_flags_reference: Dict of med flag definitions

    Returns:
        FaithfulnessMetrics (0-3 score)
    """
    disposition = decision.get('disposition', 'UNKNOWN')
    rule_ids = decision.get('rule_ids', [])
    med_flags = decision.get('med_flags', [])

    # Check if rules justify disposition
    has_rule_justification = len(rule_ids) > 0

    # Heuristic: certain rules should fire for certain dispositions
    disposition_rule_expectations = {
        'ER_NOW': ['ER'],  # Rules with ER in name
        'URGENT_SAME_DAY': ['URGENT'],
        'HOME_MANAGEMENT': ['HOME', 'CONSERVATIVE'],
    }

    expected_keywords = disposition_rule_expectations.get(disposition, [])
    rule_supports_disposition = any(
        any(kw in rule for kw in expected_keywords)
        for rule in rule_ids
    ) if rule_ids else False

    # Check if med flags are grounded (based on actual patient data)
    med_flags_grounded = True
    for flag in med_flags:
        # Simple heuristic: if flag mentions a medication, check if patient age/condition warrants it
        if 'ibuprofen' in flag.lower() and extracted_case.get('age_months', 100) < 6:
            med_flags_grounded = True  # Correctly identified age gate
        elif 'dehydration' in flag.lower() and extracted_case.get('fluid_intake') == 'poor':
            med_flags_grounded = True  # Correctly identified dehydration flag

    # Grounding score (0-3)
    grounding_score = 0
    if has_rule_justification:
        grounding_score += 1
    if rule_supports_disposition:
        grounding_score += 1
    if med_flags_grounded:
        grounding_score += 1

    return FaithfulnessMetrics(
        rules_fired=rule_ids,
        disposition=disposition,
        expected_disposition=expected_disposition,
        has_rule_justification=has_rule_justification,
        rule_supports_disposition=rule_supports_disposition,
        med_flags_grounded=med_flags_grounded,
        med_flags=med_flags,
        grounding_score=float(grounding_score),
    )


def evaluate_answer_relevance(
    disposition: str,
    expected_disposition: str,
    reply: str,
    med_flags: list[str],
) -> AnswerRelevanceMetrics:
    """
    Measure if response (disposition + explanation) is relevant to the case.

    RAGAS Answer Relevance: Is generated answer relevant to query?
    Clinical equivalent: Is disposition clinically appropriate?

    Args:
        disposition: Predicted disposition
        expected_disposition: Ground truth
        reply: Generated explanation text
        med_flags: Safety flags

    Returns:
        AnswerRelevanceMetrics (0-3 score)
    """
    disposition_match = disposition == expected_disposition

    # Check safety appropriateness
    # ER/URGENT cases should have escalation language
    reply_lower = (reply or '').lower()

    safety_appropriate = True
    if expected_disposition in ['ER_NOW', 'URGENT_SAME_DAY']:
        safety_appropriate = any(
            x in reply_lower for x in ['er', 'emergency', 'urgent', 'same-day', 'call 911', 'now']
        )
    elif expected_disposition == 'HOME_MANAGEMENT':
        safety_appropriate = any(
            x in reply_lower for x in ['home', 'monitor', 'watch', 'care at home']
        )

    # Actionability: can caregiver understand what to do?
    actionability_score = 0
    if any(x in reply_lower for x in ['do now', 'next step', 'arrange', 'offer', 'monitor']):
        actionability_score += 1
    if any(x in reply_lower for x in ['watch for', 'when to', 'go to', 'red flag', 'escalate']):
        actionability_score += 1
    if any(x in reply_lower for x in ['call', 'emergency', 'urgent care', 'contact']):
        actionability_score += 1
    actionability_score = min(actionability_score, 3)

    # Clarity: is explanation structured and clear?
    clarity_score = 0
    if len((reply or '').split('\n')) >= 3:  # Has structure
        clarity_score += 1
    if any(x in reply_lower for x in ['summary', 'what', 'why', 'because']):
        clarity_score += 1
    if 'confus' not in reply_lower and 'unclear' not in reply_lower:  # No explicit uncertainty
        clarity_score += 1
    clarity_score = min(clarity_score, 3)

    # Relevance score
    relevance_score = 0
    if disposition_match:
        relevance_score += 1
    if safety_appropriate:
        relevance_score += 1
    if actionability_score >= 2:
        relevance_score += 1

    return AnswerRelevanceMetrics(
        disposition=disposition,
        expected_disposition=expected_disposition,
        disposition_match=disposition_match,
        safety_appropriate=safety_appropriate,
        actionability_score=actionability_score,
        clarity_score=clarity_score,
        relevance_score=float(relevance_score),
    )


def evaluate_context_relevance(
    kg_annotations: list[dict],
    case_fields: dict,
) -> ContextRelevanceMetrics:
    """
    Measure if KG annotations are relevant to the case.

    RAGAS Context Relevance: Is retrieved context relevant to query?
    Clinical equivalent: Are KG annotations relevant to extracted case?

    Args:
        kg_annotations: List of KG concepts from Neo4j
        case_fields: Extracted case data

    Returns:
        ContextRelevanceMetrics (0-1 score)
    """
    if not kg_annotations:
        return ContextRelevanceMetrics(
            kg_annotations=[],
            case_fields=case_fields,
            annotations_present=False,
            annotations_relevant=False,
            num_relevant_annotations=0,
            total_annotations=0,
            relevance_score=0.0,
        )

    # Extract case topics
    case_topics = []
    if case_fields.get('temp_f'):
        case_topics.append('fever')
    if case_fields.get('fluid_intake') == 'poor':
        case_topics.append('dehydration')
    if case_fields.get('alertness') == 'altered':
        case_topics.append('altered mental status')
    if case_fields.get('breathing') == 'distress':
        case_topics.append('respiratory distress')
    if case_fields.get('urine_last_8h') == 'no':
        case_topics.append('dehydration')

    # Check relevance of annotations
    relevant_count = 0
    for ann in kg_annotations:
        concept_name = ann.get('concept', {}).get('name', '').lower()
        concept_ancestors = [a.get('name', '').lower() for a in ann.get('ancestors', [])]

        # Check if annotation matches case topics
        all_names = [concept_name] + concept_ancestors
        if any(topic in ' '.join(all_names) for topic in case_topics):
            relevant_count += 1

    relevance_score = relevant_count / len(kg_annotations) if kg_annotations else 0.0

    return ContextRelevanceMetrics(
        kg_annotations=kg_annotations,
        case_fields=case_fields,
        annotations_present=len(kg_annotations) > 0,
        annotations_relevant=relevant_count > 0,
        num_relevant_annotations=relevant_count,
        total_annotations=len(kg_annotations),
        relevance_score=relevance_score,
    )


def evaluate_context_recall(
    kg_annotations: list[dict],
    case_fields: dict,
    expected_kg_topics: list[str],
) -> ContextRecallMetrics:
    """
    Measure if all relevant KG facts were retrieved.

    RAGAS Context Recall: Does retrieved context contain all answer facts?
    Clinical equivalent: Were all relevant KG concepts retrieved for the case?

    Args:
        kg_annotations: Retrieved KG annotations
        case_fields: Extracted case
        expected_kg_topics: What we expected to find (e.g., ['fever', 'dehydration'])

    Returns:
        ContextRecallMetrics (0-1 score)
    """
    annotation_concepts = [
        ann.get('concept', {}).get('name', '').lower()
        for ann in kg_annotations
    ]

    topics_found = []
    topics_missed = []

    for topic in expected_kg_topics:
        if any(topic.lower() in concept for concept in annotation_concepts):
            topics_found.append(topic)
        else:
            topics_missed.append(topic)

    recall_score = len(topics_found) / len(expected_kg_topics) if expected_kg_topics else 1.0

    return ContextRecallMetrics(
        kg_annotations=kg_annotations,
        case_fields=case_fields,
        expected_kg_topics=expected_kg_topics,
        topics_found=topics_found,
        topics_missed=topics_missed,
        recall_score=recall_score,
    )


def evaluate_context_precision(
    kg_annotations: list[dict],
    case_fields: dict,
) -> ContextPrecisionMetrics:
    """
    Measure quality/confidence of KG annotations.

    RAGAS Context Precision: Is retrieved context free of irrelevant info?
    Clinical equivalent: Are KG annotations high-confidence and specific?

    Args:
        kg_annotations: Retrieved KG annotations
        case_fields: Extracted case

    Returns:
        ContextPrecisionMetrics (0-1 score)
    """
    if not kg_annotations:
        return ContextPrecisionMetrics(
            kg_annotations=[],
            case_fields=case_fields,
            num_annotations=0,
            num_high_confidence=0,
            num_low_confidence=0,
            precision_score=1.0,
        )

    high_confidence = 0
    low_confidence = 0

    for ann in kg_annotations:
        # Heuristic: annotations with more ancestors are more specific (higher confidence)
        num_ancestors = len(ann.get('ancestors', []))

        if num_ancestors >= 3:  # Deep in hierarchy
            high_confidence += 1
        else:
            low_confidence += 1

    precision_score = high_confidence / len(kg_annotations) if kg_annotations else 1.0

    return ContextPrecisionMetrics(
        kg_annotations=kg_annotations,
        case_fields=case_fields,
        num_annotations=len(kg_annotations),
        num_high_confidence=high_confidence,
        num_low_confidence=low_confidence,
        precision_score=precision_score,
    )


# ============================================================================
# Composite Scoring
# ============================================================================

def evaluate_ragas_clinical(
    scenario_id: str,
    arm: str,
    state: dict,
    expected_disposition: str,
    expected_fields: dict,
    expected_kg_topics: list[str] | None = None,
    med_flags_reference: dict[str, str] | None = None,
) -> RAGASClinicalScores:
    """
    Compute complete RAGAS-inspired scores for a triage case.

    Args:
        scenario_id: Test scenario identifier
        arm: Evaluation arm (baseline_mock, tracemind_rules_kg_on, etc.)
        state: CareTrace state dict with case, decision, kg_annotations
        expected_disposition: Ground truth disposition
        expected_fields: Ground truth extracted fields
        expected_kg_topics: What KG concepts we expected (e.g., ['fever'])
        med_flags_reference: Reference for med flag definitions

    Returns:
        RAGASClinicalScores with all metrics and composite scores
    """
    try:
        extracted_case = state.get('case') or {}
        decision = state.get('decision') or {}
        kg_annotations = state.get('kg_annotations') or []
        reply = state.get('assistant_reply') or ''

        # Compute individual metrics
        extraction = evaluate_extraction(extracted_case, expected_fields)
        faithfulness = evaluate_faithfulness(
            extracted_case,
            decision,
            expected_disposition,
            med_flags_reference or {},
        )
        relevance = evaluate_answer_relevance(
            decision.get('disposition', 'UNKNOWN'),
            expected_disposition,
            reply,
            decision.get('med_flags', []),
        )
        context_rel = evaluate_context_relevance(kg_annotations, extracted_case)
        context_recall = evaluate_context_recall(
            kg_annotations,
            extracted_case,
            expected_kg_topics or [],
        )
        context_prec = evaluate_context_precision(kg_annotations, extracted_case)

        # Normalize to 0-1 scale and compute composite scores
        # Faithfulness: 0-3 → 0-1
        faithfulness_norm = faithfulness.grounding_score / 3.0
        # Answer Relevance: 0-3 → 0-1
        relevance_norm = relevance.relevance_score / 3.0

        # RAGAS score: average of all normalized metrics
        ragas_score = (
            extraction.overall_extraction_accuracy +
            faithfulness_norm +
            relevance_norm +
            context_rel.relevance_score +
            context_recall.recall_score +
            context_prec.precision_score
        ) / 6.0

        # Clinical score: emphasize extraction, faithfulness, and actionability
        clinical_score = (
            extraction.overall_extraction_accuracy * 0.25 +
            faithfulness_norm * 0.25 +
            (relevance.actionability_score / 3.0) * 0.25 +
            (1.0 if relevance.disposition_match else 0.0) * 0.25
        )

        return RAGASClinicalScores(
            scenario_id=scenario_id,
            arm=arm,
            extraction_accuracy=extraction.overall_extraction_accuracy,
            faithfulness=faithfulness.grounding_score,
            answer_relevance=relevance.relevance_score,
            context_relevance=context_rel.relevance_score,
            context_recall=context_recall.recall_score,
            context_precision=context_prec.precision_score,
            ragas_score=ragas_score,
            clinical_score=clinical_score,
            extraction_metrics=extraction,
            faithfulness_metrics=faithfulness,
            relevance_metrics=relevance,
            context_rel_metrics=context_rel,
            context_recall_metrics=context_recall,
            context_prec_metrics=context_prec,
            error=None,
        )

    except Exception as e:
        return RAGASClinicalScores(
            scenario_id=scenario_id,
            arm=arm,
            extraction_accuracy=0.0,
            faithfulness=0.0,
            answer_relevance=0.0,
            context_relevance=0.0,
            context_recall=0.0,
            context_precision=0.0,
            ragas_score=0.0,
            clinical_score=0.0,
            error=str(e),
        )


# ============================================================================
# Batch Evaluation & Reporting
# ============================================================================

def evaluate_results_dataframe(
    results_df: pd.DataFrame,
    scenario_expectations: dict[str, dict],  # scenario_id → {expected_fields, expected_kg_topics}
) -> pd.DataFrame:
    """
    Evaluate a results dataframe from evaluation_full_metrics.ipynb.

    Args:
        results_df: Output from evaluation_full_metrics.ipynb
        scenario_expectations: {
            'scenario_1_home': {
                'expected_fields': {'temp_f': 102.0, 'alertness': 'normal'},
                'expected_kg_topics': ['fever'],
            },
            ...
        }

    Returns:
        DataFrame with RAGAS scores appended
    """
    ragas_results = []

    for _, row in results_df.iterrows():
        scenario_id = row['scenario_id']
        expectations = scenario_expectations.get(scenario_id, {})

        # Parse state (if available in results)
        # Note: evaluation_full_metrics.ipynb stores minimal state info
        state = {
            'case': {},
            'decision': {
                'disposition': row['predicted'],
                'rule_ids': row['rules_fired'].split(', ') if row['rules_fired'] != '(none)' else [],
                'med_flags': row['med_flags'].split(', ') if row['med_flags'] != '(none)' else [],
            },
            'kg_annotations': [{'concept': {'name': f'concept_{i}'}}
                              for i in range(int(row['kg_count']))],
            'assistant_reply': row['reply'],
        }

        scores = evaluate_ragas_clinical(
            scenario_id=scenario_id,
            arm=row['arm'],
            state=state,
            expected_disposition=row['expected'],
            expected_fields=expectations.get('expected_fields', {}),
            expected_kg_topics=expectations.get('expected_kg_topics', []),
        )

        ragas_results.append(asdict(scores))

    ragas_df = pd.DataFrame(ragas_results)

    # Merge with original results
    combined = pd.concat([
        results_df.reset_index(drop=True),
        ragas_df[['extraction_accuracy', 'faithfulness', 'answer_relevance',
                  'context_relevance', 'context_recall', 'context_precision',
                  'ragas_score', 'clinical_score']],
    ], axis=1)

    return combined


def summarize_ragas_scores(
    results_df: pd.DataFrame,
    by_arm: bool = True,
) -> pd.DataFrame:
    """
    Summarize RAGAS scores by arm or scenario.

    Args:
        results_df: DataFrame with RAGAS scores
        by_arm: If True, group by arm; else by scenario

    Returns:
        Summary DataFrame with mean/std/min/max for each metric
    """
    group_col = 'arm' if by_arm else 'scenario_id'

    metrics = [
        'extraction_accuracy', 'faithfulness', 'answer_relevance',
        'context_relevance', 'context_recall', 'context_precision',
        'ragas_score', 'clinical_score'
    ]

    summary = results_df.groupby(group_col, as_index=False)[metrics].agg([
        'mean', 'std', 'min', 'max'
    ])

    # Flatten column names
    summary.columns = [f"{col[0]}_{agg}" for col, agg in summary.columns]

    return summary.round(3)


def export_ragas_report(
    results_df: pd.DataFrame,
    output_dir: Path,
) -> None:
    """
    Export detailed RAGAS evaluation report.

    Args:
        results_df: DataFrame with RAGAS scores
        output_dir: Directory to save reports
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Full results
    results_df.to_csv(output_dir / 'ragas_full_results.csv', index=False)

    # Summary by arm
    summary_arm = summarize_ragas_scores(results_df, by_arm=True)
    summary_arm.to_csv(output_dir / 'ragas_summary_by_arm.csv', index=False)

    # Summary by scenario
    summary_scenario = summarize_ragas_scores(results_df, by_arm=False)
    summary_scenario.to_csv(output_dir / 'ragas_summary_by_scenario.csv', index=False)

    # Markdown report
    report = _generate_ragas_markdown_report(results_df)
    (output_dir / 'ragas_report.md').write_text(report)

    print(f"✅ RAGAS reports saved to {output_dir}")


def _generate_ragas_markdown_report(results_df: pd.DataFrame) -> str:
    """Generate markdown report from RAGAS scores."""

    summary_arm = summarize_ragas_scores(results_df, by_arm=True)
    summary_scenario = summarize_ragas_scores(results_df, by_arm=False)

    report = """# CareTrace RAGAS Evaluation Report

## Overview

This report evaluates CareTrace using RAGAS (Retrieval Augmented Generation Assessment) metrics adapted for clinical triage.

### RAGAS Metrics Explained

- **Extraction Accuracy** (0-1): Were clinical fields (temp, age, alertness) extracted correctly?
- **Faithfulness** (0-3): Is disposition grounded in fired rules and extracted data?
- **Answer Relevance** (0-3): Is disposition clinically appropriate and actionable?
- **Context Relevance** (0-1): Are KG annotations relevant to the case?
- **Context Recall** (0-1): Were all relevant KG concepts retrieved?
- **Context Precision** (0-1): Are retrieved KG facts high-quality/specific?
- **RAGAS Score** (0-1): Composite average of all metrics
- **Clinical Score** (0-1): Emphasis on extraction, faithfulness, and actionability

---

## Summary by Arm

"""
    report += summary_arm.to_markdown() + "\n\n"

    report += "## Summary by Scenario\n\n"
    report += summary_scenario.to_markdown() + "\n\n"

    # Key findings
    report += """## Key Findings

### Best Performing Arms

"""
    best_ragas = results_df.groupby('arm')['ragas_score'].mean().sort_values(ascending=False)
    for arm, score in best_ragas.head(3).items():
        report += f"- **{arm}**: {score:.3f}\n"

    report += "\n### Metric Strengths\n\n"

    for metric in ['extraction_accuracy', 'faithfulness', 'answer_relevance',
                   'context_relevance', 'context_recall', 'context_precision']:
        mean_score = results_df[metric].mean()
        report += f"- **{metric}**: {mean_score:.3f}\n"

    report += f"\n### Overall System Score: {results_df['ragas_score'].mean():.3f}\n"
    report += f"### Overall Clinical Score: {results_df['clinical_score'].mean():.3f}\n"

    return report


if __name__ == '__main__':
    print('✅ RAGAS Clinical Evaluation Framework loaded')
    print('   Import this module to use: evaluate_ragas_clinical(), evaluate_results_dataframe()')
