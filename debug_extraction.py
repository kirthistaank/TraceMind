#!/usr/bin/env python3
"""Debug breathing extraction for specific scenarios."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from source.agents.interpretation import interpret_user_message
from source.config import Settings

settings = Settings.from_env()

# Test asthma_mild breathing extraction
print("=" * 80)
print("ASTHMA MILD - Turn 2 breathing extraction")
print("=" * 80)

turn2 = "He has no fever. Oxygen is 97%. He's speaking in full sentences and breathing normally at rest. Just a little wheezy when he runs."
print(f"Text: {turn2}\n")

# Manual extraction
from source.agents.interpretation import _heuristic_extract
delta = _heuristic_extract(turn2)
print(f"Extracted breathing: {delta.get('breathing', 'NOT SET')}")
print(f"Extracted oxygen_saturation: {delta.get('oxygen_saturation', 'NOT SET')}")
print(f"Extracted ability_to_speak: {delta.get('ability_to_speak', 'NOT SET')}")
print(f"Extracted retractions: {delta.get('retractions', 'NOT SET')}\n")

# Check what phrases are in the text
t = turn2.lower()
print(f"Checking breathing patterns:")
print(f"  'breathing normally at rest' in text: {'breathing normally at rest' in t}")
print(f"  'breathing normally' in text: {'breathing normally' in t}")
print(f"  'trouble breathing' in text: {'trouble breathing' in t}")
print(f"  'breathing hard' in text: {'breathing hard' in t}")
print(f"  'pulling in' in text: {'pulling in' in t}")
print(f"  'breathing ok' in text: {'breathing ok' in t}\n")

# Test croup_mild turn 2
print("=" * 80)
print("CROUP MILD - Turn 2 breathing extraction")
print("=" * 80)

turn2_croup = "No fever or very low-grade. He has a barky cough and some mild stridor when he cries. He's playing between cough fits. Breathing is normal at rest with no retractions."
print(f"Text: {turn2_croup}\n")

delta_croup = _heuristic_extract(turn2_croup)
print(f"Extracted breathing: {delta_croup.get('breathing', 'NOT SET')}")
print(f"Extracted retractions: {delta_croup.get('retractions', 'NOT SET')}\n")

t_croup = turn2_croup.lower()
print(f"Checking breathing patterns:")
print(f"  'breathing is normal' in text: {'breathing is normal' in t_croup}")
print(f"  'breathing' and 'normal' present: {'breathing' in t_croup and 'normal' in t_croup}")
print(f"  'no retractions' in text: {'no retractions' in t_croup}")
