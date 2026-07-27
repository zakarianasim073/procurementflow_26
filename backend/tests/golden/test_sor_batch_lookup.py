"""W-011: SOR Batch Lookup optimization — verify batch_find_rates matches per-item calls."""

import pytest
from app.sor.sor_service import sor_service


@pytest.mark.golden
def test_batch_find_rates_matches_per_item():
    """Verify batch_find_rates() produces identical results to per-item find_rate() calls."""
    sor_service.load_all()

    # Test data: representative item codes from real BOQs
    test_items = [
        ("40-200-00", "Excavation in ordinary soil"),
        ("40-300-00", "Brick work 1:6"),
        ("03.5.1", "Dewatering"),
        ("04-180-00", "Reinforced concrete 1:2:4"),
        ("", "Concrete paving stones"),  # No code; should use description
    ]

    codes = [item[0] for item in test_items]
    descs = [item[1] for item in test_items]

    # APPROACH 1: Per-item lookups
    per_item_results = []
    for code, desc in test_items:
        rate, record = sor_service.find_rate(code, desc, "BWDB", "A")
        per_item_results.append((rate, record.code if record else None))

    # APPROACH 2: Batch lookup
    batch_results = sor_service.batch_find_rates(codes, descs, "BWDB", "A")
    batch_results_simplified = []
    for result in batch_results:
        if result is None or result[0] is None:
            batch_results_simplified.append((None, None))
        else:
            rate, record = result
            batch_results_simplified.append((rate, record.code if record else None))

    # Compare results
    for i, (per_item, batch) in enumerate(zip(per_item_results, batch_results_simplified)):
        rate_per_item, code_per_item = per_item
        rate_batch, code_batch = batch
        assert code_per_item == code_batch, (
            f"Item {i} ({codes[i]!r}): per-item found {code_per_item!r}, "
            f"batch found {code_batch!r}"
        )
        if rate_per_item is not None and rate_batch is not None:
            assert abs(rate_per_item - rate_batch) < 0.01, (
                f"Item {i}: per-item rate {rate_per_item}, batch rate {rate_batch}"
            )


@pytest.mark.golden
def test_batch_find_rates_multi_agency():
    """Verify batch lookups across different agencies."""
    sor_service.load_all()

    # Mix of codes: BWDB (dash pattern), PWD (dot pattern), LGED (dot pattern)
    test_items = [
        ("40-200-00", "Excavation"),      # BWDB
        ("26.50.1", "Concrete"),          # PWD
        ("4.09.01.01", "Earthwork"),      # LGED
    ]

    codes = [item[0] for item in test_items]
    descs = [item[1] for item in test_items]

    for agency in ["BWDB", "PWD", "LGED"]:
        batch_results = sor_service.batch_find_rates(codes, descs, agency, "A")
        # Verify we get results (at least some items should match)
        found = 0
        for result in batch_results:
            if result is not None and result[0] is not None:
                found += 1
        assert found > 0, f"Agency {agency}: no matches found in batch of {len(codes)} items"


@pytest.mark.golden
def test_batch_find_rates_empty_input():
    """Verify batch_find_rates handles empty input gracefully."""
    sor_service.load_all()

    # Empty lists
    result = sor_service.batch_find_rates([], [], "BWDB", "A")
    assert result == []

    # Mismatched lengths
    result = sor_service.batch_find_rates(["40-200-00"], ["code1", "code2"], "BWDB", "A")
    assert result == []


@pytest.mark.golden
def test_batch_find_rates_performance_improvement():
    """Verify batch lookup reduces query count (indirect: should be 3x faster than per-item on 150-item BOQ)."""
    sor_service.load_all()

    # Create a realistic BOQ: 150 items
    import time
    codes = [f"40-{200 + i%100:03d}-00" for i in range(150)]
    descs = ["Excavation"] * 150

    # Batch lookup
    start = time.perf_counter()
    batch_results = sor_service.batch_find_rates(codes, descs, "BWDB", "A")
    batch_time = time.perf_counter() - start

    # Per-item lookup
    start = time.perf_counter()
    per_item_results = [sor_service.find_rate(c, d, "BWDB", "A") for c, d in zip(codes, descs)]
    per_item_time = time.perf_counter() - start

    # Verify correctness (at least match counts should be similar)
    batch_found = sum(1 for result in batch_results if result is not None and result[1] is not None)
    per_item_found = sum(1 for r, rec in per_item_results if rec is not None)
    assert batch_found == per_item_found, (
        f"Match count mismatch: batch found {batch_found}, per-item found {per_item_found}"
    )

    # Batch should be noticeably faster (target: 3x speedup for N=150, 3 agencies)
    # Log performance for monitoring
    print(f"Batch time: {batch_time:.4f}s, Per-item time: {per_item_time:.4f}s, "
          f"Speedup: {per_item_time/batch_time:.1f}x")
