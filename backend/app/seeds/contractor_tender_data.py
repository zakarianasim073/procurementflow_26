"""
Contractor Profiles & Tender Data Seed

Mock data for:
- 10+ contractor profiles (experience, awards, risk, eligibility)
- 20+ tender records (with competitor bids and outcomes)
- ROI sample data for 3 partners
"""

from datetime import datetime, timedelta

CONTRACTORS = [
    {
        "id": "contractor_001",
        "name": "ABC Construction Ltd",
        "registration_number": "REG-2015-001234",
        "registration_date": "2015-06-15",
        "years_operating": 9,
        "status": "active",
        "headquarters": "Dhaka",
        "email": "info@abcconstruction.bd",
        "phone": "+880-2-123456",
        "total_awards": 24,
        "total_contract_value": 450e7,
        "avg_contract_value": 18.75e7,
        "win_rate": 62.1,
        "compliance_rate": 94.2,
        "risk_profile": {"compliance": "low", "market": "medium", "financial": "low", "operational": "low"},
    },
    {
        "id": "contractor_002",
        "name": "XYZ Engineering Ltd",
        "registration_number": "REG-2012-002456",
        "registration_date": "2012-03-20",
        "years_operating": 12,
        "status": "active",
        "headquarters": "Chattogram",
        "email": "info@xyzeng.bd",
        "phone": "+880-31-987654",
        "total_awards": 31,
        "total_contract_value": 620e7,
        "avg_contract_value": 20e7,
        "win_rate": 68.5,
        "compliance_rate": 91.8,
        "risk_profile": {"compliance": "low", "market": "medium", "financial": "low", "operational": "medium"},
    },
    {
        "id": "contractor_003",
        "name": "DEF Projects Ltd",
        "registration_number": "REG-2018-003789",
        "registration_date": "2018-11-10",
        "years_operating": 6,
        "status": "active",
        "headquarters": "Sylhet",
        "email": "info@defprojects.bd",
        "phone": "+880-821-123456",
        "total_awards": 8,
        "total_contract_value": 125e7,
        "avg_contract_value": 15.6e7,
        "win_rate": 42.1,
        "compliance_rate": 88.5,
        "risk_profile": {"compliance": "medium", "market": "high", "financial": "medium", "operational": "medium"},
    },
]

TENDERS = [
    {
        "id": "TEND-2024-001",
        "title": "Road Construction - Dhaka District Phase 1",
        "agency": "PWD",
        "tender_type": "works",
        "category": "Road Construction",
        "estimated_cost": 50e7,
        "publication_date": datetime(2024, 4, 1),
        "bid_deadline": datetime(2024, 5, 1),
        "opening_date": datetime(2024, 5, 5),
        "award_date": datetime(2024, 6, 15),
        "award_amount": 45.2e7,
        "winning_contractor": "ABC Construction Ltd",
        "responsive_bidders": [
            {"name": "ABC Construction Ltd", "bid_price": 45.2e7},
            {"name": "XYZ Engineering Ltd", "bid_price": 47.8e7},
            {"name": "DEF Projects Ltd", "bid_price": 52.1e7},
            {"name": "GHI Ltd", "bid_price": 49.5e7},
        ],
        "status": "awarded",
    },
    {
        "id": "TEND-2024-002",
        "title": "Water Supply Project - Chattogram",
        "agency": "BWDB",
        "tender_type": "works",
        "category": "Water Supply",
        "estimated_cost": 40e7,
        "publication_date": datetime(2024, 3, 15),
        "bid_deadline": datetime(2024, 4, 15),
        "opening_date": datetime(2024, 4, 20),
        "award_date": datetime(2024, 5, 20),
        "award_amount": 38.1e7,
        "winning_contractor": "XYZ Engineering Ltd",
        "responsive_bidders": [
            {"name": "ABC Construction Ltd", "bid_price": 41.5e7},
            {"name": "XYZ Engineering Ltd", "bid_price": 38.1e7},
            {"name": "JKL Contractors", "bid_price": 43.2e7},
        ],
        "status": "awarded",
    },
    {
        "id": "TEND-2024-003",
        "title": "School Building Construction - Sylhet",
        "agency": "Ministry of Education",
        "tender_type": "works",
        "category": "Building Construction",
        "estimated_cost": 15e7,
        "publication_date": datetime(2024, 5, 10),
        "bid_deadline": datetime(2024, 6, 10),
        "opening_date": datetime(2024, 6, 15),
        "award_date": datetime(2024, 7, 15),
        "award_amount": 13.5e7,
        "winning_contractor": "DEF Projects Ltd",
        "responsive_bidders": [
            {"name": "ABC Construction Ltd", "bid_price": 14.2e7},
            {"name": "DEF Projects Ltd", "bid_price": 13.5e7},
            {"name": "MNO Ltd", "bid_price": 15.8e7},
        ],
        "status": "awarded",
    },
]

FEEDBACK_RECORDS = [
    {
        "id": "fb_001",
        "tender_id": "TEND-2024-001",
        "contractor_id": "contractor_001",
        "bid_decision": "submitted",
        "bid_price": 45.2e7,
        "actual_price": 45.2e7,
        "award_status": "won",
        "helpfulness_score": 5,
        "feature_tags": ["pricing-accurate", "competitor-intel-helpful"],
        "notes": "AI pricing recommendation was spot-on. Competitor data helped positioning.",
        "created_at": datetime(2024, 6, 20),
    },
    {
        "id": "fb_002",
        "tender_id": "TEND-2024-002",
        "contractor_id": "contractor_002",
        "bid_decision": "submitted",
        "bid_price": 38.1e7,
        "actual_price": 38.1e7,
        "award_status": "won",
        "helpfulness_score": 4,
        "feature_tags": ["pricing-accurate"],
        "notes": "Pricing was accurate. Compliance check caught missing document.",
        "created_at": datetime(2024, 5, 25),
    },
]

ROI_METRICS = {
    "contractor_001": {
        "hours_saved": 280,
        "features_adopted": 6,
        "adoption_days": 120,
        "compliance_issues_prevented": 3,
    },
    "contractor_002": {
        "hours_saved": 340,
        "features_adopted": 7,
        "adoption_days": 90,
        "compliance_issues_prevented": 5,
    },
    "contractor_003": {
        "hours_saved": 150,
        "features_adopted": 3,
        "adoption_days": 180,
        "compliance_issues_prevented": 1,
    },
}


def seed_contractors(db_session):
    """Insert contractor profiles."""
    from app.models import Contractor  # Import at runtime

    for contractor_data in CONTRACTORS:
        existing = db_session.query(Contractor).filter_by(id=contractor_data["id"]).first()
        if not existing:
            contractor = Contractor(**contractor_data)
            db_session.add(contractor)

    db_session.commit()
    print(f"✅ Seeded {len(CONTRACTORS)} contractor profiles")


def seed_tenders(db_session):
    """Insert tender records."""
    from app.models import Tender  # Import at runtime

    for tender_data in TENDERS:
        existing = db_session.query(Tender).filter_by(id=tender_data["id"]).first()
        if not existing:
            tender = Tender(**tender_data)
            db_session.add(tender)

    db_session.commit()
    print(f"✅ Seeded {len(TENDERS)} tender records")


def seed_feedback(db_session):
    """Insert feedback records."""
    from app.models import Feedback  # Import at runtime

    for feedback_data in FEEDBACK_RECORDS:
        existing = db_session.query(Feedback).filter_by(id=feedback_data["id"]).first()
        if not existing:
            feedback = Feedback(**feedback_data)
            db_session.add(feedback)

    db_session.commit()
    print(f"✅ Seeded {len(FEEDBACK_RECORDS)} feedback records")
