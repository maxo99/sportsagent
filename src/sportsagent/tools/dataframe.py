import io
from typing import Annotated

import pandas as pd
from langchain.tools import tool
from langgraph.prebuilt import InjectedState

from sportsagent.models.comparisonmetric import ComparisionMetrics, ComparisonMetric


@tool(response_format="content")
def explain_data(
    data_raw: Annotated[dict, InjectedState("data_raw")],
    n_sample: int = 30,
    skip_stats: bool = False,
):
    """
    Tool: explain_data
    Description:
        Provides an extensive, narrative summary of a DataFrame including its shape, column types,
        missing value percentages, unique counts, sample rows, and (if not skipped) descriptive stats/info.

    Parameters:
        data_raw (dict): Raw data.
        n_sample (int, default=30): Number of rows to display.
        skip_stats (bool, default=False): If True, omit descriptive stats/info.

    LLM Guidance:
        Use when a detailed, human-readable explanation is needed—i.e., a full overview is preferred over a concise numerical summary.

    Returns:
        str: Detailed DataFrame summary.
    """
    print("    * Tool: explain_data")
    result = get_dataframe_summary(pd.DataFrame(data_raw), n_sample=n_sample, skip_stats=skip_stats)
    return result


@tool(response_format="content_and_artifact")
def describe_dataset(
    data_raw: Annotated[dict, InjectedState("data_raw")],
) -> tuple[str, dict]:
    """
    Tool: describe_dataset
    Description:
        Compute and return summary statistics for the dataset using pandas' describe() method.
        The tool provides both a textual summary and a structured artifact (a dictionary) for further processing.

    Parameters:
    -----------
    data_raw : dict
        The raw data in dictionary format.

    LLM Selection Guidance:
    ------------------------
    Use this tool when:
      - The request emphasizes numerical descriptive statistics (e.g., count, mean, std, min, quartiles, max).
      - The user needs a concise statistical snapshot rather than a detailed narrative.
      - Both a brief text explanation and a structured data artifact (for downstream tasks) are required.

    Returns:
    -------
    Tuple[str, Dict]:
        - content: A textual summary indicating that summary statistics have been computed.
        - artifact: A dictionary (derived from DataFrame.describe()) containing detailed statistical measures.
    """
    print("    * Tool: describe_dataset")

    df = pd.DataFrame(data_raw)
    description_df = df.describe(include="all")
    content = "Summary statistics computed using pandas describe()."
    artifact = {"describe_df": description_df.to_dict()}
    return content, artifact


@tool(response_format="content_and_artifact")
def compare_performance(
    data_raw: Annotated[dict, InjectedState("data_raw")],
) -> tuple[str, dict]:
    """
    Tool: compare_performance
    Description:
        Calculates comparison metrics between players in the dataset.
        Identifies leaders and trailers for each numeric statistic.

    Parameters:
        data_raw (dict): Raw data injected from state.

    Returns:
        tuple[str, dict]: A summary string and the comparison metrics artifact.
    """
    print("    * Tool: compare_performance")
    df = pd.DataFrame(data_raw)

    if df.empty or len(df) < 2:
        return "Insufficient data for comparison (need at least 2 records).", {}

    metrics = ComparisionMetrics(player_count=len(df), comparisons=[])

    # Get numeric columns for comparison
    numeric_cols = df.select_dtypes(include=["number"]).columns.tolist()
    stat_cols = [col for col in numeric_cols if col not in ["season", "week", "games_played"]]

    # Calculate differences for each stat
    for stat in stat_cols:
        if stat in df.columns and df[stat].notna().any():
            values = df[stat].dropna()
            if len(values) >= 2:
                max_val = values.max()
                min_val = values.min()
                if max_val > 0:  # Avoid division by zero and irrelevant stats
                    pct_diff = ((max_val - min_val) / max_val) * 100

                    # Find players with max and min values
                    # Handle potential duplicates by taking the first one
                    max_players = df.loc[df[stat] == max_val, "player_name"]
                    max_player = (
                        max_players.iloc[0]
                        if isinstance(max_players, pd.Series)
                        and not max_players.empty
                        and "player_name" in df.columns
                        else "Unknown"
                    )

                    min_players = df.loc[df[stat] == min_val, "player_name"]
                    min_player = (
                        min_players.iloc[0]
                        if isinstance(min_players, pd.Series)
                        and not min_players.empty
                        and "player_name" in df.columns
                        else "Unknown"
                    )

                    metrics.comparisons.append(
                        ComparisonMetric(
                            stat=stat,
                            max_value=max_val,
                            min_value=min_val,
                            difference=max_val - min_val,
                            percent_difference=pct_diff,
                            leader=max_player,
                            trailing=min_player,
                        )
                    )

    # Sort comparisons by percent difference to highlight biggest gaps
    metrics.comparisons.sort(key=lambda x: x.percent_difference, reverse=True)

    # Generate summary string
    summary_lines = [f"Comparison across {len(df)} players:"]
    for comp in metrics.comparisons[:5]:  # Top 5 differences
        stat_name = comp.stat.replace("_", " ").title()
        summary_lines.append(
            f"- {stat_name}: {comp.leader} ({comp.max_value:.1f}) vs {comp.trailing} ({comp.min_value:.1f}) "
            f"| Diff: {comp.difference:.1f} ({comp.percent_difference:.1f}%)"
        )

    return "\n".join(summary_lines), metrics.model_dump()


def get_dataframe_summary(
    dataframes: pd.DataFrame | list[pd.DataFrame] | dict[str, pd.DataFrame],
    n_sample: int = 30,
    skip_stats: bool = False,
) -> list[str]:
    """
    Generate a summary for one or more DataFrames. Accepts a single DataFrame, a list of DataFrames,
    or a dictionary mapping names to DataFrames.

    Parameters
    ----------
    dataframes : pandas.DataFrame or list of pandas.DataFrame or dict of (str -> pandas.DataFrame)
        - Single DataFrame: produce a single summary (returned within a one-element list).
        - List of DataFrames: produce a summary for each DataFrame, using index-based names.
        - Dictionary of DataFrames: produce a summary for each DataFrame, using dictionary keys as names.
    n_sample : int, default 30
        Number of rows to display in the "Data (first 30 rows)" section.
    skip_stats : bool, default False
        If True, skip the descriptive statistics and DataFrame info sections.

    Example:
    --------
    ``` python
    import pandas as pd
    from sklearn.datasets import load_iris
    data = load_iris(as_frame=True)
    dataframes = {
        "iris": data.frame,
        "iris_target": data.target,
    }
    summaries = get_dataframe_summary(dataframes)
    print(summaries[0])
    ```

    Returns
    -------
    list of str
        A list of summaries, one for each provided DataFrame. Each summary includes:
        - Shape of the DataFrame (rows, columns)
        - Column data types
        - Missing value percentage
        - Unique value counts
        - First 30 rows
        - Descriptive statistics
        - DataFrame info output
    """

    summaries = []

    # --- Dictionary Case ---
    if isinstance(dataframes, dict):
        for dataset_name, df in dataframes.items():
            summaries.append(_summarize_dataframe(df, dataset_name, n_sample, skip_stats))

    # --- Single DataFrame Case ---
    elif isinstance(dataframes, pd.DataFrame):
        summaries.append(_summarize_dataframe(dataframes, "Single_Dataset", n_sample, skip_stats))

    # --- List of DataFrames Case ---
    elif isinstance(dataframes, list):
        for idx, df in enumerate(dataframes):
            dataset_name = f"Dataset_{idx}"
            summaries.append(_summarize_dataframe(df, dataset_name, n_sample, skip_stats))

    else:
        raise TypeError(
            "Input must be a single DataFrame, a list of DataFrames, or a dictionary of DataFrames."
        )

    return summaries


def _summarize_dataframe(df: pd.DataFrame, dataset_name: str, n_sample=30, skip_stats=False) -> str:
    """Generate a summary string for a single DataFrame."""
    # 1. Convert dictionary-type cells to strings
    #    This prevents unhashable dict errors during df.nunique().
    df = df.apply(lambda col: col.map(lambda x: str(x) if isinstance(x, dict) else x))

    # 2. Capture df.info() output
    buffer = io.StringIO()
    df.info(buf=buffer)
    info_text = buffer.getvalue()

    # 3. Calculate missing value stats
    missing_stats = (df.isna().sum() / len(df) * 100).sort_values(ascending=False)
    missing_summary = "\n".join([f"{col}: {val:.2f}%" for col, val in missing_stats.items()])

    # 4. Get column data types
    column_types = "\n".join([f"{col}: {dtype}" for col, dtype in df.dtypes.items()])

    # 5. Get unique value counts
    unique_counts = df.nunique()  # Will no longer fail on unhashable dict
    unique_counts_summary = "\n".join([f"{col}: {count}" for col, count in unique_counts.items()])

    # 6. Generate the summary text
    if not skip_stats:
        summary_text = f"""
        Dataset Name: {dataset_name}
        ----------------------------
        Shape: {df.shape[0]} rows x {df.shape[1]} columns

        Column Data Types:
        {column_types}

        Missing Value Percentage:
        {missing_summary}

        Unique Value Counts:
        {unique_counts_summary}

        Data (first {n_sample} rows):
        {df.head(n_sample).to_string()}

        Data Description:
        {df.describe().to_string()}

        Data Info:
        {info_text}
        """
    else:
        summary_text = f"""
        Dataset Name: {dataset_name}
        ----------------------------
        Shape: {df.shape[0]} rows x {df.shape[1]} columns

        Column Data Types:
        {column_types}

        Data (first {n_sample} rows):
        {df.head(n_sample).to_string()}
        """

    return summary_text.strip()


# # inspired by https://www.kaggle.com/code/rishabh15virgo/cmi-dss-first-impression-data-understanding-eda
# def summarize_dataframe(df):
#     summary_df = pd.DataFrame(df.dtypes, columns=["dtypes"])
#     summary_df["missing#"] = df.isna().sum().values * 100
#     summary_df["missing%"] = (df.isna().sum().values * 100) / len(df)
#     summary_df["uniques"] = df.nunique().values
#     summary_df["first_value"] = df.iloc[0].values
#     summary_df["last_value"] = df.iloc[len(df) - 1].values
#     summary_df["count"] = df.count().values
#     # sum['skew'] = df.skew().values
#     desc = pd.DataFrame(df.describe().T)
#     summary_df["min"] = desc["min"]
#     summary_df["max"] = desc["max"]
#     summary_df["mean"] = desc["mean"]
#     return summary_df


# def check_missing_values(df):
#     for col in df.columns:
#         PrintColor(
#             f"\n---> column: {col:>10}\t Percent of NaN value: {100 * (df[col].isnull().sum() / df[col].shape[0]):.2f}%"
#         )


# def style_df(df, color="grey", caption=""):
#     """
#     Styles a pandas DataFrame with a specified background color.

#     Parameters:
#     df (pandas.DataFrame): The DataFrame to style.
#     color (str): The background color to apply to the DataFrame cells.

#     Returns:
#     pandas.io.formats.style.Styler: A Styler object with the applied styles.
#     """
#     return df.style.set_caption(caption).set_properties(
#         **{"border": "1.3px solid blue", "color": color}
#     )


# # Color printing
# # inspired by https://www.kaggle.com/code/ravi20076/sleepstate-eda-baseline
# def PrintColor(text: str, color=Fore.BLUE, style=Style.BRIGHT):
#     """Prints color outputs using colorama using a text F-string"""
#     print(style + color + text + Style.RESET_ALL)
