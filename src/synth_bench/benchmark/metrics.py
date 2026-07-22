"""Evaluation metrics for ingredient parsing and mapping.

Parsing Metrics (Module 5 — Ingredient Parsing):
  - Precision, Recall, F1 for token/span-level ingredient detection
  - Exact Match for full ingredient list accuracy
  - Intersection over Union (IoU) for ingredient set overlap

Mapping Metrics (Module 5 — Ingredient Mapping):
  - Recall@K: whether correct target is in top-K predictions
  - Mean Reciprocal Rank (MRR): average of 1/rank
  - Exact Match Rate: fraction of exact target matches
"""

from __future__ import annotations


def _normalize_ingredient_name(name: str) -> str:
    return " ".join(name.strip().casefold().split())


def _normalize_target_id(target_id: str) -> str:
    return " ".join(str(target_id).strip().casefold().split())


# ═══════════════════════════════════════════════════════════════════════════════
# Parsing Metrics
# ═══════════════════════════════════════════════════════════════════════════════


def compute_parsing_metrics(
    ground_truth_ingredients: set[str],
    predicted_ingredients: set[str],
) -> dict[str, float]:
    """Compute ingredient parsing metrics.

    Compares ground truth ingredients (from the structured label) to
    ingredients predicted by a parser.

    Args:
        ground_truth_ingredients: Set of ground truth ingredient names.
        predicted_ingredients: Set of ingredient names predicted by parser.

    Returns:
        Dict with 'precision', 'recall', 'f1', 'exact_match', 'iou'.
    """
    gt = {_normalize_ingredient_name(name) for name in ground_truth_ingredients}
    pred = {_normalize_ingredient_name(name) for name in predicted_ingredients}
    gt.discard("")
    pred.discard("")

    n_gt = len(gt)
    n_pred = len(pred)
    n_correct = len(gt & pred)

    if n_gt == 0 and n_pred == 0:
        precision = recall = f1 = exact_match = iou = 1.0
        return {
            "precision": precision,
            "recall": recall,
            "f1": f1,
            "exact_match": exact_match,
            "iou": iou,
            "n_ground_truth": n_gt,
            "n_predicted": n_pred,
            "n_correct": n_correct,
        }

    precision = n_correct / n_pred if n_pred > 0 else 0.0
    recall = n_correct / n_gt if n_gt > 0 else 0.0
    f1 = 2.0 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0
    exact_match = 1.0 if gt == pred else 0.0
    union_size = len(gt | pred)
    iou = n_correct / union_size if union_size > 0 else 1.0

    return {
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "f1": round(f1, 4),
        "exact_match": round(exact_match, 4),
        "iou": round(iou, 4),
        "n_ground_truth": n_gt,
        "n_predicted": n_pred,
        "n_correct": n_correct,
    }


def compute_ordered_parsing_metrics(
    ground_truth: list[str],
    predicted: list[str],
) -> dict[str, float]:
    """Compute parsing metrics that account for ingredient order.

    Args:
        ground_truth: Ordered list of ground truth ingredient names.
        predicted: Ordered list of predicted ingredient names.

    Returns:
        Dict with order-sensitive metrics.
    """
    normalized_gt = [
        _normalize_ingredient_name(name)
        for name in ground_truth
        if _normalize_ingredient_name(name)
    ]
    normalized_pred = [
        _normalize_ingredient_name(name) for name in predicted if _normalize_ingredient_name(name)
    ]
    set_metrics = compute_parsing_metrics(set(normalized_gt), set(normalized_pred))

    # Order accuracy: fraction of matching positions
    if not normalized_gt and not normalized_pred:
        order_accuracy = 1.0
        pos_matches = 0
    else:
        n = min(len(normalized_gt), len(normalized_pred))
        pos_matches = sum(1 for i in range(n) if normalized_gt[i] == normalized_pred[i])
        order_accuracy = pos_matches / max(len(normalized_gt), len(normalized_pred))

    return {
        **set_metrics,
        "order_accuracy": round(order_accuracy, 4),
        "order_correct_positions": pos_matches,
    }


# ═══════════════════════════════════════════════════════════════════════════════
# Mapping Metrics
# ═══════════════════════════════════════════════════════════════════════════════


def compute_mapping_metrics(
    ground_truth: dict[str, str],
    predictions: dict[str, list[str]],
    k: int = 5,
) -> dict[str, float]:
    """Compute ingredient mapping metrics.

    Args:
        ground_truth: {ingredient_name: correct_target_id}.
        predictions: {ingredient_name: [ranked_predicted_ids]}.
        k: Top-K for Recall@K.

    Returns:
        Dict with 'recall_at_k', 'mrr', 'exact_match_rate'.
    """
    if not ground_truth:
        return {f"recall_at_{k}": 0.0, "mrr": 0.0, "exact_match_rate": 0.0, "n_ingredients": 0}

    total = len(ground_truth)
    recall_k_count = 0
    reciprocal_ranks: list[float] = []
    exact_match_count = 0

    for ingredient, correct_id in ground_truth.items():
        correct_norm = _normalize_target_id(correct_id)
        pred_list = predictions.get(ingredient, [])
        pred_norm = [_normalize_target_id(pid) for pid in pred_list]

        # Exact match: correct ID is the first prediction
        if pred_norm and pred_norm[0] == correct_norm:
            exact_match_count += 1

        # Recall@K: correct ID is in top-K
        if correct_norm in pred_norm[:k]:
            recall_k_count += 1

        # MRR: 1/rank of first correct hit
        rank = next(
            (i + 1 for i, pid in enumerate(pred_norm) if pid == correct_norm),
            0,
        )
        reciprocal_ranks.append(1.0 / rank if rank > 0 else 0.0)

    return {
        f"recall_at_{k}": round(recall_k_count / total, 4),
        "mrr": round(sum(reciprocal_ranks) / total, 4),
        "exact_match_rate": round(exact_match_count / total, 4),
        "n_ingredients": total,
    }
