"""
RAGAS Test Harness for CareTrace.

Parses Test_scenario_main.txt and runs RAGAS evaluation.
No git commit - for local testing only.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Optional

import pandas as pd

from source.evaluation.ragas_clinical_eval import (
    evaluate_ragas_clinical,
    summarize_ragas_scores,
    export_ragas_report,
)
from source.orchestration.graph import run_turn
from source.state import CareTraceState, default_case


# ============================================================================
# Test Scenarios (from Test_scenario_main.txt)
# ============================================================================

TEST_SCENARIOS = {
    'scenario_1_home_management': {
        'expected_disposition': 'HOME_MANAGEMENT',
        'turns': [
            "My 6-year-old has a fever, threw up once, and looks really wiped out.",
            "Temp is 101.8. He's tired but answers me. No breathing issues. He's sipping water, not much though. He's been on medication for a recent ear infection.",
            "He's on amoxicillin. Last dose was earlier tonight. Just vomited once. He peed earlier this evening.",
        ],
        'expected_fields': {
            'temp_f': 101.8,
            'age_years': 6.0,
            'alertness': 'normal',  # "tired but answers me" = normal responsiveness
            'fluid_intake': 'poor',  # "sipping water, not much"
            'urine_last_8h': 'yes',  # "peed earlier this evening"
            'breathing': 'normal',  # "No breathing issues"
        },
        'expected_kg_topics': ['fever', 'vomiting', 'medication_interaction'],
    },
    'scenario_2_er_now': {
        'expected_disposition': 'ER_NOW',
        'turns': [
            "My 6-year-old has a fever, threw up, and looks really wiped out. I'm worried.",
            "Temp is 103.5. He's barely responding, just lying there. He doesn't want to drink. No trouble breathing. Also, there's been a stomach virus going around his school this week.",
            "I don't think he's peed since this afternoon.",
        ],
        'expected_fields': {
            'temp_f': 103.5,
            'age_years': 6.0,
            'alertness': 'altered',  # "barely responding, just lying there"
            'fluid_intake': 'poor',  # "doesn't want to drink"
            'urine_last_8h': 'no',  # "hasn't peed since afternoon"
            'breathing': 'normal',  # "No trouble breathing"
        },
        'expected_kg_topics': ['fever', 'high_fever', 'dehydration', 'altered_mental_status', 'viral_infection'],
    },
    'scenario_3_urgent_same_day': {
        'expected_disposition': 'URGENT_SAME_DAY',
        'turns': [
            "5 year old fever and vomiting",
            "he vomited 4 times in the last 2 hours and only sips",
            "102.5 fever, breathing fine, answers questions, he keeps throwing up and won't drink much, he peed an hour ago",
        ],
        'expected_fields': {
            'temp_f': 102.5,
            'age_years': 5.0,
            'alertness': 'normal',  # "answers questions"
            'fluid_intake': 'poor',  # "only sips", "won't drink much"
            'urine_last_8h': 'yes',  # "peed an hour ago"
            'breathing': 'normal',  # "breathing fine"
        },
        'expected_kg_topics': ['fever', 'repeated_vomiting', 'dehydration'],
    },
    'scenario_4_gray_zone_throat_pain': {
        'expected_disposition': 'OUT_OF_SCOPE',
        'turns': [
            "My 6-year-old has a fever and I'm scared. He says his throat hurts when he swallows.",
            "Temp is 101.2. He's tired but answers questions. Breathing seems normal, no wheezing.",
            "He refuses all fluids since dinner — says it hurts too much — but he did pee twice this evening.",
            "He only vomited once, about an hour ago.",
        ],
        'expected_fields': {
            'temp_f': 101.2,
            'age_years': 6.0,
            'alertness': 'normal',  # "tired but answers questions"
            'fluid_intake': 'poor',  # "refuses all fluids"
            'urine_last_8h': 'yes',  # "peed twice this evening"
            'breathing': 'normal',  # "breathing seems normal"
        },
        'expected_kg_topics': ['fever', 'sore_throat', 'possible_strep'],
        'notes': 'Gray zone: has fever + throat pain + vomiting. Unclear if needs urgent care (could be simple pharyngitis, could need UA for strep).',
    },
    'scenario_5_incomplete_intake': {
        'expected_disposition': 'OUT_OF_SCOPE',
        'turns': [
            "My 4-year-old has been sick tonight and I'm not sure what to do.",
            "She's warm and threw up once. I'm really worried.",
        ],
        'expected_fields': {
            'temp_f': None,  # Not provided
            'age_years': 4.0,
            'alertness': None,  # Not provided
            'fluid_intake': None,  # Not provided
            'urine_last_8h': None,  # Not provided
            'breathing': None,  # Not provided
        },
        'expected_kg_topics': [],
        'notes': 'Incomplete intake: missing temperature, alertness, fluids, urination, breathing.',
    },
    'scenario_6_newborn_fever': {
        'expected_disposition': 'ER_NOW',
        'turns': [
            "My baby is only 10 days old and has a fever.",
            "Temperature is 38.5°C, which is 101.3°F. He's sleeping a lot. No obvious infection. Last feeding was 3 hours ago.",
            "He's taking feeds okay when awake.",
        ],
        'expected_fields': {
            'temp_f': 101.3,
            'age_days': 10.0,
            'alertness': 'normal',  # "sleeping a lot" is normal for newborn
            'fluid_intake': 'good',  # "taking feeds okay"
            'urine_last_8h': 'yes',  # Implied from feeding
            'breathing': 'normal',
        },
        'expected_kg_topics': ['fever', 'newborn', 'early_infancy_sepsis_risk'],
        'notes': 'Newborns with fever always need ER evaluation per AAP guidelines.',
    },
    'scenario_7_mild_cold': {
        'expected_disposition': 'HOME_MANAGEMENT',
        'turns': [
            "My 4-year-old has a runny nose and mild cough.",
            "Temperature 99.5°F. He's playful, eating well, and breathing fine.",
            "He has been coughing for 2 days, mostly at night. No fever before today.",
        ],
        'expected_fields': {
            'temp_f': 99.5,
            'age_years': 4.0,
            'alertness': 'normal',  # "playful"
            'fluid_intake': 'good',  # "eating well"
            'urine_last_8h': None,  # Not mentioned but not concerning
            'breathing': 'normal',  # "breathing fine"
        },
        'expected_kg_topics': ['viral_upper_respiratory', 'mild_cough'],
        'notes': 'Mild URI with low fever and good status - home care appropriate.',
    },
    'scenario_8_diarrhea_dehydration': {
        'expected_disposition': 'URGENT_SAME_DAY',
        'turns': [
            "My 2-year-old has diarrhea and isn't keeping anything down.",
            "He's had diarrhea for 3 days. Temperature 100.5°F. He's acting tired and won't drink.",
            "Last urine was 8 hours ago. He's sunken eyes. Lips are a bit dry.",
        ],
        'expected_fields': {
            'temp_f': 100.5,
            'age_years': 2.0,
            'alertness': 'normal',  # "tired" but responsive (not altered)
            'fluid_intake': 'poor',  # "won't drink"
            'urine_last_8h': 'no',  # "8 hours ago"
            'breathing': 'normal',
        },
        'expected_kg_topics': ['diarrhea', 'dehydration', 'gastroenteritis'],
        'notes': 'Moderate dehydration (sunken eyes, dry lips, decreased urine) - needs same-day IV fluids.',
    },
    'scenario_9_acetaminophen_overdose_risk': {
        'expected_disposition': 'URGENT_SAME_DAY',
        'turns': [
            "My 5-year-old has a fever and I gave him Tylenol.",
            "Temperature was 102.5°F 2 hours ago. I gave him 500mg acetaminophen. He's alert and breathing well.",
            "He weighs 40 lbs (18 kg). I gave him another 500mg 30 minutes ago because the fever came back.",
        ],
        'expected_fields': {
            'temp_f': 102.5,
            'age_years': 5.0,
            'alertness': 'normal',  # "alert"
            'fluid_intake': 'good',
            'urine_last_8h': 'yes',
            'breathing': 'normal',  # "breathing well"
        },
        'expected_kg_topics': ['fever', 'acetaminophen', 'dosing_calculation'],
        'notes': 'Dosing concern: 1000mg in 2.5 hours may exceed max for 18kg child (5000mg/day max). Needs pharmacist review.',
    },
    'scenario_10_post_immunization_fever': {
        'expected_disposition': 'HOME_MANAGEMENT',
        'turns': [
            "My 2-month-old got vaccinations today and now has a fever.",
            "Temperature is 38.2°C (100.8°F). He's fussy but feeding okay. No rash.",
            "Fever started 4 hours after shots. He's having normal wet diapers.",
        ],
        'expected_fields': {
            'temp_f': 100.8,
            'age_months': 2.0,
            'alertness': 'normal',  # "fussy" is expected post-vaccine
            'fluid_intake': 'good',  # "feeding okay"
            'urine_last_8h': 'yes',  # "normal wet diapers"
            'breathing': 'normal',
        },
        'expected_kg_topics': ['post_vaccination_fever', 'expected_adverse_reaction'],
        'notes': 'Fever within 24h of vaccination is common and expected. Home care with monitoring appropriate.',
    },
}


# ============================================================================
# Test Harness Functions
# ============================================================================

def run_tracemind_on_scenario(
    turns: list[str],
    skip_neo4j: bool = True,
    use_mock_llm: bool = True,
) -> dict:
    """
    Run CareTrace on a scenario.

    Args:
        turns: List of caregiver messages (multi-turn)
        skip_neo4j: If True, don't use Neo4j KG
        use_mock_llm: If True, use mock LLM (fast); else use real LLM

    Returns:
        Final state with decision, case fields, etc.
    """
    state: CareTraceState = {
        'messages': [],
        'case': default_case(),
        'kg_annotations': [],
        'turn': 0,
    }

    # Set environment
    os.environ['TRACEMIND_SKIP_NEO4J'] = '1' if skip_neo4j else '0'
    os.environ['TRACEMIND_MOCK_LLM'] = '1' if use_mock_llm else '0'

    # Run each turn
    for i, turn_text in enumerate(turns, start=1):
        state['raw_user_text'] = turn_text
        msgs = list(state.get('messages') or [])
        msgs.append({'role': 'user', 'content': turn_text})
        state['messages'] = msgs

        # Run turn
        state = run_turn(state)

    return state


def evaluate_scenario(
    scenario_id: str,
    scenario_config: dict,
    run_args: dict | None = None,
) -> dict:
    """
    Evaluate a single scenario with RAGAS.

    Args:
        scenario_id: Scenario identifier
        scenario_config: Config dict with turns, expected_disposition, expected_fields
        run_args: Kwargs for run_tracemind_on_scenario (skip_neo4j, use_mock_llm)

    Returns:
        Dict with evaluation results
    """
    run_args = run_args or {}

    # Run CareTrace
    state = run_tracemind_on_scenario(
        scenario_config['turns'],
        **run_args,
    )

    # Evaluate with RAGAS
    ragas_scores = evaluate_ragas_clinical(
        scenario_id=scenario_id,
        arm='tracemind_rules_kg_off' if run_args.get('skip_neo4j', True) else 'tracemind_rules_kg_on',
        state=state,
        expected_disposition=scenario_config['expected_disposition'],
        expected_fields=scenario_config['expected_fields'],
        expected_kg_topics=scenario_config.get('expected_kg_topics', []),
    )

    return {
        'scenario_id': scenario_id,
        'config': scenario_config,
        'state': state,
        'ragas_scores': ragas_scores,
    }


def run_full_test_suite(
    scenarios: dict[str, dict] | None = None,
    skip_neo4j: bool = True,
) -> pd.DataFrame:
    """
    Run full RAGAS test suite on all scenarios.

    Args:
        scenarios: Dict of scenarios to test (default: TEST_SCENARIOS)
        skip_neo4j: If True, test without KG; else test with KG

    Returns:
        DataFrame with all RAGAS scores
    """
    scenarios = scenarios or TEST_SCENARIOS
    results = []

    for scenario_id, config in scenarios.items():
        print(f"\n🔄 Testing {scenario_id}...")
        try:
            result = evaluate_scenario(
                scenario_id,
                config,
                run_args={'skip_neo4j': skip_neo4j},
            )
            scores = result['ragas_scores']

            predicted_disp = (
                scores.faithfulness_metrics.disposition
                if scores.faithfulness_metrics
                else 'UNKNOWN'
            )

            results.append({
                'scenario_id': scenario_id,
                'expected_disposition': config['expected_disposition'],
                'predicted_disposition': predicted_disp,
                'disposition_correct': predicted_disp == config['expected_disposition'],
                'extraction_accuracy': scores.extraction_accuracy,
                'faithfulness': scores.faithfulness,
                'answer_relevance': scores.answer_relevance,
                'context_relevance': scores.context_relevance,
                'context_recall': scores.context_recall,
                'context_precision': scores.context_precision,
                'ragas_score': scores.ragas_score,
                'clinical_score': scores.clinical_score,
                'error': scores.error,
            })
            print(f"  ✅ RAGAS Score: {scores.ragas_score:.3f}")
        except Exception as e:
            print(f"  ❌ Error: {e}")
            results.append({
                'scenario_id': scenario_id,
                'expected_disposition': config['expected_disposition'],
                'predicted_disposition': None,
                'error': str(e),
            })

    return pd.DataFrame(results)


def generate_test_report(results_df: pd.DataFrame, output_dir: Path | str) -> str:
    """
    Generate detailed test report.

    Returns:
        Report text
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Filter out error rows for summary
    valid_results = results_df[results_df['error'].isna()].copy()

    # Summary (only if we have valid results)
    if len(valid_results) > 0:
        summary = f"Valid results: {len(valid_results)}/{len(results_df)}"
    else:
        summary = "No valid results"

    # Report
    report = "# RAGAS Test Suite Results\n\n"
    report += f"**Date:** {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"

    report += "## Summary Statistics\n\n"
    report += f"- Total scenarios tested: {len(results_df)}\n"
    report += f"- Valid results: {len(valid_results)}\n"

    if len(valid_results) > 0:
        report += f"- Correct dispositions: {valid_results['disposition_correct'].sum()}/{len(valid_results)}\n"
        report += f"- Mean RAGAS Score: {valid_results['ragas_score'].mean():.3f}\n"
        report += f"- Mean Clinical Score: {valid_results['clinical_score'].mean():.3f}\n"
        report += f"- Mean Extraction Accuracy: {valid_results['extraction_accuracy'].mean():.3f}\n\n"

        report += "## Per-Scenario Results\n\n"
        display_cols = [
            'scenario_id', 'expected_disposition', 'predicted_disposition',
            'disposition_correct', 'ragas_score', 'clinical_score',
            'extraction_accuracy', 'faithfulness'
        ]
        results_display = valid_results[display_cols].copy()
        results_display = results_display.round(3)
        report += results_display.to_markdown(index=False) + "\n\n"

        report += "## Metric Breakdown\n\n"
        metrics = [
            'extraction_accuracy', 'faithfulness', 'answer_relevance',
            'context_relevance', 'context_recall', 'context_precision'
        ]
        for metric in metrics:
            if metric in valid_results.columns:
                mean_val = valid_results[metric].mean()
                report += f"- **{metric}**: {mean_val:.3f}\n"
    else:
        report += "⚠️  No valid results to report\n\n"

    # Show errors if any
    if len(results_df) > len(valid_results):
        report += "\n## Errors\n\n"
        error_rows = results_df[results_df['error'].notna()]
        for _, row in error_rows.iterrows():
            report += f"- **{row['scenario_id']}**: {row['error']}\n"

    # Save
    report_path = output_dir / 'ragas_test_report.md'
    report_path.write_text(report)
    results_df.to_csv(output_dir / 'ragas_test_results.csv', index=False)

    print(f"\n📄 Report saved to {report_path}")

    return report


# ============================================================================
# Main Entry Point
# ============================================================================

if __name__ == '__main__':
    import sys

    print("=" * 80)
    print("CareTrace RAGAS Test Harness - Comprehensive Suite")
    print("=" * 80)

    output_dir = Path('tracemind/evaluation/exports')
    output_dir.mkdir(parents=True, exist_ok=True)

    # Test 1: Without KG (baseline)
    print("\n" + "=" * 80)
    print("TEST 1: Rules Only (No KG)")
    print("=" * 80)
    print(f"\n🚀 Running {len(TEST_SCENARIOS)} scenarios without Neo4j...")
    results_kg_off = run_full_test_suite(TEST_SCENARIOS, skip_neo4j=True)

    print("\n📊 Generating KG-off report...")
    report_kg_off = generate_test_report(results_kg_off, output_dir)

    # Test 2: With KG (if available)
    has_neo4j = bool(os.environ.get('NEO4J_URI_KGA'))

    if has_neo4j:
        print("\n" + "=" * 80)
        print("TEST 2: Rules + KG (Neo4j Enabled)")
        print("=" * 80)
        print(f"\n🚀 Running {len(TEST_SCENARIOS)} scenarios with Neo4j...")
        try:
            results_kg_on = run_full_test_suite(TEST_SCENARIOS, skip_neo4j=False)

            print("\n📊 Generating KG-on report...")
            report_kg_on = generate_test_report(results_kg_on, output_dir)

            # Comparison
            print("\n" + "=" * 80)
            print("COMPARISON: Rules Only vs Rules + KG")
            print("=" * 80)
            kg_off_mean = results_kg_off['ragas_score'].mean()
            kg_on_mean = results_kg_on['ragas_score'].mean()
            improvement = kg_on_mean - kg_off_mean

            print(f"\nRules Only (KG off):  {kg_off_mean:.3f}")
            print(f"Rules + KG (KG on):   {kg_on_mean:.3f}")
            print(f"Improvement:          {improvement:+.3f} ({(improvement/kg_off_mean)*100:+.1f}%)")

            # Save comparison
            comparison = f"""# RAGAS Evaluation: KG Impact Analysis

## Summary

**Rules Only (No KG)**
- RAGAS Score: {kg_off_mean:.3f}
- Clinical Score: {results_kg_off['clinical_score'].mean():.3f}
- Extraction Accuracy: {results_kg_off['extraction_accuracy'].mean():.3f}
- Disposition Accuracy: {(results_kg_off['disposition_correct'].sum() / len(results_kg_off))*100:.1f}%

**Rules + KG (Neo4j Enabled)**
- RAGAS Score: {kg_on_mean:.3f}
- Clinical Score: {results_kg_on['clinical_score'].mean():.3f}
- Extraction Accuracy: {results_kg_on['extraction_accuracy'].mean():.3f}
- Disposition Accuracy: {(results_kg_on['disposition_correct'].sum() / len(results_kg_on))*100:.1f}%

## KG Impact

- RAGAS Score Improvement: {improvement:+.3f} ({(improvement/kg_off_mean)*100:+.1f}%)
- Context Relevance: {results_kg_on['context_relevance'].mean():.3f}
- Context Recall: {results_kg_on['context_recall'].mean():.3f}
- Context Precision: {results_kg_on['context_precision'].mean():.3f}

## Interpretation

{"🎉 KG significantly improves system performance!" if improvement > 0.05 else "⚠️  KG has minimal impact on this test set" if improvement > -0.05 else "❌ KG slightly hurts performance (investigate)"}
"""
            (output_dir / 'ragas_kg_comparison.md').write_text(comparison)
            print(f"\n📄 Comparison saved to ragas_kg_comparison.md")

        except Exception as e:
            print(f"\n⚠️  Neo4j test failed: {e}")
            print("   Run tests with KG disabled...")
    else:
        print("\n⚠️  NEO4J_URI_KGA not set - skipping KG tests")
        print("    To test with KG, set environment variables:")
        print("    export NEO4J_URI_KGA=bolt://localhost:7687")
        print("    export NEO4J_USERNAME_KGA=neo4j")
        print("    export NEO4J_PASSWORD_KGA=your_password")

    # Final summary
    print("\n" + "=" * 80)
    print("FINAL TEST SUMMARY")
    print("=" * 80)
    print(f"\nTotal scenarios tested: {len(TEST_SCENARIOS)}")
    print(f"Mean RAGAS Score: {results_kg_off['ragas_score'].mean():.3f}")
    print(f"Mean Clinical Score: {results_kg_off['clinical_score'].mean():.3f}")
    print(f"Disposition Accuracy: {(results_kg_off['disposition_correct'].sum() / len(results_kg_off))*100:.1f}%")

    print(f"\n✅ RAGAS test harness complete!")
    print(f"📊 Results saved to: {output_dir}")
    print(f"\n📄 Generated files:")
    print(f"   - ragas_test_results.csv (full results)")
    print(f"   - ragas_test_report.md (summary report)")
    if has_neo4j:
        print(f"   - ragas_kg_comparison.md (KG impact analysis)")
