# CareTrace Evaluation Notebooks - Comprehensive Review

**Date:** June 3, 2026  
**Notebooks Reviewed:**
1. `evaluation_full_metrics.ipynb` - Deterministic scoring + multi-arm comparison
2. `evaluation_openai_judge.ipynb` - LLM-as-judge evaluation

---

## 📊 Current Evaluation Framework

### Strengths ✅

1. **Multi-Arm Comparison** (excellent)
   - Baseline Mock (deterministic rules only)
   - Baseline Ollama LLM (no rules, no KG)
   - CareTrace Rules Only (rules, no KG)
   - CareTrace Rules + KG
   - CareTrace Full Live (with LLM interpretation)
   - **Impact:** Isolates value of rules vs KG vs LLM

2. **Deterministic Rubric** (clinical-appropriate)
   - Safety Score (0-3): disposition accuracy + med flags
   - Actionability Score (0-3): concrete next steps, escalation triggers
   - Trust Score (0-3): justification, rule provenance
   - **Impact:** Reproducible, no API variance

3. **Real Scenarios** (5 clinical cases)
   - Cover HOME_MANAGEMENT, ER_NOW, URGENT_SAME_DAY
   - Include age-gated rules (5-month-old ibuprofen)
   - Include medication safety flags
   - Multi-turn conversations

4. **LLM-as-Judge** (secondary validation)
   - OpenAI gpt-4o-mini judge with structured JSON
   - Scoring rubric included in prompt
   - Error handling for malformed JSON
   - Useful for human-in-the-loop validation

### Weaknesses & Gaps ❌

1. **Limited Scenario Coverage** (CRITICAL)
   - Only 5 scenarios for 4 disposition types
   - No edge cases:
     - Newborn (<28 days) scenarios
     - Birth trauma/risk factors
     - Missing required fields (OUT_OF_SCOPE handling)
     - Contradictory inputs
     - Typos/encoding issues (tested in security_tests but not eval)
   - **Recommendation:** Expand to 15-20 scenarios minimum

2. **No Extraction Quality Metrics** (MISSING)
   - Does not measure if temperature/age/alertness extracted correctly
   - Only measures final disposition
   - Can't distinguish:
     - Rules working from correct extraction
     - Rules failing from poor extraction
   - **RAGAS Comparison:** RAGAS measures context relevance, which requires measuring extraction accuracy
   - **Recommendation:** Add extraction metrics:
     ```python
     - temp_extraction_accuracy
     - age_extraction_accuracy  
     - field_completeness (how many required fields extracted)
     - extraction_precision (correct vs wrong values)
     ```

3. **No Faithfulness/Groundedness Metrics** (MAJOR GAP)
   - Judge scores "trust" but doesn't measure:
     - Do fired rules actually justify the disposition?
     - Are med flags real (or hallucinated)?
     - Does KG evidence match extracted data?
   - **RAGAS Equivalent:** RAGAS has `faithfulness` metric
   - **Recommendation:** Add:
     ```python
     - rule_chain_validity: Do rule conditions match extracted fields?
     - med_flag_groundedness: Are flags based on actual patient data?
     - kg_evidence_relevance: Are KG annotations related to case?
     ```

4. **No Diversity/Coverage Metrics** (MISSING)
   - Doesn't measure:
     - How many unique rules triggered across scenarios?
     - Are all medication CPGs being tested?
     - Coverage of age ranges (3mo, 6mo, 1yr, 3yr, 5yr, 10yr)?
   - **Recommendation:** Add coverage analysis:
     ```python
     - rule_coverage_report: Which rules fired in tests?
     - age_distribution: Test cases by age group
     - cpg_coverage: Which medication rules triggered?
     ```

5. **No Failure Mode Analysis** (MISSING)
   - 5/5 accuracy reported but:
     - Baseline Ollama fails on 2/5 (40% → not deeply analyzed)
     - Why did scenario_2_er and scenario_5 fail for Ollama?
     - No error categorization (extraction vs rules vs KG)
   - **Recommendation:** Add error classification:
     ```python
     ERROR_CATEGORIES = {
         'extraction_failure': 'Required field extraction failed',
         'rule_not_fired': 'Data extracted but rule not triggered',
         'llm_confusion': 'LLM gave wrong disposition',
         'kg_lookup_fail': 'Neo4j unavailable or no results',
     }
     ```

6. **No Consistency/Stability Metrics** (MISSING)
   - Doesn't measure:
     - Same scenario run 10x → same result? (esp. with LLM arm)
     - Multi-turn stability (turn 1 vs turn 3 in same conversation)
   - **RAGAS Equivalent:** Doesn't directly have this, but important for clinical
   - **Recommendation:** Add:
     ```python
     - multi_run_stability: Run same scenario N times, measure disposition consistency
     - multi_turn_consistency: Track disposition changes across conversation
     ```

7. **No Clinical Validation** (MISSING)
   - Scenarios may not reflect real clinical practice
   - No clinician review of:
     - Are expected dispositions correct?
     - Do explanations match clinical reasoning?
     - Any safety concerns with any arm?
   - **Recommendation:** Have pediatrician review:
     - Scenario definitions
     - Expected dispositions
     - Sample explanations

8. **No Latency/Performance Metrics** (MISSING)
   - Doesn't measure:
     - Time to disposition (critical for ER cases)
     - LLM vs rules latency tradeoff
     - KG lookup time impact
   - **Recommendation:** Add:
     ```python
     - elapsed_time_per_arm
     - first_response_latency
     - kg_lookup_latency
     ```

---

## 📈 Comparison to RAGAS Framework

### RAGAS Metrics Overview
RAGAS (Retrieval Augmented Generation Assessment) provides 5 core metrics:

| RAGAS Metric | What It Measures | Your Framework | Gap |
|---|---|---|---|
| **Faithfulness** | Is generated text grounded in retrieved context? | ❌ Missing | Need rule→output chain validation |
| **Answer Relevance** | Is answer relevant to query? | ✅ Safety Score (partial) | Good but could be stronger |
| **Context Relevance** | Is retrieved context relevant to query? | ✅ KG Evidence (partial) | Only counts presence, not relevance |
| **Context Recall** | Does retrieved context contain answer facts? | ❌ Missing | Need to check if all relevant KG facts retrieved |
| **Context Precision** | Is retrieved context free of irrelevant info? | ❌ Missing | Need KG precision measurement |

### How Your Framework Differs (Better for Clinical)

1. **Clinical-Specific Rubric** ✅
   - RAGAS is generic LLM evaluation
   - Your Safety/Actionability/Trust rubric is domain-specific
   - Better for triage evaluation

2. **Symbolic Rules Integration** ✅
   - RAGAS doesn't handle rule-based systems
   - Your multi-arm comparison isolates rule vs KG vs LLM value
   - Excellent for neurosymbolic systems

3. **Medication Safety** ✅
   - RAGAS has no notion of safety flags
   - Your med_flags evaluation is clinical-appropriate

### How RAGAS Is Better (Your Gaps)

1. **Extraction Quality Measurement** 🔴
   - RAGAS measures if retrieved docs are relevant
   - You should measure if extracted fields are correct
   - Equivalent: extraction is like "retrieval" for clinical data

2. **Chain-of-Thought Validation** 🔴
   - RAGAS checks if generated text matches retrieval
   - You should check if disposition matches rule firing
   - Missing faithfulness check

3. **Statistical Rigor** 🟡
   - RAGAS supports 100+ test cases with aggregated metrics
   - You have 5 scenarios (too small for statistical significance)
   - Need confidence intervals

---

## 🎯 Recommended Additions

### Priority 1: CRITICAL (blocks publication)

```python
# 1. Extraction Accuracy Metrics
def evaluate_extraction_accuracy(state, expected_fields):
    """Measure if temp, age, alertness extracted correctly."""
    extracted = state.get('case', {})
    errors = {}
    for field, expected_val in expected_fields.items():
        actual_val = extracted.get(field)
        if actual_val != expected_val:
            errors[field] = {'expected': expected_val, 'actual': actual_val}
    return {
        'extraction_accuracy': 1.0 - (len(errors) / len(expected_fields)),
        'errors': errors,
        'field_completeness': sum(1 for f in expected_fields if extracted.get(f) is not None) / len(expected_fields),
    }

# 2. Rule Faithfulness Validation
def validate_rule_firing(decision, case, expected_disposition):
    """Check if fired rules actually justify disposition."""
    rule_ids = decision.get('rule_ids', [])
    disposition = decision.get('disposition')
    
    return {
        'rules_fired': rule_ids,
        'disposition_matches_rules': len(rule_ids) > 0 or disposition == 'OUT_OF_SCOPE',
        'unexpected_rule_combo': check_rule_conflicts(rule_ids),
    }

# 3. Expand Scenarios
SCENARIOS = [
    # Current 5
    # + Newborns
    {'age': '5 days', 'temp': 38.5, 'expected': 'ER_NOW'},  # Newborn fever
    {'age': '14 days', 'temp': 37.9, 'expected': 'ER_NOW'},  # Newborn monitoring
    # + Edge cases
    {'description': 'Contradictory inputs: fever + no fever', 'expected': 'OUT_OF_SCOPE'},
    {'description': 'Missing critical field (no temp)', 'expected': 'OUT_OF_SCOPE'},
    # + Medication rules
    {'age': '2 months', 'med': 'ibuprofen', 'expected': 'HOME_MANAGEMENT', 'flag': 'ibuprofen_age_gate'},
    # + KG-sensitive
    {'condition': 'chickenpox', 'med': 'aspirin', 'expected': 'ER_NOW', 'flag': 'contraindication'},
    # + Natural language variations
    {'description': 'drinkng water (typo)', 'expected': 'HOME_MANAGEMENT'},  # fuzzy match test
]
```

### Priority 2: HIGH (important for paper)

```python
# 1. Multi-Run Stability Test
def test_consistency(scenario, n_runs=10):
    """Run same scenario N times, measure disposition consistency."""
    results = []
    for _ in range(n_runs):
        result = run_tracemind_variant(scenario)
        results.append(result.get('disposition'))
    
    consensus_disposition = max(set(results), key=results.count)
    consistency_rate = results.count(consensus_disposition) / n_runs
    
    return {
        'consistency_rate': consistency_rate,
        'consensus': consensus_disposition,
        'variations': list(set(results)),
    }

# 2. Error Classification
ERROR_TAXONOMY = {
    'CORRECT': 'Correct disposition',
    'EXTRACTION_FAIL': 'Required field not extracted',
    'RULE_SILENT': 'Data correct but rule not fired',
    'RULE_WRONG': 'Wrong rule fired',
    'LLM_CONFUSION': 'LLM gave different disposition',
    'KG_SILENT': 'KG lookup failed or no results',
    'CONTRADICTION': 'Contradictory input detected but not handled',
}

# 3. Clinical Validation
def clinical_review_template(scenario, response):
    """Structured review for pediatrician."""
    return {
        'scenario': scenario,
        'expected_disposition': scenario.get('expected'),
        'predicted_disposition': response.get('disposition'),
        'clinician_review_q1': 'Is expected disposition clinically appropriate?',
        'clinician_review_q2': 'Is explanation medically sound?',
        'clinician_review_q3': 'Any safety concerns?',
        'clinician_score_safety_0_5': None,  # To be filled
    }
```

### Priority 3: MEDIUM (nice-to-have for paper)

```python
# 1. Coverage Report
def coverage_analysis(results_df):
    """Measure which rules/CPGs tested."""
    fired_rules = {}
    for rules_str in results_df['rules_fired']:
        for rule in rules_str.split(', '):
            if rule != '(none)':
                fired_rules[rule] = fired_rules.get(rule, 0) + 1
    
    return {
        'unique_rules_fired': len(fired_rules),
        'rule_frequency': fired_rules,
        'coverage_percentage': (len(fired_rules) / TOTAL_RULES) * 100,
    }

# 2. Performance Metrics
def performance_analysis(results_df):
    """Measure latency and resource usage."""
    return {
        'avg_time_per_turn_ms': results_df['elapsed_time_ms'].mean(),
        'kg_lookup_latency_ms': results_df['kg_lookup_time_ms'].mean(),
        'p95_latency_ms': results_df['elapsed_time_ms'].quantile(0.95),
    }

# 3. Sensitivity Analysis
def test_sensitivity():
    """How robust are decisions to input variations?"""
    # Test with typos
    # Test with temperature ± 0.5°F
    # Test with reordered turns
    # Test with abbreviated vs full descriptions
    pass
```

---

## 🔧 Implementation Roadmap

### Phase 1: Foundation (1-2 hours)
- [ ] Expand scenarios to 15-20 cases
- [ ] Add extraction accuracy measurement
- [ ] Add error classification to results
- [ ] Document expected values in scenarios.csv

### Phase 2: Validation (2-3 hours)
- [ ] Add rule faithfulness validation
- [ ] Add multi-run consistency test
- [ ] Add clinical review template (send to pediatrician)
- [ ] Add coverage report

### Phase 3: Polish (1-2 hours)
- [ ] Add performance metrics
- [ ] Add sensitivity analysis
- [ ] Create comparison plots (accuracy by arm, by scenario)
- [ ] Write evaluation results markdown

---

## 📝 Updated scenarios.csv Structure

```csv
id,expected_disposition,description,turns_json,expected_fields_json,sensitivity_notes
scenario_1_home,HOME_MANAGEMENT,...,["Turn 1: ..."],"{""temp_f"": 102.0, ""alertness"": ""normal""}",Standard case
scenario_newborn_fever,ER_NOW,...,["Turn 1: ..."],"{""age_days"": 5, ""temp_f"": 38.5}",Age-gated rule
scenario_contradictory,OUT_OF_SCOPE,...,["Turn 1: ..."],null,Contradiction detection test
```

---

## ✅ Validation Checklist

Before publishing evaluation:

- [ ] 15+ scenarios covering all disposition types
- [ ] Extraction accuracy measured per scenario
- [ ] Rule faithfulness validated (rules → disposition)
- [ ] Clinician review of expected dispositions
- [ ] Error analysis showing failure modes
- [ ] Multi-run stability tested for LLM arms
- [ ] Coverage report showing which rules/CPGs tested
- [ ] Performance metrics (latency, KG lookup time)
- [ ] Comparison plots for paper (accuracy by arm, rubric scores)
- [ ] Statistical significance (confidence intervals, p-values)

---

## 💡 Key Recommendations Summary

| Recommendation | Impact | Effort |
|---|---|---|
| Expand to 15+ scenarios | High (currently too small) | Medium |
| Add extraction accuracy | Critical (can't validate rules) | Low |
| Add rule faithfulness check | Critical (measure groundedness) | Medium |
| Clinical review of scenarios | High (domain validation) | Medium |
| Multi-run stability test | High (for LLM arms) | Low |
| Error taxonomy | Medium (understand failure modes) | Low |
| Performance metrics | Medium (for deployment) | Low |
| Coverage report | Medium (show CPG completeness) | Low |

---

## 📌 Final Thoughts

**What You're Doing Right:**
- Multi-arm comparison isolates component value (great for neurosymbolic systems)
- Clinical rubric (Safety/Actionability/Trust) is domain-appropriate
- Using LLM-as-judge for secondary validation is smart

**What's Missing:**
- Extraction quality measurement (can't validate if rules work without this)
- Faithfulness/groundedness checks (RAGAS core metric missing)
- Too few scenarios for statistical validity
- No error categorization (hard to debug failures)

**Next Step:**
Start with extraction accuracy metrics + expanding scenarios. These are quick wins that enable better evaluation of everything else.

---

**Generated:** June 3, 2026
