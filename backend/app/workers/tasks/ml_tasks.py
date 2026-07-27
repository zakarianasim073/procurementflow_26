"""W-008 (ADR-015): Celery Beat task that (re)trains the PPR win-probability
models daily across every agency/zone/regime combination and publishes them to
the versioned model registry. Inference (predict_market_row) loads from the
registry, so the request path never fits a model — training is fully decoupled
from prediction and runs only on the Beat schedule.
"""

import asyncio
import logging

from sqlalchemy import text

from app.celery_app import celery_app
from app.db.database import get_async_session

logger = logging.getLogger(__name__)

# Canonical training axes. Every (agency, zone, regime) slice gets its own
# registered model; (None, None, None) is the global model trained on the
# full dataset.
PPR_AGENCIES = ("BWDB", "PWD", "LGED")
PPR_ZONES = ("A", "B", "C", "D")
PPR_REGIMES = ("PPR2008", "PPR2025")


async def _reconcile_opening_labels() -> "dict":
    """Fill missing PPR 2025 Works labels from an exact lifecycle tender match."""
    async with get_async_session() as session:
        result = await session.execute(
            text(
                """
                UPDATE opening_reports AS o
                SET estimated_amount_bdt = CASE
                        WHEN COALESCE(o.estimated_amount_bdt, 0) <= 0
                        THEN l.estimated_cost_bdt
                        ELSE o.estimated_amount_bdt
                    END,
                    winner_name = CASE
                        WHEN NULLIF(BTRIM(o.winner_name), '') IS NULL
                        THEN NULLIF(BTRIM(l.winner), '')
                        ELSE o.winner_name
                    END,
                    winner_amount = CASE
                        WHEN COALESCE(o.winner_amount, 0) <= 0
                        THEN l.award_amount_bdt
                        ELSE o.winner_amount
                    END,
                    raw_data = (
                        COALESCE(o.raw_data, '{}'::json)::jsonb
                        || jsonb_build_object(
                            'lifecycle_enrichment',
                            jsonb_build_object(
                                'source', 'procurement_lifecycle',
                                'matched_by', 'tender_id',
                                'works_only', true
                            )
                        )
                    )::json,
                    updated_at = NOW()
                FROM procurement_lifecycle AS l
                WHERE l.tender_id = o.tender_id
                  AND o.opening_date >= DATE '2025-09-28'
                  AND EXISTS (
                      SELECT 1
                      FROM procurement_tenders AS pt
                      JOIN app_records AS a
                        ON a.procurement_tender_id = pt.id
                      WHERE pt.package_no = l.package_no
                        AND LOWER(BTRIM(a.category)) = 'works'
                  )
                  AND (
                      (COALESCE(o.estimated_amount_bdt, 0) <= 0 AND l.estimated_cost_bdt > 0)
                      OR (
                          NULLIF(BTRIM(o.winner_name), '') IS NULL
                          AND NULLIF(BTRIM(l.winner), '') IS NOT NULL
                      )
                      OR (COALESCE(o.winner_amount, 0) <= 0 AND l.award_amount_bdt > 0)
                  )
                RETURNING o.id
                """
            )
        )
        updated = len(result.fetchall())
        await session.commit()
        return {
            "status": "success",
            "updated": updated,
            "source": "procurement_lifecycle",
            "matched_by": "tender_id",
            "category": "Works",
        }


@celery_app.task(name="reconcile_ppr_opening_labels")
def reconcile_ppr_opening_labels() -> "dict":
    """Populate missing verified labels before the daily PPR model run."""
    return asyncio.run(_reconcile_opening_labels())


def enumerate_training_combinations() -> "list[tuple]":
    """All scoped training keys plus the global 'all' model.

    Returns a list of (agency, zone, regime) tuples; (None, None, None) is the
    global model trained on the full dataset.
    """
    combos = [(None, None, None)]
    for agency in PPR_AGENCIES:
        for zone in PPR_ZONES:
            for regime in PPR_REGIMES:
                combos.append((agency, zone, regime))
    return combos


async def _train_all(force: bool) -> "dict":
    from app.services.ppr_ml_service import PPRMLService

    results: "dict" = {}
    async with get_async_session() as session:
        svc = PPRMLService(db=session)
        # Global model.
        try:
            summary = await svc.train_models(force=force)
            results["all"] = {
                "trained": bool(summary.get("trained")),
                "promoted": bool(summary.get("promoted", False)),
                "skipped": bool(summary.get("skipped", False)),
                "rows": summary.get("rows"),
            }
        except Exception as exc:
            logger.warning("PPR global model training failed: %s", exc)
            results["all"] = {"trained": False, "error": str(exc)}
        # Scoped models (skip the global entry at index 0).
        for agency, zone, regime in enumerate_training_combinations()[1:]:
            key = svc._regime_key_dict(agency, zone, regime)
            try:
                summary = await svc.train_model(agency=agency, zone=zone, regime=regime, force=force)
                results[key] = {
                    "trained": bool(summary.get("trained")),
                    "promoted": bool(summary.get("promoted", False)),
                    "skipped": bool(summary.get("skipped", False)),
                    "rows": summary.get("rows"),
                }
            except Exception as exc:
                logger.warning("PPR model training failed for key=%s: %s", key, exc)
                results[key] = {"trained": False, "error": str(exc)}
    return results


@celery_app.task(bind=True, max_retries=2, name="train_ppr_models")
def train_ppr_models(self, force: bool = False) -> "dict":
    """Daily Celery Beat entry point — retrain all PPR win-probability models."""
    try:
        results = asyncio.run(_train_all(force=force))
        trained = sum(1 for r in results.values() if r.get("trained"))
        skipped = sum(1 for r in results.values() if r.get("skipped"))
        logger.info(
            "PPR ML training complete: %d trained, %d skipped, %d total",
            trained,
            skipped,
            len(results),
        )
        return {
            "status": "success",
            "total": len(results),
            "trained": trained,
            "skipped": skipped,
            "results": results,
        }
    except Exception as exc:
        logger.error("PPR ML training task failed: %s", exc)
        self.retry(exc=exc, countdown=300)
