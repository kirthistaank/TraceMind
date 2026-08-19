# 🩺 TraceMind

**Neurosymbolic AI-Driven Pediatric Triage — Research Prototype**

A research-grade neurosymbolic system demonstrating secure LLM integration with symbolic reasoning, knowledge graphs, and comprehensive security hardening. Originally a UC Berkeley final project, significantly enhanced post-graduation with production-grade architecture, enterprise-level security practices, and audit logging capabilities.

[License: MIT](LICENSE)
[Python 3.9+](https://www.python.org/downloads/)
[Security: Hardened](security_tests/reports/)
[Status: Research Prototype](#status--scope)

---

## 🎯 Overview

TraceMind demonstrates a **neurosymbolic approach to clinical triage**, combining:

- **Natural language processing** via LLM for parent/caregiver communication
- **Symbolic reasoning** using PyDatalog rule engine for explicit logic
- **Knowledge graphs** (SNOMED-CT) for evidence-based decision support
- **Comprehensive audit trails** for transparency and compliance

**Scope:** Pediatric triage across **4 clinical conditions**:

- 🌡️ **Fever** + GI symptoms + dehydration (NIH/Seattle Children's CPG) 
- 🫁 **Asthma Exacerbation** with severity stratification (NIH NAEPP CPG)
- 🔴 **Allergic Reaction / Anaphylaxis** with multi-system assessment (AAP/AAAAI)
- 🛑 **Croup (Laryngotracheobronchitis)** with airway assessment (AAP CPG)

**Ages:** 3 months - 12 years  
**Purpose:** Research demonstration showcasing secure, explainable neurosymbolic AI in healthcare  
**Origins:** UC Berkeley final project, enhanced post-graduation with production-grade security & architecture

**What it demonstrates:**

- ✅ **Modular CPG architecture** (4 conditions, expandable for more)
- ✅ **Secure LLM integration** (jailbreak & injection resistant)
- ✅ **Transparent decision logic** (rule traces & audit logs)
- ✅ **Production-grade architecture** (LangGraph, audit trails, validation)
- ✅ **Clinical safety patterns** (medication flags, antibiotic stewardship)



### Key Technical Features


| Feature                 | Details                                                                             |
| ----------------------- | ----------------------------------------------------------------------------------- |
| **Condition Routing**   | Chief complaint detection (fever/asthma/anaphylaxis/croup) → condition-specific CPG |
| **LLM Interpretation**  | Parent input → structured CaseFields (30+ clinical parameters, condition-aware)     |
| **Knowledge Graph**     | SNOMED-CT concepts + CPG evidence for all 4 conditions via Neo4j                    |
| **Symbolic Reasoning**  | Condition-specific rule engines (PyDatalog fever + dedicated CPG modules)           |
| **Explainability**      | Decision rationale linked to rules fired + evidence retrieved + CPG basis           |
| **Audit Logging**       | Immutable audit trail (timestamps, rules, evidence, user input, condition)          |
| **Input Validation**    | Range checking (age, vitals), fuzzy matching, contradiction detection               |
| **Security Hardened**   | Jailbreak-resistant prompts, injection-defended extraction, input sanitization      |
| **Multi-turn Tracking** | Conversation context, consistency validation, field accumulation across turns       |


---



## 🩺 Supported Clinical Conditions



### 1. 🌡️ Fever (Pediatric Fever Management)

- **CPG:** NIH/Seattle Children's Hospital CPG
- **Assessment:** Temperature, alertness, breathing, fluid intake, urination, dehydration risk
- **Dispositions:** Home Management, Urgent Same-Day, ER Now
- **Special Rules:** Infant <3mo fever rule, seizure monitoring, antibiotic stewardship



### Extended Usecases:



### 2. 🫁 Asthma Exacerbation (Respiratory Emergency)

- **CPG:** NIH NAEPP (National Asthma Education & Prevention Program)
- **Assessment:** Wheeze, oxygen saturation, speech ability, retractions, respiratory rate
- **Severity:** Mild (home) → Moderate (urgent) → Severe (ER)
- **Special Rules:** Hypoxia alert, altered mental status, prior intubation history



### 3. 🔴 Allergic Reaction / Anaphylaxis (Immune Emergency)

- **CPG:** AAP/AAAAI (American Academy of Pediatrics / American Academy of Allergy)
- **Assessment:** Urticaria, angioedema, breathing, GI symptoms, cardiovascular signs
- **Discrimination:** Mild hives (home) vs significant reaction (urgent) vs anaphylaxis (ER/CALL 911)
- **Special Rules:** Multi-system assessment, biphasic reaction monitoring, epinephrine alert



### 4. 🛑 Croup (Laryngotracheobronchitis - Airway Emergency)

- **CPG:** AAP Croup Management (Westley scoring concept)
- **Assessment:** Barky cough, stridor type (inspiratory/biphasic), retractions, oxygen, vocal ability
- **Severity:** Mild (home) → Moderate (dexamethasone+urgent) → Severe (ER)
- **Special Rules:** Epiglottitis alert (high fever + stridor + drooling), racemic epinephrine for ER



### Test Scenarios

Each condition includes **3 preset scenarios** (12 total):

- ✅ **Home Management:** Mild presentation, safe for home care
- ✅ **Urgent Same-Day:** Moderate severity, needs same-day evaluation
- ✅ **ER Now:** Severe presentation or red flags, emergency transport

📋 See `[Docs/PRESET_SCENARIOS.txt](Docs/PRESET_SCENARIOS.txt)` for all 12 scenarios with turn-by-turn examples.

---



## 🔐 Security & Quality

**Comprehensive Security Testing:**

- ✅ **6 LLM prompt injection vectors** — all blocked
- ✅ **19 adversarial attack cases** — all defended
- ✅ **100+ attack scenario catalog** — thoroughly tested
- ✅ **Input validation suite** — range & format checking
- ✅ **Contradiction detection** — multi-turn consistency

📋 **See** `[security_tests/reports/](security_tests/reports/)` for detailed findings and proof of hardening.

---



## 🏗️ Architecture

```
User Input (natural language)
        ↓
  ┌─────────────────────┐
  │  Interpretation     │  LLM or heuristics → CaseFields
  │  (tracemind/agents) │  (age, temp, alertness, fluids, urine)
  └──────────┬──────────┘
             ↓
  ┌─────────────────────┐
  │  Knowledge Graph    │  SNOMED-CT retrieval
  │  (tracemind/graph)  │  Neo4j mini-KG for fever CPG
  └──────────┬──────────┘
             ↓
  ┌─────────────────────┐
  │  Safety Logic       │  PyDatalog rules
  │  (tracemind/logic)  │  Triage rules (R_CPG_SEIZURE, etc.)
  └──────────┬──────────┘
             ↓
  ┌─────────────────────┐
  │  Explanation        │  Clinical rationale + safety netting
  │  (tracemind/agents) │  Medication flags & guidance
  └──────────┬──────────┘
             ↓
  Disposition (ER_NOW, URGENT_SAME_DAY, HOME_MANAGEMENT)
  + Explanation + Audit Log
```

**See** `[Docs/ARCHITECTURE.md](Docs/ARCHITECTURE.md)` for detailed control flow.

---



## 📊 Project Structure

```
tracemind/
├── README.md                          (this file)
├── requirements.txt                   (dependencies)
├── .env.example                       (configuration template)
│
├── 📁 tracemind/                      (Python package)
│   ├── main.py                        (CLI entry point)
│   ├── ui_streamlit.py                (Web UI)
│   ├── config.py                      (settings & env handling)
│   ├── state.py                       (case state management)
│   │
│   ├── 📁 agents/                     (LLM & heuristic agents)
│   │   ├── interpretation.py          (natural language → CaseFields)
│   │   ├── explanation.py             (decision rationale)
│   │   └── medication.py              (safety flags)
│   │
│   ├── 📁 graph/                      (Knowledge graph retrieval - condition-aware)
│   │   ├── neo4j_client.py            (Neo4j driver)
│   │   ├── snomed_retrieval.py        (SNOMED-CT lookups)
│   │   ├── fever_cpg_mentions.py      (fever CPG mapping)
│   │   ├── kg_loader.py               (load SNOMED-CT + CPG concepts for all conditions)
│   │   └── condition_kg_mappings.py   (asthma/anaphylaxis/croup KG integration)
│   │
│   ├── 📁 logic/                      (Symbolic reasoning & CPG rules)
│   │   ├── triage_rules.py            (condition routing + PyDatalog fever rules)
│   │   ├── cpg_asthma.py              (NIH NAEPP asthma severity assessment)
│   │   ├── cpg_anaphylaxis.py         (AAP/AAAAI anaphylaxis logic)
│   │   ├── cpg_croup.py               (AAP croup (Westley) assessment)
│   │   ├── contradiction_detector.py  (consistency checking)
│   │   └── multiturn_consistency.py   (conversation tracking)
│   │
│   ├── 📁 orchestration/              (LangGraph workflow)
│   │   └── graph.py                   (interpret → KG → safety → explain)
│   │
│   ├── 📁 audit/                      (Compliance & logging)
│   │   └── postgres_logger.py         (Neon Postgres audit trail)
│   │
│   └── 📁 evaluation/                 (Testing & benchmarking)
│       ├── scenarios.csv              (test case catalog)
│       ├── harness.py                 (evaluation runner)
│       └── ragas_test_harness.py      (RAGAS metric evaluation)
│
├── 📁 security_tests/                 (Security testing)
│   ├── README.md                      (security suite documentation)
│   ├── 📁 test_scripts/               (runnable tests)
│   │   ├── test_adversarial.py        (19 adversarial cases)
│   │   ├── test_prompt_injection_llm.py (6 injection tests)
│   │   └── debug_llm_extraction.py    (diagnostic tools)
│   └── 📁 reports/                    (security findings - SHOWCASE)
│       ├── SECURITY_AUDIT_SUMMARY.md
│       ├── ADVERSARIAL_TEST_CASES.md
│       ├── LLM_PROMPT_INJECTION_REPORT.md
│       ├── VULNERABILITY_FINDINGS.md
│       └── PHASE1_TEST_RESULTS.md
│
├── 📁 Docs/                           (Documentation)
│   ├── ARCHITECTURE.md                (detailed architecture)
│   ├── CPG Fever - Seattle Children's.pdf
│   └── screenshots/
│
├── 📁 KG_implementation/              (Knowledge graph setup)
│   └── Pediatric_Fever_KG_*.ipynb    (Jupyter notebooks)
│
└── 📁 scripts/                        (Utility scripts)
    └── extract_cpg_pdf.py             (PDF extraction)
```

---



## 🚀 Quick Start



### Prerequisites

- Python 3.9+
- pip or conda



### Installation

```bash
# Clone and navigate
cd TraceMind/tracemind

# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate          # macOS/Linux
# or
.venv\Scripts\activate              # Windows

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
```



### Run Interactive CLI

```bash
# Mock mode (no LLM or Neo4j required)
TRACEMIND_MOCK_LLM=1 TRACEMIND_SKIP_NEO4J=1 python -m tracemind.main

# With OpenAI + Neo4j (set .env first)
python -m tracemind.main
```



### Run Web UI (Streamlit)

```bash
# Mock mode
TRACEMIND_MOCK_LLM=1 TRACEMIND_SKIP_NEO4J=1 streamlit run tracemind/ui_streamlit.py

# With OpenAI + Neo4j
streamlit run tracemind/ui_streamlit.py
```

Open browser to `http://localhost:8501`

---



## 🧪 Testing



### Run Security Tests

```bash
# All tests
python -m security_tests.test_scripts.test_adversarial
python -m security_tests.test_scripts.test_prompt_injection_llm
python -m security_tests.test_scripts.debug_llm_extraction

# View security reports
ls -lh security_tests/reports/
```



### Run Scenario Evaluation

```bash
TRACEMIND_MOCK_LLM=1 TRACEMIND_SKIP_NEO4J=1 python -m tracemind.evaluation

# Custom scenario file
python -m tracemind.evaluation path/to/scenarios.csv
```

**Expected:** Exit code 0 when all scenarios match expected disposition.

---



## 🔧 Configuration



### Environment Variables

```bash
# LLM Configuration
OPENAI_API_KEY=sk-...              # OpenAI API key
OPENAI_MODEL=gpt-4                 # Model name

# Neo4j Graph Database
NEO4J_URI=neo4j+s://instance.databases.neo4j.io
NEO4J_USER=neo4j
NEO4J_PASSWORD=...
NEO4J_DATABASE=neo4j               # Leave unset for default

# Audit Logging
DATABASE_URL=postgresql://user:password@host/dbname

# Feature Flags
TRACEMIND_MOCK_LLM=1               # Use mock LLM (no API key needed)
TRACEMIND_SKIP_NEO4J=1             # Skip graph retrieval
TRACEMIND_EXIT_ON_COMPLETE=1       # Exit CLI after disposition
TRACEMIND_USE_LAG=1                # Use Logic-Augmented Generation
```

---



## 📖 Documentation

- **[ARCHITECTURE.md](Docs/ARCHITECTURE.md)** — Detailed control flow & module interactions
- **[SECURITY AUDIT](security_tests/reports/SECURITY_AUDIT_SUMMARY.md)** — Security findings & hardening proof
- **[CPG Reference](Docs/CPG_Fever_Seattle_Childrens_reference.md)** — Fever CPG mapping
- **[Demo Video](https://youtu.be/OlysHYbYaqU)** — Interactive system walkthrough. (not included in huggingface portal. Refer back to portfolio page)

---



## ⚕️ Status & Scope



### What This Is

- **Original:** UC Berkeley final project for pediatric fever triage
- **Enhancement:** Significantly improved post-graduation with security hardening, architecture refinement, and production-grade practices
- **Purpose:** Research demonstration of secure, explainable neurosymbolic AI in healthcare
- **Current Status:** Research prototype with enterprise-level security
- **Not intended for:** Direct clinical use without comprehensive validation



### Scope Limitations

- **Clinical scope:** Fever + GI symptoms + dehydration (limited bundle)
- **Age range:** Pediatric only (3 months - 12 years)
- **Data:** Limited to Seattle Children's CPG (not comprehensive)
- **Validation:** No clinical validation in real-world settings
- **Deployment:** Requires additional clinical testing before any patient-facing use



### Medical Disclaimer

**RESEARCH USE ONLY.** TraceMind is **not** a substitute for licensed clinical decision support or medical advice. This system:

- ❌ Is not FDA approved or cleared
- ❌ Has not been validated in clinical practice
- ❌ Should not be used for actual patient care without physician oversight
- ❌ Does not replace clinical judgment

Use only for research, demonstration, and proof-of-concept purposes under appropriate supervision.

### Technical Compliance Features

While **not clinically validated**, the system demonstrates compliance-minded patterns:

- ✅ Immutable audit trail logging
- ✅ No sensitive data exposed in UI
- ✅ All decisions traceable to rules & evidence
- ✅ Input validation & sanitization
- ✅ Jailbreak & injection resistance



### Future Enhancements (for actual deployment)

To prepare for real clinical use, would require:

1. **Clinical validation** — Testing against real patient data
2. **Expanded scope** — Additional symptoms, age groups, conditions
3. **Regulatory approval** — FDA clearance or equivalent
4. **Integration testing** — EHR systems, clinical workflows
5. **Clinician validation** — Review by practicing pediatricians
6. **Continuous monitoring** — Real-world performance tracking

---



## 👨‍💻 Development



### Adding a New Rule

1. Edit `tracemind/logic/triage_rules.py`
2. Define predicate and rule trace ID:
  ```python
   def R_CUSTOM_RULE(case_fields):
       # Rule logic
       return disposition, rule_ids, med_flags
  ```
3. Add test case in `security_tests/test_scripts/test_adversarial.py`
4. Run tests: `python -m security_tests.test_scripts.test_adversarial`



### Adding LLM Support

1. Update extraction patterns in `tracemind/agents/interpretation.py`
2. Test with `debug_llm_extraction.py`:
  ```bash
   python -m security_tests.test_scripts.debug_llm_extraction
  ```
3. Add test scenario to `tracemind/evaluation/scenarios.csv`

---



## 📚 References

- **Seattle Children's Fever CPG** — Integrated in `Docs/`
- **SNOMED-CT** — Knowledge graph foundation
- **LangGraph** — Orchestration framework
- **Neo4j** — Graph database backend
- **PyDatalog** — Logic programming engine

---



## 📝 License

MIT License — See LICENSE file for details.

---



## 📞 Support

For questions or issues:

1. Check `[Docs/ARCHITECTURE.md](Docs/ARCHITECTURE.md)`
2. Review `[security_tests/reports/](security_tests/reports/)` for security findings
3. Check test cases in `security_tests/test_scripts/`

---

**Last Updated:** June 2026  
**Status:** Research Prototype (UC Berkeley → Enhanced) ✅  
**Security:** Comprehensively Tested & Hardened ✅  
**Clinical Use:** Not validated for production deployment ⚠️