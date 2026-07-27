"""
Database seed management for mock data initialization.

Usage:
  python -m app.seeds.runner

Or from Python:
  from app.seeds import seed_all
  seed_all(db_session)
"""

from app.seeds.ppr2025_clauses import seed_clauses, seed_rule_edges
from app.seeds.contractor_tender_data import seed_contractors, seed_tenders, seed_feedback


def seed_all(db_session):
    """Run all database seeds."""
    print("🌱 Starting database seeding...")
    seed_clauses(db_session)
    seed_rule_edges(db_session)
    seed_contractors(db_session)
    seed_tenders(db_session)
    seed_feedback(db_session)
    print("✅ Database seeding complete!")


__all__ = [
    "seed_all",
    "seed_clauses",
    "seed_rule_edges",
    "seed_contractors",
    "seed_tenders",
    "seed_feedback",
]
