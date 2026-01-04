import base64
from unittest.mock import MagicMock, patch

import pytest

from sportsagent.utils.visualization_helpers import encode_team_logo


@patch("PIL.Image.open")
def test_encode_team_logo_success(mock_image_open):
    """Test that encode_team_logo successfully encodes a logo to base64 data URI."""
    # Mock PIL Image
    mock_img = MagicMock()
    mock_image_open.return_value = mock_img

    # Mock the save to BytesIO
    def mock_save(buffer, format):
        buffer.write(b"fake_image_data")

    mock_img.save = mock_save

    # Call the function
    result = encode_team_logo("fake/path/to/logo.png")

    # Verify the result is a data URI
    assert result.startswith("data:image/png;base64,")

    # Verify base64 encoding
    base64_part = result.split(",")[1]
    decoded = base64.b64decode(base64_part)
    assert decoded == b"fake_image_data"

    # Verify Image.open was called with correct path
    mock_image_open.assert_called_once_with("fake/path/to/logo.png")

    # Verify thumbnail was called with default size
    mock_img.thumbnail.assert_called_once()
    call_args = mock_img.thumbnail.call_args[0]
    assert call_args[0] == (60, 60)


@patch("PIL.Image.open")
def test_encode_team_logo_custom_size(mock_image_open):
    """Test that encode_team_logo respects custom size parameter."""
    mock_img = MagicMock()
    mock_image_open.return_value = mock_img

    def mock_save(buffer, format):
        buffer.write(b"data")

    mock_img.save = mock_save

    # Call with custom size
    result = encode_team_logo("path/to/logo.png", size=(100, 100))

    # Verify thumbnail was called with custom size
    mock_img.thumbnail.assert_called_once()
    call_args = mock_img.thumbnail.call_args[0]
    assert call_args[0] == (100, 100)


@patch("PIL.Image.open")
def test_encode_team_logo_file_not_found(mock_image_open):
    """Test that encode_team_logo raises error for missing file."""
    mock_image_open.side_effect = FileNotFoundError("Logo not found")

    with pytest.raises(FileNotFoundError):
        encode_team_logo("nonexistent/logo.png")


@patch("PIL.Image.open")
def test_encode_team_logo_maintains_format(mock_image_open):
    """Test that the logo is saved as PNG format."""
    mock_img = MagicMock()
    mock_image_open.return_value = mock_img

    save_format = None

    def mock_save(buffer, format):
        nonlocal save_format
        save_format = format
        buffer.write(b"data")

    mock_img.save = mock_save

    encode_team_logo("path/to/logo.png")

    # Verify PNG format was used
    assert save_format == "PNG"
