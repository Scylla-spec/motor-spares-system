"""
Automotive Spare Parts Categorization Engine.
Analyses part numbers, names, and descriptions to assign standardized categories.
"""
import re
from typing import Tuple
from database.db_manager import get_connection

# Rule definitions: (Category Name, list of keywords/patterns)
CATEGORY_RULES = [
    ("FILTERS", [
        "AIR FILTER", "OIL FILTER", "FUEL FILTER", "CABIN FILTER", "HYDRAULIC FILTER",
        "ELEMENT", "FILTER"
    ]),
    ("BEARINGS & SEALS", [
        "BEARING", "BEARNG", "OIL SEAL", "WHEEL BEARING", "HUB BEARING", "DAC", "SEAL",
        "BUSH", "BUSHING"
    ]),
    ("SPARK PLUGS & IGNITION", [
        "SPARK PLUG", "GLOW PLUG", "IGNITION COIL", "PLUG LEAD", "PLUG", "BP5", "BP6",
        "B4H", "B6H", "B7H", "AP6"
    ]),
    ("BRAKE SYSTEM", [
        "BRAKE PAD", "BRAKE DISC", "BRAKE SHOE", "BRAKE FLUID", "BRAKE HOSE",
        "CALIPER", "MASTER CYLINDER", "DISC", "PAD SET", "ROTOR", "BRAKE"
    ]),
    ("SUSPENSION & STEERING", [
        "SHOCK ABSORBER", "SHOCK", "STRUT", "BALL JOINT", "CONTROL ARM", "TIE ROD",
        "RACK END", "STABILIZER LINK", "DRAG LINK", "STEERING"
    ]),
    ("BELTS & PULLEYS", [
        "FAN BELT", "TIMING BELT", "V-BELT", "SERPENTINE BELT", "BELT", "TENSIONER", "PULLEY"
    ]),
    ("CABLES & CONTROLS", [
        "ACC CABLE", "ACCELERATOR CABLE", "CLUTCH CABLE", "HANDBRAKE CABLE",
        "SPEEDO CABLE", "CABLE"
    ]),
    ("COOLING & HEATING", [
        "HOSE", "WATER PUMP", "RADIATOR", "THERMOSTAT", "COOLANT", "FAN BLADE",
        "HEATER", "RADIATOR CAP"
    ]),
    ("ENGINE COMPONENTS", [
        "PISTON", "PISTON RING", "CYLINDER HEAD", "GASKET", "VALVE", "ENGINE MOUNT",
        "OIL PUMP", "CAMSHAFT", "CRANKSHAFT", "MANIFOLD"
    ]),
    ("TRANSMISSION & CLUTCH", [
        "CLUTCH KIT", "CLUTCH PLATE", "RELEASE BEARING", "CV JOINT", "UNIVERSAL JOINT",
        "DRIVESHAFT", "FLYWHEEL", "GEARBOX", "TRANSMISSION"
    ]),
    ("ELECTRICAL & LIGHTING", [
        "BULB", "HEADLIGHT", "TAIL LIGHT", "LAMP", "SENSOR", "SWITCH", "RELAY",
        "ALTERNATOR", "STARTER MOTOR", "STARTER", "FUSE", "HORN"
    ]),
    ("FLUIDS & LUBRICANTS", [
        "ENGINE OIL", "GEAR OIL", "ATF", "GREASE", "ADDITIVE", "FLUID"
    ]),
    ("HARDWARE & FASTENERS", [
        "BOLT", "NUT", "WASHER", "SCREW", "CLIP", "CLAMP", "STUD", "PIN"
    ]),
]


def infer_category(name: str, part_number: str = "") -> str:
    """
    Infers the best-matching category for a given part name and part number.
    Returns standard uppercase category string.
    """
    text = f"{name or ''} {part_number or ''}".upper()
    if not text.strip():
        return "GENERAL SPARES"

    for category, keywords in CATEGORY_RULES:
        for kw in keywords:
            if kw in text:
                return category

    return "GENERAL SPARES"


def categorize_existing_parts_in_db() -> int:
    """
    Scans all parts in the database and populates missing/blank categories.
    Returns the number of parts updated.
    """
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT part_id, part_number, name, category FROM Part")
    rows = cursor.fetchall()

    updated_count = 0
    for part_id, part_number, name, current_cat in rows:
        if not current_cat or not str(current_cat).strip():
            new_cat = infer_category(name, part_number)
            cursor.execute(
                "UPDATE Part SET category = ? WHERE part_id = ?",
                (new_cat, part_id)
            )
            updated_count += 1

    conn.commit()
    conn.close()
    return updated_count
