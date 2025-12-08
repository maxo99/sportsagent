from pydantic import BaseModel


class ComparisonMetric(BaseModel):
    stat: str
    max_value: float
    min_value: float
    difference: float
    percent_difference: float
    leader: str
    trailing: str


class ComparisionMetrics(BaseModel):
    player_count: int
    comparisons: list[ComparisonMetric]
