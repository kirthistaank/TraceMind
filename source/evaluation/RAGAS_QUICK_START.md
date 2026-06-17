# RAGAS Quick Start - Test Your CareTrace

This guide shows how to quickly test RAGAS evaluation using the scenarios from `Test_scenario_main.txt`.

## 5-Minute Setup

### Option 1: Run Test Harness (Recommended)

```bash
cd tracemind
python -c "
from tracemind.evaluation.ragas_test_harness import run_full_test_suite, generate_test_report
from pathlib import Path

# Run all 5 test scenarios
results = run_full_test_suite()

# Generate report
generate_test_report(results, Path('tracemind/evaluation/exports'))

# Print summary
print('\n🎯 SUMMARY')
print(f'RAGAS Score: {results[\"ragas_score\"].mean():.3f}')
print(f'Clinical Score: {results[\"clinical_score\"].mean():.3f}')
print(f'Disposition Accuracy: {(results[\"disposition_correct\"].sum() / len(results))*100:.0f}%')
"
```

**Output:**
- `tracemind/evaluation/exports/ragas_test_results.csv` - Full results
- `tracemind/evaluation/exports/ragas_test_report.md` - Summary report

### Option 2: Jupyter Notebook

```bash
jupyter notebook tracemind/evaluation/ragas_evaluation_example.ipynb
```

Then modify the notebook to use `TEST_SCENARIOS` from ragas_test_harness:

```python
from tracemind.evaluation.ragas_test_harness import TEST_SCENARIOS

scenario_expectations = {
    sid: {
        'expected_fields': cfg['expected_fields'],
        'expected_kg_topics': cfg.get('expected_kg_topics', []),
    }
    for sid, cfg in TEST_SCENARIOS.items()
}
```

---

## Test Scenarios Included

### 1. **scenario_1_home_management** ✅
- 6-year-old, fever 101.8°F
- Tired but responsive
- Vomiting, poor fluid intake, normal breathing
- **Expected:** HOME_MANAGEMENT
- **Why:** Low-risk fever with clear safety netting available

### 2. **scenario_2_er_now** 🚨
- 6-year-old, fever 103.5°F
- Barely responding (altered mental status)
- Refusing fluids, no urine since afternoon
- **Expected:** ER_NOW
- **Why:** High fever + altered alertness + dehydration = emergency

### 3. **scenario_3_urgent_same_day** ⚠️
- 5-year-old, fever 102.5°F
- Normal alertness, normal breathing
- Repeated vomiting (4x in 2 hours), poor fluids
- **Expected:** URGENT_SAME_DAY
- **Why:** Repeated vomiting with dehydration = urgent but not ER

### 4. **scenario_4_gray_zone_throat_pain** ❓
- 6-year-old, fever 101.2°F
- Sore throat (difficult to swallow)
- Normal breathing, normal alertness
- **Expected:** OUT_OF_SCOPE
- **Why:** Presents like strep, but triage rules may not cover sore throat protocol

### 5. **scenario_5_incomplete_intake** ❌
- 4-year-old, sick, warm
- Only vomiting reported once
- Missing: temperature, alertness, fluid status, urination, breathing
- **Expected:** OUT_OF_SCOPE
- **Why:** Incomplete information - can't make triage decision

---

## What Gets Measured

For each scenario, you'll see:

```
scenario_1_home_management
├─ Disposition Match: ✅ (predicted HOME_MANAGEMENT vs expected HOME_MANAGEMENT)
├─ Extraction Accuracy: 0.87/1.0 (extracted temp, age, alertness, etc.)
├─ Faithfulness: 2.5/3.0 (rules fired and support disposition)
├─ Answer Relevance: 2.5/3.0 (disposition appropriate + actionable)
├─ Context Relevance: 0.67/1.0 (KG annotations relevant)
├─ Context Recall: 0.75/1.0 (found expected KG topics)
├─ Context Precision: 0.80/1.0 (KG facts are specific)
└─ RAGAS Score: 0.75/1.0 (composite metric)
```

---

## Interpreting Results

### Overall Scores

| Score | Interpretation |
|-------|---|
| 0.8-1.0 | Excellent - production ready |
| 0.6-0.8 | Good - solid performance |
| 0.4-0.6 | Fair - has issues to address |
| 0.0-0.4 | Poor - needs significant work |

### Metric Insights

**Extraction Accuracy Low?**
- Check if natural language patterns are understood
- May need fuzzy matching or synonym expansion
- See Phase 2 enhancements in PHASE2_IMPLEMENTATION.md

**Faithfulness Low?**
- Rules not firing correctly
- Rules don't match expected disposition
- Check rule definitions in tracemind/logic/triage_rules.py

**Answer Relevance Low?**
- Disposition is wrong (incorrect triage)
- Response is not actionable
- Explanation lacks clarity

**Context Relevance Low?**
- KG annotations not matching case
- Neo4j lookup returning irrelevant facts
- Consider improving KG queries

---

## Customizing Tests

### Add Your Own Scenario

```python
# In ragas_test_harness.py, add to TEST_SCENARIOS:

TEST_SCENARIOS['my_custom_scenario'] = {
    'expected_disposition': 'HOME_MANAGEMENT',
    'turns': [
        'Turn 1 message from caregiver',
        'Turn 2 message...',
        'Turn 3 message...',
    ],
    'expected_fields': {
        'temp_f': 101.5,
        'age_years': 3.0,
        'alertness': 'normal',
        'fluid_intake': 'good',
        'urine_last_8h': 'yes',
        'breathing': 'normal',
    },
    'expected_kg_topics': ['fever', 'viral_infection'],
}
```

### Test Without KG

```python
# Run without Neo4j
results = run_full_test_suite(skip_neo4j=True)
```

### Test With KG

```python
# Run with Neo4j (requires NEO4J_* env vars set)
results = run_full_test_suite(skip_neo4j=False)
```

---

## Common Issues & Solutions

### "ModuleNotFoundError: No module named 'tracemind'"

**Solution:** Run from CareTrace directory:
```bash
cd tracemind
python -c "from tracemind.evaluation.ragas_test_harness import ..."
```

### "KeyError: expected_fields"

**Solution:** Add ground truth to TEST_SCENARIOS:
```python
TEST_SCENARIOS['my_scenario']['expected_fields'] = {
    'temp_f': 102.0,
    'age_years': 6.0,
    ...
}
```

### "Neo4j connection failed"

**Solution:** Set skip_neo4j=True or configure Neo4j:
```bash
export NEO4J_URI_KGA=bolt://localhost:7687
export NEO4J_USERNAME_KGA=neo4j
export NEO4J_PASSWORD_KGA=your_password
```

---

## Next Steps

1. ✅ Run `python ragas_test_harness.py` to test all scenarios
2. 📊 Review `ragas_test_report.md` for detailed results
3. 🔍 Identify which metrics are low
4. 🛠️ Make improvements (extraction, rules, KG)
5. 🔄 Retest to measure improvements

---

## File Reference

| File | Purpose |
|------|---------|
| `ragas_test_harness.py` | Main test runner (this is what you execute) |
| `ragas_clinical_eval.py` | RAGAS evaluation framework |
| `ragas_evaluation_example.ipynb` | Detailed notebook walkthrough |
| `Test_scenario_main.txt` | Clinical scenarios (source material) |
| `RAGAS_README.md` | Full documentation |

---

## One-Liner Quick Test

```bash
cd tracemind && python -c "from tracemind.evaluation.ragas_test_harness import run_full_test_suite, generate_test_report; results = run_full_test_suite(); generate_test_report(results, 'tracemind/evaluation/exports'); print(f'\n📊 RAGAS Score: {results[\"ragas_score\"].mean():.3f}, Clinical: {results[\"clinical_score\"].mean():.3f}')"
```

---

**No git commits needed.** Just local testing to verify your evaluation framework is working correctly.
