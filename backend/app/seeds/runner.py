"""
Database seed runner - CLI tool to initialize mock data.

Usage:
  python -m app.seeds.runner
"""

import sys
import logging
from app.db import get_db_session
from app.seeds import seed_all

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def main():
    """Run all seeds."""
    try:
        db = get_db_session()
        seed_all(db)
        db.close()
        print("\n🎉 All seeds completed successfully!")
        return 0
    except Exception as e:
        logger.error(f"Seed failed: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
