from typing import Optional

from pydantic import BaseModel, Field


class MatchResult(BaseModel):
    audio_path: str
    # Each score is (name, score, voice_id)
    scores: list[tuple[str, float, str]] = Field(default_factory=list)
    threshold: float = 0.8
    elapsed: float = 0.0

    @property
    def best_match(self) -> Optional[str]:
        if self.scores and self.scores[0][1] >= self.threshold:
            return self.scores[0][0]
        return None

    @property
    def best_match_id(self) -> Optional[str]:
        if self.scores and self.scores[0][1] >= self.threshold:
            return self.scores[0][2]
        return None

    @property
    def best_score(self) -> float:
        if self.scores:
            return self.scores[0][1]
        return 0.0

    model_config = {"from_attributes": True}


class BatchResult(BaseModel):
    results: dict[str, MatchResult] = Field(default_factory=dict)
    elapsed: float = 0.0

    @property
    def mapping(self) -> dict[str, Optional[str]]:
        return {spk: r.best_match for spk, r in self.results.items()}

    @property
    def id_mapping(self) -> dict[str, Optional[str]]:
        return {spk: r.best_match_id for spk, r in self.results.items()}

    model_config = {"from_attributes": True}
