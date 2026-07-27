import numpy as np

from app.services.ppr_ml_service import PPRMLService


def test_temporal_split_keeps_tender_groups_disjoint():
    service = PPRMLService()
    groups = np.asarray([f"tender-{index // 2}" for index in range(40)])
    regimes = np.ones(40, dtype=int)
    dates = np.asarray([float(index // 2) for index in range(40)])
    labels = np.asarray([index % 2 for index in range(40)])

    train, calibration, test = service._split_indices(
        regimes, dates, labels, groups=groups
    )

    train_groups = set(groups[train])
    calibration_groups = set(groups[calibration])
    test_groups = set(groups[test])
    assert train_groups.isdisjoint(calibration_groups)
    assert train_groups.isdisjoint(test_groups)
    assert calibration_groups.isdisjoint(test_groups)
    assert max(dates[train]) < min(dates[calibration])
    assert max(dates[calibration]) < min(dates[test])
