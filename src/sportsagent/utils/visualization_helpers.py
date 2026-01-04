import base64
import json
from io import BytesIO

# from typing import TYPE_CHECKING
import plotly.io as pio

# if TYPE_CHECKING:
#     from PIL import Image


def encode_team_logo(logo_path: str, size: tuple[int, int] = (60, 60)) -> str:
    """
    Convert a team logo file to a base64-encoded data URI for use in Plotly charts.

    Args:
        logo_path: Path to the logo image file
        size: Target size for the logo (width, height). Maintains aspect ratio.

    Returns:
        Base64-encoded data URI string (format: "data:image/png;base64,...")

    Example:
        logo_uri = encode_team_logo(TEAM_LOGO_PATHS['KC'])
        # Use in plotly: fig.add_layout_image(dict(source=logo_uri, ...))
    """
    from PIL import Image

    img = Image.open(logo_path)
    img.thumbnail(size, Image.Resampling.LANCZOS)

    buffered = BytesIO()
    img.save(buffered, format="PNG")
    img_str = base64.b64encode(buffered.getvalue()).decode()

    return f"data:image/png;base64,{img_str}"


def plotly_from_dict(plotly_graph_dict: dict):
    """
    Convert a Plotly graph dictionary to a Plotly graph object.

    Parameters:
    -----------
    plotly_graph_dict: dict
        A Plotly graph dictionary.

    Returns:
    --------
    plotly_graph: plotly.graph_objs.graph_objs.Figure
        A Plotly graph object.
    """

    if plotly_from_dict is None:
        return None

    return pio.from_json(json.dumps(plotly_graph_dict))


# def matplotlib_from_base64(
#     encoded: str,
#     title: str | None = None,
#     figsize: tuple = (8, 6),
# ):
#     """
#     Convert a base64-encoded image to a matplotlib plot and display it.

#     Parameters:
#     -----------
#     encoded : str
#         The base64-encoded image string.
#     title : str, optional
#         A title for the plot. Default is None.
#     figsize : tuple, optional
#         Figure size (width, height) for the plot. Default is (8, 6).

#     Returns:
#     --------
#     fig, ax : tuple
#         The matplotlib figure and axes objects.
#     """
#     # Decode the base64 string to bytes
#     img_data = base64.b64decode(encoded)

#     # Load the bytes data into a BytesIO buffer
#     buf = BytesIO(img_data)

#     # Open the image using Pillow
#     img = Image.open(buf)

#     # Create a matplotlib figure and axis
#     fig, ax = plt.subplots(figsize=figsize)
#     # Display the image
#     ax.imshow(np.array(img))
#     # ax.imshow(np.array(img))

#     ax.axis("off")  # Hide the axis
#     ax.axis("off")  # Hide the axis

#     if title:
#         ax.set_title(title)

#     # Show the plot
#     plt.show()

#     return fig, ax
