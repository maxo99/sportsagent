from unittest.mock import MagicMock, patch

from sportsagent.datasource import get_datasource


@patch("sportsagent.datasource.NFLReadPyDataSource")
def test_get_datasource_singleton(mock_datasource_class):
    """Test that get_datasource returns the same instance on multiple calls."""
    # Reset the singleton
    import sportsagent.datasource as ds_module

    ds_module._datasource_singleton = None

    # Create mock instance
    mock_instance = MagicMock()
    mock_datasource_class.return_value = mock_instance

    # First call should create instance
    ds1 = get_datasource()
    assert ds1 is mock_instance
    assert mock_datasource_class.call_count == 1

    # Second call should return same instance
    ds2 = get_datasource()
    assert ds2 is ds1
    assert ds2 is mock_instance
    # Should not create a new instance
    assert mock_datasource_class.call_count == 1

    # Third call should still return same instance
    ds3 = get_datasource()
    assert ds3 is ds1
    assert mock_datasource_class.call_count == 1


@patch("sportsagent.datasource.NFLReadPyDataSource")
def test_get_datasource_has_required_attributes(mock_datasource_class):
    """Test that datasource instance has expected attributes."""
    import sportsagent.datasource as ds_module

    ds_module._datasource_singleton = None

    # Configure mock to have expected attributes
    mock_instance = MagicMock()
    mock_instance.TEAM_COLORS = {"KC": ["#E31837", "#FFB612"]}
    mock_instance.TEAM_LOGO_PATHS = {"KC": "data/logos/KC.png"}
    mock_datasource_class.return_value = mock_instance

    ds = get_datasource()

    assert hasattr(ds, "TEAM_COLORS")
    assert hasattr(ds, "TEAM_LOGO_PATHS")
    assert ds.TEAM_COLORS == {"KC": ["#E31837", "#FFB612"]}
    assert ds.TEAM_LOGO_PATHS == {"KC": "data/logos/KC.png"}


@patch("sportsagent.datasource.NFLReadPyDataSource")
def test_get_datasource_returns_nflreadpy_instance(mock_datasource_class):
    """Test that get_datasource returns an NFLReadPyDataSource instance."""
    import sportsagent.datasource as ds_module

    ds_module._datasource_singleton = None

    mock_instance = MagicMock()
    mock_datasource_class.return_value = mock_instance

    ds = get_datasource()

    # Verify the constructor was called
    mock_datasource_class.assert_called_once()
    assert ds is mock_instance
