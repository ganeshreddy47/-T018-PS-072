"""
PS-072 Online Exam Proctoring Result Engine
Domain models representing the core entities of the online recruitment exam.
"""

from dataclasses import dataclass, field
from typing import Optional, List, Dict, Set


@dataclass
class Exam:
    exam_id: str
    exam_name: str
    total_questions: int
    overall_cutoff_pct: float
    top_fraction_pct: float
    min_attempt_pct: float
    pooling_min_candidates: int


@dataclass
class Section:
    section_id: str
    section_name: str
    question_from: int
    question_to: int
    marks_per_question: int
    negative_scheme: str  # 'THIRD' or 'QUARTER'
    window_start_sec: int
    window_end_sec: int
    cutoff_pct: float
    is_tie_breaker: bool

    @property
    def question_count(self) -> int:
        return self.question_to - self.question_from + 1

    @property
    def max_marks(self) -> float:
        return float(self.question_count * self.marks_per_question)


@dataclass
class Shift:
    shift_id: str
    exam_date: str
    slot: str
    start_time: str
    paper_id: str


@dataclass
class AnswerKeyQuestion:
    paper_id: str
    question_no: int
    section_id: str
    correct_options: str
    multi_correct: bool
    is_dropped: bool = False


@dataclass
class Candidate:
    roll_no: str
    candidate_name: str
    gender: str
    date_of_birth: str
    category: str  # GEN, OBC, SC, ST, EWS
    pwd: bool
    shift_id: str


@dataclass
class CandidateResponse:
    roll_no: str
    question_no: int
    option_chosen: str
    status: str  # ANSWERED, NOT_ATTEMPTED, MARKED_FOR_REVIEW
    time_spent_sec: int
    recorded_at_sec: Optional[int]


@dataclass
class ProctorFlag:
    flag_id: str
    roll_no: str
    flag_type: str  # FACE_NOT_VISIBLE, MULTIPLE_FACES, TAB_SWITCH, AUDIO, CONFIRMED_MALPRACTICE
    severity: int
    flag_ts: str


@dataclass
class Challenge:
    challenge_id: str
    paper_id: str
    question_no: int
    raised_by: str
    claimed_options: str
    decision: str  # REJECTED, KEY_CHANGED, DROPPED
    final_options: str
    decided_on: str


@dataclass
class ScoreCard:
    roll_no: str
    shift_id: str
    sec1_raw: float
    sec2_raw: float
    sec3_raw: float
    sec4_raw: float
    attempted: int
    correct: int
    wrong: int
    raw_total: float
    proctor_severity: int
    penalty_pct: int
    raw_after_penalty: float
    normalised: Optional[float]
    status: str  # QUALIFIED, NOT_QUALIFIED_SECTIONAL, NOT_QUALIFIED_OVERALL, NOT_QUALIFIED_MIN_ATTEMPT, DISQUALIFIED
    reason: str
    is_disqualified: bool = False


@dataclass
class ShiftStats:
    group_id: str
    shift_ids: str
    candidates: int
    mean_raw: float
    top_count: int
    top_mean: float
    normalisation_flag: str  # NORMALISED or NO_NORMALISATION


@dataclass
class MeritCandidate:
    version: int
    rank: int
    roll_no: str
    category: str
    normalised: float
    tie_breaker_score: float
    wrong: int
    date_of_birth: str
    candidate_name: str
    counted_in: str


@dataclass
class CategoryCutoff:
    version: int
    category: str
    vacancies: int
    list_size: int
    cutoff_normalised: float
