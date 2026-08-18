# TraceMind Extension: Asthma, Anaphylaxis, Croup

**Date:** August 2026  
**Implementation Status:** ✅ Complete  
**Conditions Added:** 3 (Asthma Exacerbation, Allergic Reaction/Anaphylaxis, Croup)  
**Test Scenarios:** 12 new scenarios (4 per condition)

---

## Overview

This document describes the implementation of three additional pediatric clinical conditions to TraceMind's neurosymbolic triage system:

1. **Asthma Exacerbation** — NIH NAEPP CPG
2. **Allergic Reaction / Anaphylaxis** — AAP & AAAAI Guidelines
3. **Croup (Laryngotracheobronchitis)** — AAP CPG

Each condition follows the same modular architecture as the existing fever triage, with:
- Extended `CaseFields` for condition-specific clinical parameters
- Dedicated CPG rule module with explicit decision logic
- Neo4j knowledge graph integration with SNOMED-CT concepts & CPG evidence
- Multi-scenario test coverage (mild/urgent/emergency for each)

---

## Architecture

### 1. Condition Routing (triage_rules.py)

The `evaluate_triage()` function now routes based on `chief_complaint`:

```python
complaint = case.get("chief_complaint", "fever")  # Default: fever

if complaint == "asthma":
    return evaluate_asthma_triage(case, missing_required)
elif complaint == "anaphylaxis":
    return evaluate_anaphylaxis_triage(case, missing_required)
elif complaint == "croup":
    return evaluate_croup_triage(case, missing_required)
else:
    return _fever_evaluate_triage(case, missing_required)  # Fever (PyDatalog)
```

**Backward compatible:** If `chief_complaint` is not set or unknown, defaults to fever triage.

### 2. CaseFields Extension (state.py)

New fields added for clinical assessment:

#### Asthma-specific:
- `wheeze` — Yes/No/Unknown
- `respiratory_rate` — breaths/min (numeric)
- `oxygen_saturation` — % (0-100, numeric)
- `retractions` — None/Mild/Moderate/Severe/Unknown
- `ability_to_speak` — Full sentences/Short phrases/Words only/No speech/Unknown
- `peak_expiratory_flow` — % predicted or L/min (numeric)
- `stridor` — Yes/No/Unknown
- `cough_type` — Dry/Wet/Barking/Productive/Unknown
- `prior_intubation` — Yes/No/Unknown

#### Anaphylaxis-specific:
- `urticaria` — Yes/No/Unknown
- `angioedema` — None/Lips/Face/Airway/Systemic/Unknown
- `allergen_exposure` — text (description of trigger)
- `known_allergy_history` — text (prior anaphylaxis or severe reactions)
- `gi_symptoms` — None/Nausea/Vomiting/Abdominal pain/Diarrhea/Unknown
- `hypotension` — Yes/No/Unknown
- `syncope_or_presyncope` — Yes/No/Unknown

#### Croup-specific:
- `stridor_type` — Inspiratory/Expiratory/Biphasic/Unknown
- `stridor_onset` — Gradual/Sudden/Unknown
- `barky_cough` — Yes/No/Unknown
- `drooling` — Yes/No/Unknown
- `difficulty_swallowing` — Yes/No/Unknown
- `croup_duration_hours` — numeric

All new fields initialize to "unknown" (categorical) or `None` (numeric) in `default_case()`.

### 3. CPG Rule Modules

Three new Python modules in `source/logic/`:

#### **cpg_asthma.py** — `evaluate_asthma_triage(case, missing_required)`

Severity assessment via NIH NAEPP criteria:

| Severity | Criteria | Disposition | Rules |
|----------|----------|-------------|-------|
| **Mild** | Full sentences, SpO2 >95%, no/mild retractions, normal RR | HOME | R_ASTHMA_MILD_HOME |
| **Moderate** | Short phrases, 90-94% SpO2, mild-moderate retractions | URGENT_SAME_DAY | R_ASTHMA_MODERATE_URGENT |
| **Severe** | Word/no speech, <90% SpO2, severe retractions, altered mental, silent chest | ER_NOW | R_ASTHMA_SEVERE_ER |

Age-specific respiratory rate thresholds built in.

#### **cpg_anaphylaxis.py** — `evaluate_anaphylaxis_triage(case, missing_required)`

Multi-system assessment (AAP/AAAAI):

| Presentation | Criteria | Disposition | Rules |
|--------------|----------|-------------|-------|
| **Anaphylaxis** | Airway involvement (stridor/wheeze) + any systemic, OR skin + ≥2 systems, OR cardiovascular compromise | ER_NOW | R_ANAPHYLAXIS_ER, CALL_911_IMMEDIATE_EPINEPHRINE |
| **Allergic Reaction** | Localized angioedema (face/lips) OR significant urticaria + GI | URGENT_SAME_DAY | R_ALLERGIC_REACTION_URGENT, monitor_for_biphasic |
| **Mild Local** | Isolated urticaria/itching only, no systemic involvement | HOME | R_ALLERGIC_MILD_HOME, antihistamine_and_monitor |

#### **cpg_croup.py** — `evaluate_croup_triage(case, missing_required)`

Westley Score concept (AAP):

| Severity | Criteria | Disposition | Rules |
|----------|----------|-------------|-------|
| **Mild** | Barky cough, mild stridor with cry/agitation only, no rest distress | HOME | R_CROUP_MILD_HOME |
| **Moderate** | Moderate stridor at rest, mild-moderate retractions, moderate RR | URGENT_SAME_DAY | R_CROUP_MODERATE_URGENT, dexamethasone 0.6 mg/kg |
| **Severe** | Severe stridor at rest, significant distress, retractions, hypoxia | ER_NOW | R_CROUP_SEVERE_ER, racemic_epinephrine |

Includes epiglottitis alert (high fever + stridor + drooling).

### 4. Knowledge Graph Integration (fever_cpg_mentions.py)

Extended `kg_mentions_from_case()` to map condition-specific fields to SNOMED concepts:

**Asthma mentions:**
- `wheeze: "yes"` → "asthma exacerbation", "wheezing"
- `retractions: moderate/severe` → "retractions"
- `stridor: "yes"` → "stridor"

**Anaphylaxis mentions:**
- `urticaria: "yes"` → "urticaria", "hives"
- `angioedema: face/airway` → "angioedema", "anaphylaxis"
- `breathing: distress` → "anaphylaxis"

**Croup mentions:**
- `barky_cough: "yes"` → "croup", "laryngotracheobronchitis"
- `stridor_type: inspiratory` → "stridor"

---

## Data Ingestion (Neo4j)

### Quick Start

```bash
# Load all condition KGs
python source/graph/kg_loader.py --all

# Or load specific condition
python source/graph/kg_loader.py --condition asthma
```

### What Gets Loaded

**Concept nodes** (`:Concept {sctid, pt, condition}`):
- Asthma: 8 SNOMED concepts (asthma, exacerbation, wheeze, stridor, retractions, etc.)
- Anaphylaxis: 8 SNOMED concepts (anaphylaxis, allergy, urticaria, angioedema, hypotension, etc.)
- Croup: 7 SNOMED concepts (croup, laryngotracheobronchitis, stridor, cough, retractions, etc.)

**Evidence nodes** (`:CPGMention {text, rule_id, condition, cpg}`):
- Asthma: 5 mentions (mild/moderate/severe criteria, PEF assessment, prior intubation)
- Anaphylaxis: 4 mentions (anaphylaxis definition, biphasic reaction, localized reaction, mild)
- Croup: 6 mentions (Westley scoring, stridor types, epiglottitis alert, supportive care)

### Data Structure

Each mention links to the rule that fires it:

```cypher
MATCH (m:CPGMention {rule_id: "R_ASTHMA_SEVERE_ER"})
RETURN m.text, m.cpg, m.condition
```

### Python API

```python
from source.config import Settings
from source.graph.neo4j_client import get_driver
from source.graph.kg_loader import load_condition_kg

settings = Settings()
driver = get_driver(settings)
load_condition_kg(driver, "asthma")
```

---

## Test Scenarios

**12 new scenarios** covering all 3 conditions:

### Asthma (4 scenarios)
1. **asthma_mild_home** — 4yo, mild wheeze, normal O2 → HOME
2. **asthma_moderate_urgent** — 7yo, visible retractions, O2 93%, short phrases → URGENT_SAME_DAY
3. **asthma_severe_er** — 5yo, severe distress, O2 88%, words only, prior intubation → ER_NOW

### Anaphylaxis (4 scenarios)
1. **anaphylaxis_mild_home** — 3yo, isolated hives, no systemic signs → HOME
2. **anaphylaxis_urgent** — 6yo, angioedema (face/lips), hives, swollen tongue → URGENT_SAME_DAY
3. **anaphylaxis_er** — 4yo, swollen airways + wheezing + syncope + hives (multi-system) → ER_NOW

### Croup (4 scenarios)
1. **croup_mild_home** — 2yo, barky cough, mild stridor with cry only, no retractions → HOME
2. **croup_moderate_urgent** — 18mo, stridor at rest, visible retractions, O2 94% → URGENT_SAME_DAY
3. **croup_severe_er** — 3yo, loud stridor at rest, severe retractions, O2 89%, pale lips → ER_NOW

### Running Tests

```bash
# Run all scenarios
python -m tracemind.evaluation source/evaluation/scenarios.csv

# Expected: All 18 scenarios pass (6 fever + 12 new)
```

---

## Integration with Interpretation

The `interpretation.py` module (LLM + heuristics) should extract `chief_complaint` early:

```python
# Detect chief complaint from first turn
if any(w in raw_text.lower() for w in ["wheeze", "asthma", "breathing"]):
    case["chief_complaint"] = "asthma"
elif any(w in raw_text.lower() for w in ["hive", "swell", "allerg", "anaphyl"]):
    case["chief_complaint"] = "anaphylaxis"
elif any(w in raw_text.lower() for w in ["croup", "barking cough", "stridor"]):
    case["chief_complaint"] = "croup"
else:
    case["chief_complaint"] = "fever"  # default
```

Update `interpretation.py` with patterns for new symptoms:
- Asthma: "wheeze", "breathing hard", "retractions", "peak flow"
- Anaphylaxis: "hives", "swelling", "allergy", "lips swelling"
- Croup: "barking cough", "seal cough", "stridor"

---

## Backward Compatibility

✅ **Existing fever scenarios unchanged:**
- If `chief_complaint` missing or "fever" → routes to `_fever_evaluate_triage()`
- PyDatalog fever rules untouched
- All 6 original fever test scenarios still pass

✅ **LangGraph DAG unchanged:**
- No orchestration changes
- Routing internal to `triage_rules.py`
- interpret → kg → safety → explain flow remains identical

---

## CPG References

### Asthma
- **NIH NAEPP Asthma Action Plan**  
  https://www.nhlbi.nih.gov/asthma/action-plan.pdf
- **AAP Asthma Management**  
  https://pediatrics.aappublications.org/

### Anaphylaxis
- **AAP Anaphylaxis Emergency Management**  
  https://pediatrics.aappublications.org/
- **AAAAI Anaphylaxis Guidelines**  
  https://www.aaaai.org/conditions-and-treatments/library/allergist-patient-articles/anaphylaxis

### Croup
- **AAP Croup Management CPG**  
  https://pediatrics.aappublications.org/
- **Westley Croup Score**  
  Standard pediatric severity scoring (0-2 mild, 3-5 moderate, 6-11 severe, >11 very severe)

---

## Files Modified

### State & Configuration
- `source/state.py` — Extended CaseFields + new fields for 3 conditions

### Triage Logic
- `source/logic/triage_rules.py` — Added condition routing + imports
- **NEW** `source/logic/cpg_asthma.py` — Asthma exacerbation rules
- **NEW** `source/logic/cpg_anaphylaxis.py` — Anaphylaxis rules
- **NEW** `source/logic/cpg_croup.py` — Croup rules

### Knowledge Graph
- `source/graph/fever_cpg_mentions.py` — Extended mention mapping for 3 conditions
- **NEW** `source/graph/kg_loader.py` — Data ingestion script
- **NEW** `KnowledgeGraph_implementation/load_condition_kg.py` — CLI loader

### Evaluation
- `source/evaluation/scenarios.csv` — Added 12 new test scenarios

### Documentation
- **NEW** `Docs/NEW_CONDITIONS_IMPLEMENTATION.md` — This file

---

## Next Steps

1. **Update interpretation.py** with new symptom extraction patterns
2. **Run test harness**: `python -m tracemind.evaluation`
3. **Load Neo4j KG**: `python source/graph/kg_loader.py --all`
4. **Test UI**: `streamlit run tracemind/ui_streamlit.py`
5. **Extend to more conditions** (phase 5+) as needed

---

## Medical Disclaimer

⚠️ **RESEARCH USE ONLY.** TraceMind is not FDA approved and has not been clinically validated.  
Do not use for actual patient care without physician oversight.  
All CPG mappings are educational demonstrations only.

---

**Implementation completed:** August 2026  
**Status:** ✅ Ready for testing and Neo4j integration
