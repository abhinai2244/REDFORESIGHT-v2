from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime

class ObservedSignal(BaseModel):
    signal_id: str
    source_index: str = "redforesight_range"
    sourcetype: str
    host: str
    user: Optional[str] = None
    process_name: Optional[str] = None
    command_line: Optional[str] = None
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    raw_event: Dict[str, Any] = Field(default_factory=dict)

class MitreTechnique(BaseModel):
    technique_id: str
    name: str
    tactic: str
    description: str
    platforms: List[str] = Field(default_factory=lambda: ["Windows"])

class PredictedMove(BaseModel):
    technique_id: str
    technique_name: str
    tactic: str
    raw_probability: float
    llm_adjusted_probability: float
    reasoning: str

    @property
    def confidence_tier(self) -> str:
        prob = self.llm_adjusted_probability
        if prob >= 0.75:
            return "HIGH"
        elif prob >= 0.45:
            return "MEDIUM"
        else:
            return "LOW"

class IncidentEpisode(BaseModel):
    episode_id: str
    observed_signal: ObservedSignal
    observed_technique_id: Optional[str] = None
    observed_tactic: Optional[str] = None
    predicted_moves: List[PredictedMove] = Field(default_factory=list)
    ground_truth_next_technique: Optional[str] = None  # Purely for evaluation runs against ground truth
    outcome_confirmed: Optional[bool] = None  # True if analyst confirmed, False if rejected
    created_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())

class SplunkContext(BaseModel):
    host: str
    process_events: List[Dict[str, Any]] = Field(default_factory=list)
    auth_events: List[Dict[str, Any]] = Field(default_factory=list)
    net_events: List[Dict[str, Any]] = Field(default_factory=list)
    registry_events: List[Dict[str, Any]] = Field(default_factory=list)

class MCPToolResult(BaseModel):
    tool_name: str
    success: bool
    data: Any
    error: Optional[str] = None

class DefenderBrief(BaseModel):
    brief_id: str
    episode_id: str
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    host: str
    observed_technique: Optional[str] = None
    observed_tactic: Optional[str] = None
    predicted_moves: List[PredictedMove] = Field(default_factory=list)
    splunk_context_summary: str = ""
    recommended_mitigations: List[str] = Field(default_factory=list)
    llm_adversarial_narrative: str = ""
