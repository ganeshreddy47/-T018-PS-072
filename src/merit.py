"""
Merit list and category cut-offs module for PS-072 Result Engine.
Implements BR-11 and BR-12.
"""

from typing import Dict, List, Tuple
from .models import Candidate, ScoreCard, MeritCandidate, CategoryCutoff


def generate_merit_list_and_cutoffs(
    scorecards: Dict[str, ScoreCard],
    candidates: Dict[str, Candidate],
    vacancies: Dict[str, int],
    version: int = 1
) -> Tuple[List[MeritCandidate], List[CategoryCutoff]]:
    """
    Generates the merit list and category cut-offs according to BR-11 and BR-12:
    - Filters only candidates with status == 'QUALIFIED'.
    - Ranks them strictly using the 5-level tie-breaking hierarchy:
      1. Normalised overall score (DESC)
      2. SEC-2 tie-breaker section raw score (DESC)
      3. Wrong answer count (ASC)
      4. Date of birth (ASC, older first)
      5. Candidate name (ASC, alphabetical)
    - Computes GEN cut-off from all qualified candidates (rank vacancies['GEN'] * 10).
    - Reserved candidates scoring >= GEN cut-off are counted in GEN.
    - Category cut-offs computed from remaining qualified candidates of each reserved category.
    """
    # 1. Filter qualified candidates
    qualified_cards = [sc for sc in scorecards.values() if sc.status == "QUALIFIED"]

    # 2. Sort by 5-level tie-breaking rule
    def tie_breaker_key(sc: ScoreCard):
        cand = candidates[sc.roll_no]
        norm = sc.normalised if sc.normalised is not None else 0.0
        return (
            -norm,
            -sc.sec2_raw,
            sc.wrong,
            cand.date_of_birth,
            cand.candidate_name
        )

    qualified_cards.sort(key=tie_breaker_key)

    # 3. GEN cut-off and assignment
    gen_vac = vacancies.get("GEN", 0)
    gen_list_target = gen_vac * 10
    total_qualified = len(qualified_cards)

    gen_cutoff_score = 0.0
    if total_qualified > 0:
        cutoff_idx = min(gen_list_target, total_qualified) - 1
        gen_cutoff_score = qualified_cards[cutoff_idx].normalised or 0.0

    # 4. Reservation Migration and Counted_in Assignment
    merit_candidates: List[MeritCandidate] = []
    counted_in_map: Dict[str, str] = {}

    # Assign top gen_list_target to GEN
    for i in range(min(gen_list_target, total_qualified)):
        counted_in_map[qualified_cards[i].roll_no] = "GEN"

    # For candidates beyond GEN cut-off, assign their own category
    for i in range(gen_list_target, total_qualified):
        roll = qualified_cards[i].roll_no
        cand = candidates[roll]
        counted_in_map[roll] = cand.category

    # Build MeritCandidate list
    for rank, sc in enumerate(qualified_cards, 1):
        cand = candidates[sc.roll_no]
        merit_candidates.append(MeritCandidate(
            version=version,
            rank=rank,
            roll_no=sc.roll_no,
            category=cand.category,
            normalised=round(sc.normalised or 0.0, 5),
            tie_breaker_score=round(sc.sec2_raw, 2),
            wrong=sc.wrong,
            date_of_birth=cand.date_of_birth,
            candidate_name=cand.candidate_name,
            counted_in=counted_in_map[sc.roll_no]
        ))

    # 5. Compute category cutoffs
    category_cutoffs: List[CategoryCutoff] = []
    category_order = ["GEN", "OBC", "SC", "ST", "EWS"]

    for cat in category_order:
        vac = vacancies.get(cat, 0)
        target_size = vac * 10

        if cat == "GEN":
            actual_size = min(target_size, total_qualified)
            cutoff_score = gen_cutoff_score
            category_cutoffs.append(CategoryCutoff(
                version=version,
                category=cat,
                vacancies=vac,
                list_size=actual_size,
                cutoff_normalised=round(cutoff_score, 5)
            ))
        else:
            # Reserved category: candidates counted against this reserved quota (beyond GEN cutoff)
            reserved_cands = [
                mc for mc in merit_candidates
                if mc.category == cat and mc.counted_in == cat
            ]
            actual_size = len(reserved_cands)
            cutoff_score = 0.0
            if actual_size > 0:
                cutoff_idx = min(target_size, actual_size) - 1
                cutoff_score = reserved_cands[cutoff_idx].normalised

            category_cutoffs.append(CategoryCutoff(
                version=version,
                category=cat,
                vacancies=vac,
                list_size=actual_size,
                cutoff_normalised=round(cutoff_score, 5)
            ))

    return merit_candidates, category_cutoffs
