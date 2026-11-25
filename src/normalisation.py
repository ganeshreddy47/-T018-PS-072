"""
Normalisation module for PS-072 Result Engine.
Implements BR-08, BR-09, BR-10.
"""

import math
from typing import Dict, List, Tuple
from .models import Shift, ScoreCard, ShiftStats


def form_normalisation_groups(
    shifts: List[Shift],
    candidate_counts: Dict[str, int],
    min_candidates: int = 100
) -> List[Dict]:
    """
    Forms normalisation groups according to BR-08:
    - Shifts are ordered chronologically by exam_date and shift order.
    - If a shift has fewer than min_candidates (e.g. 100), it is pooled with
      the next shift of the same day.
    """
    sorted_shifts = sorted(shifts, key=lambda s: (s.exam_date, s.shift_id))
    groups = []
    i = 0
    grp_index = 1

    while i < len(sorted_shifts):
        cur_shift = sorted_shifts[i]
        count = candidate_counts.get(cur_shift.shift_id, 0)

        if count < min_candidates and (i + 1) < len(sorted_shifts):
            next_shift = sorted_shifts[i + 1]
            if next_shift.exam_date == cur_shift.exam_date:
                # Pool with next shift of the same day
                groups.append({
                    "group_id": f"GRP-{grp_index}",
                    "shift_ids": [cur_shift.shift_id, next_shift.shift_id]
                })
                grp_index += 1
                i += 2
                continue

        # Single shift group
        groups.append({
            "group_id": f"GRP-{grp_index}",
            "shift_ids": [cur_shift.shift_id]
        })
        grp_index += 1
        i += 1

    return groups


def compute_shift_normalisation(
    scorecards: Dict[str, ScoreCard],
    shifts: List[Shift],
    groups: List[Dict],
    top_fraction_pct: float = 0.10
) -> Tuple[List[ShiftStats], Dict[str, float]]:
    """
    Computes shift normalisation according to BR-09 and BR-10:
    - Excludes disqualified candidates from normalisation statistics.
    - Computes overall mean (M_g) and top 0.1% mean (M_gt).
    - Computes group mean (M_s) and top 0.1% mean (M_st).
    - Normalisation Guard: if denominator (M_st - M_s) <= 0, uses raw score and flags NO_NORMALISATION.
    - Returns list of ShiftStats and updates scorecards with normalised scores.
    """
    # 1. Pool all non-disqualified candidates across all shifts
    all_valid = [sc for sc in scorecards.values() if not sc.is_disqualified]
    all_valid_sorted = sorted(all_valid, key=lambda sc: sc.raw_after_penalty, reverse=True)

    n_all = len(all_valid_sorted)
    if n_all == 0:
        return [], {}

    # Top 0.1% count across all shifts (ceil, at least 1)
    fraction = top_fraction_pct / 100.0  # 0.1% -> 0.001
    top_n_all = max(1, math.ceil(n_all * fraction))

    M_gt = sum(sc.raw_after_penalty for sc in all_valid_sorted[:top_n_all]) / top_n_all
    M_g = sum(sc.raw_after_penalty for sc in all_valid_sorted) / n_all

    shift_stats_list: List[ShiftStats] = []
    shift_to_group = {}
    for grp in groups:
        for sid in grp["shift_ids"]:
            shift_to_group[sid] = grp

    for grp in groups:
        s_ids = grp["shift_ids"]
        # All candidates in group (including disqualified for shift candidate count, per README line 200)
        all_cands_grp = [sc for sc in scorecards.values() if sc.shift_id in s_ids]
        valid_cands_grp = [sc for sc in all_cands_grp if not sc.is_disqualified]
        valid_cands_sorted = sorted(valid_cands_grp, key=lambda sc: sc.raw_after_penalty, reverse=True)

        n_grp = len(valid_cands_sorted)
        if n_grp == 0:
            shift_stats_list.append(ShiftStats(
                group_id=grp["group_id"],
                shift_ids=";".join(s_ids),
                candidates=len(all_cands_grp),
                mean_raw=0.0,
                top_count=0,
                top_mean=0.0,
                normalisation_flag="NO_NORMALISATION"
            ))
            continue

        top_n_grp = max(1, math.ceil(n_grp * fraction))
        M_st = sum(sc.raw_after_penalty for sc in valid_cands_sorted[:top_n_grp]) / top_n_grp
        M_s = sum(sc.raw_after_penalty for sc in valid_cands_sorted) / n_grp

        denom = M_st - M_s
        flag = "NORMALISED" if denom > 0 else "NO_NORMALISATION"

        shift_stats_list.append(ShiftStats(
            group_id=grp["group_id"],
            shift_ids=";".join(s_ids),
            candidates=len(all_cands_grp),
            mean_raw=round(M_s, 2),
            top_count=top_n_grp,
            top_mean=round(M_st, 2),
            normalisation_flag=flag
        ))

        # Apply normalisation formula to candidates in this group
        for sc in all_cands_grp:
            if sc.is_disqualified:
                sc.normalised = None  # Normalisation is NEVER applied to DISQUALIFIED candidates
            else:
                if denom > 0:
                    raw = sc.raw_after_penalty
                    norm_score = ((M_gt - M_g) / denom) * (raw - M_s) + M_g
                    sc.normalised = round(norm_score, 5)
                else:
                    sc.normalised = round(sc.raw_after_penalty, 5)

    return shift_stats_list, {"M_gt": M_gt, "M_g": M_g}
