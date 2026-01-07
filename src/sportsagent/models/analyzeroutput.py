from pydantic import BaseModel, Field


class AnalyzerOutput(BaseModel):
    """Structured output from the analyzer agent."""

    analysis: str = Field(
        description="Supporting reasoning, calculations, and observations. This section includes detailed exploration of the data, statistical insights, and intermediate findings."
    )
    judgment: str = Field(
        description="The direct user-facing answer or conclusion. This is the main response that addresses the user's question in a clear, concise manner."
    )
    visualization_request: str | None = Field(
        default=None,
        description="Explicit chart intent for reporting purposes only. This describes what type of visualization would help present the findings. Note: This does not drive the state.needs_visualization flag - that remains controlled by the query parser.",
    )
