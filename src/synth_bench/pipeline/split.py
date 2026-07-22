"""Dataset splitting utilities.

Splits are based on original recipe (FDC ID) to prevent data leakage
between training, validation, and test sets.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from synth_bench.canonical.models import BenchmarkSample


@dataclass
class DatasetSplit:
    """A named subset of the dataset."""

    name: str  # "train", "val", "test"
    samples: list[BenchmarkSample] = field(default_factory=list)
    fdc_ids: set[int] = field(default_factory=set)

    def __post_init__(self) -> None:
        """Auto-populate fdc_ids from samples if not already set."""
        if not self.fdc_ids and self.samples:
            self.fdc_ids = {s.canonical_food.fdc_id for s in self.samples}

    def __len__(self) -> int:
        return len(self.samples)


def split_dataset(
    samples: list[BenchmarkSample],
    train_ratio: float = 0.7,
    val_ratio: float = 0.15,
    test_ratio: float = 0.15,
    seed: int = 42,
) -> tuple[DatasetSplit, DatasetSplit, DatasetSplit]:
    """Split samples into train/val/test by FDC ID to prevent data leakage.

    The split is performed at the original recipe level: all variants of
    the same FNDDS recipe go into the same split. This prevents the
    same recipe (under different transformations) from appearing in
    both train and test.

    Args:
        samples: List of all generated samples.
        train_ratio: Proportion for training set.
        val_ratio: Proportion for validation set.
        test_ratio: Proportion for test set.
        seed: Random seed for reproducibility.

    Returns:
        (train_split, val_split, test_split) tuple.
    """
    if abs((train_ratio + val_ratio + test_ratio) - 1.0) > 1e-6:
        raise ValueError(f"Ratios must sum to 1.0, got {train_ratio}+{val_ratio}+{test_ratio}")

    # Group by FDC ID
    from collections import OrderedDict

    fdc_groups: dict[int, list[BenchmarkSample]] = OrderedDict()
    for s in samples:
        fid = s.canonical_food.fdc_id
        if fid not in fdc_groups:
            fdc_groups[fid] = []
        fdc_groups[fid].append(s)

    unique_fdc_ids = list(fdc_groups.keys())

    # Shuffle FDC IDs deterministically
    import random as rng

    rng.seed(seed)
    rng.shuffle(unique_fdc_ids)

    # Split by FDC ID count. Honor zero ratios and keep behavior sensible for
    # tiny datasets instead of forcing empty-ratio splits to receive samples.
    n_total = len(unique_fdc_ids)
    if n_total == 0:
        return (
            DatasetSplit(name="train"),
            DatasetSplit(name="val"),
            DatasetSplit(name="test"),
        )

    n_train = round(n_total * train_ratio)
    n_val = round(n_total * val_ratio)
    n_test = max(0, n_total - n_train - n_val)
    while n_train + n_val + n_test > n_total:
        if n_train >= n_val and n_train > 0:
            n_train -= 1
        elif n_val > 0:
            n_val -= 1
        else:
            n_test -= 1

    if train_ratio > 0 and n_train == 0:
        n_train = 1
    if val_ratio > 0 and n_val == 0 and n_train + n_val + n_test < n_total:
        n_val = 1
    if test_ratio > 0 and n_test == 0 and n_train + n_val + n_test < n_total:
        n_test = 1
    while n_train + n_val + n_test > n_total:
        if n_train > 1 and n_train >= n_val:
            n_train -= 1
        elif n_val > 1:
            n_val -= 1
        elif n_test > 1:
            n_test -= 1
        else:
            break

    train_ids = set(unique_fdc_ids[:n_train])
    val_ids = set(unique_fdc_ids[n_train : n_train + n_val])
    test_ids = set(unique_fdc_ids[n_train + n_val :])

    # Build splits
    train_samples = []
    val_samples = []
    test_samples = []
    for s in samples:
        fid = s.canonical_food.fdc_id
        if fid in train_ids:
            train_samples.append(s)
        elif fid in val_ids:
            val_samples.append(s)
        else:
            test_samples.append(s)

    train = DatasetSplit(name="train", samples=train_samples, fdc_ids=train_ids)
    val = DatasetSplit(name="val", samples=val_samples, fdc_ids=val_ids)
    test = DatasetSplit(name="test", samples=test_samples, fdc_ids=test_ids)

    return train, val, test
