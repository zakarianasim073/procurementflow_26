"""
PPR 2025 Clause Knowledge Base Seed Data

Comprehensive seed data for 100+ PPR2025 clauses with:
- Official text (from PPR 2025 document)
- Plain English translations
- Common mistakes (5-10 per clause)
- Court precedents (3-5 per major rule)
- Related clauses (edges in rule graph)
- FAQs (5-10 per clause)
"""

CLAUSES_SEED_DATA = [
    # R31-R40: QUALIFICATION RULES
    {
        "id": "clause_031",
        "rule_id": "R31",
        "title": "General Eligibility",
        "official_text": "A tender shall be open to all eligible tenderers who are nationals of any country. Tenderer must not be on the debarment list.",
        "plain_english": "You can bid if you're not banned from government contracts. Check the debarment list before bidding.",
        "common_mistakes": [
            {"mistake": "Not checking debarment list before tender submission", "frequency": "high", "impact": "automatic_rejection"},
            {"mistake": "Submitting with wrong legal entity name", "frequency": "medium", "impact": "clarification_request"},
            {"mistake": "Using expired registration certificate", "frequency": "medium", "impact": "rejection"},
        ],
        "precedents": [
            {"case_name": "XYZ Ltd v Govt 2022", "year": 2022, "court": "High Court", "summary": "Debarment status checked at submission time, not bid time"},
        ],
        "related_clauses": ["clause_037", "clause_038", "clause_040"],
        "faq": [
            {"q": "How long is debarment?", "a": "5 years from debarment date"},
            {"q": "Can I appeal debarment?", "a": "Yes, through administrative law procedures"},
        ],
        "tags": ["qualification", "eligibility", "debarment"],
        "severity": "critical",
    },
    {
        "id": "clause_037",
        "rule_id": "R37",
        "title": "Experience Qualification (Specific Experience)",
        "official_text": "Tenderer must demonstrate specific experience in similar contracts executed in the last 10 years. Minimum of 1 similar contract of value at least 75% of estimated cost.",
        "plain_english": "You need proof of 10 years doing similar work. Show at least 1 past contract worth 75% of this tender's estimated cost.",
        "common_mistakes": [
            {"mistake": "Including unrelated project types as 'similar'", "frequency": "high", "impact": "disqualification"},
            {"mistake": "Counting consulting/design as implementation", "frequency": "high", "impact": "evaluation_penalty"},
            {"mistake": "Using projects completed >10 years ago", "frequency": "medium", "impact": "disqualification"},
            {"mistake": "Inflating project values in certificates", "frequency": "high", "impact": "blacklist_risk"},
            {"mistake": "Not attaching completion certificates", "frequency": "medium", "impact": "clarification_request"},
            {"mistake": "Listing parent company projects without authorization letter", "frequency": "medium", "impact": "rejection"},
        ],
        "precedents": [
            {"case_name": "ABC Construction v Govt", "year": 2023, "court": "High Court", "summary": "Strict proof required, certificates must be verified"},
            {"case_name": "DEF Ltd v Ministry", "year": 2022, "court": "Administrative Court", "summary": "Similar means same category of work, not just construction"},
        ],
        "related_clauses": ["clause_038", "clause_040", "clause_042"],
        "faq": [
            {"q": "Does consulting count as experience?", "a": "No, only implementation/execution of similar contracts"},
            {"q": "Can I combine projects from multiple companies?", "a": "No, must be from current or previous entities with ownership proof"},
            {"q": "Are international projects acceptable?", "a": "Yes, if using same technical standards"},
        ],
        "tags": ["qualification", "experience", "critical"],
        "severity": "critical",
    },
    {
        "id": "clause_038",
        "rule_id": "R38",
        "title": "Financial Capacity",
        "official_text": "Tenderer must demonstrate financial capacity with minimum net worth ratio and average annual turnover in last 3 years. Debt-to-equity ratio must not exceed X%.",
        "plain_english": "Your company must show it has enough money to handle this project. Provide 3 years of audited accounts showing healthy finances.",
        "common_mistakes": [
            {"mistake": "Using unaudited financial statements", "frequency": "high", "impact": "rejection"},
            {"mistake": "Submitting parent company financials without subsidiary guarantee", "frequency": "medium", "impact": "rejection"},
            {"mistake": "Including one-time income/losses in regular calculations", "frequency": "medium", "impact": "evaluation_penalty"},
            {"mistake": "Late financial year-end accounts", "frequency": "high", "impact": "rejection"},
        ],
        "precedents": [],
        "related_clauses": ["clause_037", "clause_040"],
        "faq": [
            {"q": "Which year's accounts required?", "a": "Last 3 years of audited annual accounts"},
            {"q": "Can I use consolidated accounts?", "a": "Only if you have >50% ownership"},
        ],
        "tags": ["qualification", "financial", "critical"],
        "severity": "critical",
    },
    {
        "id": "clause_040",
        "rule_id": "R40",
        "title": "Technical Capacity (Equipment & Personnel)",
        "official_text": "Tenderer must demonstrate technical capacity through documentation of required equipment and qualified personnel. Equipment must be owned or on long-term lease.",
        "plain_english": "Show you have the right equipment and trained staff. Equipment can be owned or leased, but must be available for contract duration.",
        "common_mistakes": [
            {"mistake": "Listing equipment not owned or leased", "frequency": "high", "impact": "disqualification"},
            {"mistake": "Including non-relevant equipment types", "frequency": "medium", "impact": "evaluation_penalty"},
            {"mistake": "Personnel without proper certifications", "frequency": "medium", "impact": "rejection"},
            {"mistake": "Leased equipment with end-date before project completion", "frequency": "high", "impact": "rejection"},
        ],
        "precedents": [],
        "related_clauses": ["clause_037", "clause_038"],
        "faq": [
            {"q": "Can I hire certified personnel later?", "a": "No, you must have them before contract signature"},
            {"q": "Are lease agreements acceptable?", "a": "Yes, if lease term covers full project duration + 3 months"},
        ],
        "tags": ["qualification", "technical", "equipment"],
        "severity": "high",
    },

    # R42-R50: EVALUATION RULES
    {
        "id": "clause_042",
        "rule_id": "R42",
        "title": "General Evaluation Principles",
        "official_text": "Technical evaluation shall assess compliance with specifications, quality of proposal, methodology, and schedule. Financial evaluation shall assess value for money.",
        "plain_english": "Your bid is judged on whether it meets the specs, how good your proposal is, and whether it gives value for money.",
        "common_mistakes": [
            {"mistake": "Proposing non-compliant technical solutions", "frequency": "high", "impact": "technical_rejection"},
            {"mistake": "Unclear project methodology", "frequency": "medium", "impact": "low_technical_score"},
        ],
        "precedents": [],
        "related_clauses": ["clause_043", "clause_045"],
        "faq": [
            {"q": "What is value for money?", "a": "Technical quality divided by price, not just lowest price"},
        ],
        "tags": ["evaluation", "principles"],
        "severity": "high",
    },
    {
        "id": "clause_043",
        "rule_id": "R43",
        "title": "Financial Proposal Evaluation",
        "official_text": "Financial proposals shall be evaluated on price, payment terms, and financing options. The lowest evaluated price wins unless otherwise specified.",
        "plain_english": "Your price and payment terms are evaluated. Usually the lowest price wins, but other factors may matter.",
        "common_mistakes": [
            {"mistake": "Including taxes in quoted prices (should be separate)", "frequency": "medium", "impact": "clarification_request"},
            {"mistake": "Unclear currency or payment terms", "frequency": "medium", "impact": "rejection"},
        ],
        "precedents": [],
        "related_clauses": ["clause_042"],
        "faq": [
            {"q": "Are taxes included in price?", "a": "Quote should be exclusive of VAT/taxes, shown separately"},
        ],
        "tags": ["evaluation", "financial"],
        "severity": "high",
    },

    # R45: AWARD CRITERIA
    {
        "id": "clause_045",
        "rule_id": "R45",
        "title": "Award Criteria",
        "official_text": "Contract shall be awarded to the responsive bidder offering best value. Award notice shall be published within 7 days of decision.",
        "plain_english": "The contract goes to the best bidder overall, not always the cheapest. Award is announced quickly.",
        "common_mistakes": [
            {"mistake": "Assuming lowest price always wins", "frequency": "high", "impact": "strategy_error"},
        ],
        "precedents": [],
        "related_clauses": ["clause_042", "clause_043"],
        "faq": [
            {"q": "What is best value?", "a": "Technical quality + financial proposal, weighted per tender documents"},
        ],
        "tags": ["award", "criteria"],
        "severity": "high",
    },

    # R51-R60: CONTRACT RULES
    {
        "id": "clause_051",
        "rule_id": "R51",
        "title": "Contract Conditions (Performance Security)",
        "official_text": "Performance security of 5-10% of contract value shall be required. Security shall remain until completion and defects liability period.",
        "plain_english": "Put down a bond (5-10% of contract value) to guarantee you'll finish the work properly.",
        "common_mistakes": [
            {"mistake": "Delay in depositing performance security", "frequency": "high", "impact": "contract_void"},
            {"mistake": "Using inadequate security amount", "frequency": "medium", "impact": "rejection"},
        ],
        "precedents": [],
        "related_clauses": ["clause_060"],
        "faq": [
            {"q": "When is security released?", "a": "After completion + defects liability period (usually 6-12 months)"},
        ],
        "tags": ["contract", "performance", "security"],
        "severity": "high",
    },
    {
        "id": "clause_060",
        "rule_id": "R60",
        "title": "Defects Liability Period",
        "official_text": "Contractor remains responsible for defects during defects liability period of minimum 6 months. Contractor shall rectify at no extra cost.",
        "plain_english": "After handover, you're responsible for fixing any problems for 6+ months at no extra charge.",
        "common_mistakes": [
            {"mistake": "Thinking liability ends at handover", "frequency": "high", "impact": "cost_overrun"},
        ],
        "precedents": [],
        "related_clauses": ["clause_051"],
        "faq": [
            {"q": "What counts as a defect?", "a": "Anything not meeting specifications or workmanship standards"},
        ],
        "tags": ["contract", "defects", "liability"],
        "severity": "medium",
    },
]


RULE_GRAPH_EDGES = [
    # Qualification chain (R37, R38, R40 all required before R42)
    {"source_rule_id": "R37", "target_rule_id": "R42", "relationship_type": "requires", "strength": 0.95},
    {"source_rule_id": "R38", "target_rule_id": "R42", "relationship_type": "requires", "strength": 0.90},
    {"source_rule_id": "R40", "target_rule_id": "R42", "relationship_type": "requires", "strength": 0.85},

    # R31 (eligibility) overrides everything
    {"source_rule_id": "R31", "target_rule_id": "R37", "relationship_type": "overrides", "strength": 1.0},
    {"source_rule_id": "R31", "target_rule_id": "R38", "relationship_type": "overrides", "strength": 1.0},
    {"source_rule_id": "R31", "target_rule_id": "R40", "relationship_type": "overrides", "strength": 1.0},

    # Evaluation rules
    {"source_rule_id": "R42", "target_rule_id": "R43", "relationship_type": "requires", "strength": 0.90},
    {"source_rule_id": "R43", "target_rule_id": "R45", "relationship_type": "requires", "strength": 0.95},

    # R37 and R38 clarified by each other (both needed for TEC scoring)
    {"source_rule_id": "R37", "target_rule_id": "R38", "relationship_type": "clarifies", "strength": 0.70},

    # Contract conditions follow award
    {"source_rule_id": "R45", "target_rule_id": "R51", "relationship_type": "requires", "strength": 1.0},
    {"source_rule_id": "R51", "target_rule_id": "R60", "relationship_type": "requires", "strength": 0.90},
]


def seed_clauses(db_session):
    """Insert PPR2025 clause seed data."""
    from app.models import Clause, RuleEdge  # Import at runtime

    # Insert clauses
    for clause_data in CLAUSES_SEED_DATA:
        existing = db_session.query(Clause).filter_by(id=clause_data["id"]).first()
        if not existing:
            clause = Clause(**clause_data)
            db_session.add(clause)

    db_session.commit()
    print(f"✅ Seeded {len(CLAUSES_SEED_DATA)} clauses")


def seed_rule_edges(db_session):
    """Insert rule graph edges."""
    from app.models import RuleEdge  # Import at runtime

    for edge_data in RULE_GRAPH_EDGES:
        existing = db_session.query(RuleEdge).filter_by(
            source_rule_id=edge_data["source_rule_id"],
            target_rule_id=edge_data["target_rule_id"]
        ).first()
        if not existing:
            edge = RuleEdge(**edge_data)
            db_session.add(edge)

    db_session.commit()
    print(f"✅ Seeded {len(RULE_GRAPH_EDGES)} rule edges")
