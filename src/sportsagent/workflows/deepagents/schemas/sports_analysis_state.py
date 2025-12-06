from pydantic import BaseModel, Field


class SportsAnalysisState(BaseModel):
    data_input: dict | None = Field(default=None)
    data_raw: dict | None = Field(default=None)
    stats_artifact: dict | None = Field(default=None)


