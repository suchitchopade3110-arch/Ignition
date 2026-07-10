from typing import Literal, Generic, TypeVar, Any
from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel

T = TypeVar("T")

class CamelModel(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )

SeverityLevel = Literal[
    "info", "warning", "danger", "critical", "success", "none", "low", "medium", "high"
]

ReviewStatusType = Literal[
    "queued", "running", "paused", "waiting_hitl", "completed", "failed", "cancelled"
]

class Repository(CamelModel):
    id: str
    name: str
    owner: str
    last_review_date: str
    acs_score: float
    status: Literal["healthy", "warning", "critical"]
    language: str

class Review(CamelModel):
    id: str
    repo_id: str
    repo_name: str
    pull_request_number: int
    title: str
    status: ReviewStatusType
    severity: SeverityLevel
    findings_count: int
    created_at: str
    completed_at: str | None = None
    duration: str | None = None
    acs_score: float | None = None

class DashboardStats(CamelModel):
    active_reviews: int
    hitl_pending: int
    avg_acs_score: float
    issues_found: int

class ReviewDiff(CamelModel):
    file: str
    additions: int
    deletions: int
    content: str  # Contains unified diff format

class Finding(CamelModel):
    # Note: Critic output doesn't natively have rule, recommendation, or id.
    # We will generate them and note the gap.
    id: str
    agent_id: str
    severity: SeverityLevel
    file: str
    line: int | None = None
    description: str
    rule: str
    recommendation: str
    suggested_fix: str | None = None

class AgentProgress(CamelModel):
    id: str
    name: str
    status: Literal["pending", "running", "completed", "failed"]
    execution_time_ms: int | None = None
    finding_count: int

class RegressionAlert(CamelModel):
    # Note: Critic only produces a boolean is_regression.
    # rule_regressed, impact, and recommendation are gaps in current graph output.
    is_regression: bool
    rule_regressed: str | None = None
    previous_score: float | None = None
    current_score: float | None = None
    impact: str | None = None
    recommendation: str | None = None

class ReviewDetail(Review):
    author: str
    branch: str
    commit_sha: str
    files_changed: int
    lines_added: int
    lines_deleted: int
    previous_acs_score: float
    regression: RegressionAlert
    agents: list[AgentProgress] = []
    findings: list[Finding] = []
    diffs: list[ReviewDiff] = []
    github_comment_preview: str | None = None

class HitlItem(ReviewDetail):
    waiting_since: str

class RepositorySettings(CamelModel):
    enable_ai_review: bool
    enable_auto_fix: bool
    enable_hitl: bool
    security_scan: bool
    architecture_scan: bool
    logic_scan: bool

class LedgerStats(CamelModel):
    average_acs: float
    total_reviews: int
    critical_findings: int
    active_regressions: int

class LedgerTrend(CamelModel):
    date: str
    acs_score: float
    reviews_count: int
    critical_count: int

SseEventType = Literal[
    "review.started",
    "agent.started",
    "agent.completed",
    "agent.failed",
    "critic.started",
    "critic.completed",
    "acs.updated",
    "regression.detected",
    "waiting.hitl",
    "hitl.approved",
    "hitl.rejected",
    "review.completed",
    "review.failed",
]

class SseEventPayload(CamelModel):
    type: SseEventType
    review_id: str
    agent_id: str | None = None
    execution_time_ms: int | None = None
    finding_count: int | None = None
    acs_score: float | None = None
    status: str | None = None

class User(CamelModel):
    id: str
    name: str

class Paginated(CamelModel, Generic[T]):
    items: list[T]
    page: int
    page_size: int
    total: int
