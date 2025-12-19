from typing import Any

from pydantic import BaseModel, Field

type DataFrameData = list[dict[str, Any]]

class RetrievedData(BaseModel):
    players: DataFrameData = Field(default_factory=list)
    teams: DataFrameData = Field(default_factory=list)
    extra: dict[str, DataFrameData] = Field(default_factory=dict)

    def items(self):
        """Iterate over non-empty datasets."""
        if self.players:
            yield "players", self.players
        if self.teams:
            yield "teams", self.teams
        for key, value in self.extra.items():
            if value:
                yield key, value

    def keys(self):
        """Return keys of non-empty datasets."""
        keys = []
        if self.players:
            keys.append("players")
        if self.teams:
            keys.append("teams")
        keys.extend([k for k, v in self.extra.items() if v])
        return keys

    def __len__(self):
        """Return number of non-empty datasets."""
        return (
            (1 if self.players else 0)
            + (1 if self.teams else 0)
            + sum(1 for v in self.extra.values() if v)
        )

    def add_player_data(self, data: list[dict[str, Any]]) -> None:
        self.players.extend(data)

    def add_team_data(self, data: list[dict[str, Any]]) -> None:
        self.teams.extend(data)

    def set_dataset(self, key: str, data: list[dict[str, Any]]) -> None:
        self.extra[key] = data

    def add_to_dataset(self, key: str, data: list[dict[str, Any]]) -> None:
        self.extra.setdefault(key, []).extend(data)
