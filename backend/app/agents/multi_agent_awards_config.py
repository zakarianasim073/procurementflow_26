"""Multi-Agent Configuration for Awards, Experience, and Contracts Data Collection
Focuses on collecting data from all PE offices under all ministries"""

from enum import Enum
from typing import Dict, List

class MultiAgentPhase(Enum):
    """Phases for focused data collection"""
    AWARDS_COLLECTION = "awards_collection"
    EXPERIENCE_COLLECTION = "experience_collection"
    CONTRACTS_COLLECTION = "contracts_collection"
    DATA_RECONCILIATION = "data_reconciliation"
    ANALYSIS = "analysis"

# Focused pipeline definition for awards, experience, and contracts
FOCUSED_PIPELINE_DEFINITION: Dict[MultiAgentPhase, List[str]] = {
    MultiAgentPhase.AWARDS_COLLECTION: [
        "agent-014-award-intelligence",  # Award Intelligence Agent
        "agent-013-competitor-intelligence",  # Competitor Intelligence (includes award data)
    ],
    MultiAgentPhase.EXPERIENCE_COLLECTION: [
        "agent-014-award-intelligence",  # Also handles experience data
        # Note: Experience data is primarily handled by services, not a dedicated agent
    ],
    MultiAgentPhase.CONTRACTS_COLLECTION: [
        "agent-014-award-intelligence",  # Contracts are part of award data
        "agent-013-competitor-intelligence",  # Competitor data includes contract info
    ],
    MultiAgentPhase.DATA_RECONCILIATION: [
        # These are services, not agents, but we can create agent wrappers
        "experience_reconciliation_service",
        "contractor_dna_service",
    ],
    MultiAgentPhase.ANALYSIS: [
        "agent-015-competitor-pricing-predictor",  # Uses award/contract data
        "agent-016-win-probability",  # Uses historical award data
        "agent-017-bid-position-optimizer",  # Uses competitor data
    ],
}

# Target ministries and their PE offices
TARGET_MINISTRIES = {
    "Ministry of Water Resources": [
        "BWDB",  # Bangladesh Water Development Board
        "BIWTA",  # Bangladesh Inland Water Transport Authority
    ],
    "Local Government Division": [
        "LGED",  # Local Government Engineering Department
    ],
    "Ministry of Housing and Public Works": [
        "PWD",  # Public Works Department
        "RAJUK",  # Rajdhani Unnayan Kartripakkha
    ],
    "Road Transport and Highways Division": [
        "RHD",  # Roads and Highways Department
        "BBA",  # Bangladesh Bridge Authority
    ],
    "Ministry of Railways": [
        "BR",  # Bangladesh Railway
    ],
    "Ministry of Power, Energy and Mineral Resources": [
        "BPDB",  # Bangladesh Power Development Board
        "PGCB",  # Power Grid Company of Bangladesh
    ],
}

# Department IDs for server-side filtering (from department_tree.py)
DEPARTMENT_IDS = {
    "BWDB": "7",
    "LGED": "5",
    "PWD": "21",
    "RHD": "10",
    "BBA": "23",
    "BIWTA": "8",
    "RAJUK": "22",
    "BR": "12",
    "BPDB": "15",
    "PGCB": "16",
}

# Configuration for multi-agent parallel execution
MULTI_AGENT_CONFIG = {
    "concurrency": 5,  # Number of agents to run concurrently
    "rate_limiting": {
        "requests_per_minute": 120,  # Stay under eGP rate limits
        "burst_limit": 10,  # Max concurrent requests to eGP
    },
    "data_collection": {
        "years_back": 5,  # Collect 5 years of historical data
        "min_records_per_agency": 1000,  # Minimum records to collect per agency
        "max_records_total": 50000,  # Safety limit
    },
    "database": {
        "batch_size": 1000,  # Records per database insert batch
        "flush_interval": 300,  # Auto-flush every 5 minutes
        "validate_on_insert": True,  # Validate data before inserting
    },
    "logging": {
        "progress_interval": 100,  # Log progress every 100 records
        "error_logging": "detailed",  # Detailed error logging
        "performance_metrics": True,  # Track performance metrics
    },
}

# Agent-specific configurations
AGENT_SPECIFIC_CONFIGS = {
    "agent-014-award-intelligence": {
        "target_agencies": list(DEPARTMENT_IDS.keys()),
        "department_ids": DEPARTMENT_IDS,
        "data_types": ["awards", "contracts", "experience"],
        "priority": "high",
    },
    "agent-013-competitor-intelligence": {
        "focus_areas": ["historical_awards", "current_contracts", "competitor_profiles"],
        "depth": 5,  # Years of historical data
        "priority": "medium",
    },
}

# Database verification queries
DB_VERIFICATION_QUERIES = {
    "awards_count": "SELECT COUNT(*) FROM award_records",
    "contracts_count": "SELECT COUNT(*) FROM contracts",
    "experience_count": "SELECT COUNT(*) FROM econtract_execution",
    "contractor_dna_count": "SELECT COUNT(*) FROM contractor_dna",
    "recent_awards": """
        SELECT agency_code, COUNT(*) as count
        FROM award_records
        WHERE award_date >= CURRENT_DATE - INTERVAL '5 years'
        GROUP BY agency_code
        ORDER BY count DESC
        LIMIT 10
    """,
    "data_quality_check": """
        SELECT 
            SUM(CASE WHEN contract_value IS NULL THEN 1 ELSE 0 END) as missing_contract_values,
            SUM(CASE WHEN contractor_name = '' THEN 1 ELSE 0 END) as missing_contractor_names,
            SUM(CASE WHEN package_no = '' THEN 1 ELSE 0 END) as missing_package_nos,
            COUNT(*) as total_records
        FROM award_records
    """,
}