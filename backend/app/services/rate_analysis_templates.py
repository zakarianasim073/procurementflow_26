"""
Rate Analysis Engine — breaks SOR work items down into
constituent materials, labor, and equipment per standard BD norms.
"""
import uuid, logging
from datetime import datetime
from typing import List, Dict, Optional, Tuple

logger = logging.getLogger(__name__)

# ── Standard rate analysis compositions for common BWDB SOR items ──
# Each entry: SOR code prefix → list of (sub_desc, unit, qty, component_type, material_category)
# Quantities are per unit of the parent work item

RATE_ANALYSIS_TEMPLATES = {
    # ── Earth Work (16-xxx) ──────────────────────────────────────────
    "16": [
        # Generic earthwork (per cum)
        {"sub_desc": "Earth filling (borrow)", "unit": "cum", "qty": 1.2, "component": "material", "mat_cat": "", "remarks": "incl shrinkage"},
        {"sub_desc": "Excavation by machine", "unit": "hour", "qty": 0.1, "component": "equipment", "mat_cat": "", "remarks": ""},
        {"sub_desc": "Compaction", "unit": "hour", "qty": 0.15, "component": "equipment", "mat_cat": "", "remarks": ""},
        {"sub_desc": "Unskilled labor", "unit": "hour", "qty": 2.0, "component": "labor", "mat_cat": "", "remarks": ""},
        {"sub_desc": "Skilled labor", "unit": "hour", "qty": 0.5, "component": "labor", "mat_cat": "", "remarks": ""},
    ],
    "16-350": [
        # Sand filling (per cum)
        {"sub_desc": "Sand (local)", "unit": "cft", "qty": 35.3, "component": "material", "mat_cat": "sand", "remarks": "1 cum = 35.3 cft"},
        {"sub_desc": "Watering & compaction", "unit": "hour", "qty": 0.5, "component": "equipment", "mat_cat": "", "remarks": "vibratory roller"},
        {"sub_desc": "Unskilled labor", "unit": "hour", "qty": 1.5, "component": "labor", "mat_cat": "", "remarks": "spreading & leveling"},
    ],
    "16-540": [
        # Earthwork in embankment (per cum)
        {"sub_desc": "Earth (borrow pit)", "unit": "cum", "qty": 1.2, "component": "material", "mat_cat": "", "remarks": "20% shrinkage factor"},
        {"sub_desc": "Dozer spreading", "unit": "hour", "qty": 0.1, "component": "equipment", "mat_cat": "", "remarks": "D6 dozer"},
        {"sub_desc": "Roller compaction", "unit": "hour", "qty": 0.15, "component": "equipment", "mat_cat": "", "remarks": "8-ton roller"},
        {"sub_desc": "Watering", "unit": "liter", "qty": 50.0, "component": "material", "mat_cat": "", "remarks": "optimum moisture"},
        {"sub_desc": "Skilled labor", "unit": "hour", "qty": 0.3, "component": "labor", "mat_cat": "", "remarks": "supervision"},
        {"sub_desc": "Unskilled labor", "unit": "hour", "qty": 1.0, "component": "labor", "mat_cat": "", "remarks": "dressing & finishing"},
    ],

    # ── Concrete Construction (28-xxx) ───────────────────────────────
    "28-100": [
        # RCC 1:2:4 (20mm agg) per cum
        {"sub_desc": "Cement (Portland)", "unit": "bag", "qty": 8.0, "component": "material", "mat_cat": "cement", "remarks": "50kg/bag, 400kg/cum"},
        {"sub_desc": "Sand (Sylhet)", "unit": "cft", "qty": 14.0, "component": "material", "mat_cat": "sand", "remarks": "fine aggregate"},
        {"sub_desc": "Brick chips (20mm)", "unit": "cft", "qty": 28.0, "component": "material", "mat_cat": "aggregate", "remarks": "coarse aggregate"},
        {"sub_desc": "Water", "unit": "liter", "qty": 180.0, "component": "material", "mat_cat": "", "remarks": "w/c ratio 0.45"},
        {"sub_desc": "Mixer machine", "unit": "hour", "qty": 0.25, "component": "equipment", "mat_cat": "", "remarks": "1 bag mixer"},
        {"sub_desc": "Vibrator", "unit": "hour", "qty": 0.15, "component": "equipment", "mat_cat": "", "remarks": "needle vibrator"},
        {"sub_desc": "Skilled labor (mason)", "unit": "hour", "qty": 2.0, "component": "labor", "mat_cat": "", "remarks": "casting & finishing"},
        {"sub_desc": "Unskilled labor", "unit": "hour", "qty": 6.0, "component": "labor", "mat_cat": "", "remarks": "mixing, carrying, placing"},
    ],
    "28-200": [
        # PCC 1:3:6 (40mm agg) per cum
        {"sub_desc": "Cement (Portland)", "unit": "bag", "qty": 4.5, "component": "material", "mat_cat": "cement", "remarks": "50kg/bag"},
        {"sub_desc": "Sand (local)", "unit": "cft", "qty": 18.0, "component": "material", "mat_cat": "sand", "remarks": "fine aggregate"},
        {"sub_desc": "Brick chips (40mm)", "unit": "cft", "qty": 36.0, "component": "material", "mat_cat": "aggregate", "remarks": "coarse aggregate"},
        {"sub_desc": "Water", "unit": "liter", "qty": 130.0, "component": "material", "mat_cat": "", "remarks": ""},
        {"sub_desc": "Mixer machine", "unit": "hour", "qty": 0.2, "component": "equipment", "mat_cat": "", "remarks": ""},
        {"sub_desc": "Skilled labor", "unit": "hour", "qty": 1.5, "component": "labor", "mat_cat": "", "remarks": ""},
        {"sub_desc": "Unskilled labor", "unit": "hour", "qty": 4.0, "component": "labor", "mat_cat": "", "remarks": ""},
    ],
    "28-240": [
        # RCC 1:1.5:3 (20mm agg) per cum
        {"sub_desc": "Cement (Portland)", "unit": "bag", "qty": 9.5, "component": "material", "mat_cat": "cement", "remarks": "475kg/cum"},
        {"sub_desc": "Sand (Sylhet)", "unit": "cft", "qty": 12.0, "component": "material", "mat_cat": "sand", "remarks": ""},
        {"sub_desc": "Brick chips (20mm)", "unit": "cft", "qty": 24.0, "component": "material", "mat_cat": "aggregate", "remarks": ""},
        {"sub_desc": "Water", "unit": "liter", "qty": 190.0, "component": "material", "mat_cat": "", "remarks": ""},
        {"sub_desc": "Mixer machine", "unit": "hour", "qty": 0.3, "component": "equipment", "mat_cat": "", "remarks": ""},
        {"sub_desc": "Vibrator", "unit": "hour", "qty": 0.2, "component": "equipment", "mat_cat": "", "remarks": ""},
        {"sub_desc": "Skilled labor (mason)", "unit": "hour", "qty": 2.5, "component": "labor", "mat_cat": "", "remarks": ""},
        {"sub_desc": "Unskilled labor", "unit": "hour", "qty": 7.0, "component": "labor", "mat_cat": "", "remarks": ""},
    ],

    # ── Brick Work (20-xxx) ──────────────────────────────────────────
    "20": [
        # Generic brick work (per cum)
        {"sub_desc": "Brick (standard)", "unit": "pcs", "qty": 400.0, "component": "material", "mat_cat": "brick", "remarks": ""},
        {"sub_desc": "Cement (Portland)", "unit": "bag", "qty": 2.5, "component": "material", "mat_cat": "cement", "remarks": ""},
        {"sub_desc": "Sand (local)", "unit": "cft", "qty": 12.0, "component": "material", "mat_cat": "sand", "remarks": ""},
        {"sub_desc": "Skilled labor (mason)", "unit": "hour", "qty": 4.0, "component": "labor", "mat_cat": "", "remarks": ""},
        {"sub_desc": "Unskilled labor", "unit": "hour", "qty": 8.0, "component": "labor", "mat_cat": "", "remarks": ""},
        {"sub_desc": "Scaffolding", "unit": "lump", "qty": 0.05, "component": "equipment", "mat_cat": "", "remarks": ""},
    ],
    "20-200": [
        # Brick work with cement mortar 1:4 (per cum)
        {"sub_desc": "Brick (standard)", "unit": "pcs", "qty": 400.0, "component": "material", "mat_cat": "brick", "remarks": "incl 5% breakage"},
        {"sub_desc": "Cement (Portland)", "unit": "bag", "qty": 2.5, "component": "material", "mat_cat": "cement", "remarks": "mortar 1:4"},
        {"sub_desc": "Sand (local)", "unit": "cft", "qty": 12.0, "component": "material", "mat_cat": "sand", "remarks": ""},
        {"sub_desc": "Water", "unit": "liter", "qty": 80.0, "component": "material", "mat_cat": "", "remarks": ""},
        {"sub_desc": "Skilled labor (mason)", "unit": "hour", "qty": 4.0, "component": "labor", "mat_cat": "", "remarks": ""},
        {"sub_desc": "Unskilled labor", "unit": "hour", "qty": 8.0, "component": "labor", "mat_cat": "", "remarks": ""},
        {"sub_desc": "Scaffolding", "unit": "lump", "qty": 0.05, "component": "equipment", "mat_cat": "", "remarks": "bamboo scaffolding"},
    ],

    # ── Form Work / Shuttering (36-xxx) ──────────────────────────────
    "36-100": [
        # Form work for slab (per sqm)
        {"sub_desc": "Plywood (18mm)", "unit": "sqm", "qty": 1.0, "component": "material", "mat_cat": "wood", "remarks": "incl 10 uses"},
        {"sub_desc": "Timber (50x75mm)", "unit": "running_meter", "qty": 3.0, "component": "material", "mat_cat": "wood", "remarks": "support battens"},
        {"sub_desc": "Nail & fittings", "unit": "kg", "qty": 0.3, "component": "material", "mat_cat": "steel", "remarks": ""},
        {"sub_desc": "Skilled labor (carpenter)", "unit": "hour", "qty": 2.0, "component": "labor", "mat_cat": "", "remarks": ""},
        {"sub_desc": "Unskilled labor", "unit": "hour", "qty": 2.0, "component": "labor", "mat_cat": "", "remarks": ""},
    ],
    "36-300": [
        # Form work for beam/column (per sqm)
        {"sub_desc": "Plywood (18mm)", "unit": "sqm", "qty": 1.0, "component": "material", "mat_cat": "wood", "remarks": ""},
        {"sub_desc": "Timber (75x100mm)", "unit": "running_meter", "qty": 4.0, "component": "material", "mat_cat": "wood", "remarks": "vertical supports"},
        {"sub_desc": "Nail & fittings", "unit": "kg", "qty": 0.4, "component": "material", "mat_cat": "steel", "remarks": ""},
        {"sub_desc": "Skilled labor (carpenter)", "unit": "hour", "qty": 3.0, "component": "labor", "mat_cat": "", "remarks": ""},
        {"sub_desc": "Unskilled labor", "unit": "hour", "qty": 3.0, "component": "labor", "mat_cat": "", "remarks": ""},
    ],

    # ── Protective Work (40-xxx) CC Block / Geobag ───────────────────
    "40": [
        # Generic protective work (per cum/sqm)
        {"sub_desc": "Cement (Portland)", "unit": "bag", "qty": 6.0, "component": "material", "mat_cat": "cement", "remarks": ""},
        {"sub_desc": "Sand (local)", "unit": "cft", "qty": 12.0, "component": "material", "mat_cat": "sand", "remarks": ""},
        {"sub_desc": "Brick chips/aggregate", "unit": "cft", "qty": 24.0, "component": "material", "mat_cat": "aggregate", "remarks": ""},
        {"sub_desc": "Skilled labor", "unit": "hour", "qty": 2.0, "component": "labor", "mat_cat": "", "remarks": ""},
        {"sub_desc": "Unskilled labor", "unit": "hour", "qty": 6.0, "component": "labor", "mat_cat": "", "remarks": ""},
        {"sub_desc": "Mixer & vibrator", "unit": "hour", "qty": 0.25, "component": "equipment", "mat_cat": "", "remarks": ""},
    ],
    "40-200": [
        # CC block (1:2:4) per cum
        {"sub_desc": "Cement (Portland)", "unit": "bag", "qty": 8.0, "component": "material", "mat_cat": "cement", "remarks": ""},
        {"sub_desc": "Sand (Sylhet)", "unit": "cft", "qty": 14.0, "component": "material", "mat_cat": "sand", "remarks": ""},
        {"sub_desc": "Brick chips (20mm)", "unit": "cft", "qty": 28.0, "component": "material", "mat_cat": "aggregate", "remarks": ""},
        {"sub_desc": "Water", "unit": "liter", "qty": 180.0, "component": "material", "mat_cat": "", "remarks": ""},
        {"sub_desc": "Mold & vibration", "unit": "hour", "qty": 0.3, "component": "equipment", "mat_cat": "", "remarks": "block molding machine"},
        {"sub_desc": "Skilled labor", "unit": "hour", "qty": 2.0, "component": "labor", "mat_cat": "", "remarks": ""},
        {"sub_desc": "Unskilled labor", "unit": "hour", "qty": 6.0, "component": "labor", "mat_cat": "", "remarks": ""},
    ],
    "40-250": [
        # Geobag / geotextile dumping (per sqm)
        {"sub_desc": "Geotextile bag (woven)", "unit": "pcs", "qty": 2.5, "component": "material", "mat_cat": "geotextile", "remarks": "40kg capacity"},
        {"sub_desc": "Sand for filling", "unit": "cft", "qty": 1.5, "component": "material", "mat_cat": "sand", "remarks": "per bag"},
        {"sub_desc": "Unskilled labor", "unit": "hour", "qty": 1.0, "component": "labor", "mat_cat": "", "remarks": "filling & placing"},
        {"sub_desc": "Boat/transport", "unit": "hour", "qty": 0.2, "component": "equipment", "mat_cat": "", "remarks": "if river work"},
    ],
    "40-290": [
        # Stone pitching / CC block paving (per sqm)
        {"sub_desc": "CC block (precast)", "unit": "pcs", "qty": 10.0, "component": "material", "mat_cat": "", "remarks": "0.3x0.3m block"},
        {"sub_desc": "Sand bedding (50mm)", "unit": "cft", "qty": 0.6, "component": "material", "mat_cat": "sand", "remarks": ""},
        {"sub_desc": "Skilled labor", "unit": "hour", "qty": 0.5, "component": "labor", "mat_cat": "", "remarks": "paving"},
        {"sub_desc": "Unskilled labor", "unit": "hour", "qty": 1.0, "component": "labor", "mat_cat": "", "remarks": ""},
    ],

    # ── Piling & Caisson (44-xxx) ────────────────────────────────────
    "44": [
        # Generic piling (per running meter)
        {"sub_desc": "Cement (Portland)", "unit": "bag", "qty": 3.0, "component": "material", "mat_cat": "cement", "remarks": ""},
        {"sub_desc": "Sand (Sylhet)", "unit": "cft", "qty": 5.0, "component": "material", "mat_cat": "sand", "remarks": ""},
        {"sub_desc": "Aggregate (20mm)", "unit": "cft", "qty": 10.0, "component": "material", "mat_cat": "aggregate", "remarks": ""},
        {"sub_desc": "MS Rod", "unit": "kg", "qty": 25.0, "component": "material", "mat_cat": "steel", "remarks": ""},
        {"sub_desc": "Pile driving rig", "unit": "hour", "qty": 0.3, "component": "equipment", "mat_cat": "", "remarks": ""},
        {"sub_desc": "Skilled labor", "unit": "hour", "qty": 1.0, "component": "labor", "mat_cat": "", "remarks": ""},
        {"sub_desc": "Unskilled labor", "unit": "hour", "qty": 3.0, "component": "labor", "mat_cat": "", "remarks": ""},
    ],
    "44-100": [
        # RCC pile casting (per running meter)
        {"sub_desc": "Cement (Portland)", "unit": "bag", "qty": 3.5, "component": "material", "mat_cat": "cement", "remarks": "per rm of 400mm dia"},
        {"sub_desc": "Sand (Sylhet)", "unit": "cft", "qty": 6.0, "component": "material", "mat_cat": "sand", "remarks": ""},
        {"sub_desc": "Brick chips (20mm)", "unit": "cft", "qty": 12.0, "component": "material", "mat_cat": "aggregate", "remarks": ""},
        {"sub_desc": "MS Rod (60 grade)", "unit": "kg", "qty": 30.0, "component": "material", "mat_cat": "steel", "remarks": "1% reinforcement"},
        {"sub_desc": "Binding wire", "unit": "kg", "qty": 0.5, "component": "material", "mat_cat": "steel", "remarks": ""},
        {"sub_desc": "Mixer & vibrator", "unit": "hour", "qty": 0.2, "component": "equipment", "mat_cat": "", "remarks": ""},
        {"sub_desc": "Skilled labor", "unit": "hour", "qty": 1.0, "component": "labor", "mat_cat": "", "remarks": ""},
        {"sub_desc": "Unskilled labor", "unit": "hour", "qty": 3.0, "component": "labor", "mat_cat": "", "remarks": ""},
    ],
    "44-130": [
        # Pile driving (per running meter)
        {"sub_desc": "Pile driving rig", "unit": "hour", "qty": 0.5, "component": "equipment", "mat_cat": "", "remarks": "hydraulic hammer"},
        {"sub_desc": "Crane support", "unit": "hour", "qty": 0.5, "component": "equipment", "mat_cat": "", "remarks": "mobile crane"},
        {"sub_desc": "Skilled operator", "unit": "hour", "qty": 0.5, "component": "labor", "mat_cat": "", "remarks": ""},
        {"sub_desc": "Unskilled labor", "unit": "hour", "qty": 2.0, "component": "labor", "mat_cat": "", "remarks": ""},
    ],

    # ── Road Construction (56-xxx) ───────────────────────────────────
    "56-120": [
        # Sand sub-base (per cum)
        {"sub_desc": "Sand (coarse)", "unit": "cft", "qty": 38.0, "component": "material", "mat_cat": "sand", "remarks": "incl compaction loss"},
        {"sub_desc": "Water", "unit": "liter", "qty": 60.0, "component": "material", "mat_cat": "", "remarks": ""},
        {"sub_desc": "Roller compaction", "unit": "hour", "qty": 0.2, "component": "equipment", "mat_cat": "", "remarks": "8-10 ton"},
        {"sub_desc": "Unskilled labor", "unit": "hour", "qty": 1.5, "component": "labor", "mat_cat": "", "remarks": ""},
    ],
    "56-270": [
        # Bituminous carpet (per sqm)
        {"sub_desc": "Bitumen (80/100)", "unit": "kg", "qty": 3.5, "component": "material", "mat_cat": "bitumen", "remarks": "surface dressing"},
        {"sub_desc": "Stone chips (12mm)", "unit": "cft", "qty": 0.4, "component": "material", "mat_cat": "aggregate", "remarks": ""},
        {"sub_desc": "Hot mix plant", "unit": "hour", "qty": 0.02, "component": "equipment", "mat_cat": "", "remarks": ""},
        {"sub_desc": "Paver finisher", "unit": "hour", "qty": 0.02, "component": "equipment", "mat_cat": "", "remarks": ""},
        {"sub_desc": "Roller (6-8 ton)", "unit": "hour", "qty": 0.03, "component": "equipment", "mat_cat": "", "remarks": "initial rolling"},
        {"sub_desc": "Roller (8-10 ton)", "unit": "hour", "qty": 0.03, "component": "equipment", "mat_cat": "", "remarks": "final rolling"},
        {"sub_desc": "Skilled labor", "unit": "hour", "qty": 0.2, "component": "labor", "mat_cat": "", "remarks": "raking & finishing"},
        {"sub_desc": "Unskilled labor", "unit": "hour", "qty": 0.5, "component": "labor", "mat_cat": "", "remarks": ""},
    ],
    "56-430": [
        # WBM road (per cum)
        {"sub_desc": "Stone boulder (coarse)", "unit": "cft", "qty": 25.0, "component": "material", "mat_cat": "aggregate", "remarks": "90mm-75mm grade"},
        {"sub_desc": "Stone chips (medium)", "unit": "cft", "qty": 10.0, "component": "material", "mat_cat": "aggregate", "remarks": "40mm grade"},
        {"sub_desc": "Stone chips (fine)", "unit": "cft", "qty": 5.0, "component": "material", "mat_cat": "aggregate", "remarks": "10mm grade"},
        {"sub_desc": "Water", "unit": "liter", "qty": 80.0, "component": "material", "mat_cat": "", "remarks": ""},
        {"sub_desc": "Roller (8-10 ton)", "unit": "hour", "qty": 0.25, "component": "equipment", "mat_cat": "", "remarks": ""},
        {"sub_desc": "Unskilled labor", "unit": "hour", "qty": 3.0, "component": "labor", "mat_cat": "", "remarks": ""},
    ],

    # ── Building Construction (64-xxx) ───────────────────────────────
    "64-470": [
        # Brick work in cement mortar (per cum)
        {"sub_desc": "Brick (standard)", "unit": "pcs", "qty": 400.0, "component": "material", "mat_cat": "brick", "remarks": ""},
        {"sub_desc": "Cement (Portland)", "unit": "bag", "qty": 2.5, "component": "material", "mat_cat": "cement", "remarks": "mortar 1:5"},
        {"sub_desc": "Sand (local)", "unit": "cft", "qty": 14.0, "component": "material", "mat_cat": "sand", "remarks": ""},
        {"sub_desc": "Water", "unit": "liter", "qty": 80.0, "component": "material", "mat_cat": "", "remarks": ""},
        {"sub_desc": "Skilled labor (mason)", "unit": "hour", "qty": 4.5, "component": "labor", "mat_cat": "", "remarks": ""},
        {"sub_desc": "Unskilled labor", "unit": "hour", "qty": 9.0, "component": "labor", "mat_cat": "", "remarks": ""},
        {"sub_desc": "Scaffolding & tools", "unit": "lump", "qty": 0.05, "component": "equipment", "mat_cat": "", "remarks": ""},
    ],
    "64-580": [
        # Plaster work (per sqm)
        {"sub_desc": "Cement (Portland)", "unit": "bag", "qty": 0.2, "component": "material", "mat_cat": "cement", "remarks": "12mm thick 1:4"},
        {"sub_desc": "Sand (local)", "unit": "cft", "qty": 0.8, "component": "material", "mat_cat": "sand", "remarks": ""},
        {"sub_desc": "Water", "unit": "liter", "qty": 10.0, "component": "material", "mat_cat": "", "remarks": ""},
        {"sub_desc": "Skilled labor (mason)", "unit": "hour", "qty": 0.5, "component": "labor", "mat_cat": "", "remarks": ""},
        {"sub_desc": "Unskilled labor", "unit": "hour", "qty": 0.5, "component": "labor", "mat_cat": "", "remarks": ""},
    ],

    # ── Dewatering (12-xxx) ──────────────────────────────────────────
    "12": [
        # Generic dewatering (per hour)
        {"sub_desc": "Dewatering pump", "unit": "hour", "qty": 1.0, "component": "equipment", "mat_cat": "", "remarks": ""},
        {"sub_desc": "Operator", "unit": "hour", "qty": 1.0, "component": "labor", "mat_cat": "", "remarks": ""},
        {"sub_desc": "Unskilled labor", "unit": "hour", "qty": 1.0, "component": "labor", "mat_cat": "", "remarks": ""},
        {"sub_desc": "Fuel", "unit": "liter", "qty": 3.0, "component": "material", "mat_cat": "", "remarks": ""},
    ],
    "12-180": [
        # Dewatering by pump (per hour)
        {"sub_desc": "Dewatering pump (4\")", "unit": "hour", "qty": 1.0, "component": "equipment", "mat_cat": "", "remarks": "diesel pump"},
        {"sub_desc": "HDPE pipe", "unit": "running_meter", "qty": 0.1, "component": "material", "mat_cat": "pipe", "remarks": "amortized"},
        {"sub_desc": "Operator", "unit": "hour", "qty": 1.0, "component": "labor", "mat_cat": "", "remarks": ""},
        {"sub_desc": "Diesel fuel", "unit": "liter", "qty": 3.0, "component": "material", "mat_cat": "", "remarks": "per hour operation"},
    ],
}


def get_composition(sor_code: str) -> List[Dict]:
    """Look up rate analysis composition for a given SOR code.
    Tries exact match first, then prefix match.
    """
    if not sor_code:
        return []
    
    # Exact match
    if sor_code in RATE_ANALYSIS_TEMPLATES:
        return RATE_ANALYSIS_TEMPLATES[sor_code]
    
    # Prefix match (try progressively shorter prefixes)
    parts = sor_code.split("-")
    for i in range(len(parts) - 1, 0, -1):
        prefix = "-".join(parts[:i])
        if prefix in RATE_ANALYSIS_TEMPLATES:
            return RATE_ANALYSIS_TEMPLATES[prefix]
    
    return []


async def ensure_rate_analysis_table():
    """Create rate_analysis table if not exists."""
    from app.db.database import get_engine
    from sqlalchemy import text
    
    e = get_engine()
    async with e.connect() as conn:
        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS rate_analysis (
                id UUID PRIMARY KEY,
                sor_code VARCHAR(50) NOT NULL,
                sor_category VARCHAR(100),
                agency VARCHAR(20) DEFAULT 'BWDB',
                sub_item_no INT DEFAULT 1,
                sub_description VARCHAR(300) NOT NULL,
                sub_unit VARCHAR(50),
                sub_quantity DECIMAL(12,4) DEFAULT 0,
                component_type VARCHAR(30) DEFAULT 'material',
                material_category VARCHAR(100),
                remarks TEXT,
                parent_unit VARCHAR(50) DEFAULT 'unit',
                created_at TIMESTAMP DEFAULT NOW()
            )
        """))
        await conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_rate_analysis_sor 
            ON rate_analysis(sor_code)
        """))
        await conn.commit()
    logger.info("rate_analysis table ready")


async def populate_rate_analysis():
    """Populate rate_analysis table from templates if empty."""
    from app.db.database import get_session
    from sqlalchemy import text
    
    await ensure_rate_analysis_table()
    
    async with get_session() as session:
        existing = await session.execute(text("SELECT COUNT(*) FROM rate_analysis"))
        if existing.scalar() > 0:
            logger.info(f"rate_analysis already has {existing.scalar()} rows, skipping")
            return
        
        count = 0
        for sor_code, items in RATE_ANALYSIS_TEMPLATES.items():
            for idx, item in enumerate(items, 1):
                try:
                    async with session.begin_nested():
                        await session.execute(text("""
                            INSERT INTO rate_analysis
                                (id, sor_code, sub_item_no, sub_description, sub_unit,
                                 sub_quantity, component_type, material_category, remarks)
                            VALUES (:id, :code, :no, :desc, :unit,
                                    :qty, :comp, :mat, :remarks)
                        """), {
                            "id": str(uuid.uuid4()),
                            "code": sor_code,
                            "no": idx,
                            "desc": item["sub_desc"],
                            "unit": item["unit"],
                            "qty": item["qty"],
                            "comp": item["component"],
                            "mat": item.get("mat_cat", ""),
                            "remarks": item.get("remarks", ""),
                        })
                    count += 1
                except Exception as e:
                    logger.debug(f"Failed to insert rate analysis item: {e}")
        
        if count > 0:
            await session.commit()
            logger.info(f"Populated {count} rate analysis items for {len(RATE_ANALYSIS_TEMPLATES)} SOR code templates")
