"""
Scoring module for PS-072 Result Engine.
Implements BR-01, BR-02, BR-03, BR-04, BR-05, BR-06, BR-07.
"""

from typing import Dict, List, Tuple, Optional
from .models import (
    Exam, Section, Shift, AnswerKeyQuestion,
    Candidate, CandidateResponse, ProctorFlag, ScoreCard
)


def compute_category_relaxation(category: str, is_pwd: bool) -> float:
    """
    Computes percentage point relaxation for category and PwD:
    - GEN: 0
    - OBC / EWS: 5 percentage points
    - SC / ST: 10 percentage points
    - PwD: additional 5 percentage points
    """
    rel = 0.0
    cat_upper = category.upper()
    if cat_upper in ("OBC", "EWS"):
        rel += 5.0
    elif cat_upper in ("SC", "ST"):
        rel += 10.0
    if is_pwd:
        rel += 5.0
    return rel


def evaluate_response_attempt(
    resp: CandidateResponse,
    sec: Section
) -> bool:
    """
    Determines if a candidate response constitutes a valid attempt.
    - Status must be ANSWERED or MARKED_FOR_REVIEW with an option chosen.
    - Response recorded within section window: recorded_at_sec <= sec.window_end_sec.
    """
    if resp.status not in ("ANSWERED", "MARKED_FOR_REVIEW"):
        return False
    if not resp.option_chosen or resp.option_chosen.strip() == "":
        return False
    if resp.recorded_at_sec is None:
        return False
    if resp.recorded_at_sec > sec.window_end_sec:
        return False
    return True


def score_single_candidate(
    candidate: Candidate,
    paper_key: Dict[int, AnswerKeyQuestion],
    responses: List[CandidateResponse],
    sections: Dict[str, Section],
    exam: Exam,
    proctor_flags: List[ProctorFlag]
) -> ScoreCard:
    """
    Scores a single candidate's responses according to all exam business rules:
    - BR-01: Scoring scheme & negative marking
    - BR-02: Dropped questions & key changes
    - BR-03: Sectional time window & skipped sections
    - BR-04: Sectional cut-offs & relaxations
    - BR-05: Overall cut-off
    - BR-06: Minimum attempts
    - BR-07: Proctoring penalties & disqualification
    """
    # Proctoring evaluation (BR-07)
    total_severity = sum(f.severity for f in proctor_flags)
    has_malpractice = any(f.flag_type == "CONFIRMED_MALPRACTICE" for f in proctor_flags)
    is_disqualified = has_malpractice or (total_severity >= 10)

    # Relaxation calculation (BR-04, BR-05)
    relaxation = compute_category_relaxation(candidate.category, candidate.pwd)

    # Initialize section metrics
    sec_scores: Dict[str, float] = {s_id: 0.0 for s_id in sections}
    sec_attempts: Dict[str, int] = {s_id: 0 for s_id in sections}
    sec_skipped: Dict[str, bool] = {s_id: False for s_id in sections}

    total_attempted = 0
    total_correct = 0
    total_wrong = 0

    # Sort responses by question number
    sorted_responses = sorted(responses, key=lambda r: r.question_no)

    for resp in sorted_responses:
        q_no = resp.question_no
        q_info = paper_key.get(q_no)
        if not q_info:
            continue

        sec = sections.get(q_info.section_id)
        if not sec:
            continue
        s_id = sec.section_id

        is_attempted = evaluate_response_attempt(resp, sec)

        if is_attempted:
            sec_attempts[s_id] += 1
            total_attempted += 1

            if q_info.is_dropped:
                # BR-02: Dropped question attempted -> full marks, no negative, section max unchanged
                sec_scores[s_id] += sec.marks_per_question
                total_correct += 1
            elif q_info.multi_correct:
                # BR-01: Multiple-correct questions
                cand_opt = "".join(sorted(resp.option_chosen.strip()))
                corr_opt = "".join(sorted(q_info.correct_options.strip()))
                if cand_opt == corr_opt:
                    sec_scores[s_id] += sec.marks_per_question
                    total_correct += 1
                else:
                    # 0 marks, NO negative deduction, does not increment wrong count
                    pass
            else:
                # BR-01: Single-correct questions
                if resp.option_chosen.strip() == q_info.correct_options.strip():
                    sec_scores[s_id] += sec.marks_per_question
                    total_correct += 1
                else:
                    total_wrong += 1
                    deduction_fraction = 1.0 / 3.0 if sec.negative_scheme == "THIRD" else 0.25
                    sec_scores[s_id] -= sec.marks_per_question * deduction_fraction

    # BR-03: Flag skipped sections
    for s_id in sections:
        if sec_attempts[s_id] == 0:
            sec_skipped[s_id] = True

    # Raw overall score before penalties
    raw_total = sum(sec_scores.values())

    # BR-07: Proctoring penalties
    penalty_pct = 0
    if is_disqualified:
        penalty_pct = 100
        raw_after_penalty = 0.0
    elif total_severity >= 7:
        penalty_pct = 15
        raw_after_penalty = raw_total * 0.85
    elif total_severity >= 4:
        penalty_pct = 5
        raw_after_penalty = raw_total * 0.95
    else:
        penalty_pct = 0
        raw_after_penalty = raw_total

    # Qualification logic (BR-04, BR-05, BR-06, BR-07)
    status = "QUALIFIED"
    reasons: List[str] = []

    min_attempts_required = (exam.min_attempt_pct / 100.0) * exam.total_questions

    if is_disqualified:
        status = "DISQUALIFIED"
        # Disqualified candidate has score 0
    elif total_attempted < min_attempts_required:
        status = "NOT_QUALIFIED_MIN_ATTEMPT"
    else:
        # Check sectional cut-offs
        sec_fails: List[str] = []
        for s_id, sec in sections.items():
            if sec_skipped[s_id]:
                sec_fails.append("SECTION_SKIPPED")
            else:
                relaxed_cutoff_pct = sec.cutoff_pct - relaxation
                cutoff_marks = (relaxed_cutoff_pct / 100.0) * sec.max_marks
                # Exact unrounded comparison
                if sec_scores[s_id] < cutoff_marks:
                    sec_fails.append(s_id)

        if sec_fails:
            status = "NOT_QUALIFIED_SECTIONAL"
            reasons = sec_fails
        else:
            # Check overall cut-off (relaxed, applied to raw_after_penalty)
            relaxed_overall_pct = exam.overall_cutoff_pct - relaxation
            exam_max_marks = sum(s.max_marks for s in sections.values())
            overall_cutoff_marks = (relaxed_overall_pct / 100.0) * exam_max_marks
            if raw_after_penalty < overall_cutoff_marks:
                status = "NOT_QUALIFIED_OVERALL"

    return ScoreCard(
        roll_no=candidate.roll_no,
        shift_id=candidate.shift_id,
        sec1_raw=sec_scores.get("SEC-1", 0.0),
        sec2_raw=sec_scores.get("SEC-2", 0.0),
        sec3_raw=sec_scores.get("SEC-3", 0.0),
        sec4_raw=sec_scores.get("SEC-4", 0.0),
        attempted=total_attempted,
        correct=total_correct,
        wrong=total_wrong,
        raw_total=raw_total,
        proctor_severity=total_severity,
        penalty_pct=penalty_pct,
        raw_after_penalty=raw_after_penalty,
        normalised=None,
        status=status,
        reason=";".join(reasons),
        is_disqualified=is_disqualified
    )
