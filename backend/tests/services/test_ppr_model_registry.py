"""W-008 (ADR-015): versioned PPR model registry — save, get_latest, rollback,
and pruning to REGISTRY_VERSIONS_TO_KEEP."""
from __future__ import annotations

from pathlib import Path

from app.services.ppr_ml_service import PPRModelRegistry, REGISTRY_VERSIONS_TO_KEEP


def _bundle(v: int) -> dict:
    return {"version": v, "models": {"slt": {"n": v}, "win": {"n": v}}}


def test_save_and_get_latest(tmp_path: Path):
    reg = PPRModelRegistry(base_dir=tmp_path)
    assert reg.get_latest("bwdb_a") is None
    vid = reg.save("bwdb_a", _bundle(1), {"rows": 100})
    assert vid
    bundle, meta = reg.get_latest("bwdb_a")
    assert bundle["version"] == 1
    assert meta["rows"] == 100
    assert meta["feature_version"]


def test_latest_points_at_newest_and_rollback(tmp_path: Path):
    reg = PPRModelRegistry(base_dir=tmp_path)
    reg.save("k", _bundle(1), {})
    reg.save("k", _bundle(2), {})
    bundle, _ = reg.get_latest("k")
    assert bundle["version"] == 2

    # Rollback promotes the previous version.
    assert reg.rollback("k") is True
    bundle, _ = reg.get_latest("k")
    assert bundle["version"] == 1

    # Rolling back again promotes the other stored version.
    assert reg.rollback("k") is True
    bundle, _ = reg.get_latest("k")
    assert bundle["version"] == 2


def test_rollback_with_single_version_is_noop(tmp_path: Path):
    reg = PPRModelRegistry(base_dir=tmp_path)
    reg.save("k", _bundle(1), {})
    assert reg.rollback("k") is False


def test_prune_keeps_only_newest_n(tmp_path: Path):
    reg = PPRModelRegistry(base_dir=tmp_path)
    vids = [reg.save("k", _bundle(i), {}) for i in range(1, REGISTRY_VERSIONS_TO_KEEP + 3)]
    kept = {v for v, _ in reg.list_versions("k")}
    assert len(kept) == REGISTRY_VERSIONS_TO_KEEP
    assert kept == set(vids[-REGISTRY_VERSIONS_TO_KEEP:])


def test_key_isolation(tmp_path: Path):
    reg = PPRModelRegistry(base_dir=tmp_path)
    reg.save("a", _bundle(1), {})
    reg.save("b", _bundle(99), {})
    ba, _ = reg.get_latest("a")
    bb, _ = reg.get_latest("b")
    assert ba["version"] == 1
    assert bb["version"] == 99
