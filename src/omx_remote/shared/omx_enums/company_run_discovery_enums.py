from enum import StrEnum


class CompanyRunSmallTaskMarker(StrEnum):
    """Markers that indicate company-run is too heavy for the task."""

    STATUS_ONLY = "status only"
    JUST_STATUS = "just status"
    JUST_LINT = "just lint"
    JUST_FORMAT = "just format"
    TINY_TASK = "tiny task"
    SMALL_DETERMINISTIC = "small deterministic"
    FIX_A_TYPO = "fix a typo"
    TYPO_ONLY = "typo only"


class CompanyRunDeepInterviewMarker(StrEnum):
    """Markers that indicate company-run should hand off to deep-interview."""

    VAGUE = "vague"
    UNCLEAR = "unclear"
    AMBIGUOUS = "ambiguous"
    DO_NOT_ASSUME_APOSTROPHE = "don't assume"
    DO_NOT_ASSUME_PLAIN = "dont assume"
    KOREAN_UNCLEAR = "모호"
    KOREAN_AMBIGUOUS = "애매"


class CompanyRunNoBuildMarker(StrEnum):
    """Markers that explicitly block build/development work."""

    NO_BUILD_HYPHEN = "no-build"
    NO_BUILD_SPACE = "no build"
    DO_NOT_BUILD = "do not build"
    DO_NOT_BUILD_APOSTROPHE = "don't build"
    DO_NOT_BUILD_PLAIN = "dont build"


class CompanyRunResearchFirstMarker(StrEnum):
    """Markers that require research before product/development planning."""

    RESEARCH_FIRST = "research first"
    INVESTIGATE_WHETHER = "investigate whether"
    EVALUATE_WHETHER = "evaluate whether"
    COMPARE_OPTIONS = "compare options"
    FEASIBILITY = "feasibility"


class CompanyRunNonGoalMarker(StrEnum):
    """Markers that show the request contains explicit non-goal constraints."""

    NON_GOAL_HYPHEN = "non-goal"
    NON_GOAL_SPACE = "non goal"
    DO_NOT = "do not"
    DO_NOT_APOSTROPHE = "don't"
    DO_NOT_PLAIN = "dont"
    WITHOUT = "without"


class CompanyRunDecisionBoundaryMarker(StrEnum):
    """Markers that show the request contains decision/autonomy boundaries."""

    BOUNDARY = "boundary"
    BOUNDARIES = "boundaries"
    WITHIN = "within"
    PRESERVE = "preserve"
    AUTONOMY = "autonomy"


class CompanyRunOutcomeMarker(StrEnum):
    """Markers that show company-run artifact/outcome expectations."""

    PRD = "prd"
    TEST = "test"
    IMPLEMENTATION = "implementation"
    TEAM = "team"
    REVIEW = "review"
    RELEASE = "release"
    ARTIFACT = "artifact"
    EVIDENCE = "evidence"


COMPANY_RUN_SMALL_TASK_MARKERS: tuple[CompanyRunSmallTaskMarker, ...] = (
    CompanyRunSmallTaskMarker.STATUS_ONLY,
    CompanyRunSmallTaskMarker.JUST_STATUS,
    CompanyRunSmallTaskMarker.JUST_LINT,
    CompanyRunSmallTaskMarker.JUST_FORMAT,
    CompanyRunSmallTaskMarker.TINY_TASK,
    CompanyRunSmallTaskMarker.SMALL_DETERMINISTIC,
    CompanyRunSmallTaskMarker.FIX_A_TYPO,
    CompanyRunSmallTaskMarker.TYPO_ONLY,
)
COMPANY_RUN_DEEP_INTERVIEW_MARKERS: tuple[CompanyRunDeepInterviewMarker, ...] = (
    CompanyRunDeepInterviewMarker.VAGUE,
    CompanyRunDeepInterviewMarker.UNCLEAR,
    CompanyRunDeepInterviewMarker.AMBIGUOUS,
    CompanyRunDeepInterviewMarker.DO_NOT_ASSUME_APOSTROPHE,
    CompanyRunDeepInterviewMarker.DO_NOT_ASSUME_PLAIN,
    CompanyRunDeepInterviewMarker.KOREAN_UNCLEAR,
    CompanyRunDeepInterviewMarker.KOREAN_AMBIGUOUS,
)
COMPANY_RUN_NO_BUILD_MARKERS: tuple[CompanyRunNoBuildMarker, ...] = (
    CompanyRunNoBuildMarker.NO_BUILD_HYPHEN,
    CompanyRunNoBuildMarker.NO_BUILD_SPACE,
    CompanyRunNoBuildMarker.DO_NOT_BUILD,
    CompanyRunNoBuildMarker.DO_NOT_BUILD_APOSTROPHE,
    CompanyRunNoBuildMarker.DO_NOT_BUILD_PLAIN,
)
COMPANY_RUN_RESEARCH_FIRST_MARKERS: tuple[CompanyRunResearchFirstMarker, ...] = (
    CompanyRunResearchFirstMarker.RESEARCH_FIRST,
    CompanyRunResearchFirstMarker.INVESTIGATE_WHETHER,
    CompanyRunResearchFirstMarker.EVALUATE_WHETHER,
    CompanyRunResearchFirstMarker.COMPARE_OPTIONS,
    CompanyRunResearchFirstMarker.FEASIBILITY,
)
COMPANY_RUN_NON_GOAL_MARKERS: tuple[CompanyRunNonGoalMarker, ...] = (
    CompanyRunNonGoalMarker.NON_GOAL_HYPHEN,
    CompanyRunNonGoalMarker.NON_GOAL_SPACE,
    CompanyRunNonGoalMarker.DO_NOT,
    CompanyRunNonGoalMarker.DO_NOT_APOSTROPHE,
    CompanyRunNonGoalMarker.DO_NOT_PLAIN,
    CompanyRunNonGoalMarker.WITHOUT,
)
COMPANY_RUN_DECISION_BOUNDARY_MARKERS: tuple[CompanyRunDecisionBoundaryMarker, ...] = (
    CompanyRunDecisionBoundaryMarker.BOUNDARY,
    CompanyRunDecisionBoundaryMarker.BOUNDARIES,
    CompanyRunDecisionBoundaryMarker.WITHIN,
    CompanyRunDecisionBoundaryMarker.PRESERVE,
    CompanyRunDecisionBoundaryMarker.AUTONOMY,
)
COMPANY_RUN_OUTCOME_MARKERS: tuple[CompanyRunOutcomeMarker, ...] = (
    CompanyRunOutcomeMarker.PRD,
    CompanyRunOutcomeMarker.TEST,
    CompanyRunOutcomeMarker.IMPLEMENTATION,
    CompanyRunOutcomeMarker.TEAM,
    CompanyRunOutcomeMarker.REVIEW,
    CompanyRunOutcomeMarker.RELEASE,
    CompanyRunOutcomeMarker.ARTIFACT,
    CompanyRunOutcomeMarker.EVIDENCE,
)
