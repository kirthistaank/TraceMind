"""
Neo4j Knowledge Graph loader for pediatric clinical conditions.

Loads SNOMED-CT concepts and CPG evidence for:
- Asthma exacerbation (NIH NAEPP)
- Anaphylaxis (AAP/AAAAI)
- Croup (AAP)

Usage:
    from source.graph.kg_loader import load_condition_kg
    load_condition_kg(driver, "asthma")
    load_condition_kg(driver, "anaphylaxis")
    load_condition_kg(driver, "croup")

Or from command line:
    python -m source.graph.kg_loader --all
    python -m source.graph.kg_loader --condition asthma
"""

from __future__ import annotations

import sys
import os
from typing import Any

from neo4j import Driver

# Handle both direct import and CLI execution
try:
    from source.graph.neo4j_client import run_cypher
except ModuleNotFoundError:
    # Running as script; add parent to path
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))
    from source.graph.neo4j_client import run_cypher


SNOMED_IS_A_TYPE_ID = "116680003"


# Fever concepts and CPG mappings (Seattle Children's)
FEVER_CONCEPTS = [
    {"sctid": "386661006", "pt": "Fever", "condition": "fever"},
    {"sctid": "91175000", "pt": "Seizure", "condition": "fever"},
    {"sctid": "422587007", "pt": "Nausea and vomiting", "condition": "fever"},
    {"sctid": "248643006", "pt": "Tachypnea", "condition": "fever"},
    {"sctid": "103228002", "pt": "Respiratory distress", "condition": "fever"},
    {"sctid": "24740000", "pt": "Lethargy", "condition": "fever"},
    {"sctid": "50960005", "pt": "Oliguria", "condition": "fever"},
    {"sctid": "34095006", "pt": "Dehydration", "condition": "fever"},
    {"sctid": "86823004", "pt": "Febrile seizure", "condition": "fever"},
]

FEVER_MENTIONS = [
    {
        "text": "Seattle Children's CPG: Fever >100.4°F (38°C) in infants <3 months = call doctor immediately (ER_NOW)",
        "rule_id": "R_CPG_INFANT_UNDER_3MO_FEVER",
        "cpg": "Seattle Children's Fever - Safety and Wellness",
    },
    {
        "text": "Seizure with fever = call doctor immediately (ER_NOW)",
        "rule_id": "R_CPG_SEIZURE",
        "cpg": "Seattle Children's Fever - Safety and Wellness",
    },
    {
        "text": "Altered alertness / lethargy with fever = call doctor immediately (ER_NOW)",
        "rule_id": "R_ER_ALERTNESS",
        "cpg": "Seattle Children's Fever - Safety and Wellness",
    },
    {
        "text": "Trouble breathing / respiratory distress with fever = call doctor immediately (ER_NOW)",
        "rule_id": "R_ER_BREATHING",
        "cpg": "Seattle Children's Fever - Safety and Wellness",
    },
    {
        "text": "No fluid intake AND no urine in 8 hours = severe dehydration, call doctor immediately (ER_NOW)",
        "rule_id": "R_ER_NO_FLUID_NO_URINE",
        "cpg": "Seattle Children's Fever - Safety and Wellness",
    },
    {
        "text": "Severe dehydration (poor fluid + no urine) = call doctor immediately (ER_NOW)",
        "rule_id": "R_ER_DEHYDRATION_SEVERE",
        "cpg": "Seattle Children's Fever - Safety and Wellness",
    },
    {
        "text": "Fever >104°F = call doctor same day (URGENT_SAME_DAY)",
        "rule_id": "R_URGENT_VERY_HIGH_FEVER",
        "cpg": "Seattle Children's Fever - Safety and Wellness",
    },
    {
        "text": "Fever lasting >3 days = call doctor same day (URGENT_SAME_DAY)",
        "rule_id": "R_URGENT_FEVER_OVER_3_DAYS",
        "cpg": "Seattle Children's Fever - Safety and Wellness",
    },
    {
        "text": "Repeated vomiting + poor fluid intake = call doctor same day (URGENT_SAME_DAY)",
        "rule_id": "R_URGENT_REPEATED_VOMIT_POOR_FLUID",
        "cpg": "Seattle Children's Fever - Safety and Wellness",
    },
    {
        "text": "Rapid breathing (tachypnea) with fever = call doctor same day (URGENT_SAME_DAY)",
        "rule_id": "R_URGENT_TACHYPNEA_CONCERN",
        "cpg": "Seattle Children's Fever - Safety and Wellness",
    },
    {
        "text": "Ibuprofen contraindicated in children <6 months",
        "rule_id": "R_MEDICATION_IBUPROFEN_AGE_GATE",
        "cpg": "Seattle Children's Fever - Safety and Wellness",
    },
    {
        "text": "No routine antipyretic in children <3 months without clinician guidance",
        "rule_id": "R_MEDICATION_ACETAMINOPHEN_AGE_GATE",
        "cpg": "Seattle Children's Fever - Safety and Wellness",
    },
]

# Asthma concepts and CPG mappings
ASTHMA_CONCEPTS = [
    {"sctid": "195967001", "pt": "Asthma", "condition": "asthma"},
    {"sctid": "370816002", "pt": "Asthma exacerbation", "condition": "asthma"},
    {"sctid": "301495002", "pt": "Wheezing", "condition": "asthma"},
    {"sctid": "258891007", "pt": "Stridor", "condition": "asthma"},
    {"sctid": "386594008", "pt": "Retractions", "condition": "asthma"},
    {"sctid": "103228002", "pt": "Respiratory distress", "condition": "asthma"},
    {"sctid": "16386004", "pt": "Hypoxia", "condition": "asthma"},
    {"sctid": "248643006", "pt": "Tachypnea", "condition": "asthma"},
]

ASTHMA_MENTIONS = [
    {
        "text": "NIH NAEPP Guidelines: Mild exacerbation if normal speech, SpO2 >95%, mild-no retractions",
        "rule_id": "R_ASTHMA_MILD_HOME",
        "cpg": "NIH NAEPP Asthma Action Plan",
    },
    {
        "text": "Moderate exacerbation if short-phrase speech, 90-94% SpO2, moderate retractions, consider systemic corticosteroids",
        "rule_id": "R_ASTHMA_MODERATE_URGENT",
        "cpg": "NIH NAEPP Asthma Action Plan",
    },
    {
        "text": "Severe exacerbation (ER) if word/no speech, <90% SpO2, severe retractions, altered mental status, silent chest",
        "rule_id": "R_ASTHMA_SEVERE_ER",
        "cpg": "NIH NAEPP Asthma Action Plan",
    },
    {
        "text": "Peak expiratory flow <50% predicted = severe; 50-80% = moderate; >80% = mild exacerbation",
        "rule_id": "R_ASTHMA_PEF_ASSESSMENT",
        "cpg": "NIH NAEPP Asthma Action Plan",
    },
    {
        "text": "Prior intubation history elevated risk; any wheezing + prior intubation = consider ER",
        "rule_id": "R_ASTHMA_PRIOR_INTUBATION",
        "cpg": "AAP Asthma Management",
    },
]

# Anaphylaxis concepts and CPG mappings
ANAPHYLAXIS_CONCEPTS = [
    {"sctid": "39579001", "pt": "Anaphylaxis", "condition": "anaphylaxis"},
    {"sctid": "232348004", "pt": "Allergic reaction", "condition": "anaphylaxis"},
    {"sctid": "247472004", "pt": "Urticaria", "condition": "anaphylaxis"},
    {"sctid": "41834007", "pt": "Angioedema", "condition": "anaphylaxis"},
    {"sctid": "258891007", "pt": "Stridor", "condition": "anaphylaxis"},
    {"sctid": "56018004", "pt": "Wheezing", "condition": "anaphylaxis"},
    {"sctid": "45007003", "pt": "Hypotension", "condition": "anaphylaxis"},
    {"sctid": "24740000", "pt": "Syncope", "condition": "anaphylaxis"},
]

ANAPHYLAXIS_MENTIONS = [
    {
        "text": "Anaphylaxis: Multi-system involvement (skin + airway/breathing/GI/CV), stridor, wheezing, hypotension, syncope = medical emergency, call 911, give epinephrine IM immediately",
        "rule_id": "R_ANAPHYLAXIS_ER",
        "cpg": "AAP Anaphylaxis Management",
    },
    {
        "text": "Biphasic anaphylaxis: symptoms resolve then recur 1-72 hours later; monitor all anaphylaxis patients for ≥4-8 hours minimum",
        "rule_id": "R_ANAPHYLAXIS_BIPHASIC",
        "cpg": "AAAAI Anaphylaxis Guidelines",
    },
    {
        "text": "Localized angioedema (lips/face only) without airway involvement or systemic signs = allergic reaction, urgent evaluation, monitor for progression",
        "rule_id": "R_ALLERGIC_ANGIOEDEMA_FACE_URGENT",
        "cpg": "AAP Allergic Reactions",
    },
    {
        "text": "Urticaria alone (no systemic signs) = mild allergic reaction; antihistamine and monitor; ensure resolution",
        "rule_id": "R_ALLERGIC_MILD_HOME",
        "cpg": "AAP Allergic Reactions",
    },
]

# Croup concepts and CPG mappings
CROUP_CONCEPTS = [
    {"sctid": "3602002", "pt": "Croup", "condition": "croup"},
    {"sctid": "275396000", "pt": "Laryngotracheobronchitis", "condition": "croup"},
    {"sctid": "258891007", "pt": "Stridor", "condition": "croup"},
    {"sctid": "49727002", "pt": "Cough", "condition": "croup"},
    {"sctid": "386594008", "pt": "Retractions", "condition": "croup"},
    {"sctid": "248643006", "pt": "Tachypnea", "condition": "croup"},
    {"sctid": "16386004", "pt": "Hypoxia", "condition": "croup"},
]

CROUP_MENTIONS = [
    {
        "text": "AAP Croup CPG: Mild croup if barky cough, mild stridor with cry/agitation only, no distress at rest, normal air entry, SpO2 >95%",
        "rule_id": "R_CROUP_MILD_HOME",
        "cpg": "AAP Croup Management",
    },
    {
        "text": "Moderate croup if moderate stridor at rest, mild-moderate retractions, some work of breathing; give dexamethasone 0.6 mg/kg IM/IV/PO",
        "rule_id": "R_CROUP_MODERATE_URGENT",
        "cpg": "AAP Croup Management",
    },
    {
        "text": "Severe croup (ER) if severe stridor at rest, significant distress, severe retractions, hypoxia, altered mental status; consider racemic epinephrine + dexamethasone",
        "rule_id": "R_CROUP_SEVERE_ER",
        "cpg": "AAP Croup Management",
    },
    {
        "text": "Westley Croup Score: 0-2 = mild; 3-5 = moderate; 6-11 = severe; >11 = very severe",
        "rule_id": "R_CROUP_WESTLEY_SCORE",
        "cpg": "AAP Croup Management",
    },
    {
        "text": "Stridor types: Inspiratory stridor = laryngeal issue (croup); biphasic/expiratory = lower airway involvement",
        "rule_id": "R_CROUP_STRIDOR_TYPE",
        "cpg": "Pediatric Airway Management",
    },
    {
        "text": "High fever (>103F) + croup-like symptoms may indicate epiglottitis, not simple croup; drooling + stridor = possible epiglottitis, treat as emergency",
        "rule_id": "R_CROUP_EPIGLOTTITIS_ALERT",
        "cpg": "AAP Epiglottitis Management",
    },
]


def load_condition_kg(
    driver: Driver | None,
    condition: str,
    *,
    database: str | None = None,
) -> None:
    """Load SNOMED concepts and CPG mentions for a condition into Neo4j."""
    if driver is None:
        print(f"[KG Loader] Skipping {condition} (no Neo4j driver configured)")
        return

    print(f"[KG Loader] Loading {condition} concepts and evidence...")

    if condition == "fever":
        _load_concepts(driver, FEVER_CONCEPTS, database=database)
        _load_mentions(driver, FEVER_MENTIONS, condition="fever", database=database)
    elif condition == "asthma":
        _load_concepts(driver, ASTHMA_CONCEPTS, database=database)
        _load_mentions(driver, ASTHMA_MENTIONS, condition="asthma", database=database)
    elif condition == "anaphylaxis":
        _load_concepts(driver, ANAPHYLAXIS_CONCEPTS, database=database)
        _load_mentions(driver, ANAPHYLAXIS_MENTIONS, condition="anaphylaxis", database=database)
    elif condition == "croup":
        _load_concepts(driver, CROUP_CONCEPTS, database=database)
        _load_mentions(driver, CROUP_MENTIONS, condition="croup", database=database)
    else:
        print(f"[KG Loader] Unknown condition: {condition}")
        return

    print(f"[KG Loader] ✓ {condition} KG loaded")


def _load_concepts(
    driver: Driver,
    concepts: list[dict[str, Any]],
    *,
    database: str | None = None,
) -> None:
    """Load Concept nodes into Neo4j."""
    for concept in concepts:
        query = """
        MERGE (c:Concept {sctid: $sctid})
        SET c.pt = $pt, c.condition = $condition
        RETURN c.sctid AS id
        """
        run_cypher(
            driver,
            query,
            params={
                "sctid": concept["sctid"],
                "pt": concept["pt"],
                "condition": concept.get("condition", "general"),
            },
            database=database,
        )


def _load_mentions(
    driver: Driver,
    mentions: list[dict[str, Any]],
    condition: str,
    *,
    database: str | None = None,
) -> None:
    """Load CPGMention nodes and link to concepts."""
    for mention in mentions:
        # Create mention node
        query = """
        MERGE (m:CPGMention {
            text: $text,
            rule_id: $rule_id,
            condition: $condition,
            cpg: $cpg
        })
        RETURN m.rule_id AS rule_id
        """
        run_cypher(
            driver,
            query,
            params={
                "text": mention["text"],
                "rule_id": mention["rule_id"],
                "condition": condition,
                "cpg": mention.get("cpg", ""),
            },
            database=database,
        )


def load_all_condition_kg(driver: Driver | None, *, database: str | None = None) -> None:
    """Load all condition KGs."""
    for condition in ["fever", "asthma", "anaphylaxis", "croup"]:
        load_condition_kg(driver, condition, database=database)


if __name__ == "__main__":
    import argparse
    from source.config import Settings
    from source.graph.neo4j_client import get_driver, close_driver

    parser = argparse.ArgumentParser(description="Load pediatric condition KGs into Neo4j")
    parser.add_argument(
        "--condition",
        choices=["fever", "asthma", "anaphylaxis", "croup"],
        help="Specific condition to load",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Load all conditions",
    )

    args = parser.parse_args()

    settings = Settings.from_env()
    driver = get_driver(settings)

    if not driver:
        print("❌ Neo4j driver not configured.")
        print("   Set NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD in .env")
        sys.exit(1)

    try:
        if args.all or (not args.condition):
            print("📚 Loading all condition KGs...")
            load_all_condition_kg(driver)
        elif args.condition:
            print(f"📚 Loading {args.condition} KG...")
            load_condition_kg(driver, args.condition)

        print("✅ KG load complete!")

    except Exception as e:
        print(f"❌ Error loading KG: {e}")
        sys.exit(1)

    finally:
        close_driver(driver)
