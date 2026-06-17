# CareTrace RAGAS Clinical Evaluation Framework

This module implements RAGAS (Retrieval Augmented Generation Assessment) metrics adapted for pediatric triage evaluation.

## Overview

### What is RAGAS?

RAGAS is a framework for evaluating RAG (Retrieval Augmented Generation) systems. It measures:
1. **Faithfulness** - Is output grounded in retrieved context?
2. **Answer Relevance** - Is answer relevant to query?
3. **Context Relevance** - Is retrieved context relevant?
4. **Context Recall** - Are all necessary facts retrieved?
5. **Context Precision** - Is retrieved context high-quality?

### Adapted for CareTrace

We've adapted RAGAS for clinical triage by mapping:

| Original RAGAS | CareTrace Equivalent | Measure |
|---|---|---|
| Faithfulness | Rule Grounding | Do fired rules explain disposition? |
| Answer Relevance | Disposition Appropriateness | Is triage decision clinically sound? |
| Context Relevance | KG Relevance | Are Neo4j annotations relevant to case? |
| Context Recall | KG Completeness | Were all relevant KG topics retrieved? |
| Context Precision | KG Quality | Are KG annotations high-confidence? |

**Plus Clinical-Specific Metrics:**
- **Extraction Accuracy** (0-1) - Did we extract temp/age/alertness correctly?
- **Clinical Score** (0-1) - Composite focusing on clinical actionability

---

## Files

### Core Module
- **`ragas_clinical_eval.py`** (~400 lines)
  - Evaluation functions for each metric
  - Data classes for structured results
  - Batch processing and reporting utilities
  - **Import:** `from tracemind.evaluation.ragas_clinical_eval import evaluate_ragas_clinical`

### Example Notebook
- **`ragas_evaluation_example.ipynb`**
  - Step-by-step walkthrough
  - How to load results from `evaluation_full_metrics.ipynb`
  - How to interpret scores
  - Custom analysis queries

### Documentation
- **`RAGAS_README.md`** (this file)
- **`EVALUATION_REVIEW.md`** - Detailed review of your existing evaluation

---

## Quick Start

### Step 1: Run Your Existing Evaluation

```bash
# From CareTrace folder
cd tracemind
jupyter notebook tracemind/evaluation/evaluation_full_metrics.ipynb

# Export results to CSV
# (notebook should save to tracemind/evaluation/exports/results_full_metrics.csv)
```

### Step 2: Run RAGAS Evaluation

```bash
jupyter notebook tracemind/evaluation/ragas_evaluation_example.ipynb
```

### Step 3: Extract RAGAS Metrics

```python
from tracemind.evaluation.ragas_clinical_eval import (
    evaluate_ragas_clinical,
    evaluate_results_dataframe,
)

# Define ground truth for scenarios
scenario_expectations = {
    'scenario_1_home': {
        'expected_fields': {
            'temp_f': 102.0,
            'age_years': 6.0,
            'alertness': 'normal',
        },
        'expected_kg_topics': ['fever'],
    },
}

# Add RAGAS scores to your results
ragas_results = evaluate_results_dataframe(
    results_df,  # Your results from evaluation_full_metrics.ipynb
    scenario_expectations,
)

# Extract metrics
print(f"RAGAS Score: {ragas_results['ragas_score'].mean():.3f}")
print(f"Clinical Score: {ragas_results['clinical_score'].mean():.3f}")
```

---

## Metric Definitions

### 1. Extraction Accuracy (0-1)

**What it measures:** Did we correctly extract clinical fields from user input?

**Scoring:**
- Temperature within ±0.5°F of expected: ✓
- Age within ±1 month of expected: ✓
- Alertness matches expected: ✓
- Fluid intake, urination, breathing correct: ✓

**Score = (# correct fields) / 6**

**Why it matters:** 
- Without correct extraction, rules can't work properly
- Foundation for all downstream metrics
- Validates NLU layer

### 2. Faithfulness (0-3)

**What it measures:** Is the disposition grounded in fired rules and extracted data?

**Scoring:**
- +1 if any rules fired (not relying on LLM alone)
- +1 if rule names match disposition (e.g., "R_ER_*" for ER_NOW)
- +1 if med flags are based on extracted data

**Score: 0-3**

**Interpretation:**
- 0 = No rule justification (pure LLM)
- 1 = Weak rule support
- 2 = Good rule + data support
- 3 = Excellent grounding

**Why it matters:**
- Measures explainability (can we justify the decision?)
- Validates rule engine is actually being used
- Clinical requirement: decisions must be traceable

### 3. Answer Relevance (0-3)

**What it measures:** Is the response clinically appropriate and actionable?

**Scoring:**
- +1 if disposition matches ground truth
- +1 if response includes safety language (for ER/URGENT cases)
- +1 if actionability score ≥ 2 (clear next steps)

**Score: 0-3**

**Why it matters:**
- Primary clinical outcome
- Measures if caregiver can actually act on the response
- Combines correctness + usability

### 4. Context Relevance (0-1)

**What it measures:** Are retrieved KG annotations relevant to the case?

**Scoring:**
- For each KG annotation, check if it matches case topics
- Topics derived from extracted data (fever → temp, dehydration → poor fluids, etc.)
- **Score = (# relevant annotations) / (total annotations)**

**Range: 0-1**

**Why it matters:**
- Validates Neo4j lookup is finding relevant facts
- Prevents "noisy" KG that confuses decision-making

### 5. Context Recall (0-1)

**What it measures:** Were all relevant KG facts retrieved for the case?

**Scoring:**
- Define expected topics for each scenario (e.g., ["fever", "dehydration"])
- Check if any KG annotation covers each topic
- **Score = (# topics found) / (# expected topics)**

**Range: 0-1**

**Example:**
- Expected: ["fever", "dehydration", "altered mental status"]
- Retrieved: fever ✓, dehydration ✓, altered mental status ✗
- Recall = 2/3 = 0.667

**Why it matters:**
- Completeness of KG coverage
- Identifies gaps in knowledge graph
- Important for rare conditions

### 6. Context Precision (0-1)

**What it measures:** Are retrieved KG facts high-quality/specific?

**Scoring:**
- Annotations deep in hierarchy (many ancestors) = high confidence
- Shallow annotations (few ancestors) = low confidence
- **Score = (# high-confidence) / (total annotations)**

**Why it matters:**
- Prevents overly general/vague annotations
- Favors specific, actionable KG facts

---

## Output Formats

### Single Case Evaluation

```python
scores = evaluate_ragas_clinical(
    scenario_id='scenario_1',
    arm='tracemind_rules_kg_on',
    state=state_dict,
    expected_disposition='HOME_MANAGEMENT',
    expected_fields={'temp_f': 102.0, ...},
)

# Access individual metrics
print(scores.extraction_accuracy)  # 0.87
print(scores.faithfulness)  # 2.5
print(scores.ragas_score)  # 0.75
print(scores.clinical_score)  # 0.82
```

### Batch Evaluation

```python
ragas_results = evaluate_results_dataframe(
    results_df,
    scenario_expectations,
)

# Returns DataFrame with columns:
# - extraction_accuracy, faithfulness, answer_relevance
# - context_relevance, context_recall, context_precision
# - ragas_score, clinical_score
# - error (if evaluation failed)
```

### Summary Reports

```python
export_ragas_report(ragas_results, output_dir)

# Generates:
# - ragas_full_results.csv (detailed results)
# - ragas_summary_by_arm.csv (aggregated by arm)
# - ragas_summary_by_scenario.csv (aggregated by scenario)
# - ragas_report.md (markdown summary)
```

---

## Integration with evaluation_full_metrics.ipynb

The RAGAS framework works with existing evaluation results:

1. **Run evaluation_full_metrics.ipynb** to generate:
   - Baseline mock results
   - Baseline Ollama results
   - CareTrace (rules only) results
   - CareTrace (rules + KG) results
   - CareTrace (full live) results

2. **Export results to CSV:**
   ```python
   results_df.to_csv('exports/results_full_metrics.csv', index=False)
   ```

3. **Run RAGAS evaluation:**
   ```python
   ragas_results = evaluate_results_dataframe(results_df, scenario_expectations)
   ```

4. **Analyze:**
   ```python
   # By arm
   ragas_results.groupby('arm')['ragas_score'].mean()
   
   # By scenario
   ragas_results.groupby('scenario_id')['ragas_score'].mean()
   
   # Best/worst cases
   ragas_results.nlargest(5, 'ragas_score')
   ragas_results.nsmallest(5, 'ragas_score')
   ```

---

## Interpreting Results

### Overall RAGAS Score (0-1)

**Composite of all metrics, normalized to 0-1:**

- 0.0-0.3: Needs significant work
- 0.3-0.6: Functional but has gaps
- 0.6-0.8: Good performance
- 0.8-1.0: Excellent

### Clinical Score (0-1)

**Emphasizes extraction, faithfulness, and actionability:**

- Extraction accuracy: 25%
- Faithfulness: 25%
- Actionability: 25%
- Correct disposition: 25%

---

## Common Queries

### "Which arm performs best?"

```python
ragas_results.groupby('arm')['ragas_score'].mean().sort_values(ascending=False)
```

### "Which scenarios are hardest?"

```python
ragas_results.groupby('scenario_id')['ragas_score'].mean().sort_values(ascending=False)
```

### "Where are extraction failures?"

```python
extraction_failures = ragas_results[ragas_results['extraction_accuracy'] < 0.5]
extraction_failures[['scenario_id', 'arm', 'extraction_accuracy']]
```

### "How much does KG help?"

```python
kg_off = ragas_results[ragas_results['arm'].str.contains('kg_off')]
kg_on = ragas_results[ragas_results['arm'].str.contains('kg_on')]

print(f"KG Off: {kg_off['ragas_score'].mean():.3f}")
print(f"KG On:  {kg_on['ragas_score'].mean():.3f}")
print(f"Improvement: {(kg_on['ragas_score'].mean() - kg_off['ragas_score'].mean()):.3f}")
```

### "Do correct dispositions have better metrics?"

```python
correct = ragas_results[ragas_results['correct'] == True]
incorrect = ragas_results[ragas_results['correct'] == False]

print(f"Correct:   {correct['ragas_score'].mean():.3f}")
print(f"Incorrect: {incorrect['ragas_score'].mean():.3f}")
```

---

## Implementation Notes

### Extraction Accuracy Heuristics

The evaluation uses heuristic matching for extracted fields:
- Temperature: within ±0.5°F
- Age: within ±1 month
- Categorical fields: exact match

For production evaluation, you may want stricter thresholds.

### KG Relevance Scoring

Currently uses keyword matching on concept names:
- Case topics derived from extracted fields
- Annotations checked against topics

Consider replacing with embeddings-based similarity for production.

### Faithfulness Heuristics

Rule support validation is rule-name-based:
- Rules with "ER" in name → ER_NOW disposition
- Rules with "URGENT" in name → URGENT_SAME_DAY
- Rules with "HOME" in name → HOME_MANAGEMENT

Customize the `disposition_rule_expectations` dict for your rules.

---

## Extending the Framework

### Add Custom Metrics

```python
@dataclass
class CustomMetrics:
    score: float
    details: dict

def evaluate_custom(state, expected):
    # Your custom evaluation logic
    return CustomMetrics(...)

# Add to RAGASClinicalScores
```

### Add Domain-Specific Scoring

```python
# For pediatric-specific concerns
def evaluate_age_gated_rules(decision, extracted_case):
    """Measure if age-gated medication rules fired correctly."""
    age = extracted_case.get('age_months', 100)
    
    # Check for age-specific safety flags
    ...
```

### Connect to External Judge

```python
from langchain_openai import ChatOpenAI

def evaluate_with_llm_judge(case, decision, openai_key):
    """Use GPT-4 for additional validation."""
    ...
```

---

## Troubleshooting

### "Missing scenario expectations"

Add ground truth for all scenarios in `scenario_expectations` dict:
```python
scenario_expectations['my_scenario'] = {
    'expected_fields': {...},
    'expected_kg_topics': [...],
}
```

### "KG metrics all zero"

Ensure your `state` dict includes KG annotations:
```python
state['kg_annotations'] = result.get('kg_annotations', [])
```

### "Extraction accuracy always 0"

Check that `expected_fields` match the keys in CareTrace's extracted case:
- `temp_f` not `temperature`
- `age_years` or `age_months`
- `alertness`, `fluid_intake`, `urine_last_8h`, `breathing`

---

## Next Steps

1. **Run the example notebook** to familiarize yourself with metrics
2. **Define scenario expectations** for your test cases
3. **Export reports** for analysis
4. **Customize heuristics** for your specific rules
5. **Consider adding** clinician validation on top of RAGAS scores

---

## Citation

Based on RAGAS: A Package for Retrieval Augmented Generation Assessment
- Paper: https://arxiv.org/abs/2309.15217
- Adapted for clinical neurosymbolic systems

---

**Last Updated:** June 3, 2026
