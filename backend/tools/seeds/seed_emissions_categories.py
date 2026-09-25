"""
Seed script: emissions_categories
Inserts a standard CMRT emissions category hierarchy.
Idempotent — uses INSERT ... ON CONFLICT (id) DO NOTHING with stable UUIDs.

Structure:
  Top-level (no parent):
    - Materials (Scope 1/3)
    - Transport (Scope 1/3)
    - Energy (Scope 1/2)
    - Waste (Scope 1/3)
    - Water (Scope 3)
    - Other (all scopes)

Run from the backend/ directory:
    python -m tools.seeds.seed_emissions_categories
"""
import asyncio
import sys
from pathlib import Path
from uuid import UUID

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine
from core.config import settings

# Stable UUIDs so re-runs are idempotent
CATEGORIES = [
    # Top-level categories (no parent)
    {
        "id": "00000000-0001-0000-0000-000000000001",
        "code": "MAT",
        "name": "Materials",
        "scope": None,
        "parent_category_id": None,
        "description": "Embodied emissions from raw materials extraction, processing and manufacturing.",
        "is_active": True,
        "sort_order": 1,
    },
    {
        "id": "00000000-0001-0000-0000-000000000002",
        "code": "TRN",
        "name": "Transport",
        "scope": None,
        "parent_category_id": None,
        "description": "Emissions from the transport of materials, equipment and people.",
        "is_active": True,
        "sort_order": 2,
    },
    {
        "id": "00000000-0001-0000-0000-000000000003",
        "code": "ENE",
        "name": "Energy",
        "scope": None,
        "parent_category_id": None,
        "description": "Emissions from fuel combustion and electricity consumption.",
        "is_active": True,
        "sort_order": 3,
    },
    {
        "id": "00000000-0001-0000-0000-000000000004",
        "code": "WST",
        "name": "Waste",
        "scope": None,
        "parent_category_id": None,
        "description": "Emissions from the treatment and disposal of waste generated on-site.",
        "is_active": True,
        "sort_order": 4,
    },
    {
        "id": "00000000-0001-0000-0000-000000000005",
        "code": "WAT",
        "name": "Water",
        "scope": 3,
        "parent_category_id": None,
        "description": "Emissions associated with water supply and treatment.",
        "is_active": True,
        "sort_order": 5,
    },
    {
        "id": "00000000-0001-0000-0000-000000000006",
        "code": "OTH",
        "name": "Other",
        "scope": None,
        "parent_category_id": None,
        "description": "Other emissions not captured elsewhere.",
        "is_active": True,
        "sort_order": 6,
    },
    # Materials sub-categories
    {
        "id": "00000000-0002-0000-0000-000000000001",
        "code": "MAT-A1-3",
        "name": "Materials – Product Stage (A1-3)",
        "scope": 3,
        "parent_category_id": "00000000-0001-0000-0000-000000000001",
        "description": "Raw material supply, transport to manufacturer, and manufacturing (EN 15978 modules A1–A3).",
        "is_active": True,
        "sort_order": 1,
    },
    {
        "id": "00000000-0002-0000-0000-000000000002",
        "code": "MAT-B2-5",
        "name": "Materials – Use Stage Maintenance (B2-5)",
        "scope": 3,
        "parent_category_id": "00000000-0001-0000-0000-000000000001",
        "description": "Maintenance, repair, replacement and refurbishment of materials in-use stage (EN 15978 modules B2–B5).",
        "is_active": True,
        "sort_order": 2,
    },
    {
        "id": "00000000-0002-0000-0000-000000000003",
        "code": "MAT-C3-4",
        "name": "Materials – End of Life (C3-4)",
        "scope": 3,
        "parent_category_id": "00000000-0001-0000-0000-000000000001",
        "description": "Waste processing and disposal at end of life (EN 15978 modules C3–C4).",
        "is_active": True,
        "sort_order": 3,
    },
    # Transport sub-categories
    {
        "id": "00000000-0002-0000-0000-000000000010",
        "code": "TRN-A4",
        "name": "Transport – Transport to Site (A4)",
        "scope": 3,
        "parent_category_id": "00000000-0001-0000-0000-000000000002",
        "description": "Transport of materials and products to the construction site (EN 15978 module A4).",
        "is_active": True,
        "sort_order": 1,
    },
    {
        "id": "00000000-0002-0000-0000-000000000011",
        "code": "TRN-A5",
        "name": "Transport – Construction Site Transport (A5)",
        "scope": 1,
        "parent_category_id": "00000000-0001-0000-0000-000000000002",
        "description": "Transport and plant movements on-site during construction (EN 15978 module A5).",
        "is_active": True,
        "sort_order": 2,
    },
    {
        "id": "00000000-0002-0000-0000-000000000012",
        "code": "TRN-C2",
        "name": "Transport – End-of-Life Transport (C2)",
        "scope": 3,
        "parent_category_id": "00000000-0001-0000-0000-000000000002",
        "description": "Transport of waste materials off-site at end of life (EN 15978 module C2).",
        "is_active": True,
        "sort_order": 3,
    },
    # Energy sub-categories
    {
        "id": "00000000-0002-0000-0000-000000000020",
        "code": "ENE-S1",
        "name": "Energy – Stationary Combustion (Scope 1)",
        "scope": 1,
        "parent_category_id": "00000000-0001-0000-0000-000000000003",
        "description": "Direct emissions from fuel combustion in stationary equipment.",
        "is_active": True,
        "sort_order": 1,
    },
    {
        "id": "00000000-0002-0000-0000-000000000021",
        "code": "ENE-S2",
        "name": "Energy – Purchased Electricity (Scope 2)",
        "scope": 2,
        "parent_category_id": "00000000-0001-0000-0000-000000000003",
        "description": "Indirect emissions from consumption of purchased electricity.",
        "is_active": True,
        "sort_order": 2,
    },
    # Waste sub-categories
    {
        "id": "00000000-0002-0000-0000-000000000030",
        "code": "WST-GEN",
        "name": "Waste – Construction Waste",
        "scope": 3,
        "parent_category_id": "00000000-0001-0000-0000-000000000004",
        "description": "Emissions from disposal of construction waste (A5).",
        "is_active": True,
        "sort_order": 1,
    },
    {
        "id": "00000000-0002-0000-0000-000000000031",
        "code": "WST-EOL",
        "name": "Waste – End-of-Life Waste",
        "scope": 3,
        "parent_category_id": "00000000-0001-0000-0000-000000000004",
        "description": "Emissions from treatment and disposal of materials at end of life (C3–C4).",
        "is_active": True,
        "sort_order": 2,
    },

    # NOTE: we haven't defined sub-categories for Water and Other yet, but they can be added here in the future as needed.
    # Material-type categories (used by density lookup tables)
    # Top-level: no parent — these are material classification groups
    # NOTE: These categories are used for material classification in density lookup tables.

    {"id": "00000000-0003-0000-0000-000000000001", "code": "MT-AGG",  "name": "Aggregate",            "scope": None, "parent_category_id": None, "description": "Aggregate materials.", "is_active": True, "sort_order": 10},
    {"id": "00000000-0003-0000-0000-000000000002", "code": "MT-ALU",  "name": "Aluminium",             "scope": None, "parent_category_id": None, "description": "Aluminium materials.", "is_active": True, "sort_order": 11},
    {"id": "00000000-0003-0000-0000-000000000003", "code": "MT-BEN",  "name": "Building Envelope",     "scope": None, "parent_category_id": None, "description": "Building envelope materials.", "is_active": True, "sort_order": 12},
    {"id": "00000000-0003-0000-0000-000000000004", "code": "MT-BIN",  "name": "Building Internals",    "scope": None, "parent_category_id": None, "description": "Building internal materials.", "is_active": True, "sort_order": 13},
    {"id": "00000000-0003-0000-0000-000000000005", "code": "MT-BSV",  "name": "Building Services",     "scope": None, "parent_category_id": None, "description": "Building services and MEP.", "is_active": True, "sort_order": 14},
    {"id": "00000000-0003-0000-0000-000000000006", "code": "MT-CON",  "name": "Concrete & components", "scope": None, "parent_category_id": None, "description": "Concrete and concrete components.", "is_active": True, "sort_order": 15},
    {"id": "00000000-0003-0000-0000-000000000007", "code": "MT-FUL",  "name": "Fuels",                 "scope": None, "parent_category_id": None, "description": "Fuel types.", "is_active": True, "sort_order": 16},
    {"id": "00000000-0003-0000-0000-000000000008", "code": "MT-MAS",  "name": "Masonry",               "scope": None, "parent_category_id": None, "description": "Masonry materials.", "is_active": True, "sort_order": 17},
    {"id": "00000000-0003-0000-0000-000000000009", "code": "MT-PAI",  "name": "Paint",                 "scope": None, "parent_category_id": None, "description": "Paint materials.", "is_active": True, "sort_order": 18},
    {"id": "00000000-0003-0000-0000-000000000010", "code": "MT-PAV",  "name": "Pavements",             "scope": None, "parent_category_id": None, "description": "Pavement materials.", "is_active": True, "sort_order": 19},
    {"id": "00000000-0003-0000-0000-000000000011", "code": "MT-PIP",  "name": "Pipes",                 "scope": None, "parent_category_id": None, "description": "Pipe materials.", "is_active": True, "sort_order": 20},
    {"id": "00000000-0003-0000-0000-000000000012", "code": "MT-POL",  "name": "Polymer",               "scope": None, "parent_category_id": None, "description": "Polymer materials.", "is_active": True, "sort_order": 21},
    {"id": "00000000-0003-0000-0000-000000000013", "code": "MT-STL",  "name": "Steel",                 "scope": None, "parent_category_id": None, "description": "Steel materials.", "is_active": True, "sort_order": 22},
    {"id": "00000000-0003-0000-0000-000000000014", "code": "MT-TIM",  "name": "Timber",                "scope": None, "parent_category_id": None, "description": "Timber materials.", "is_active": True, "sort_order": 23},

    # NOTE: The following are example sub-categories for materials. Adjust as needed based on actual classification requirements. These sub-categories are used for more granular material classification in density lookup tables and can be expanded over time.
    # Material-type sub-categories (children of the groups above)
    # Aggregate
    {"id": "00000000-0004-0000-0000-000000000001", "code": "MT-AGG-AGG",  "name": "Aggregate",                          "scope": None, "parent_category_id": "00000000-0003-0000-0000-000000000001", "description": None, "is_active": True, "sort_order": 1},
    # Aluminium
    {"id": "00000000-0004-0000-0000-000000000002", "code": "MT-ALU-EXT",  "name": "Aluminium - extruded",               "scope": None, "parent_category_id": "00000000-0003-0000-0000-000000000002", "description": None, "is_active": True, "sort_order": 1},
    # Building Envelope
    {"id": "00000000-0004-0000-0000-000000000003", "code": "MT-BEN-CLR",  "name": "Cladding/roofing",                   "scope": None, "parent_category_id": "00000000-0003-0000-0000-000000000003", "description": None, "is_active": True, "sort_order": 1},
    {"id": "00000000-0004-0000-0000-000000000004", "code": "MT-BEN-CUR",  "name": "Curtain wall",                        "scope": None, "parent_category_id": "00000000-0003-0000-0000-000000000003", "description": None, "is_active": True, "sort_order": 2},
    {"id": "00000000-0004-0000-0000-000000000005", "code": "MT-BEN-EXT",  "name": "External shading system",            "scope": None, "parent_category_id": "00000000-0003-0000-0000-000000000003", "description": None, "is_active": True, "sort_order": 3},
    {"id": "00000000-0004-0000-0000-000000000006", "code": "MT-BEN-GLS",  "name": "Glass",                              "scope": None, "parent_category_id": "00000000-0003-0000-0000-000000000003", "description": None, "is_active": True, "sort_order": 4},
    {"id": "00000000-0004-0000-0000-000000000007", "code": "MT-BEN-WLV",  "name": "Wall louvre system",                 "scope": None, "parent_category_id": "00000000-0003-0000-0000-000000000003", "description": None, "is_active": True, "sort_order": 5},
    {"id": "00000000-0004-0000-0000-000000000008", "code": "MT-BEN-WIN",  "name": "Windows & doors",                    "scope": None, "parent_category_id": "00000000-0003-0000-0000-000000000003", "description": None, "is_active": True, "sort_order": 6},
    # Building Internals
    {"id": "00000000-0004-0000-0000-000000000009", "code": "MT-BIN-CEI",  "name": "Ceilings & walls",                   "scope": None, "parent_category_id": "00000000-0003-0000-0000-000000000004", "description": None, "is_active": True, "sort_order": 1},
    {"id": "00000000-0004-0000-0000-000000000010", "code": "MT-BIN-FLR",  "name": "Floors",                             "scope": None, "parent_category_id": "00000000-0003-0000-0000-000000000004", "description": None, "is_active": True, "sort_order": 2},
    {"id": "00000000-0004-0000-0000-000000000011", "code": "MT-BIN-STK",  "name": "Stick-framed wall /ceiling system",  "scope": None, "parent_category_id": "00000000-0003-0000-0000-000000000004", "description": None, "is_active": True, "sort_order": 3},
    {"id": "00000000-0004-0000-0000-000000000012", "code": "MT-BIN-WCI",  "name": "Wall ceiling Insulated Panel",       "scope": None, "parent_category_id": "00000000-0003-0000-0000-000000000004", "description": None, "is_active": True, "sort_order": 4},
    {"id": "00000000-0004-0000-0000-000000000013", "code": "MT-BIN-WIN",  "name": "Windows & doors",                    "scope": None, "parent_category_id": "00000000-0003-0000-0000-000000000004", "description": None, "is_active": True, "sort_order": 5},
    # Building Services
    {"id": "00000000-0004-0000-0000-000000000014", "code": "MT-BSV-MEP",  "name": "Building and MEP services",          "scope": None, "parent_category_id": "00000000-0003-0000-0000-000000000005", "description": None, "is_active": True, "sort_order": 1},
    {"id": "00000000-0004-0000-0000-000000000015", "code": "MT-BSV-ESC",  "name": "Escalator",                          "scope": None, "parent_category_id": "00000000-0003-0000-0000-000000000005", "description": None, "is_active": True, "sort_order": 2},
    {"id": "00000000-0004-0000-0000-000000000016", "code": "MT-BSV-LFT",  "name": "Lifts",                              "scope": None, "parent_category_id": "00000000-0003-0000-0000-000000000005", "description": None, "is_active": True, "sort_order": 3},
    {"id": "00000000-0004-0000-0000-000000000017", "code": "MT-BSV-PVP",  "name": "Photovoltaic panels",                "scope": None, "parent_category_id": "00000000-0003-0000-0000-000000000005", "description": None, "is_active": True, "sort_order": 4},
    # Concrete & components
    {"id": "00000000-0004-0000-0000-000000000018", "code": "MT-CON-COM",  "name": "Concrete components",                "scope": None, "parent_category_id": "00000000-0003-0000-0000-000000000006", "description": None, "is_active": True, "sort_order": 1},
    {"id": "00000000-0004-0000-0000-000000000019", "code": "MT-CON-INS",  "name": "Concrete in-situ",                   "scope": None, "parent_category_id": "00000000-0003-0000-0000-000000000006", "description": None, "is_active": True, "sort_order": 2},
    {"id": "00000000-0004-0000-0000-000000000020", "code": "MT-CON-PRE",  "name": "Precast concrete",                   "scope": None, "parent_category_id": "00000000-0003-0000-0000-000000000006", "description": None, "is_active": True, "sort_order": 3},
    # Fuels
    {"id": "00000000-0004-0000-0000-000000000021", "code": "MT-FUL-GAS",  "name": "Gaseous Fuels",                      "scope": None, "parent_category_id": "00000000-0003-0000-0000-000000000007", "description": None, "is_active": True, "sort_order": 1},
    {"id": "00000000-0004-0000-0000-000000000022", "code": "MT-FUL-LST",  "name": "Liquid Fuels (Stationary)",          "scope": None, "parent_category_id": "00000000-0003-0000-0000-000000000007", "description": None, "is_active": True, "sort_order": 2},
    {"id": "00000000-0004-0000-0000-000000000023", "code": "MT-FUL-LTR",  "name": "Liquid Fuels (Transport)",           "scope": None, "parent_category_id": "00000000-0003-0000-0000-000000000007", "description": None, "is_active": True, "sort_order": 3},
    # Masonry
    {"id": "00000000-0004-0000-0000-000000000024", "code": "MT-MAS-MAS",  "name": "Masonry",                            "scope": None, "parent_category_id": "00000000-0003-0000-0000-000000000008", "description": None, "is_active": True, "sort_order": 1},
    # Paint
    {"id": "00000000-0004-0000-0000-000000000025", "code": "MT-PAI-PAI",  "name": "Paint",                              "scope": None, "parent_category_id": "00000000-0003-0000-0000-000000000009", "description": None, "is_active": True, "sort_order": 1},
    # Pavements
    {"id": "00000000-0004-0000-0000-000000000026", "code": "MT-PAV-ASP",  "name": "Asphalt",                            "scope": None, "parent_category_id": "00000000-0003-0000-0000-000000000010", "description": None, "is_active": True, "sort_order": 1},
    {"id": "00000000-0004-0000-0000-000000000027", "code": "MT-PAV-BIT",  "name": "Bitumen",                            "scope": None, "parent_category_id": "00000000-0003-0000-0000-000000000010", "description": None, "is_active": True, "sort_order": 2},
    {"id": "00000000-0004-0000-0000-000000000028", "code": "MT-PAV-PAV",  "name": "Pavers",                             "scope": None, "parent_category_id": "00000000-0003-0000-0000-000000000010", "description": None, "is_active": True, "sort_order": 3},
    # Pipes
    {"id": "00000000-0004-0000-0000-000000000029", "code": "MT-PIP-GEO",  "name": "Geopolymer pipes",                   "scope": None, "parent_category_id": "00000000-0003-0000-0000-000000000011", "description": None, "is_active": True, "sort_order": 1},
    {"id": "00000000-0004-0000-0000-000000000030", "code": "MT-PIP-PE",   "name": "PE Pipes",                           "scope": None, "parent_category_id": "00000000-0003-0000-0000-000000000011", "description": None, "is_active": True, "sort_order": 2},
    {"id": "00000000-0004-0000-0000-000000000031", "code": "MT-PIP-PVC",  "name": "PVC Pipes",                          "scope": None, "parent_category_id": "00000000-0003-0000-0000-000000000011", "description": None, "is_active": True, "sort_order": 3},
    {"id": "00000000-0004-0000-0000-000000000032", "code": "MT-PIP-STL",  "name": "Steel pipes",                        "scope": None, "parent_category_id": "00000000-0003-0000-0000-000000000011", "description": None, "is_active": True, "sort_order": 4},
    # Polymer
    {"id": "00000000-0004-0000-0000-000000000033", "code": "MT-POL-RUB",  "name": "Rubbers",                            "scope": None, "parent_category_id": "00000000-0003-0000-0000-000000000012", "description": None, "is_active": True, "sort_order": 1},
    {"id": "00000000-0004-0000-0000-000000000034", "code": "MT-POL-SEA",  "name": "Sealants and adhesives",             "scope": None, "parent_category_id": "00000000-0003-0000-0000-000000000012", "description": None, "is_active": True, "sort_order": 2},
    {"id": "00000000-0004-0000-0000-000000000035", "code": "MT-POL-THM",  "name": "Thermoplastics",                     "scope": None, "parent_category_id": "00000000-0003-0000-0000-000000000012", "description": None, "is_active": True, "sort_order": 3},
    # Steel
    {"id": "00000000-0004-0000-0000-000000000036", "code": "MT-STL-CLD",  "name": "Cold rolled steel",                  "scope": None, "parent_category_id": "00000000-0003-0000-0000-000000000013", "description": None, "is_active": True, "sort_order": 1},
    {"id": "00000000-0004-0000-0000-000000000037", "code": "MT-STL-HOT",  "name": "Hot rolled steel",                   "scope": None, "parent_category_id": "00000000-0003-0000-0000-000000000013", "description": None, "is_active": True, "sort_order": 2},
    {"id": "00000000-0004-0000-0000-000000000038", "code": "MT-STL-REI",  "name": "Reinforcing steel",                  "scope": None, "parent_category_id": "00000000-0003-0000-0000-000000000013", "description": None, "is_active": True, "sort_order": 3},
    {"id": "00000000-0004-0000-0000-000000000039", "code": "MT-STL-STA",  "name": "Stainless steel",                    "scope": None, "parent_category_id": "00000000-0003-0000-0000-000000000013", "description": None, "is_active": True, "sort_order": 4},
    {"id": "00000000-0004-0000-0000-000000000040", "code": "MT-STL-WIR",  "name": "Steel wire",                         "scope": None, "parent_category_id": "00000000-0003-0000-0000-000000000013", "description": None, "is_active": True, "sort_order": 5},
    # Timber
    {"id": "00000000-0004-0000-0000-000000000041", "code": "MT-TIM-ENG",  "name": "Timber (engineered)",                "scope": None, "parent_category_id": "00000000-0003-0000-0000-000000000014", "description": None, "is_active": True, "sort_order": 1},
    {"id": "00000000-0004-0000-0000-000000000042", "code": "MT-TIM-SAW",  "name": "Timber (sawn)",                      "scope": None, "parent_category_id": "00000000-0003-0000-0000-000000000014", "description": None, "is_active": True, "sort_order": 2},
    # Water sub-category (parent: existing Water 00000000-0001-0000-0000-000000000005)
    {"id": "00000000-0004-0000-0000-000000000043", "code": "WAT-USE",     "name": "Water Use",                          "scope": 3,    "parent_category_id": "00000000-0001-0000-0000-000000000005", "description": "Water consumption and associated emissions.", "is_active": True, "sort_order": 1},
    # Additional fuel sub-categories used by Transport Distances CSV
    {"id": "00000000-0004-0000-0000-000000000044", "code": "MT-FUL-SOL",  "name": "Solid Fuels",                        "scope": None, "parent_category_id": "00000000-0003-0000-0000-000000000007", "description": "Solid fuel types.", "is_active": True, "sort_order": 4},
    {"id": "00000000-0004-0000-0000-000000000045", "code": "MT-FUL-HFC",  "name": "Hydrofluorocarbons (HFCs)",          "scope": None, "parent_category_id": "00000000-0003-0000-0000-000000000007", "description": "Hydrofluorocarbon refrigerants and gases.", "is_active": True, "sort_order": 5},
    {"id": "00000000-0004-0000-0000-000000000046", "code": "MT-FUL-PFC",  "name": "Perfluorocarbons (PFCs)",            "scope": None, "parent_category_id": "00000000-0003-0000-0000-000000000007", "description": "Perfluorocarbon gases.", "is_active": True, "sort_order": 6},
    {"id": "00000000-0004-0000-0000-000000000047", "code": "MT-FUL-OTH",  "name": "Other gases",                        "scope": None, "parent_category_id": "00000000-0003-0000-0000-000000000007", "description": "Other gaseous emissions sources.", "is_active": True, "sort_order": 7},

    # -------------------------------------------------------------------------
    # ECCL Grade 2 — top-level categories (0005 series)
    # Used as emissions_category_id FK in background_grade_metrics for Grade 2
    # -------------------------------------------------------------------------
    {"id": "00000000-0005-0000-0000-000000000001", "code": None, "name": "Constructors' Site Overheads",       "scope": None, "parent_category_id": None, "description": "ECCL Grade 2 benchmark category.", "is_active": True, "sort_order": 1},
    {"id": "00000000-0005-0000-0000-000000000002", "code": None, "name": "Drainage Assets",                   "scope": None, "parent_category_id": None, "description": "ECCL Grade 2 benchmark category.", "is_active": True, "sort_order": 2},
    {"id": "00000000-0005-0000-0000-000000000003", "code": None, "name": "External and Ancillary Works",       "scope": None, "parent_category_id": None, "description": "ECCL Grade 2 benchmark category.", "is_active": True, "sort_order": 3},
    {"id": "00000000-0005-0000-0000-000000000004", "code": None, "name": "Ground Improvements",               "scope": None, "parent_category_id": None, "description": "ECCL Grade 2 benchmark category.", "is_active": True, "sort_order": 4},
    {"id": "00000000-0005-0000-0000-000000000005", "code": None, "name": "Intersections",                     "scope": None, "parent_category_id": None, "description": "ECCL Grade 2 benchmark category.", "is_active": True, "sort_order": 5},
    {"id": "00000000-0005-0000-0000-000000000006", "code": None, "name": "Local Roads Pavements and Surfacing","scope": None, "parent_category_id": None, "description": "ECCL Grade 2 benchmark category.", "is_active": True, "sort_order": 6},
    {"id": "00000000-0005-0000-0000-000000000007", "code": None, "name": "Paths, Cycleways and Crossings",    "scope": None, "parent_category_id": None, "description": "ECCL Grade 2 benchmark category.", "is_active": True, "sort_order": 7},
    {"id": "00000000-0005-0000-0000-000000000008", "code": None, "name": "Pipe Network",                      "scope": None, "parent_category_id": None, "description": "ECCL Grade 2 benchmark category.", "is_active": True, "sort_order": 8},
    {"id": "00000000-0005-0000-0000-000000000009", "code": None, "name": "Preliminaries",                     "scope": None, "parent_category_id": None, "description": "ECCL Grade 2 benchmark category.", "is_active": True, "sort_order": 9},
    {"id": "00000000-0005-0000-0000-000000000010", "code": None, "name": "Rail Drainage",                     "scope": None, "parent_category_id": None, "description": "ECCL Grade 2 benchmark category.", "is_active": True, "sort_order": 10},
    {"id": "00000000-0005-0000-0000-000000000011", "code": None, "name": "Rail Structures",                   "scope": None, "parent_category_id": None, "description": "ECCL Grade 2 benchmark category.", "is_active": True, "sort_order": 11},
    {"id": "00000000-0005-0000-0000-000000000012", "code": None, "name": "Rail overhead lines",               "scope": None, "parent_category_id": None, "description": "ECCL Grade 2 benchmark category.", "is_active": True, "sort_order": 12},
    {"id": "00000000-0005-0000-0000-000000000013", "code": None, "name": "Rails and Formation",               "scope": None, "parent_category_id": None, "description": "ECCL Grade 2 benchmark category.", "is_active": True, "sort_order": 13},
    {"id": "00000000-0005-0000-0000-000000000014", "code": None, "name": "Retaining Walls",                   "scope": None, "parent_category_id": None, "description": "ECCL Grade 2 benchmark category.", "is_active": True, "sort_order": 14},
    {"id": "00000000-0005-0000-0000-000000000015", "code": None, "name": "Road Marking",                      "scope": None, "parent_category_id": None, "description": "ECCL Grade 2 benchmark category.", "is_active": True, "sort_order": 15},
    {"id": "00000000-0005-0000-0000-000000000016", "code": None, "name": "Safety Barriers and Fencing",       "scope": None, "parent_category_id": None, "description": "ECCL Grade 2 benchmark category.", "is_active": True, "sort_order": 16},
    {"id": "00000000-0005-0000-0000-000000000017", "code": None, "name": "Services and Equipment",            "scope": None, "parent_category_id": None, "description": "ECCL Grade 2 benchmark category.", "is_active": True, "sort_order": 17},
    {"id": "00000000-0005-0000-0000-000000000018", "code": None, "name": "Signage",                           "scope": None, "parent_category_id": None, "description": "ECCL Grade 2 benchmark category.", "is_active": True, "sort_order": 18},
    {"id": "00000000-0005-0000-0000-000000000019", "code": None, "name": "Site Clearance and Earthworks",     "scope": None, "parent_category_id": None, "description": "ECCL Grade 2 benchmark category.", "is_active": True, "sort_order": 19},
    {"id": "00000000-0005-0000-0000-000000000020", "code": None, "name": "State Highway Structures",          "scope": None, "parent_category_id": None, "description": "ECCL Grade 2 benchmark category.", "is_active": True, "sort_order": 20},
    {"id": "00000000-0005-0000-0000-000000000021", "code": None, "name": "Street Furniture",                  "scope": None, "parent_category_id": None, "description": "ECCL Grade 2 benchmark category.", "is_active": True, "sort_order": 21},
    {"id": "00000000-0005-0000-0000-000000000022", "code": None, "name": "Street Lighting",                   "scope": None, "parent_category_id": None, "description": "ECCL Grade 2 benchmark category.", "is_active": True, "sort_order": 22},
    {"id": "00000000-0005-0000-0000-000000000023", "code": None, "name": "Structure",                         "scope": None, "parent_category_id": None, "description": "ECCL Grade 2 benchmark category.", "is_active": True, "sort_order": 23},
    {"id": "00000000-0005-0000-0000-000000000024", "code": None, "name": "Substructure and Pavements",        "scope": None, "parent_category_id": None, "description": "ECCL Grade 2 benchmark category.", "is_active": True, "sort_order": 24},
    {"id": "00000000-0005-0000-0000-000000000025", "code": None, "name": "Surface and Underground Drainage",  "scope": None, "parent_category_id": None, "description": "ECCL Grade 2 benchmark category.", "is_active": True, "sort_order": 25},
    {"id": "00000000-0005-0000-0000-000000000026", "code": None, "name": "Traffic Islands and Raised Tables", "scope": None, "parent_category_id": None, "description": "ECCL Grade 2 benchmark category.", "is_active": True, "sort_order": 26},
    {"id": "00000000-0005-0000-0000-000000000027", "code": None, "name": "Traffic Signals",                   "scope": None, "parent_category_id": None, "description": "ECCL Grade 2 benchmark category.", "is_active": True, "sort_order": 27},
    {"id": "00000000-0005-0000-0000-000000000028", "code": None, "name": "Utilities",                         "scope": None, "parent_category_id": None, "description": "ECCL Grade 2 benchmark category.", "is_active": True, "sort_order": 28},

    # -------------------------------------------------------------------------
    # ECCL Grade 2 — sub-categories (0006 series)
    # parent_category_id points to the 0005 series top-level above
    # -------------------------------------------------------------------------
    # Constructors' Site Overheads
    {"id": "00000000-0006-0000-0000-000000000001", "code": None, "name": "Principal's Project Accommodation",                          "scope": None, "parent_category_id": "00000000-0005-0000-0000-000000000001", "description": None, "is_active": True, "sort_order": 1},
    # Drainage Assets
    {"id": "00000000-0006-0000-0000-000000000002", "code": None, "name": "Box Culvert",                                                 "scope": None, "parent_category_id": "00000000-0005-0000-0000-000000000002", "description": None, "is_active": True, "sort_order": 1},
    {"id": "00000000-0006-0000-0000-000000000003", "code": None, "name": "Catchpits",                                                   "scope": None, "parent_category_id": "00000000-0005-0000-0000-000000000002", "description": None, "is_active": True, "sort_order": 2},
    {"id": "00000000-0006-0000-0000-000000000004", "code": None, "name": "Drainage to Footpath and Road",                              "scope": None, "parent_category_id": "00000000-0005-0000-0000-000000000002", "description": None, "is_active": True, "sort_order": 3},
    {"id": "00000000-0006-0000-0000-000000000005", "code": None, "name": "Gross Pollutant Trap",                                       "scope": None, "parent_category_id": "00000000-0005-0000-0000-000000000002", "description": None, "is_active": True, "sort_order": 4},
    {"id": "00000000-0006-0000-0000-000000000006", "code": None, "name": "Kerbs",                                                       "scope": None, "parent_category_id": "00000000-0005-0000-0000-000000000002", "description": None, "is_active": True, "sort_order": 5},
    {"id": "00000000-0006-0000-0000-000000000007", "code": None, "name": "Manholes",                                                    "scope": None, "parent_category_id": "00000000-0005-0000-0000-000000000002", "description": None, "is_active": True, "sort_order": 6},
    {"id": "00000000-0006-0000-0000-000000000008", "code": None, "name": "Raingarden",                                                  "scope": None, "parent_category_id": "00000000-0005-0000-0000-000000000002", "description": None, "is_active": True, "sort_order": 7},
    {"id": "00000000-0006-0000-0000-000000000009", "code": None, "name": "Stormwater System Connection",                               "scope": None, "parent_category_id": "00000000-0005-0000-0000-000000000002", "description": None, "is_active": True, "sort_order": 8},
    {"id": "00000000-0006-0000-0000-000000000010", "code": None, "name": "Stormwater Treatment",                                       "scope": None, "parent_category_id": "00000000-0005-0000-0000-000000000002", "description": None, "is_active": True, "sort_order": 9},
    {"id": "00000000-0006-0000-0000-000000000011", "code": None, "name": "Swale",                                                       "scope": None, "parent_category_id": "00000000-0005-0000-0000-000000000002", "description": None, "is_active": True, "sort_order": 10},
    {"id": "00000000-0006-0000-0000-000000000012", "code": None, "name": "Trenches",                                                    "scope": None, "parent_category_id": "00000000-0005-0000-0000-000000000002", "description": None, "is_active": True, "sort_order": 11},
    {"id": "00000000-0006-0000-0000-000000000013", "code": None, "name": "Watercourse Drainage",                                       "scope": None, "parent_category_id": "00000000-0005-0000-0000-000000000002", "description": None, "is_active": True, "sort_order": 12},
    {"id": "00000000-0006-0000-0000-000000000014", "code": None, "name": "Wingwalls",                                                   "scope": None, "parent_category_id": "00000000-0005-0000-0000-000000000002", "description": None, "is_active": True, "sort_order": 13},
    # External and Ancillary Works
    {"id": "00000000-0006-0000-0000-000000000015", "code": None, "name": "Construction of Verges",                                     "scope": None, "parent_category_id": "00000000-0005-0000-0000-000000000003", "description": None, "is_active": True, "sort_order": 1},
    {"id": "00000000-0006-0000-0000-000000000016", "code": None, "name": "Landscape Planting",                                         "scope": None, "parent_category_id": "00000000-0005-0000-0000-000000000003", "description": None, "is_active": True, "sort_order": 2},
    {"id": "00000000-0006-0000-0000-000000000017", "code": None, "name": "Street Lighting",                                            "scope": None, "parent_category_id": "00000000-0005-0000-0000-000000000003", "description": None, "is_active": True, "sort_order": 3},
    # Ground Improvements
    {"id": "00000000-0006-0000-0000-000000000018", "code": None, "name": "Aggregate",                                                  "scope": None, "parent_category_id": "00000000-0005-0000-0000-000000000004", "description": None, "is_active": True, "sort_order": 1},
    {"id": "00000000-0006-0000-0000-000000000019", "code": None, "name": "Geogrid",                                                    "scope": None, "parent_category_id": "00000000-0005-0000-0000-000000000004", "description": None, "is_active": True, "sort_order": 2},
    {"id": "00000000-0006-0000-0000-000000000020", "code": None, "name": "Geotextile",                                                 "scope": None, "parent_category_id": "00000000-0005-0000-0000-000000000004", "description": None, "is_active": True, "sort_order": 3},
    {"id": "00000000-0006-0000-0000-000000000021", "code": None, "name": "RipRap",                                                     "scope": None, "parent_category_id": "00000000-0005-0000-0000-000000000004", "description": None, "is_active": True, "sort_order": 4},
    {"id": "00000000-0006-0000-0000-000000000022", "code": None, "name": "Topsoil",                                                    "scope": None, "parent_category_id": "00000000-0005-0000-0000-000000000004", "description": None, "is_active": True, "sort_order": 5},
    # Intersections
    {"id": "00000000-0006-0000-0000-000000000023", "code": None, "name": "Major Intersection",                                         "scope": None, "parent_category_id": "00000000-0005-0000-0000-000000000005", "description": None, "is_active": True, "sort_order": 1},
    {"id": "00000000-0006-0000-0000-000000000024", "code": None, "name": "Major Roundabout (exc. Road areas)",                         "scope": None, "parent_category_id": "00000000-0005-0000-0000-000000000005", "description": None, "is_active": True, "sort_order": 2},
    {"id": "00000000-0006-0000-0000-000000000025", "code": None, "name": "Medium Intersection",                                        "scope": None, "parent_category_id": "00000000-0005-0000-0000-000000000005", "description": None, "is_active": True, "sort_order": 3},
    {"id": "00000000-0006-0000-0000-000000000026", "code": None, "name": "Medium Roundabout (inc. Road areas)",                        "scope": None, "parent_category_id": "00000000-0005-0000-0000-000000000005", "description": None, "is_active": True, "sort_order": 4},
    {"id": "00000000-0006-0000-0000-000000000027", "code": None, "name": "Minor Intersection",                                         "scope": None, "parent_category_id": "00000000-0005-0000-0000-000000000005", "description": None, "is_active": True, "sort_order": 5},
    {"id": "00000000-0006-0000-0000-000000000028", "code": None, "name": "Minor Roundabout (inc. Road areas)",                         "scope": None, "parent_category_id": "00000000-0005-0000-0000-000000000005", "description": None, "is_active": True, "sort_order": 6},
    # Local Roads Pavements and Surfacing
    {"id": "00000000-0006-0000-0000-000000000029", "code": None, "name": "Rural (25%)",                                                "scope": None, "parent_category_id": "00000000-0005-0000-0000-000000000006", "description": None, "is_active": True, "sort_order": 1},
    {"id": "00000000-0006-0000-0000-000000000030", "code": None, "name": "Rural (75%)",                                                "scope": None, "parent_category_id": "00000000-0005-0000-0000-000000000006", "description": None, "is_active": True, "sort_order": 2},
    {"id": "00000000-0006-0000-0000-000000000031", "code": None, "name": "Rural Unsealed",                                             "scope": None, "parent_category_id": "00000000-0005-0000-0000-000000000006", "description": None, "is_active": True, "sort_order": 3},
    {"id": "00000000-0006-0000-0000-000000000032", "code": None, "name": "Urban (25%)",                                                "scope": None, "parent_category_id": "00000000-0005-0000-0000-000000000006", "description": None, "is_active": True, "sort_order": 4},
    {"id": "00000000-0006-0000-0000-000000000033", "code": None, "name": "Urban (75%)",                                                "scope": None, "parent_category_id": "00000000-0005-0000-0000-000000000006", "description": None, "is_active": True, "sort_order": 5},
    # Paths, Cycleways and Crossings
    {"id": "00000000-0006-0000-0000-000000000034", "code": None, "name": "Cycleways",                                                  "scope": None, "parent_category_id": "00000000-0005-0000-0000-000000000007", "description": None, "is_active": True, "sort_order": 1},
    {"id": "00000000-0006-0000-0000-000000000035", "code": None, "name": "Footpaths",                                                  "scope": None, "parent_category_id": "00000000-0005-0000-0000-000000000007", "description": None, "is_active": True, "sort_order": 2},
    {"id": "00000000-0006-0000-0000-000000000036", "code": None, "name": "Reinforcement",                                              "scope": None, "parent_category_id": "00000000-0005-0000-0000-000000000007", "description": None, "is_active": True, "sort_order": 3},
    {"id": "00000000-0006-0000-0000-000000000037", "code": None, "name": "Vehicle Crossings",                                          "scope": None, "parent_category_id": "00000000-0005-0000-0000-000000000007", "description": None, "is_active": True, "sort_order": 4},
    # Pipe Network
    {"id": "00000000-0006-0000-0000-000000000038", "code": None, "name": "PE Pipes",                                                   "scope": None, "parent_category_id": "00000000-0005-0000-0000-000000000008", "description": None, "is_active": True, "sort_order": 1},
    {"id": "00000000-0006-0000-0000-000000000039", "code": None, "name": "PVC-U Pipes Gravity",                                        "scope": None, "parent_category_id": "00000000-0005-0000-0000-000000000008", "description": None, "is_active": True, "sort_order": 2},
    {"id": "00000000-0006-0000-0000-000000000040", "code": None, "name": "PVC-U Pipes Pressured",                                      "scope": None, "parent_category_id": "00000000-0005-0000-0000-000000000008", "description": None, "is_active": True, "sort_order": 3},
    {"id": "00000000-0006-0000-0000-000000000041", "code": None, "name": "RCRRJ Class 4",                                              "scope": None, "parent_category_id": "00000000-0005-0000-0000-000000000008", "description": None, "is_active": True, "sort_order": 4},
    # Preliminaries
    {"id": "00000000-0006-0000-0000-000000000042", "code": None, "name": "Soil and Water Management",                                  "scope": None, "parent_category_id": "00000000-0005-0000-0000-000000000009", "description": None, "is_active": True, "sort_order": 1},
    # Rail Drainage
    {"id": "00000000-0006-0000-0000-000000000043", "code": None, "name": "Class 6 Culverts",                                           "scope": None, "parent_category_id": "00000000-0005-0000-0000-000000000010", "description": None, "is_active": True, "sort_order": 1},
    {"id": "00000000-0006-0000-0000-000000000044", "code": None, "name": "Class 8 Culverts",                                           "scope": None, "parent_category_id": "00000000-0005-0000-0000-000000000010", "description": None, "is_active": True, "sort_order": 2},
    {"id": "00000000-0006-0000-0000-000000000045", "code": None, "name": "Drainage",                                                   "scope": None, "parent_category_id": "00000000-0005-0000-0000-000000000010", "description": None, "is_active": True, "sort_order": 3},
    # Rail Structures
    {"id": "00000000-0006-0000-0000-000000000046", "code": None, "name": "Concrete Components",                                        "scope": None, "parent_category_id": "00000000-0005-0000-0000-000000000011", "description": None, "is_active": True, "sort_order": 1},
    {"id": "00000000-0006-0000-0000-000000000047", "code": None, "name": "Rail Bridge",                                                "scope": None, "parent_category_id": "00000000-0005-0000-0000-000000000011", "description": None, "is_active": True, "sort_order": 2},
    # Rail overhead lines
    {"id": "00000000-0006-0000-0000-000000000048", "code": None, "name": "Concrete Components",                                        "scope": None, "parent_category_id": "00000000-0005-0000-0000-000000000012", "description": None, "is_active": True, "sort_order": 1},
    {"id": "00000000-0006-0000-0000-000000000049", "code": None, "name": "Gantries",                                                   "scope": None, "parent_category_id": "00000000-0005-0000-0000-000000000012", "description": None, "is_active": True, "sort_order": 2},
    {"id": "00000000-0006-0000-0000-000000000050", "code": None, "name": "Overhead lines",                                             "scope": None, "parent_category_id": "00000000-0005-0000-0000-000000000012", "description": None, "is_active": True, "sort_order": 3},
    {"id": "00000000-0006-0000-0000-000000000051", "code": None, "name": "Posts",                                                      "scope": None, "parent_category_id": "00000000-0005-0000-0000-000000000012", "description": None, "is_active": True, "sort_order": 4},
    # Rails and Formation
    {"id": "00000000-0006-0000-0000-000000000052", "code": None, "name": "Rails",                                                      "scope": None, "parent_category_id": "00000000-0005-0000-0000-000000000013", "description": None, "is_active": True, "sort_order": 1},
    {"id": "00000000-0006-0000-0000-000000000053", "code": None, "name": "Sleepers",                                                   "scope": None, "parent_category_id": "00000000-0005-0000-0000-000000000013", "description": None, "is_active": True, "sort_order": 2},
    # Retaining Walls
    {"id": "00000000-0006-0000-0000-000000000054", "code": None, "name": "Concrete Components",                                        "scope": None, "parent_category_id": "00000000-0005-0000-0000-000000000014", "description": None, "is_active": True, "sort_order": 1},
    # Road Marking
    {"id": "00000000-0006-0000-0000-000000000055", "code": None, "name": "Painting",                                                   "scope": None, "parent_category_id": "00000000-0005-0000-0000-000000000015", "description": None, "is_active": True, "sort_order": 1},
    # Safety Barriers and Fencing
    {"id": "00000000-0006-0000-0000-000000000056", "code": None, "name": "Barriers",                                                   "scope": None, "parent_category_id": "00000000-0005-0000-0000-000000000016", "description": None, "is_active": True, "sort_order": 1},
    {"id": "00000000-0006-0000-0000-000000000057", "code": None, "name": "Fences and Walls",                                           "scope": None, "parent_category_id": "00000000-0005-0000-0000-000000000016", "description": None, "is_active": True, "sort_order": 2},
    # Services and Equipment
    {"id": "00000000-0006-0000-0000-000000000058", "code": None, "name": "Bowe Kerbs",                                                 "scope": None, "parent_category_id": "00000000-0005-0000-0000-000000000017", "description": None, "is_active": True, "sort_order": 1},
    {"id": "00000000-0006-0000-0000-000000000059", "code": None, "name": "ITS Cantilever and Portal Gantries",                         "scope": None, "parent_category_id": "00000000-0005-0000-0000-000000000017", "description": None, "is_active": True, "sort_order": 2},
    {"id": "00000000-0006-0000-0000-000000000060", "code": None, "name": "Safety Barrier Systems",                                     "scope": None, "parent_category_id": "00000000-0005-0000-0000-000000000017", "description": None, "is_active": True, "sort_order": 3},
    {"id": "00000000-0006-0000-0000-000000000061", "code": None, "name": "Safety Foundations",                                         "scope": None, "parent_category_id": "00000000-0005-0000-0000-000000000017", "description": None, "is_active": True, "sort_order": 4},
    {"id": "00000000-0006-0000-0000-000000000062", "code": None, "name": "Sign relocation",                                            "scope": None, "parent_category_id": "00000000-0005-0000-0000-000000000017", "description": None, "is_active": True, "sort_order": 5},
    {"id": "00000000-0006-0000-0000-000000000063", "code": None, "name": "Sign removal",                                               "scope": None, "parent_category_id": "00000000-0005-0000-0000-000000000017", "description": None, "is_active": True, "sort_order": 6},
    {"id": "00000000-0006-0000-0000-000000000064", "code": None, "name": "Soil Nailing",                                               "scope": None, "parent_category_id": "00000000-0005-0000-0000-000000000017", "description": None, "is_active": True, "sort_order": 7},
    {"id": "00000000-0006-0000-0000-000000000065", "code": None, "name": "Soil and Water Management",                                  "scope": None, "parent_category_id": "00000000-0005-0000-0000-000000000017", "description": None, "is_active": True, "sort_order": 8},
    {"id": "00000000-0006-0000-0000-000000000066", "code": None, "name": "Street Lighting",                                            "scope": None, "parent_category_id": "00000000-0005-0000-0000-000000000017", "description": None, "is_active": True, "sort_order": 9},
    {"id": "00000000-0006-0000-0000-000000000067", "code": None, "name": "Terminal",                                                   "scope": None, "parent_category_id": "00000000-0005-0000-0000-000000000017", "description": None, "is_active": True, "sort_order": 10},
    {"id": "00000000-0006-0000-0000-000000000068", "code": None, "name": "Traffic Control Signals \u2013 New Installation and Reconstruction", "scope": None, "parent_category_id": "00000000-0005-0000-0000-000000000017", "description": None, "is_active": True, "sort_order": 11},
    # Signage
    {"id": "00000000-0006-0000-0000-000000000069", "code": None, "name": "Gantries",                                                   "scope": None, "parent_category_id": "00000000-0005-0000-0000-000000000018", "description": None, "is_active": True, "sort_order": 1},
    {"id": "00000000-0006-0000-0000-000000000070", "code": None, "name": "Local Streets",                                              "scope": None, "parent_category_id": "00000000-0005-0000-0000-000000000018", "description": None, "is_active": True, "sort_order": 2},
    {"id": "00000000-0006-0000-0000-000000000071", "code": None, "name": "Posts",                                                      "scope": None, "parent_category_id": "00000000-0005-0000-0000-000000000018", "description": None, "is_active": True, "sort_order": 3},
    {"id": "00000000-0006-0000-0000-000000000072", "code": None, "name": "Signs",                                                      "scope": None, "parent_category_id": "00000000-0005-0000-0000-000000000018", "description": None, "is_active": True, "sort_order": 4},
    {"id": "00000000-0006-0000-0000-000000000073", "code": None, "name": "Urban Infrastructure",                                       "scope": None, "parent_category_id": "00000000-0005-0000-0000-000000000018", "description": None, "is_active": True, "sort_order": 5},
    # Site Clearance and Earthworks
    {"id": "00000000-0006-0000-0000-000000000074", "code": None, "name": "Anchored Rockfall Netting",                                  "scope": None, "parent_category_id": "00000000-0005-0000-0000-000000000019", "description": None, "is_active": True, "sort_order": 1},
    {"id": "00000000-0006-0000-0000-000000000075", "code": None, "name": "Concrete Components",                                        "scope": None, "parent_category_id": "00000000-0005-0000-0000-000000000019", "description": None, "is_active": True, "sort_order": 2},
    {"id": "00000000-0006-0000-0000-000000000076", "code": None, "name": "Concrete Panel Steel Pile",                                  "scope": None, "parent_category_id": "00000000-0005-0000-0000-000000000019", "description": None, "is_active": True, "sort_order": 3},
    {"id": "00000000-0006-0000-0000-000000000077", "code": None, "name": "Concrete Secant Pile",                                       "scope": None, "parent_category_id": "00000000-0005-0000-0000-000000000019", "description": None, "is_active": True, "sort_order": 4},
    {"id": "00000000-0006-0000-0000-000000000078", "code": None, "name": "L Shape Concrete",                                           "scope": None, "parent_category_id": "00000000-0005-0000-0000-000000000019", "description": None, "is_active": True, "sort_order": 5},
    {"id": "00000000-0006-0000-0000-000000000079", "code": None, "name": "Mechanically Stabilised Earth",                              "scope": None, "parent_category_id": "00000000-0005-0000-0000-000000000019", "description": None, "is_active": True, "sort_order": 6},
    {"id": "00000000-0006-0000-0000-000000000080", "code": None, "name": "Nail/Anchor Cut Face with Shotcrete Facing",                 "scope": None, "parent_category_id": "00000000-0005-0000-0000-000000000019", "description": None, "is_active": True, "sort_order": 7},
    {"id": "00000000-0006-0000-0000-000000000081", "code": None, "name": "Timber Poles",                                               "scope": None, "parent_category_id": "00000000-0005-0000-0000-000000000019", "description": None, "is_active": True, "sort_order": 8},
    {"id": "00000000-0006-0000-0000-000000000082", "code": None, "name": "Wooden Lagging Steel Pile",                                  "scope": None, "parent_category_id": "00000000-0005-0000-0000-000000000019", "description": None, "is_active": True, "sort_order": 9},
    # State Highway Structures
    {"id": "00000000-0006-0000-0000-000000000083", "code": None, "name": "Basecourse",                                                 "scope": None, "parent_category_id": "00000000-0005-0000-0000-000000000020", "description": None, "is_active": True, "sort_order": 1},
    {"id": "00000000-0006-0000-0000-000000000084", "code": None, "name": "Pedestrian Bridge",                                          "scope": None, "parent_category_id": "00000000-0005-0000-0000-000000000020", "description": None, "is_active": True, "sort_order": 2},
    {"id": "00000000-0006-0000-0000-000000000085", "code": None, "name": "Road Bridge",                                                "scope": None, "parent_category_id": "00000000-0005-0000-0000-000000000020", "description": None, "is_active": True, "sort_order": 3},
    {"id": "00000000-0006-0000-0000-000000000086", "code": None, "name": "Station Building",                                           "scope": None, "parent_category_id": "00000000-0005-0000-0000-000000000020", "description": None, "is_active": True, "sort_order": 4},
    {"id": "00000000-0006-0000-0000-000000000087", "code": None, "name": "Surface",                                                    "scope": None, "parent_category_id": "00000000-0005-0000-0000-000000000020", "description": None, "is_active": True, "sort_order": 5},
    {"id": "00000000-0006-0000-0000-000000000088", "code": None, "name": "Underpass/Box Culvert",                                      "scope": None, "parent_category_id": "00000000-0005-0000-0000-000000000020", "description": None, "is_active": True, "sort_order": 6},
    # Street Furniture
    {"id": "00000000-0006-0000-0000-000000000089", "code": None, "name": "Bins",                                                       "scope": None, "parent_category_id": "00000000-0005-0000-0000-000000000021", "description": None, "is_active": True, "sort_order": 1},
    {"id": "00000000-0006-0000-0000-000000000090", "code": None, "name": "Bollards",                                                   "scope": None, "parent_category_id": "00000000-0005-0000-0000-000000000021", "description": None, "is_active": True, "sort_order": 2},
    {"id": "00000000-0006-0000-0000-000000000091", "code": None, "name": "Cycle Stand",                                                "scope": None, "parent_category_id": "00000000-0005-0000-0000-000000000021", "description": None, "is_active": True, "sort_order": 3},
    {"id": "00000000-0006-0000-0000-000000000092", "code": None, "name": "Seating and Benches",                                        "scope": None, "parent_category_id": "00000000-0005-0000-0000-000000000021", "description": None, "is_active": True, "sort_order": 4},
    {"id": "00000000-0006-0000-0000-000000000093", "code": None, "name": "Shelters",                                                   "scope": None, "parent_category_id": "00000000-0005-0000-0000-000000000021", "description": None, "is_active": True, "sort_order": 5},
    # Street Lighting
    {"id": "00000000-0006-0000-0000-000000000094", "code": None, "name": "Lighting Components",                                        "scope": None, "parent_category_id": "00000000-0005-0000-0000-000000000022", "description": None, "is_active": True, "sort_order": 1},
    {"id": "00000000-0006-0000-0000-000000000095", "code": None, "name": "Poles and Foundations",                                      "scope": None, "parent_category_id": "00000000-0005-0000-0000-000000000022", "description": None, "is_active": True, "sort_order": 2},
    # Structure
    {"id": "00000000-0006-0000-0000-000000000096", "code": None, "name": "Cold Milling of Road Pavement Materials",                    "scope": None, "parent_category_id": "00000000-0005-0000-0000-000000000023", "description": None, "is_active": True, "sort_order": 1},
    {"id": "00000000-0006-0000-0000-000000000097", "code": None, "name": "Construction of Reinforced Concrete Walls",                  "scope": None, "parent_category_id": "00000000-0005-0000-0000-000000000023", "description": None, "is_active": True, "sort_order": 2},
    {"id": "00000000-0006-0000-0000-000000000098", "code": None, "name": "Construction of Reinforced Concrete Walls with Piled Foundations", "scope": None, "parent_category_id": "00000000-0005-0000-0000-000000000023", "description": None, "is_active": True, "sort_order": 3},
    {"id": "00000000-0006-0000-0000-000000000099", "code": None, "name": "Construction of Reinforced Soil Walls (contractor's design)", "scope": None, "parent_category_id": "00000000-0005-0000-0000-000000000023", "description": None, "is_active": True, "sort_order": 4},
    {"id": "00000000-0006-0000-0000-000000000100", "code": None, "name": "Construction of Reinforced Soil Walls (principal's design)",  "scope": None, "parent_category_id": "00000000-0005-0000-0000-000000000023", "description": None, "is_active": True, "sort_order": 5},
    {"id": "00000000-0006-0000-0000-000000000101", "code": None, "name": "Design and Construction of Noise Walls",                     "scope": None, "parent_category_id": "00000000-0005-0000-0000-000000000023", "description": None, "is_active": True, "sort_order": 6},
    {"id": "00000000-0006-0000-0000-000000000102", "code": None, "name": "Landscape Planting",                                         "scope": None, "parent_category_id": "00000000-0005-0000-0000-000000000023", "description": None, "is_active": True, "sort_order": 7},
    {"id": "00000000-0006-0000-0000-000000000103", "code": None, "name": "Shotcrete Work without Steel Fibres",                        "scope": None, "parent_category_id": "00000000-0005-0000-0000-000000000023", "description": None, "is_active": True, "sort_order": 8},
    # Substructure and Pavements
    {"id": "00000000-0006-0000-0000-000000000104", "code": None, "name": "Bituminous Slurry Surfacing",                                "scope": None, "parent_category_id": "00000000-0005-0000-0000-000000000024", "description": None, "is_active": True, "sort_order": 1},
    {"id": "00000000-0006-0000-0000-000000000105", "code": None, "name": "Coloured Surface Coatings for Bus Lanes and Cycleways",      "scope": None, "parent_category_id": "00000000-0005-0000-0000-000000000024", "description": None, "is_active": True, "sort_order": 2},
    {"id": "00000000-0006-0000-0000-000000000106", "code": None, "name": "Construction of Plant Mixed Heavily Bound Pavement Course",  "scope": None, "parent_category_id": "00000000-0005-0000-0000-000000000024", "description": None, "is_active": True, "sort_order": 3},
    {"id": "00000000-0006-0000-0000-000000000107", "code": None, "name": "Construction of Reinforced Soil Walls (contractor's design)", "scope": None, "parent_category_id": "00000000-0005-0000-0000-000000000024", "description": None, "is_active": True, "sort_order": 4},
    {"id": "00000000-0006-0000-0000-000000000108", "code": None, "name": "Construction of Reinforced Soil Walls (principal's design)",  "scope": None, "parent_category_id": "00000000-0005-0000-0000-000000000024", "description": None, "is_active": True, "sort_order": 5},
    {"id": "00000000-0006-0000-0000-000000000109", "code": None, "name": "Crumb Rubber Asphalt",                                       "scope": None, "parent_category_id": "00000000-0005-0000-0000-000000000024", "description": None, "is_active": True, "sort_order": 6},
    {"id": "00000000-0006-0000-0000-000000000110", "code": None, "name": "Earthworks",                                                 "scope": None, "parent_category_id": "00000000-0005-0000-0000-000000000024", "description": None, "is_active": True, "sort_order": 7},
    {"id": "00000000-0006-0000-0000-000000000111", "code": None, "name": "General Concrete Paving",                                    "scope": None, "parent_category_id": "00000000-0005-0000-0000-000000000024", "description": None, "is_active": True, "sort_order": 8},
    {"id": "00000000-0006-0000-0000-000000000112", "code": None, "name": "Heavy Duty Dense Graded Asphalt",                            "scope": None, "parent_category_id": "00000000-0005-0000-0000-000000000024", "description": None, "is_active": True, "sort_order": 9},
    {"id": "00000000-0006-0000-0000-000000000113", "code": None, "name": "High Modulus Asphalt (EME2)",                                "scope": None, "parent_category_id": "00000000-0005-0000-0000-000000000024", "description": None, "is_active": True, "sort_order": 10},
    {"id": "00000000-0006-0000-0000-000000000114", "code": None, "name": "Insitu Pavement Stabilisation Using Slow Setting Binders",   "scope": None, "parent_category_id": "00000000-0005-0000-0000-000000000024", "description": None, "is_active": True, "sort_order": 11},
    {"id": "00000000-0006-0000-0000-000000000115", "code": None, "name": "Jointed Concrete Base",                                      "scope": None, "parent_category_id": "00000000-0005-0000-0000-000000000024", "description": None, "is_active": True, "sort_order": 12},
    {"id": "00000000-0006-0000-0000-000000000116", "code": None, "name": "Lean-Mix Concrete Subbase",                                  "scope": None, "parent_category_id": "00000000-0005-0000-0000-000000000024", "description": None, "is_active": True, "sort_order": 13},
    {"id": "00000000-0006-0000-0000-000000000117", "code": None, "name": "Light Duty Dense Graded Asphalt",                            "scope": None, "parent_category_id": "00000000-0005-0000-0000-000000000024", "description": None, "is_active": True, "sort_order": 14},
    {"id": "00000000-0006-0000-0000-000000000118", "code": None, "name": "No Fines Concrete Subbase",                                  "scope": None, "parent_category_id": "00000000-0005-0000-0000-000000000024", "description": None, "is_active": True, "sort_order": 15},
    {"id": "00000000-0006-0000-0000-000000000119", "code": None, "name": "Open Graded Asphalt",                                        "scope": None, "parent_category_id": "00000000-0005-0000-0000-000000000024", "description": None, "is_active": True, "sort_order": 16},
    {"id": "00000000-0006-0000-0000-000000000120", "code": None, "name": "Plastic Flexible Pipes",                                     "scope": None, "parent_category_id": "00000000-0005-0000-0000-000000000024", "description": None, "is_active": True, "sort_order": 17},
    {"id": "00000000-0006-0000-0000-000000000121", "code": None, "name": "Rock Filled Gabions and Mattresses",                         "scope": None, "parent_category_id": "00000000-0005-0000-0000-000000000024", "description": None, "is_active": True, "sort_order": 18},
    {"id": "00000000-0006-0000-0000-000000000122", "code": None, "name": "Roller Compacted Concrete Subbase",                          "scope": None, "parent_category_id": "00000000-0005-0000-0000-000000000024", "description": None, "is_active": True, "sort_order": 19},
    {"id": "00000000-0006-0000-0000-000000000123", "code": None, "name": "Soil and Water Management",                                  "scope": None, "parent_category_id": "00000000-0005-0000-0000-000000000024", "description": None, "is_active": True, "sort_order": 20},
    {"id": "00000000-0006-0000-0000-000000000124", "code": None, "name": "Sprayed Bituminous Surfacing (for enrichment & rejuvenation)","scope": None, "parent_category_id": "00000000-0005-0000-0000-000000000024", "description": None, "is_active": True, "sort_order": 21},
    {"id": "00000000-0006-0000-0000-000000000125", "code": None, "name": "Sprayed Bituminous Surfacing (with bitumen emulsion)",        "scope": None, "parent_category_id": "00000000-0005-0000-0000-000000000024", "description": None, "is_active": True, "sort_order": 22},
    {"id": "00000000-0006-0000-0000-000000000126", "code": None, "name": "Sprayed Bituminous Surfacing (with cutback bitumen)",         "scope": None, "parent_category_id": "00000000-0005-0000-0000-000000000024", "description": None, "is_active": True, "sort_order": 23},
    {"id": "00000000-0006-0000-0000-000000000127", "code": None, "name": "Sprayed Bituminous Surfacing (with fibre reinforcement)",     "scope": None, "parent_category_id": "00000000-0005-0000-0000-000000000024", "description": None, "is_active": True, "sort_order": 24},
    {"id": "00000000-0006-0000-0000-000000000128", "code": None, "name": "Sprayed Bituminous Surfacing (with polymer modified bitumen)","scope": None, "parent_category_id": "00000000-0005-0000-0000-000000000024", "description": None, "is_active": True, "sort_order": 25},
    {"id": "00000000-0006-0000-0000-000000000129", "code": None, "name": "Stabilisation of Earthworks",                                "scope": None, "parent_category_id": "00000000-0005-0000-0000-000000000024", "description": None, "is_active": True, "sort_order": 26},
    {"id": "00000000-0006-0000-0000-000000000130", "code": None, "name": "Stone Mastic Asphalt",                                       "scope": None, "parent_category_id": "00000000-0005-0000-0000-000000000024", "description": None, "is_active": True, "sort_order": 27},
    {"id": "00000000-0006-0000-0000-000000000131", "code": None, "name": "Thin Open Graded Asphalt Surfacing",                         "scope": None, "parent_category_id": "00000000-0005-0000-0000-000000000024", "description": None, "is_active": True, "sort_order": 28},
    {"id": "00000000-0006-0000-0000-000000000132", "code": None, "name": "Unbound and Modified Pavement Course",                       "scope": None, "parent_category_id": "00000000-0005-0000-0000-000000000024", "description": None, "is_active": True, "sort_order": 29},
    # Surface and Underground Drainage
    {"id": "00000000-0006-0000-0000-000000000133", "code": None, "name": "Aggregate",                                                  "scope": None, "parent_category_id": "00000000-0005-0000-0000-000000000025", "description": None, "is_active": True, "sort_order": 1},
    {"id": "00000000-0006-0000-0000-000000000134", "code": None, "name": "Class B1 - 1 Cell",                                          "scope": None, "parent_category_id": "00000000-0005-0000-0000-000000000025", "description": None, "is_active": True, "sort_order": 2},
    {"id": "00000000-0006-0000-0000-000000000135", "code": None, "name": "Class B1 - 10 Cell",                                         "scope": None, "parent_category_id": "00000000-0005-0000-0000-000000000025", "description": None, "is_active": True, "sort_order": 3},
    {"id": "00000000-0006-0000-0000-000000000136", "code": None, "name": "Class B1 - 12 Cell",                                         "scope": None, "parent_category_id": "00000000-0005-0000-0000-000000000025", "description": None, "is_active": True, "sort_order": 4},
    {"id": "00000000-0006-0000-0000-000000000137", "code": None, "name": "Class B1 - 15 Cell",                                         "scope": None, "parent_category_id": "00000000-0005-0000-0000-000000000025", "description": None, "is_active": True, "sort_order": 5},
    {"id": "00000000-0006-0000-0000-000000000138", "code": None, "name": "Class B1 - 2 Cell",                                          "scope": None, "parent_category_id": "00000000-0005-0000-0000-000000000025", "description": None, "is_active": True, "sort_order": 6},
    {"id": "00000000-0006-0000-0000-000000000139", "code": None, "name": "Class B1 - 24 Cell",                                         "scope": None, "parent_category_id": "00000000-0005-0000-0000-000000000025", "description": None, "is_active": True, "sort_order": 7},
    {"id": "00000000-0006-0000-0000-000000000140", "code": None, "name": "Class B1 - 3 Cell",                                          "scope": None, "parent_category_id": "00000000-0005-0000-0000-000000000025", "description": None, "is_active": True, "sort_order": 8},
    {"id": "00000000-0006-0000-0000-000000000141", "code": None, "name": "Class B1 - 4 Cell",                                          "scope": None, "parent_category_id": "00000000-0005-0000-0000-000000000025", "description": None, "is_active": True, "sort_order": 9},
    {"id": "00000000-0006-0000-0000-000000000142", "code": None, "name": "Class B1 - 5 Cell",                                          "scope": None, "parent_category_id": "00000000-0005-0000-0000-000000000025", "description": None, "is_active": True, "sort_order": 10},
    {"id": "00000000-0006-0000-0000-000000000143", "code": None, "name": "Class B1 - 57 Cell",                                         "scope": None, "parent_category_id": "00000000-0005-0000-0000-000000000025", "description": None, "is_active": True, "sort_order": 11},
    {"id": "00000000-0006-0000-0000-000000000144", "code": None, "name": "Class B1 - 6 Cell",                                          "scope": None, "parent_category_id": "00000000-0005-0000-0000-000000000025", "description": None, "is_active": True, "sort_order": 12},
    {"id": "00000000-0006-0000-0000-000000000145", "code": None, "name": "Class B1 - 7 Cell",                                          "scope": None, "parent_category_id": "00000000-0005-0000-0000-000000000025", "description": None, "is_active": True, "sort_order": 13},
    {"id": "00000000-0006-0000-0000-000000000146", "code": None, "name": "Class B1 - 8 Cell",                                          "scope": None, "parent_category_id": "00000000-0005-0000-0000-000000000025", "description": None, "is_active": True, "sort_order": 14},
    {"id": "00000000-0006-0000-0000-000000000147", "code": None, "name": "Class B1 - 9 Cell",                                          "scope": None, "parent_category_id": "00000000-0005-0000-0000-000000000025", "description": None, "is_active": True, "sort_order": 15},
    {"id": "00000000-0006-0000-0000-000000000148", "code": None, "name": "Clearing and Grubbing",                                      "scope": None, "parent_category_id": "00000000-0005-0000-0000-000000000025", "description": None, "is_active": True, "sort_order": 16},
    {"id": "00000000-0006-0000-0000-000000000149", "code": None, "name": "Construction of Reinforced Soil Walls (contractor's design)", "scope": None, "parent_category_id": "00000000-0005-0000-0000-000000000025", "description": None, "is_active": True, "sort_order": 17},
    {"id": "00000000-0006-0000-0000-000000000150", "code": None, "name": "Construction of Reinforced Soil Walls (principal's design)",  "scope": None, "parent_category_id": "00000000-0005-0000-0000-000000000025", "description": None, "is_active": True, "sort_order": 18},
    {"id": "00000000-0006-0000-0000-000000000151", "code": None, "name": "Crossing removal",                                           "scope": None, "parent_category_id": "00000000-0005-0000-0000-000000000025", "description": None, "is_active": True, "sort_order": 19},
    {"id": "00000000-0006-0000-0000-000000000152", "code": None, "name": "Drainage box",                                               "scope": None, "parent_category_id": "00000000-0005-0000-0000-000000000025", "description": None, "is_active": True, "sort_order": 20},
    {"id": "00000000-0006-0000-0000-000000000153", "code": None, "name": "Edge Drains",                                                "scope": None, "parent_category_id": "00000000-0005-0000-0000-000000000025", "description": None, "is_active": True, "sort_order": 21},
    {"id": "00000000-0006-0000-0000-000000000154", "code": None, "name": "Excavation",                                                 "scope": None, "parent_category_id": "00000000-0005-0000-0000-000000000025", "description": None, "is_active": True, "sort_order": 22},
    {"id": "00000000-0006-0000-0000-000000000155", "code": None, "name": "Filter",                                                     "scope": None, "parent_category_id": "00000000-0005-0000-0000-000000000025", "description": None, "is_active": True, "sort_order": 23},
    {"id": "00000000-0006-0000-0000-000000000156", "code": None, "name": "Grate",                                                      "scope": None, "parent_category_id": "00000000-0005-0000-0000-000000000025", "description": None, "is_active": True, "sort_order": 24},
    {"id": "00000000-0006-0000-0000-000000000157", "code": None, "name": "Gutters",                                                    "scope": None, "parent_category_id": "00000000-0005-0000-0000-000000000025", "description": None, "is_active": True, "sort_order": 25},
    {"id": "00000000-0006-0000-0000-000000000158", "code": None, "name": "Headwalls to Suit 1 Cell",                                   "scope": None, "parent_category_id": "00000000-0005-0000-0000-000000000025", "description": None, "is_active": True, "sort_order": 26},
    {"id": "00000000-0006-0000-0000-000000000159", "code": None, "name": "Headwalls to Suit 2 Cell",                                   "scope": None, "parent_category_id": "00000000-0005-0000-0000-000000000025", "description": None, "is_active": True, "sort_order": 27},
    {"id": "00000000-0006-0000-0000-000000000160", "code": None, "name": "Headwalls to Suit 3 Cell",                                   "scope": None, "parent_category_id": "00000000-0005-0000-0000-000000000025", "description": None, "is_active": True, "sort_order": 28},
    {"id": "00000000-0006-0000-0000-000000000161", "code": None, "name": "Headwalls to Suit 4 Cell",                                   "scope": None, "parent_category_id": "00000000-0005-0000-0000-000000000025", "description": None, "is_active": True, "sort_order": 29},
    {"id": "00000000-0006-0000-0000-000000000162", "code": None, "name": "Headwalls to Suit 5 Cell",                                   "scope": None, "parent_category_id": "00000000-0005-0000-0000-000000000025", "description": None, "is_active": True, "sort_order": 30},
    {"id": "00000000-0006-0000-0000-000000000163", "code": None, "name": "Headwalls to Suit 7 Cell",                                   "scope": None, "parent_category_id": "00000000-0005-0000-0000-000000000025", "description": None, "is_active": True, "sort_order": 31},
    {"id": "00000000-0006-0000-0000-000000000164", "code": None, "name": "Intra-Pavement Drains",                                      "scope": None, "parent_category_id": "00000000-0005-0000-0000-000000000025", "description": None, "is_active": True, "sort_order": 32},
    {"id": "00000000-0006-0000-0000-000000000165", "code": None, "name": "Kerb removal",                                               "scope": None, "parent_category_id": "00000000-0005-0000-0000-000000000025", "description": None, "is_active": True, "sort_order": 33},
    {"id": "00000000-0006-0000-0000-000000000166", "code": None, "name": "Kerbs",                                                      "scope": None, "parent_category_id": "00000000-0005-0000-0000-000000000025", "description": None, "is_active": True, "sort_order": 34},
    {"id": "00000000-0006-0000-0000-000000000167", "code": None, "name": "Kerbs and Gutters",                                          "scope": None, "parent_category_id": "00000000-0005-0000-0000-000000000025", "description": None, "is_active": True, "sort_order": 35},
    {"id": "00000000-0006-0000-0000-000000000168", "code": None, "name": "Lining of Catch Drains",                                    "scope": None, "parent_category_id": "00000000-0005-0000-0000-000000000025", "description": None, "is_active": True, "sort_order": 36},
    {"id": "00000000-0006-0000-0000-000000000169", "code": None, "name": "Open Drains",                                               "scope": None, "parent_category_id": "00000000-0005-0000-0000-000000000025", "description": None, "is_active": True, "sort_order": 37},
    {"id": "00000000-0006-0000-0000-000000000170", "code": None, "name": "Pit",                                                        "scope": None, "parent_category_id": "00000000-0005-0000-0000-000000000025", "description": None, "is_active": True, "sort_order": 38},
    {"id": "00000000-0006-0000-0000-000000000171", "code": None, "name": "Pits",                                                       "scope": None, "parent_category_id": "00000000-0005-0000-0000-000000000025", "description": None, "is_active": True, "sort_order": 39},
    {"id": "00000000-0006-0000-0000-000000000172", "code": None, "name": "Ramp Removal",                                               "scope": None, "parent_category_id": "00000000-0005-0000-0000-000000000025", "description": None, "is_active": True, "sort_order": 40},
    {"id": "00000000-0006-0000-0000-000000000173", "code": None, "name": "Ramps",                                                      "scope": None, "parent_category_id": "00000000-0005-0000-0000-000000000025", "description": None, "is_active": True, "sort_order": 41},
    {"id": "00000000-0006-0000-0000-000000000174", "code": None, "name": "Stormwater Drainage Pipe",                                   "scope": None, "parent_category_id": "00000000-0005-0000-0000-000000000025", "description": None, "is_active": True, "sort_order": 42},
    {"id": "00000000-0006-0000-0000-000000000175", "code": None, "name": "Trench Drains",                                              "scope": None, "parent_category_id": "00000000-0005-0000-0000-000000000025", "description": None, "is_active": True, "sort_order": 43},
    {"id": "00000000-0006-0000-0000-000000000176", "code": None, "name": "Vertical Wick Drains",                                       "scope": None, "parent_category_id": "00000000-0005-0000-0000-000000000025", "description": None, "is_active": True, "sort_order": 44},
    # Traffic Islands and Raised Tables
    {"id": "00000000-0006-0000-0000-000000000177", "code": None, "name": "Raised Tables",                                              "scope": None, "parent_category_id": "00000000-0005-0000-0000-000000000026", "description": None, "is_active": True, "sort_order": 1},
    {"id": "00000000-0006-0000-0000-000000000178", "code": None, "name": "Traffic Islands",                                            "scope": None, "parent_category_id": "00000000-0005-0000-0000-000000000026", "description": None, "is_active": True, "sort_order": 2},
    # Traffic Signals
    {"id": "00000000-0006-0000-0000-000000000179", "code": None, "name": "Lanterns",                                                   "scope": None, "parent_category_id": "00000000-0005-0000-0000-000000000027", "description": None, "is_active": True, "sort_order": 1},
    {"id": "00000000-0006-0000-0000-000000000180", "code": None, "name": "Signal frames",                                              "scope": None, "parent_category_id": "00000000-0005-0000-0000-000000000027", "description": None, "is_active": True, "sort_order": 2},
    # Utilities
    {"id": "00000000-0006-0000-0000-000000000181", "code": None, "name": "Cables",                                                     "scope": None, "parent_category_id": "00000000-0005-0000-0000-000000000028", "description": None, "is_active": True, "sort_order": 1},
    {"id": "00000000-0006-0000-0000-000000000182", "code": None, "name": "Ducts",                                                      "scope": None, "parent_category_id": "00000000-0005-0000-0000-000000000028", "description": None, "is_active": True, "sort_order": 2},

    # -------------------------------------------------------------------------
    # ECCL Grade 3/4 — top-level categories (0007 series)
    # -------------------------------------------------------------------------
    {"id": "00000000-0007-0000-0000-000000000001", "code": None, "name": "Electricity",      "scope": None, "parent_category_id": None, "description": "ECCL Grade 3/4 benchmark category.", "is_active": True, "sort_order": 1},
    {"id": "00000000-0007-0000-0000-000000000002", "code": None, "name": "Employee Commute", "scope": None, "parent_category_id": None, "description": "ECCL Grade 3/4 benchmark category.", "is_active": True, "sort_order": 2},
    {"id": "00000000-0007-0000-0000-000000000003", "code": None, "name": "Fuels",            "scope": None, "parent_category_id": None, "description": "ECCL Grade 3/4 benchmark category.", "is_active": True, "sort_order": 3},
    {"id": "00000000-0007-0000-0000-000000000004", "code": None, "name": "Gases",            "scope": None, "parent_category_id": None, "description": "ECCL Grade 3/4 benchmark category.", "is_active": True, "sort_order": 4},
    {"id": "00000000-0007-0000-0000-000000000005", "code": None, "name": "Materials",        "scope": None, "parent_category_id": None, "description": "ECCL Grade 3/4 benchmark category.", "is_active": True, "sort_order": 5},
    {"id": "00000000-0007-0000-0000-000000000006", "code": None, "name": "Vegetation",       "scope": None, "parent_category_id": None, "description": "ECCL Grade 3/4 benchmark category.", "is_active": True, "sort_order": 6},
    {"id": "00000000-0007-0000-0000-000000000007", "code": None, "name": "Waste",            "scope": None, "parent_category_id": None, "description": "ECCL Grade 3/4 benchmark category.", "is_active": True, "sort_order": 7},
    {"id": "00000000-0007-0000-0000-000000000008", "code": None, "name": "Water",            "scope": None, "parent_category_id": None, "description": "ECCL Grade 3/4 benchmark category.", "is_active": True, "sort_order": 8},

    # -------------------------------------------------------------------------
    # ECCL Grade 3/4 — sub-categories (0008 series)
    # -------------------------------------------------------------------------
    # Electricity
    {"id": "00000000-0008-0000-0000-000000000001", "code": None, "name": "Grid Electricity",                                "scope": None, "parent_category_id": "00000000-0007-0000-0000-000000000001", "description": None, "is_active": True, "sort_order": 1},
    {"id": "00000000-0008-0000-0000-000000000002", "code": None, "name": "Off-site renewables",                             "scope": None, "parent_category_id": "00000000-0007-0000-0000-000000000001", "description": None, "is_active": True, "sort_order": 2},
    {"id": "00000000-0008-0000-0000-000000000003", "code": None, "name": "On-site renewables",                              "scope": None, "parent_category_id": "00000000-0007-0000-0000-000000000001", "description": None, "is_active": True, "sort_order": 3},
    # Employee Commute
    {"id": "00000000-0008-0000-0000-000000000004", "code": None, "name": "Bus Transport",                                   "scope": None, "parent_category_id": "00000000-0007-0000-0000-000000000002", "description": None, "is_active": True, "sort_order": 1},
    {"id": "00000000-0008-0000-0000-000000000005", "code": None, "name": "Ferry Transport",                                 "scope": None, "parent_category_id": "00000000-0007-0000-0000-000000000002", "description": None, "is_active": True, "sort_order": 2},
    {"id": "00000000-0008-0000-0000-000000000006", "code": None, "name": "Private Car Transport",                           "scope": None, "parent_category_id": "00000000-0007-0000-0000-000000000002", "description": None, "is_active": True, "sort_order": 3},
    {"id": "00000000-0008-0000-0000-000000000007", "code": None, "name": "Private car default",                             "scope": None, "parent_category_id": "00000000-0007-0000-0000-000000000002", "description": None, "is_active": True, "sort_order": 4},
    {"id": "00000000-0008-0000-0000-000000000008", "code": None, "name": "Rail Transport",                                  "scope": None, "parent_category_id": "00000000-0007-0000-0000-000000000002", "description": None, "is_active": True, "sort_order": 5},
    {"id": "00000000-0008-0000-0000-000000000009", "code": None, "name": "Working from home",                               "scope": None, "parent_category_id": "00000000-0007-0000-0000-000000000002", "description": None, "is_active": True, "sort_order": 6},
    # Fuels
    {"id": "00000000-0008-0000-0000-000000000010", "code": None, "name": "Gaseous Fuels",                                   "scope": None, "parent_category_id": "00000000-0007-0000-0000-000000000003", "description": None, "is_active": True, "sort_order": 1},
    {"id": "00000000-0008-0000-0000-000000000011", "code": None, "name": "Liquid Fuels (Stationary)",                       "scope": None, "parent_category_id": "00000000-0007-0000-0000-000000000003", "description": None, "is_active": True, "sort_order": 2},
    {"id": "00000000-0008-0000-0000-000000000012", "code": None, "name": "Liquid Fuels (Transport)",                        "scope": None, "parent_category_id": "00000000-0007-0000-0000-000000000003", "description": None, "is_active": True, "sort_order": 3},
    {"id": "00000000-0008-0000-0000-000000000013", "code": None, "name": "Solid Fuels",                                     "scope": None, "parent_category_id": "00000000-0007-0000-0000-000000000003", "description": None, "is_active": True, "sort_order": 4},
    # Gases
    {"id": "00000000-0008-0000-0000-000000000014", "code": None, "name": "Hydrofluorocarbons (HFCs)",                       "scope": None, "parent_category_id": "00000000-0007-0000-0000-000000000004", "description": None, "is_active": True, "sort_order": 1},
    {"id": "00000000-0008-0000-0000-000000000015", "code": None, "name": "Other gases",                                     "scope": None, "parent_category_id": "00000000-0007-0000-0000-000000000004", "description": None, "is_active": True, "sort_order": 2},
    {"id": "00000000-0008-0000-0000-000000000016", "code": None, "name": "Perfluorinated compounds",                        "scope": None, "parent_category_id": "00000000-0007-0000-0000-000000000004", "description": None, "is_active": True, "sort_order": 3},
    {"id": "00000000-0008-0000-0000-000000000017", "code": None, "name": "Perfluorocarbons (PFCs)",                         "scope": None, "parent_category_id": "00000000-0007-0000-0000-000000000004", "description": None, "is_active": True, "sort_order": 4},
    # Materials
    {"id": "00000000-0008-0000-0000-000000000018", "code": None, "name": "Aggregate",                                       "scope": None, "parent_category_id": "00000000-0007-0000-0000-000000000005", "description": None, "is_active": True, "sort_order": 1},
    {"id": "00000000-0008-0000-0000-000000000019", "code": None, "name": "Aluminium - extruded",                            "scope": None, "parent_category_id": "00000000-0007-0000-0000-000000000005", "description": None, "is_active": True, "sort_order": 2},
    {"id": "00000000-0008-0000-0000-000000000020", "code": None, "name": "Asphalt",                                         "scope": None, "parent_category_id": "00000000-0007-0000-0000-000000000005", "description": None, "is_active": True, "sort_order": 3},
    {"id": "00000000-0008-0000-0000-000000000021", "code": None, "name": "Bitumen",                                         "scope": None, "parent_category_id": "00000000-0007-0000-0000-000000000005", "description": None, "is_active": True, "sort_order": 4},
    {"id": "00000000-0008-0000-0000-000000000022", "code": None, "name": "Building and MEP services",                       "scope": None, "parent_category_id": "00000000-0007-0000-0000-000000000005", "description": None, "is_active": True, "sort_order": 5},
    {"id": "00000000-0008-0000-0000-000000000023", "code": None, "name": "Cable",                                           "scope": None, "parent_category_id": "00000000-0007-0000-0000-000000000005", "description": None, "is_active": True, "sort_order": 6},
    {"id": "00000000-0008-0000-0000-000000000024", "code": None, "name": "Ceilings & walls",                                "scope": None, "parent_category_id": "00000000-0007-0000-0000-000000000005", "description": None, "is_active": True, "sort_order": 7},
    {"id": "00000000-0008-0000-0000-000000000025", "code": None, "name": "Cement",                                          "scope": None, "parent_category_id": "00000000-0007-0000-0000-000000000005", "description": None, "is_active": True, "sort_order": 8},
    {"id": "00000000-0008-0000-0000-000000000026", "code": None, "name": "Cladding/roofing",                                "scope": None, "parent_category_id": "00000000-0007-0000-0000-000000000005", "description": None, "is_active": True, "sort_order": 9},
    {"id": "00000000-0008-0000-0000-000000000027", "code": None, "name": "Cold rolled steel",                               "scope": None, "parent_category_id": "00000000-0007-0000-0000-000000000005", "description": None, "is_active": True, "sort_order": 10},
    {"id": "00000000-0008-0000-0000-000000000028", "code": None, "name": "Concrete In-situ",                                "scope": None, "parent_category_id": "00000000-0007-0000-0000-000000000005", "description": None, "is_active": True, "sort_order": 11},
    {"id": "00000000-0008-0000-0000-000000000029", "code": None, "name": "Concrete Precast",                                "scope": None, "parent_category_id": "00000000-0007-0000-0000-000000000005", "description": None, "is_active": True, "sort_order": 12},
    {"id": "00000000-0008-0000-0000-000000000030", "code": None, "name": "Concrete components",                             "scope": None, "parent_category_id": "00000000-0007-0000-0000-000000000005", "description": None, "is_active": True, "sort_order": 13},
    {"id": "00000000-0008-0000-0000-000000000031", "code": None, "name": "Concrete in-situ",                                "scope": None, "parent_category_id": "00000000-0007-0000-0000-000000000005", "description": None, "is_active": True, "sort_order": 14},
    {"id": "00000000-0008-0000-0000-000000000032", "code": None, "name": "Curtain wall",                                    "scope": None, "parent_category_id": "00000000-0007-0000-0000-000000000005", "description": None, "is_active": True, "sort_order": 15},
    {"id": "00000000-0008-0000-0000-000000000033", "code": None, "name": "Earthworks",                                      "scope": None, "parent_category_id": "00000000-0007-0000-0000-000000000005", "description": None, "is_active": True, "sort_order": 16},
    {"id": "00000000-0008-0000-0000-000000000034", "code": None, "name": "Escalator",                                       "scope": None, "parent_category_id": "00000000-0007-0000-0000-000000000005", "description": None, "is_active": True, "sort_order": 17},
    {"id": "00000000-0008-0000-0000-000000000035", "code": None, "name": "External shading system",                         "scope": None, "parent_category_id": "00000000-0007-0000-0000-000000000005", "description": None, "is_active": True, "sort_order": 18},
    {"id": "00000000-0008-0000-0000-000000000036", "code": None, "name": "Floors",                                          "scope": None, "parent_category_id": "00000000-0007-0000-0000-000000000005", "description": None, "is_active": True, "sort_order": 19},
    {"id": "00000000-0008-0000-0000-000000000037", "code": None, "name": "Geopolymer pipes",                                "scope": None, "parent_category_id": "00000000-0007-0000-0000-000000000005", "description": None, "is_active": True, "sort_order": 20},
    {"id": "00000000-0008-0000-0000-000000000038", "code": None, "name": "Glass",                                           "scope": None, "parent_category_id": "00000000-0007-0000-0000-000000000005", "description": None, "is_active": True, "sort_order": 21},
    {"id": "00000000-0008-0000-0000-000000000039", "code": None, "name": "Hot rolled steel",                                "scope": None, "parent_category_id": "00000000-0007-0000-0000-000000000005", "description": None, "is_active": True, "sort_order": 22},
    {"id": "00000000-0008-0000-0000-000000000040", "code": None, "name": "Lifts",                                           "scope": None, "parent_category_id": "00000000-0007-0000-0000-000000000005", "description": None, "is_active": True, "sort_order": 23},
    {"id": "00000000-0008-0000-0000-000000000041", "code": None, "name": "Lime",                                            "scope": None, "parent_category_id": "00000000-0007-0000-0000-000000000005", "description": None, "is_active": True, "sort_order": 24},
    {"id": "00000000-0008-0000-0000-000000000042", "code": None, "name": "Masonry",                                         "scope": None, "parent_category_id": "00000000-0007-0000-0000-000000000005", "description": None, "is_active": True, "sort_order": 25},
    {"id": "00000000-0008-0000-0000-000000000043", "code": None, "name": "Other Metal",                                     "scope": None, "parent_category_id": "00000000-0007-0000-0000-000000000005", "description": None, "is_active": True, "sort_order": 26},
    {"id": "00000000-0008-0000-0000-000000000044", "code": None, "name": "PE Pipes",                                        "scope": None, "parent_category_id": "00000000-0007-0000-0000-000000000005", "description": None, "is_active": True, "sort_order": 27},
    {"id": "00000000-0008-0000-0000-000000000045", "code": None, "name": "PVC Pipes",                                       "scope": None, "parent_category_id": "00000000-0007-0000-0000-000000000005", "description": None, "is_active": True, "sort_order": 28},
    {"id": "00000000-0008-0000-0000-000000000046", "code": None, "name": "Paint",                                           "scope": None, "parent_category_id": "00000000-0007-0000-0000-000000000005", "description": None, "is_active": True, "sort_order": 29},
    {"id": "00000000-0008-0000-0000-000000000047", "code": None, "name": "Pavers",                                          "scope": None, "parent_category_id": "00000000-0007-0000-0000-000000000005", "description": None, "is_active": True, "sort_order": 30},
    {"id": "00000000-0008-0000-0000-000000000048", "code": None, "name": "Photovoltaic panels",                             "scope": None, "parent_category_id": "00000000-0007-0000-0000-000000000005", "description": None, "is_active": True, "sort_order": 31},
    {"id": "00000000-0008-0000-0000-000000000049", "code": None, "name": "Plastic",                                         "scope": None, "parent_category_id": "00000000-0007-0000-0000-000000000005", "description": None, "is_active": True, "sort_order": 32},
    {"id": "00000000-0008-0000-0000-000000000050", "code": None, "name": "Precast concrete",                                "scope": None, "parent_category_id": "00000000-0007-0000-0000-000000000005", "description": None, "is_active": True, "sort_order": 33},
    {"id": "00000000-0008-0000-0000-000000000051", "code": None, "name": "Reinforcing steel",                               "scope": None, "parent_category_id": "00000000-0007-0000-0000-000000000005", "description": None, "is_active": True, "sort_order": 34},
    {"id": "00000000-0008-0000-0000-000000000052", "code": None, "name": "Rubbers",                                         "scope": None, "parent_category_id": "00000000-0007-0000-0000-000000000005", "description": None, "is_active": True, "sort_order": 35},
    {"id": "00000000-0008-0000-0000-000000000053", "code": None, "name": "Sealants and adhesives",                          "scope": None, "parent_category_id": "00000000-0007-0000-0000-000000000005", "description": None, "is_active": True, "sort_order": 36},
    {"id": "00000000-0008-0000-0000-000000000054", "code": None, "name": "Stainless steel",                                 "scope": None, "parent_category_id": "00000000-0007-0000-0000-000000000005", "description": None, "is_active": True, "sort_order": 37},
    {"id": "00000000-0008-0000-0000-000000000055", "code": None, "name": "Steel",                                           "scope": None, "parent_category_id": "00000000-0007-0000-0000-000000000005", "description": None, "is_active": True, "sort_order": 38},
    {"id": "00000000-0008-0000-0000-000000000056", "code": None, "name": "Steel pipes",                                     "scope": None, "parent_category_id": "00000000-0007-0000-0000-000000000005", "description": None, "is_active": True, "sort_order": 39},
    {"id": "00000000-0008-0000-0000-000000000057", "code": None, "name": "Steel wire",                                      "scope": None, "parent_category_id": "00000000-0007-0000-0000-000000000005", "description": None, "is_active": True, "sort_order": 40},
    {"id": "00000000-0008-0000-0000-000000000058", "code": None, "name": "Stick-framed wall /ceiling system",               "scope": None, "parent_category_id": "00000000-0007-0000-0000-000000000005", "description": None, "is_active": True, "sort_order": 41},
    {"id": "00000000-0008-0000-0000-000000000059", "code": None, "name": "Thermoplastics",                                  "scope": None, "parent_category_id": "00000000-0007-0000-0000-000000000005", "description": None, "is_active": True, "sort_order": 42},
    {"id": "00000000-0008-0000-0000-000000000060", "code": None, "name": "Timber (engineered)",                             "scope": None, "parent_category_id": "00000000-0007-0000-0000-000000000005", "description": None, "is_active": True, "sort_order": 43},
    {"id": "00000000-0008-0000-0000-000000000061", "code": None, "name": "Timber (sawn)",                                   "scope": None, "parent_category_id": "00000000-0007-0000-0000-000000000005", "description": None, "is_active": True, "sort_order": 44},
    {"id": "00000000-0008-0000-0000-000000000062", "code": None, "name": "Transport",                                       "scope": None, "parent_category_id": "00000000-0007-0000-0000-000000000005", "description": None, "is_active": True, "sort_order": 45},
    {"id": "00000000-0008-0000-0000-000000000063", "code": None, "name": "Wall ceiling Insulated Panel",                    "scope": None, "parent_category_id": "00000000-0007-0000-0000-000000000005", "description": None, "is_active": True, "sort_order": 46},
    {"id": "00000000-0008-0000-0000-000000000064", "code": None, "name": "Wall louvre system",                              "scope": None, "parent_category_id": "00000000-0007-0000-0000-000000000005", "description": None, "is_active": True, "sort_order": 47},
    {"id": "00000000-0008-0000-0000-000000000065", "code": None, "name": "Windows & doors",                                 "scope": None, "parent_category_id": "00000000-0007-0000-0000-000000000005", "description": None, "is_active": True, "sort_order": 48},
    {"id": "00000000-0008-0000-0000-000000000066", "code": None, "name": "Wood",                                            "scope": None, "parent_category_id": "00000000-0007-0000-0000-000000000005", "description": None, "is_active": True, "sort_order": 49},
    # Vegetation
    {"id": "00000000-0008-0000-0000-000000000067", "code": None, "name": "Deforestation - Averaging accounting",            "scope": None, "parent_category_id": "00000000-0007-0000-0000-000000000006", "description": None, "is_active": True, "sort_order": 1},
    {"id": "00000000-0008-0000-0000-000000000068", "code": None, "name": "Deforestation - Natural forests",                 "scope": None, "parent_category_id": "00000000-0007-0000-0000-000000000006", "description": None, "is_active": True, "sort_order": 2},
    {"id": "00000000-0008-0000-0000-000000000069", "code": None, "name": "Harvest - Averaging accounting",                  "scope": None, "parent_category_id": "00000000-0007-0000-0000-000000000006", "description": None, "is_active": True, "sort_order": 3},
    {"id": "00000000-0008-0000-0000-000000000070", "code": None, "name": "Harvest or Deforestation - Stock change accounting","scope": None, "parent_category_id": "00000000-0007-0000-0000-000000000006", "description": None, "is_active": True, "sort_order": 4},
    {"id": "00000000-0008-0000-0000-000000000071", "code": None, "name": "Land Clearing",                                   "scope": None, "parent_category_id": "00000000-0007-0000-0000-000000000006", "description": None, "is_active": True, "sort_order": 5},
    # Waste
    {"id": "00000000-0008-0000-0000-000000000072", "code": None, "name": "Biological treatment of waste",                   "scope": None, "parent_category_id": "00000000-0007-0000-0000-000000000007", "description": None, "is_active": True, "sort_order": 1},
    {"id": "00000000-0008-0000-0000-000000000073", "code": None, "name": "Non municipal waste",                             "scope": None, "parent_category_id": "00000000-0007-0000-0000-000000000007", "description": None, "is_active": True, "sort_order": 2},
    {"id": "00000000-0008-0000-0000-000000000074", "code": None, "name": "Waste to landfill",                               "scope": None, "parent_category_id": "00000000-0007-0000-0000-000000000007", "description": None, "is_active": True, "sort_order": 3},
    {"id": "00000000-0008-0000-0000-000000000075", "code": None, "name": "Waste to landfill with gas recovery",             "scope": None, "parent_category_id": "00000000-0007-0000-0000-000000000007", "description": None, "is_active": True, "sort_order": 4},
    {"id": "00000000-0008-0000-0000-000000000076", "code": None, "name": "Waste to landfill without gas recovery",          "scope": None, "parent_category_id": "00000000-0007-0000-0000-000000000007", "description": None, "is_active": True, "sort_order": 5},
    {"id": "00000000-0008-0000-0000-000000000077", "code": None, "name": "Waste to recycling",                              "scope": None, "parent_category_id": "00000000-0007-0000-0000-000000000007", "description": None, "is_active": True, "sort_order": 6},
    # Water
    {"id": "00000000-0008-0000-0000-000000000078", "code": None, "name": "Wastewater",                                      "scope": None, "parent_category_id": "00000000-0007-0000-0000-000000000008", "description": None, "is_active": True, "sort_order": 1},
    {"id": "00000000-0008-0000-0000-000000000079", "code": None, "name": "Water Use",                                       "scope": None, "parent_category_id": "00000000-0007-0000-0000-000000000008", "description": None, "is_active": True, "sort_order": 2},
]


async def seed() -> None:
    if not settings.database_url:
        raise RuntimeError("DATABASE_URL is not set. Check backend/.env.local")

    engine = create_async_engine(settings.database_url, echo=False)
    async with engine.begin() as conn:
        inserted = 0
        # Insert top-level (no parent) first, then children
        top_level = [c for c in CATEGORIES if c["parent_category_id"] is None]
        children = [c for c in CATEGORIES if c["parent_category_id"] is not None]

        for row in top_level + children:
            result = await conn.execute(
                text(
                    "INSERT INTO emissions_categories "
                    "  (id, code, name, scope, parent_category_id, description, is_active, sort_order, created_at) "
                    "VALUES "
                    "  (:id, :code, :name, :scope, :parent_category_id, :description, :is_active, :sort_order, now()) "
                    "ON CONFLICT (id) DO NOTHING"
                ),
                {**row, "id": str(row["id"])},
            )
            inserted += result.rowcount

        print(f"[seed_emissions_categories] {inserted}/{len(CATEGORIES)} rows inserted.")
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(seed())
