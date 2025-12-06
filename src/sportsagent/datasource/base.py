from abc import ABC, abstractmethod


class DataSourceBase(ABC):
    @property
    @abstractmethod
    def name(self) -> str:
        """Returns the name of the data source."""
        pass
