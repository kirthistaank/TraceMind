# Seattle Children’s — Fever CPG (integration notes)

**Source:** [Fever - Safety and Wellness - Seattle Children’s](https://www.seattlechildrens.org/health-safety/illness/fever)  
**Local copy:** `CPG Fever - Safety and Wellness - Seattle Children's.pdf`  
**Extracted text (for search / diff):** `CPG_Fever_Seattle_Childrens_extracted.txt` (regenerate with `python scripts/extract_cpg_pdf.py`)

## What we encoded in CareTrace

| CPG content (paraphrase) | Symbolic representation |
| --- | --- |
| Fever = temperature **over 100.4°F (38°C)** | Interpretation + explanation text; optional future: mark “fever” only if `temp_f` > 100.4 |
| **Call the doctor** — seizure | `seizure=yes` → `cpg_seizure` → **ER_NOW** (`R_CPG_SEIZURE`) |
| **Call the doctor** — **<3 months** with fever | `age_months<3` and `temp_f` > 100.4 → `cpg_infant_under_3mo_fever` → **ER_NOW** (`R_CPG_INFANT_UNDER_3MO_FEVER`) |
| **Call the doctor** — trouble breathing / breathing fast | `breathing=distress` → ER; `breathing=tachypnea_concern` → **URGENT_SAME_DAY** (`R_URGENT_TACHYPNEA_CONCERN`) |
| **Call the doctor** — not alert when awake (lethargic) | `alertness=altered` → **ER_NOW** (`R_ER_ALERTNESS`) |
| **Call the doctor** — **no urine in 8 hours** | `urine_last_8h=no` (with dehydration logic) → **ER_NOW** / severe dehydration gates |
| **Call the doctor** — fever **>3 days** | `fever_duration_hours` ≥ 72 → **URGENT_SAME_DAY** (`R_URGENT_FEVER_OVER_3_DAYS`) |
| **Call the doctor** — fever **>104°F** | `temp_f` ≥ 104 → **URGENT_SAME_DAY** (`R_URGENT_VERY_HIGH_FEVER`) |
| Medication: **no aspirin**; **no ibuprofen <6 mo** unless clinician; **no fever medicine <3 mo** unless clinician | `medication.py` + `med_flag` rules for ibuprofen / acetaminophen age gates |

**Not exhaustively modeled** (needs more fields or richer intake): localized pain, rash, immunocompromise, “3 months–2 years fever >24h with no other symptoms,” “vomiting >1 day” as distinct from repeated vomiting, etc. Extend `CaseFields` + `triage_rules.py` as your team formalizes scope.

## Medical disclaimer

Course prototype only — not a substitute for licensed clinical decision support.
