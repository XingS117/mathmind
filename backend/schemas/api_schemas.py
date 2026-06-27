from pydantic import BaseModel
from typing import Optional

class NodeCount(BaseModel):
    node: str = ""
    count: int = 0

class QuestionAnalysisResponse(BaseModel):
    success: bool
    source: str = "manual_input"
    text: str = ""
    question_type: str = "计算题"
    knowledge_points: list[str] = []
    difficulty: int = 2
    has_diagram: bool = False
    key_insight: str = ""
    raw_ocr_text: str = ""
    confidence: int = 0
    needs_human_review: bool = True
    error: Optional[str] = None
    suggestion: Optional[str] = None

class QuestionConfirmResponse(BaseModel):
    question_id: str
    status: str
    review_status: str
    text: str = ""

class TutorSessionCreate(BaseModel):
    question_id: str

class TutorSessionResponse(BaseModel):
    session_id: str
    question_text: str
    opening: str
    total_steps: int
    hints_available: int
    has_diagram: bool = False
    diagram_json: Optional[dict] = None

class TutorMessageRequest(BaseModel):
    session_id: str
    message: str = ""
    intent: str = "answer"

class TutorMessageResponse(BaseModel):
    type: str
    reply: str
    step_index: int = 0
    total_steps: int = 0
    hints_remaining: int = 0
    mastery_update: Optional[float] = None
    variant_suggested: Optional[str] = None
    variants: list[str] = []
    diagnostic_summary: Optional[dict] = None

class DashboardData(BaseModel):
    total_questions: int = 0
    total_sessions: int = 0
    avg_mastery: float = 0.0
    weak_points: list[str] = []
    recent_sessions: list = []
    active_session: Optional[TutorSessionResponse] = None
    top_studied: list[NodeCount] = []
