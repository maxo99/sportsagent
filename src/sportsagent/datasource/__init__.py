from sportsagent.datasource.nflreadpy import NFLReadPyDataSource

_datasource_singleton = None


def get_datasource() -> NFLReadPyDataSource:
    """
    Get the shared datasource singleton instance.

    This ensures that team colors, logos, and other preloaded data
    are consistent across all modules.
    """
    global _datasource_singleton
    if _datasource_singleton is None:
        _datasource_singleton = NFLReadPyDataSource()
    return _datasource_singleton
