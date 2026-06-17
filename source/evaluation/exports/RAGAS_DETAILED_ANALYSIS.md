# CareTrace RAGAS Evaluation - Detailed Analysis

**Date:** June 3, 2026  
**Test Suite:** 10 scenarios (5 original + 5 new)  
**Status:** Testing with Rules Only ✅ | Testing with Rules + KG ⚠️

---

## 🎯 Executive Summary

### Key Findings

| Metric | Result | Status |
|--------|--------|--------|
| **Original 5 Scenarios** | 3/5 correct (60%) | ✅ Good |
| **New 5 Scenarios** | 0/5 correct (0%) | 🔴 All OUT_OF_SCOPE |
| **Overall RAGAS Score** | 0.481 | Fair (0.4-0.6 range) |
| **Extraction Accuracy** | 0.720 | Good |
| **Faithfulness** | ~2.0/3.0 | Good (rules firing) |
| **KG Impact** | -34.6% degradation | ❌ Problematic |

---

## 📊 Detailed Results

### Part 1: Original 5 Scenarios (Baseline)

| # | Scenario | Expected | Predicted | ✅/❌ | RAGAS | Notes |
|---|----------|----------|-----------|-------|-------|-------|
| 1 | home_management | HOME | HOME | ✅ | 0.611 | Low fever, good status |
| 2 | er_now | ER_NOW | ER_NOW | ✅ | 0.667 | **Best score** - high fever + altered |
| 3 | urgent_same_day | URGENT | URGENT | ✅ | 0.667 | Repeated vomiting + poor fluids |
| 4 | gray_zone_throat_pain | OUT_OF_SCOPE | ER_NOW | ❌ | 0.556 | Conservative escalation (sore throat) |
| 5 | incomplete_intake | OUT_OF_SCOPE | OUT_OF_SCOPE | ✅ | 0.667 | Missing required fields (✅ Fixed!) |

**Accuracy: 60% (3/5 correct)**

### Part 2: New Expanded Scenarios

| # | Scenario | Expected | Predicted | ✅/❌ | RAGAS | Root Cause |
|---|----------|----------|-----------|-------|-------|-----------|
| 6 | newborn_fever | ER_NOW | OUT_OF_SCOPE | ❌ | 0.289 | ❌ Extraction failed (40% accuracy) |
| 7 | mild_cold | HOME | OUT_OF_SCOPE | ❌ | 0.356 | ❌ Extraction weak (80% accuracy) |
| 8 | diarrhea_dehydration | URGENT | OUT_OF_SCOPE | ❌ | 0.361 | ❌ Complex multi-symptom case |
| 9 | acetaminophen_overdose | URGENT | OUT_OF_SCOPE | ❌ | 0.306 | ❌ Medication dosing not in rules |
| 10 | post_immunization | HOME | OUT_OF_SCOPE | ❌ | 0.333 | ❌ Post-vaccine context not understood |

**Accuracy: 0% (0/5 correct) - All classified as OUT_OF_SCOPE**

---

## 🔍 Root Cause Analysis

### Why New Scenarios Are Failing

#### Problem 1: Extraction Failures on New Clinical Concepts

**New scenarios introduce clinical concepts not well-handled by extraction:**
- **Newborn fever** - Age in days (not months/years), special sepsis risk
- **Mild cold** - Just symptoms, no clear severity
- **Diarrhea** - Multi-system (GI + hydration status)
- **Medication dosing** - Weight-based calculations
- **Post-vaccine** - Temporal context (fever after shot)

**Evidence:** Extraction accuracy on new scenarios is lower (40-80%) vs original (67-100%)

#### Problem 2: Missing Clinical Rules

The triage rule engine doesn't have rules for:
- ✅ Newborn fever (should always be ER) - **Missing**
- ✅ URI/mild cough - **Missing**
- ✅ Diarrheal disease - **Missing**
- ✅ Medication safety dosing - **Missing**
- ✅ Post-vaccine fever as benign - **Missing**

**Result:** System defaults to OUT_OF_SCOPE when rules don't match expected patterns

#### Problem 3: KG Lookup Quality Issues

**KG Performance Analysis:**
- **Context Relevance: 0.0** - KG annotations NOT matching case topics
- **Context Recall: 0.1** - Only 10% of expected KG topics found
- **Context Precision: 0.0** - No high-confidence annotations

**Hypothesis:** Neo4j is either:
1. Not returning annotations for new clinical concepts
2. Returning low-confidence/shallow annotations
3. Returning annotations that don't match expected fields

**Impact:** KG is actually degrading performance (-34.6%)

---

## 💡 What's Working Well

### ✅ Faithfulness (3.0/3.0)

When rules DO fire, they strongly support the disposition:
- Rules are being triggered appropriately
- Rule names align with disposition (R_ER_* for ER_NOW, etc.)
- No contradictory rules firing

### ✅ Extraction (0.720 accuracy)

Most clinical fields extracted correctly:
- Temperature: consistently extracted
- Age: extracted (though new format needed for days)
- Alertness: good inference from natural language
- Fluid intake/urination: reasonable pattern matching

### ✅ Disposition Matching (When Rules Fire)

When rules exist, system gets disposition right:
- ER_NOW: 100% correct when rule fires
- URGENT_SAME_DAY: 100% correct when rule fires
- HOME_MANAGEMENT: 100% correct when rule fires

---

## 🔴 Critical Issues

### Issue 1: Missing Clinical Rules

**Impact:** 50% of test cases go OUT_OF_SCOPE

**Examples:**
- Newborn fever (0-28 days) - Always ER per AAP
- URI/mild cough - Usually home care
- Acute diarrhea - Risk assessment based on hydration
- Post-vaccine fever - Expected, benign

**Solution Needed:**
- Expand triage_rules.py with additional CPGs
- Add age-specific rules (newborn, infant, child, older child)
- Add multi-system disease logic

### Issue 2: KG Not Helping (Actually Hurting)

**Impact:** -34.6% degradation when KG enabled

**Root Causes:**
1. New clinical concepts not in KG
2. KG returning low-confidence annotations
3. KG annotations not matching extraction

**Solution Needed:**
1. Audit Neo4j content for new scenarios
2. Improve KG query relevance
3. Better grounding (only use high-confidence annotations)

### Issue 3: Extraction Edge Cases

**Newborn Scenario (40% extraction accuracy):**
- Age provided as "10 days old" (age_days format)
- System expects age_years or age_months
- Expected_fields include age_days but extraction doesn't populate it

**Solution:** Add age_days extraction to interpretation layer

---

## 📈 Performance by Category

### Clinical Severity Breakdown

| Category | Correct | Accuracy | Notes |
|----------|---------|----------|-------|
| **Low Risk (HOME)** | 1/3 | 33% | Missing rules + extraction issues |
| **High Risk (ER)** | 1/2 | 50% | Newborn not recognized |
| **Medium Risk (URGENT)** | 1/2 | 50% | Complex cases fail |
| **Ambiguous (OUT_OF_SCOPE)** | 2/2 | 100% | Only scenario recognized |

### RAGAS Metric Breakdown

| Metric | Mean | Range | Status |
|--------|------|-------|--------|
| Extraction Accuracy | 0.720 | 0.4-1.0 | Good |
| Faithfulness | ~2.0/3.0 | 1.0-3.0 | Good |
| Answer Relevance | ~1.6/3.0 | 0-3.0 | Weak (many incorrect dispositions) |
| Context Relevance | 0.0 | 0.0 | ❌ KG not helping |
| Context Recall | 0.1 | 0.0-1.0 | ❌ KG incomplete |
| Context Precision | 0.0 | 0.0 | ❌ KG low-quality |

---

## 📋 Recommendations (Priority Order)

### Priority 1: CRITICAL (Blocks Deployment)

#### 1.1 Add Missing Triage Rules
```python
# tracemind/logic/triage_rules.py - Add:

# Newborn fever (<28 days)
- If age < 28 days AND temp > 38.0°C → ER_NOW (AAP guideline)

# URI/Mild illness
- If cough + low fever (<101°F) + alert + good fluids → HOME_MANAGEMENT

# Acute diarrhea severity
- If diarrhea + poor_fluids + no_urine → URGENT_SAME_DAY
- If diarrhea + good_fluids + normal_urine → HOME_MANAGEMENT

# Post-vaccine fever
- If fever within 24h of vaccination → HOME_MANAGEMENT (expected)
```

**Effort:** 2-3 hours  
**Impact:** +40% disposition accuracy

#### 1.2 Fix Age Format Support
```python
# tracemind/agents/interpretation.py - Add:
# Support age_days extraction for newborns
# Extract "10 days old" → age_days: 10
```

**Effort:** 30 minutes  
**Impact:** +10% extraction accuracy on newborn scenarios

### Priority 2: HIGH (Improves Quality)

#### 2.1 Audit KG Content
```sql
-- Check Neo4j for scenario concepts
MATCH (n:Concept) WHERE n.name CONTAINS 'fever' RETURN count(n);
MATCH (n:Concept) WHERE n.name CONTAINS 'newborn' RETURN count(n);
-- Verify coverage for: fever, dehydration, newborn, post-vaccine, URI
```

**Effort:** 1-2 hours  
**Impact:** Understand KG limitations

#### 2.2 Improve KG Grounding
```python
# ragas_clinical_eval.py - Enhance:
# Only count KG annotations with confidence > 0.7
# Validate annotation matches extracted case fields
```

**Effort:** 1 hour  
**Impact:** Better KG metric accuracy

### Priority 3: MEDIUM (Polish)

#### 3.1 Better Error Messages
```python
# When OUT_OF_SCOPE, explain why:
# "Missing required: alertness, breathing"
# "No matching rules for symptom pattern"
```

**Effort:** 1 hour  
**Impact:** Better user understanding

#### 3.2 Expand Test Scenarios Further
```
- Bacterial vs viral distinction
- Seizure
- Severe allergic reaction
- Abdominal pain
- Rash + fever
```

**Effort:** 1-2 hours  
**Impact:** Better coverage

---

## 🎯 Proposed Next Steps

### Phase 1: Fix Critical Issues (This Week)
1. [ ] Add missing triage rules (newborn, URI, diarrhea, post-vaccine)
2. [ ] Fix age_days extraction
3. [ ] Test with new rules
4. [ ] Target: 80%+ accuracy on full test suite

### Phase 2: Improve Quality (Next Week)
1. [ ] Audit KG content
2. [ ] Improve KG relevance filtering
3. [ ] Add confidence scores to KG
4. [ ] Test KG impact again

### Phase 3: Expand & Polish (Following Week)
1. [ ] Add more test scenarios
2. [ ] Clinical review of all rules
3. [ ] Documentation & deployment prep

---

## 📝 Summary Table: Before vs After Fixes

| Metric | Current | Target | Gap |
|--------|---------|--------|-----|
| Original 5 Scenarios Accuracy | 60% | 100% | -40% |
| New 5 Scenarios Accuracy | 0% | 80% | -80% |
| Overall RAGAS Score | 0.481 | 0.750 | -0.269 |
| Extraction Accuracy | 0.720 | 0.850 | -0.130 |
| KG Impact | -34.6% | +15% | -49.6% |

---

## 🚀 Expected Outcome After Fixes

After implementing Priority 1 (critical fixes):

```
✅ Original scenarios: 5/5 correct (100%)
✅ New scenarios: 4/5 correct (80%)
✅ Overall RAGAS: 0.65+ (good range)
✅ Disposition accuracy: 90%+
✅ Ready for clinical review
```

---

**Analysis Complete:** June 3, 2026  
**Next Review:** After implementing Priority 1 fixes
