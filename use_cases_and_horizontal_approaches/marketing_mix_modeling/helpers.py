### Imports ###
import re
from typing import Dict, List, Optional, Set, Tuple, Union
import warnings

import datarobot as dr
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


### Functions start here ###
def assert_no_missing_values(
    df: pd.DataFrame, columns: Optional[List[str]] = None, verbose: bool = True
) -> Tuple[bool, Dict[str, int]]:
    """
    Verify that no missing values (NaN, None) exist in the specified columns of the dataframe.

    Parameters:
    -----------
    df : pandas.DataFrame
        The dataframe to check
    columns : list or None, default=None
        List of columns to check. If None, checks all columns.
    verbose : bool, default=True
        Whether to print information about missing values

    Returns:
    --------
    bool
        True if no missing values, False otherwise

    dict
        Dictionary with column names as keys and count of missing values as values
    """
    # Determine which columns to check
    if columns is None:
        columns = df.columns
    else:
        # Make sure all requested columns exist
        missing_cols = set(columns) - set(df.columns)
        if missing_cols:
            raise ValueError(f"Columns not found in dataframe: {missing_cols}")

    # Check for missing values in each column
    missing_counts = {}
    for col in columns:
        missing_count = df[col].isna().sum()
        if missing_count > 0:
            missing_counts[col] = missing_count

    # Report results if verbose
    if verbose:
        if missing_counts:
            print(
                f"❌ Found {sum(missing_counts.values())} missing values across {len(missing_counts)} columns:"
            )
            for col, count in missing_counts.items():
                print(f"  - {col}: {count} missing values ({count/len(df):.1%} of data)")
                # Show a few rows with missing values as examples
                if count > 0:
                    example_indices = df[df[col].isna()].index[:3]
                    for idx in example_indices:
                        print(f"    Row {idx}: {df.loc[idx, [col]].to_dict()}")
        else:
            print(f"✅ No missing values found in the {len(columns)} checked columns")

    return len(missing_counts) == 0, missing_counts


def assert_no_missing_dates(
    df: pd.DataFrame,
    date_col: str = "date",
    freq: Optional[str] = None,
    verbose: bool = True,
) -> Tuple[bool, List[pd.Timestamp], Optional[str]]:
    """
    Verify that no dates are missing between the min and max dates in the dataframe.

    Parameters:
    -----------
    df : pandas.DataFrame
        The dataframe to check
    date_col : str, default='date'
        Name of the column containing date values
    freq : str or None, default=None
        Frequency to use for checking. If None, tries to infer from data.
        Common options:
            - 'D': Daily
            - 'B': Business days (weekdays)
            - 'W-MON': Weekly (Mondays)
            - 'MS': Month start
            - 'M': Month end
            - 'QS': Quarter start
            - 'Q': Quarter end
            - 'YS': Year start
    verbose : bool, default=True
        Whether to print information about missing dates

    Returns:
    --------
    bool
        True if no dates are missing, False otherwise

    list
        List of missing dates

    str
        The inferred or specified frequency
    """
    # Make sure the date column exists
    if date_col not in df.columns:
        raise ValueError(f"Date column '{date_col}' not found in dataframe")

    # Convert date column to datetime if not already
    df = df.copy()
    df[date_col] = pd.to_datetime(df[date_col])

    # Sort by date
    df = df.sort_values(by=date_col)

    # Get the date range we should have based on the first and last dates
    start_date = df[date_col].min()
    end_date = df[date_col].max()

    # If frequency not provided, try to infer it
    if freq is None:
        # Get unique sorted dates
        unique_dates = sorted(df[date_col].unique())

        if len(unique_dates) <= 1:
            if verbose:
                print("⚠️ Cannot infer frequency with only one date")
            return True, [], None

        # Calculate all time differences between consecutive dates
        time_diffs = [
            (unique_dates[i + 1] - unique_dates[i]).total_seconds() / 86400
            for i in range(len(unique_dates) - 1)
        ]

        # Find the most common time difference in days
        from collections import Counter

        diff_counts = Counter(time_diffs)
        most_common_diff, _ = diff_counts.most_common(1)[0]

        # Determine frequency based on most common difference
        if most_common_diff == 1.0:
            inferred_freq = "D"  # Daily
        elif most_common_diff == 7.0:
            # For weekly, need to determine which day of the week
            weekday = unique_dates[0].weekday()
            weekday_map = {
                0: "W-MON",
                1: "W-TUE",
                2: "W-WED",
                3: "W-THU",
                4: "W-FRI",
                5: "W-SAT",
                6: "W-SUN",
            }
            inferred_freq = weekday_map[weekday]
        elif 28 <= most_common_diff <= 31:
            # Check if it's month start or end
            if unique_dates[0].day == 1:
                inferred_freq = "MS"  # Month start
            else:
                inferred_freq = "M"  # Month end
        elif 90 <= most_common_diff <= 92:
            # Quarterly
            if unique_dates[0].day == 1:
                inferred_freq = "QS"  # Quarter start
            else:
                inferred_freq = "Q"  # Quarter end
        elif 365 <= most_common_diff <= 366:
            inferred_freq = "YS"  # Yearly
        else:
            inferred_freq = f"{most_common_diff}D"  # Custom day frequency

        freq = inferred_freq

        if verbose:
            print(
                f"Inferred frequency: '{freq}' (most common difference: {most_common_diff:.1f} days)"
            )

    # Generate the expected date range with the determined frequency
    try:
        expected_dates = pd.date_range(start=start_date, end=end_date, freq=freq)
    except Exception as e:
        if verbose:
            print(f"⚠️ Error generating date range with frequency '{freq}': {e}")
            print("Falling back to simple date difference check")

        # Fallback: just check if number of unique dates matches the span
        actual_dates = set(df[date_col].unique())
        date_diff = (end_date - start_date).days
        if freq == "D" and len(actual_dates) < date_diff + 1:
            return (
                False,
                [f"Expected {date_diff + 1} dates, found {len(actual_dates)}"],
                freq,
            )
        return True, [], freq

    # Get the actual dates
    actual_dates = set(df[date_col].unique())

    # Find missing dates
    missing_dates = sorted(set(expected_dates) - actual_dates)

    # Find extra dates that don't fit the pattern
    extra_dates = sorted(actual_dates - set(expected_dates))

    if verbose:
        if missing_dates:
            print(f"❌ Missing {len(missing_dates)} dates with frequency '{freq}':")
            # Print a subset of missing dates if there are many
            display_dates = missing_dates[:10] if len(missing_dates) > 10 else missing_dates
            for date in display_dates:
                print(f"  - {date}")
            if len(missing_dates) > 10:
                print(f"  - ... and {len(missing_dates) - 10} more")
        else:
            print(f"✅ No missing dates found with frequency '{freq}'")

        if extra_dates:
            print(f"⚠️ Found {len(extra_dates)} extra dates not matching frequency '{freq}'")
            if len(extra_dates) <= 5:
                for date in extra_dates:
                    print(f"  - {date}")

    return len(missing_dates) == 0, missing_dates, freq


def run_all_data_checks(
    df: pd.DataFrame,
    date_col: str = "date",
    freq: Optional[str] = None,
    required_columns: Optional[List[str]] = None,
):
    """
    Run all data quality checks at once

    Parameters:
    -----------
    df : pandas.DataFrame
        The dataframe to check
    date_col : str, default='date'
        Name of the column containing date values
    freq : str or None, default=None
        Frequency for date checks. If None, tries to infer.
    required_columns : list or None, default=None
        List of columns that are required to have no missing values.
        If None, checks all columns.

    Returns:
    --------
    dict
        Dictionary with check results
    """
    results = {}

    # Check for missing values
    print("=" * 50)
    print("CHECKING FOR MISSING VALUES")
    print("=" * 50)
    values_result, missing_counts = assert_no_missing_values(df, columns=required_columns)
    results["missing_values"] = {"passed": values_result, "details": missing_counts}

    # Check for missing dates
    print("\n" + "=" * 50)
    print("CHECKING FOR MISSING DATES")
    print("=" * 50)
    dates_result, missing_dates, detected_freq = assert_no_missing_dates(
        df, date_col=date_col, freq=freq
    )
    results["missing_dates"] = {
        "passed": dates_result,
        "details": missing_dates,
        "frequency": detected_freq,
    }

    # Overall result
    all_passed = all(r.get("passed", False) for r in results.values())

    print("\n" + "=" * 50)
    print(f"OVERALL RESULT: {'✅ PASSED' if all_passed else '❌ FAILED'}")
    print("=" * 50)

    return results


def delayed_adstock_transformation(
    x: np.array, L: int = 7, P: float = 1, D: float = 0.8, min_value: int = 1
) -> np.array:
    """
    Applies the delayed adstock transformation to a media variable.
    The adstock effect models the carryover of a media variable over time, where
    the current time period's effect is a weighted average of the current and prior time period's values.
    This transformation assumes the max media effect can happen at exposure time or sometime after.

    Parameters:
    ----------
    x: The original media variable (e.g., daily media spend or impressions).
    L: Length of the media effect in time periods (i.e., how many previous days influence the current day).
    P: Peak delay of the media effect, determining when the maximum impact occurs.
    D: Decay or retention rate of the media effect, controlling how quickly the influence diminishes.
    min_value: Smallest non-zero value allowed after transformation -- any lower than <min_value> are set to 0.

    Returns:
    -------
    The adstock-transformed media variable.

    Notes:
    -----
    - `L` should be a positive integer, indicating the number of past time periods to consider.
    - `P` allows for specifying how many time periods the peak impact is delayed after initial exposure.
    - `D` (decay) should be a value between 0 and 1. A higher value retains the media effect longer.
    - Interpretation of decay is what percentage of the media effect carries over to the next time period (e.g., 0.8 == 80% of the media effect carries)
    - Setting a non-zero min value is useful for smaller valued spend series as the weighted average can yield values very close to 0
      This idea for including this is for situations where you get a spending value of, say, 0.000003234, which doesn't really make a lot of sense.

    References:
    -----------
    - https://static.googleusercontent.com/media/research.google.com/en//pubs/archive/46001.pdf
    - https://towardsdatascience.com/python-stan-implementation-of-multiplicative-marketing-mix-model-with-deep-dive-into-adstock-a7320865b334
    """

    # According to the paper, asserting bounds
    assert L > 0, "L > 0 must be satisfied!"
    assert (P < L) & (P >= 0), "0 <= P < L must be satisfied!"
    assert (D < 1) & (D > 0), "0 < D < 1 must be satisfied!"

    # Extend the input array to handle the initial lag
    x = np.append(np.zeros(L - 1), x)

    # Create the weights for the adstock effect
    weights = np.array([D ** ((l - P) ** 2) for l in range(L)])
    weights /= weights.sum()  # Normalize the weights to ensure they sum to 1

    # Apply the adstock effect
    # Reversing weights order because the weight at l=0 should be applied to x_t
    adstocked_x = [np.dot(x[i - L + 1 : i + 1], weights[::-1]) for i in range(L - 1, len(x))]

    # Apply min value
    values = np.array(adstocked_x)
    values[values < min_value] = 0

    return values


def add_lag_features(
    df: pd.DataFrame,
    target_col: str,
    lag_periods: List[int] = [1, 4, 12, 52],
    time_unit: str = "week",
    date_col: str = "Date",
) -> pd.DataFrame:
    """
    Add lag features to a dataframe for a specific target column.

    Parameters:
    -----------
    df : pandas DataFrame
        Input dataframe containing the target column
    target_col : str
        Column name to create lag features for
    lag_periods : list of int, default [1, 4, 12, 52]
        List of periods to lag (e.g., weeks, months)
    time_unit : str, default "week"
        The time unit used for the lag periods (e.g., "day", "week", "month")
    date_col : str, default "Date"
        Name of the date column to use as index

    Returns:
    --------
    pandas DataFrame
        DataFrame with added lag features

    Notes:
    ------
    - Creates new columns with the naming convention: "{target_col} ({period} {time_unit} ago)"
    - The function preserves the original index if date_col is already set as index
    """
    # Make a copy of the input dataframe to avoid modifying the original
    result_df = df.copy()

    # Set the date as index if it's not already
    if date_col in result_df.columns:
        result_df = result_df.set_index(date_col)

    # Apply lags
    for lag in lag_periods:
        # Use singular or plural form based on the lag value
        time_unit_formatted = time_unit if lag == 1 else f"{time_unit}s"
        lag_name = f"{target_col} ({lag} {time_unit_formatted} ago)"
        result_df[lag_name] = result_df[target_col].shift(periods=lag)

    # Reset index if it was set in this function
    if date_col in df.columns:
        result_df = result_df.reset_index()

    return result_df


def add_rolling_means(
    df: pd.DataFrame,
    target_col: str,
    rolling_windows: List[int] = [4, 12, 52],
    time_unit: str = "week",
    date_col: str = "Date",
) -> pd.DataFrame:
    """
    Add rolling mean statistics for a target column, excluding the current row's value,
    using time-based shifting.

    Parameters:
    -----------
    df : pandas DataFrame
        Input dataframe containing the target column
    target_col : str
        Column name to create rolling statistics for
    rolling_windows : list of int, default [4, 12, 52]
        List of window sizes for rolling calculations
    time_unit : str, default "week"
        The time unit used for the lag periods (e.g., "day", "week", "month")
    date_col : str, default "Date"
        Name of the date column to use as index

    Returns:
    --------
    pandas DataFrame
        DataFrame with added rolling mean statistics features

    Notes:
    ------
    - Creates columns with naming convention: "{target_col} ({window} {time_unit} average)"
    - Each statistic is computed using only previous values (not including current row)
    - The function preserves the original index if date_col is already set as index
    - Window sizes typically represent periods (e.g., 4 for monthly, 12 for quarterly)
    """
    # Make a copy of the input dataframe
    result_df = df.copy()

    # Check if we have a date index already or need to set one
    had_date_index = False
    if date_col in result_df.columns:
        result_df = result_df.set_index(date_col)
    else:
        # Check if index is already a datetime type
        if not pd.api.types.is_datetime64_any_dtype(result_df.index):
            raise ValueError("Index must be a datetime type if date_col is not provided")
        had_date_index = True

    # Ensure index is sorted
    result_df = result_df.sort_index()

    # Define time shift and window
    time_shifts = {
        "day": pd.DateOffset(days=1),
        "week": pd.DateOffset(weeks=1),
    }
    time_windows = {
        "day": 1,
        "week": 7,
    }

    if time_unit.lower() not in time_shifts:
        raise ValueError(
            f"Unsupported time_unit: {time_unit}. Supported values are: {list(time_shifts.keys())}"
        )

    # Add means
    for window in rolling_windows:
        result_df = result_df.join(
            result_df[target_col]
            .shift(freq=time_shifts[time_unit])
            .rolling(window=f"{window*time_windows[time_unit]}D", min_periods=window)
            .mean()
            .rename(f"{target_col} ({window} {time_unit} average)")
        )

    # Reset index if it was set in this function
    if not had_date_index:
        result_df = result_df.reset_index()

    return result_df


def compute_days_and_event_name(
    dates: Union[pd.Series, List, np.ndarray],
    event_dates: Union[pd.Series, List, np.ndarray],
    event_names: Union[pd.Series, List, np.ndarray],
) -> Tuple[pd.Series, pd.Series]:
    """
    Compute signed days to the nearest event AND the name of that event.

    Uses signed distances where:
    - Negative values = days before the event (e.g., -2 means 2 days before)
    - Zero = the event itself
    - Positive values = days after the event (e.g., +3 means 3 days after)

    Parameters:
    -----------
    dates : pandas Series, list, or numpy array
        The dates to calculate days to nearest event for
    event_dates : pandas Series, list, or numpy array
        All event dates to consider
    event_names : pandas Series, list, or numpy array
        Names corresponding to each event date

    Returns:
    --------
    Tuple of (days_series, names_series)
        - days_series: Signed days to nearest event for each input date
        - names_series: Name of the nearest event for each input date
    """
    # Convert inputs to pandas datetime/series
    dates = pd.to_datetime(dates)
    event_dates = pd.to_datetime(event_dates)
    event_names = pd.Series(event_names)

    # Create event dataframe and remove duplicates (keep first occurrence)
    event_df = (
        pd.DataFrame({"date": event_dates, "name": event_names})
        .drop_duplicates(subset="date", keep="first")
        .sort_values("date")
    )

    # Initialize result series
    days_result = pd.Series(
        index=dates.index if hasattr(dates, "index") else range(len(dates)), dtype=float
    )
    names_result = pd.Series(
        index=dates.index if hasattr(dates, "index") else range(len(dates)),
        dtype=object,
    )

    for i, date in enumerate(dates):
        # Calculate signed days difference to all events
        # (date - event_date) gives negative for days before, positive for days after
        days_diff = (date - event_df["date"]).dt.days

        # Find the event with minimum absolute difference
        min_abs_idx = days_diff.abs().idxmin()
        days_result.iloc[i] = days_diff.loc[min_abs_idx]
        names_result.iloc[i] = event_df.loc[min_abs_idx, "name"]

    return days_result, names_result


def add_event_context_features(
    df: pd.DataFrame,
    event_df: pd.DataFrame,
    event_col: str = "Event",
    date_col: str = "Date",
    distance_col_name: str = "Days_To_Nearest_Event",
    event_name_col: str = "Nearest_Event_Name",
) -> pd.DataFrame:
    """
    Add both signed distance to nearest event AND the name of that event.

    Returns signed distances where negative = days before event, positive = days after.
    This is more interpretable for marketing attribution than absolute distances.

    Parameters:
    -----------
    df : pandas DataFrame
        Input dataframe to add event features to
    event_df : pandas DataFrame
        DataFrame containing event dates and names
    event_col : str, default "Event"
        Column in event_df containing event names
    date_col : str, default "Date"
        Name of the date column in both dataframes
    distance_col_name : str, default "Days_To_Nearest_Event"
        Name of the distance feature column
    event_name_col : str, default "Nearest_Event_Name"
        Name of the event name feature column

    Returns:
    --------
    pandas DataFrame
        DataFrame with added signed distance and event name features
    """
    # Make a copy of the input dataframe
    result_df = df.copy()

    # Calculate both days and event names
    days_to_event, nearest_event_names = compute_days_and_event_name(
        dates=result_df[date_col],
        event_dates=event_df[date_col],
        event_names=event_df[event_col],
    )

    # Add both features to dataframe
    result_df[distance_col_name] = days_to_event
    result_df[event_name_col] = nearest_event_names

    return result_df


def add_adstock_features(
    df: pd.DataFrame,
    adstock_params: Dict[str, Dict[str, Union[int, float]]],
    date_col: str = "Date",
) -> pd.DataFrame:
    """
    Add adstock transformed features for marketing spend columns.

    Parameters:
    -----------
    df : pandas DataFrame
        Input dataframe containing marketing spend columns
    adstock_params : dict
        Dictionary where keys are marketing column names and values are
        dictionaries containing 'L', 'P', 'D', and optionally 'min_value' parameters
        Example: {'TV': {'L': 7, 'P': 1, 'D': 0.8, 'min_value': 1}, 'Radio': {...}}
    date_col : str, default "Date"
        Name of the date column

    Returns:
    --------
    pandas DataFrame
        DataFrame with added adstock features

    Notes:
    ------
    - Creates new columns with naming convention: "{original_col} (adstock L={L}, P={P}, D={D_value})"
    - Uses delayed_adstock_transformation function for each column
    - D value is sanitized in column names by replacing . with _
    - Default min_value of 1 is used if not specified in the parameters
    - See delayed_adstock_transformation function documentation for detailed explanation
    """
    # Make a copy of the input dataframe
    result_df = df.copy()

    # Transform each marketing column
    for col, params in adstock_params.items():
        # Extract parameters with defaults
        L = params.get("L", 7)
        P = params.get("P", 1)
        D = params.get("D", 0.8)
        min_value = params.get("min_value", 1)

        # Sanitize D value for column naming
        D_value = str(D).replace(".", "_")

        # Generate adstock-transformed column name
        col_name = f"{col} (L={L}, P={P}, D={D_value})"

        # Apply transformation
        result_df[col_name] = delayed_adstock_transformation(
            x=result_df[col].values, L=L, P=P, D=D, min_value=min_value
        )

    return result_df


def extract_channel_name(string: str) -> str:
    """
    Extract the base channel name from an adstock feature name by removing parameter specifications.

    Matches everything up to and including the text before '(L=', '(P=', or '(D=' and ignores
    the parameter specifications that follow.

    Parameters:
    -----------
    string : str
        String value containing channel name and potentially adstock parameters

    Returns:
    --------
    str
        The base channel name without adstock parameter specifications

    Examples:
    ---------
    >>> extract_channel_name('TV (L=7, P=0, D=0_2)')
    'TV'
    >>> extract_channel_name('Radio Spend (L=5, P=1, D=0_8)')
    'Radio Spend'
    >>> extract_channel_name('Regular Channel Name')
    'Regular Channel Name'
    """
    # Regex to match everything before (L=, (P=, or (D=
    match = re.match(r"^(.*?)\s*\([LPD]=.*$", string)

    return match.group(1).strip() if match else string


def extract_values_and_convert(
    string: str,
) -> Tuple[Optional[int], Optional[int], Optional[float]]:
    """
    Extract adstock parameter values (L, P, D) from a formatted string and convert to appropriate types.

    Uses regex to find values after L=, P=, and D= patterns, converting underscores back to
    decimal points for the D parameter.

    Parameters:
    -----------
    string : str
        String containing adstock parameters in format "L=X, P=Y, D=Z_W"
        where Z_W represents a decimal number with underscore instead of decimal point

    Returns:
    --------
    tuple of (int, int, float) or (None, None, None)
        - L (int): Length parameter for adstock transformation
        - P (int): Peak delay parameter
        - D (float): Decay rate parameter (converted from underscore format)
        - Returns (None, None, None) if no valid pattern is found

    Examples:
    ---------
    >>> extract_values_and_convert('TV (L=7, P=1, D=0_8)')
    (7, 1, 0.8)
    >>> extract_values_and_convert('Invalid format')
    (None, None, None)
    """
    pattern = r"L=(\d+), P=(\d+), D=([\d_]+)"
    match = re.search(pattern, string)
    if match:
        L, P, D = match.groups()
        # Convert D by replacing underscore with a decimal point
        D = D.replace("_", ".")
        return int(L), int(P), float(D)  # Convert L, P to int and D to float
    return (None, None, None)  # If no match is found


def reformat_prediction_row(row: pd.Series) -> pd.Series:
    """
    Reshape prediction explanation data from DataRobot format to feature-value format.

    Converts DataRobot's explanation columns (EXPLANATION_N_FEATURE_NAME, EXPLANATION_N_STRENGTH)
    into a format where feature names become column headers and SHAP values become the values.
    This transformation facilitates easier analysis of feature contributions.

    Parameters:
    -----------
    row : pd.Series
        Pandas series containing DataRobot prediction explanations with columns like:
        - EXPLANATION_1_FEATURE_NAME, EXPLANATION_1_STRENGTH
        - EXPLANATION_2_FEATURE_NAME, EXPLANATION_2_STRENGTH, etc.

    Returns:
    --------
    pd.Series
        Transformed series with:
        - Original non-explanation columns preserved
        - New columns where feature names are headers and SHAP strengths are values
        - All EXPLANATION_* columns removed

    Notes:
    ------
    This function is designed to work with DataRobot's prediction explanation output format
    and convert it to a more analysis-friendly structure for attribution modeling.
    """
    # Extract the maximum number of explanation columns dynamically
    n_explanations = max(
        int(x.split("_")[1])
        for x in row.index.tolist()
        if "EXPLANATION_" in x and "_FEATURE_NAME" in x
    )

    # Drop explanation columns
    new_row = row.drop(labels=[col for col in row.index if "EXPLANATION_" in col]).copy()

    # Add explanations in shap matrix format
    for i in range(1, n_explanations + 1):
        feature_col = f"EXPLANATION_{i}_FEATURE_NAME"
        strength_col = f"EXPLANATION_{i}_STRENGTH"

        if feature_col in row and strength_col in row:
            feature_name = row[feature_col]
            strength_value = row[strength_col]
            new_row[feature_name] = strength_value

    return new_row


def post_process_incremental_values(
    shap_incremental: pd.DataFrame,
    data: pd.DataFrame,
    marketing_spend_features: List[str],
) -> pd.DataFrame:
    """
    Post-processes incremental SHAP values to ensure attribution validity and proper normalization.

    This function applies several data quality and business logic rules to incremental SHAP values:
    1. Ensures that only channels with non-zero spend receive attribution
    2. Renames columns to their original channel names for clarity
    3. Sets any negative contributions to zero
    4. Normalizes channel contributions relative to the total marketing effect

    Parameters:
    ----------
    shap_incremental: pd.DataFrame
        DataFrame containing incremental SHAP values for marketing channels
    data: pd.DataFrame
        Original data containing marketing spend features
    marketing_spend_features: List[str]
        List of column names containing marketing spend values

    Returns:
    -------
    pd.DataFrame
        Normalized and cleaned attribution DataFrame with:
        - Original non-marketing columns from shap_incremental
        - Marketing channel columns renamed to their original names
        - All values properly normalized relative to the total marketing effect

    Notes:
    -----
    - This function assumes the existence of helper functions:
      - extract_channel_name: Extracts the base channel name from an adstock feature name
      - apply_normalization: Normalizes values to ensure they sum to a specific column
    - Negative contribution values are set to zero as they're considered invalid
    - The normalization process ensures attribution percentages sum correctly
    """
    # Create matrix of whether or not the marketing spend features in the adstock space are non-zero
    df_zero_matrix = (data[marketing_spend_features] > 0).astype(int)

    # Ensure we only have non-zero contribution for non-zero adstock spend
    shap_values = shap_incremental[marketing_spend_features].multiply(
        df_zero_matrix[marketing_spend_features]
    )

    # Rename the columns back to their original for clarity
    shap_values.columns = [extract_channel_name(x) for x in shap_values.columns.tolist()]

    # Set any remaining negatives to 0 (invalid attribution)
    shap_values[shap_values <= 0] = 0

    # Reorganize output - keep all non-marketing features and add cleaned marketing features
    df_shap_cleaned = shap_incremental[
        [x for x in shap_incremental.columns if x not in marketing_spend_features]
    ].join(shap_values)

    # Now normalize with respect to the marketing effect and the incremental shap values
    df_shap_norm = apply_normalization(
        df=df_shap_cleaned,
        sum_column="Marketing Effect",
        columns_to_use=shap_values.columns.tolist(),
        round_tolerance=2,
    )

    return df_shap_norm


def apply_normalization(
    df: pd.DataFrame,
    sum_column: str,
    columns_to_use: List[str],
    round_tolerance: int = 2,
) -> pd.DataFrame:
    """
    Applies simple normalization scheme to enforce a sum condition.

    This function normalizes specified columns so that their row-wise sum equals
    the value in a target sum column, maintaining proportional relationships
    between the normalized columns.

    Parameters:
    -----------
    df : pd.DataFrame
        Dataframe containing the columns of interest
    sum_column : str
        Name of column you want columns_to_use to sum to
    columns_to_use : List[str]
        Name(s) of columns you want to use for summing to sum_column
    round_tolerance : int, default=2
        For the assertion check, how many digits to round when checking sum validity

    Returns:
    --------
    pd.DataFrame
        DataFrame that replaces columns_to_use columns with values that sum to sum_column for each row

    Notes:
    ------
    - Uses proportional scaling to maintain relative relationships between columns
    - Issues warning if normalized values don't sum to target within specified tolerance
    - Useful for ensuring attribution percentages or contributions sum correctly
    """

    # Find scalar to reduce or increase all values by
    normalizing_factor = df[sum_column] / df[columns_to_use].sum(axis=1)

    # Multiply this out
    normalized_values = df[columns_to_use].multiply(normalizing_factor, axis="rows")

    # Add them in
    df_norm = df.drop(columns_to_use, axis=1).join(normalized_values)

    # Final check to make sure we sum to the target (should be VERY close)
    sum_check = df_norm[sum_column] - df_norm[columns_to_use].sum(axis=1)

    # Warn when they don't sum within the tolerance level
    if sum_check.round(round_tolerance).sum() != 0:
        warnings.warn(f"Shap values do not sum to the {sum_column}!")

    return df_norm


def prepare_summary_data(df: pd.DataFrame) -> pd.DataFrame:
    """
    Calculate comprehensive summary metrics by marketing channel including ROAS analysis.

    Aggregates spending and contribution data by channel and calculates key performance
    metrics including return on ad spend (ROAS) and percentage distributions.

    Parameters:
    -----------
    df : pd.DataFrame
        DataFrame containing marketing data with required columns:
        - 'channel': Marketing channel name
        - 'spend': Marketing spend amount
        - 'contribution': Attributed contribution/revenue

    Returns:
    --------
    pd.DataFrame
        Summary DataFrame with columns:
        - 'channel': Channel name
        - 'spend': Total spend per channel
        - 'contribution': Total contribution per channel
        - 'spend_pct': Percentage of total spend
        - 'contribution_pct': Percentage of total contribution
        - 'roas': Return on Ad Spend (contribution/spend)

    Notes:
    ------
    - Results are sorted by ROAS in descending order for better visualization
    - ROAS calculation assumes spend > 0 for all channels
    """
    summary = df.groupby("channel").agg({"spend": "sum", "contribution": "sum"}).reset_index()

    # Calculate percentages
    summary["spend_pct"] = (summary["spend"] / summary["spend"].sum()) * 100
    summary["contribution_pct"] = (summary["contribution"] / summary["contribution"].sum()) * 100
    summary["roas"] = summary["contribution"] / summary["spend"]

    # Sort by ROAS for better visualization
    summary = summary.sort_values("roas", ascending=False)

    return summary


def plot_summary(summary: pd.DataFrame) -> None:
    """
    Create a comprehensive visualization of marketing channel performance.

    Generates a side-by-side grouped bar chart showing spend vs contribution percentages
    with an overlay trend line displaying ROAS values. Uses a professional corporate
    color scheme with value labels and highlighting.

    Parameters:
    -----------
    summary : pd.DataFrame
        Summary data from prepare_summary_data() function containing:
        - 'channel': Channel names
        - 'spend_pct': Spend percentage
        - 'contribution_pct': Contribution percentage
        - 'roas': Return on Ad Spend values

    Returns:
    --------
    None
        Displays the plot using matplotlib

    Notes:
    ------
    - Left y-axis shows percentages (0-100%)
    - Right y-axis shows ROAS values
    - ROAS values are labeled above data points with boxes
    - Percentage values are labeled within bars
    - Professional color scheme: blue (spend), orange (contribution), green (ROAS)
    """

    fig, ax1 = plt.subplots(figsize=(14, 8))

    x = np.arange(len(summary))
    width = 0.35

    # Create grouped bars with professional corporate colors
    bars1 = ax1.bar(
        x - width / 2,
        summary["spend_pct"],
        width,
        label="Spend %",
        color="#1f77b4",
        alpha=0.8,
    )  # Professional blue
    bars2 = ax1.bar(
        x + width / 2,
        summary["contribution_pct"],
        width,
        label="Contribution %",
        color="#ff7f0e",
        alpha=0.8,
    )  # Professional orange

    # Create second y-axis for ROAS
    ax2 = ax1.twinx()

    # Add ROAS line with markers
    roas_line = ax2.plot(
        x,
        summary["roas"],
        color="#006400",
        marker="o",
        linewidth=3,
        markersize=8,
        label="ROAS",
        markerfacecolor="white",
        markeredgecolor="#006400",
        markeredgewidth=2,
    )  # Dark green

    # Calculate ROAS range for label positioning
    roas_min, roas_max = summary["roas"].min(), summary["roas"].max()

    # Add ROAS value labels on the points (ABOVE the dots) with boxes
    for i, roas_value in enumerate(summary["roas"]):
        ax2.text(
            x[i],
            roas_value + (roas_max - roas_min) * 0.03,
            f"{roas_value:.2f}",
            ha="center",
            va="bottom",
            color="#006400",
            fontweight="bold",
            fontsize=9,
            bbox=dict(
                boxstyle="round,pad=0.3",
                facecolor="white",
                edgecolor="#006400",
                linewidth=1,
                alpha=0.9,
            ),
        )

    # Add value labels on bars
    for bar, value in zip(bars1, summary["spend_pct"]):
        ax1.text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height() / 2,
            f"{value:.1f}%",
            ha="center",
            va="center",
            color="white",
            fontweight="bold",
            fontsize=9,
        )

    for bar, value in zip(bars2, summary["contribution_pct"]):
        ax1.text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height() / 2,
            f"{value:.1f}%",
            ha="center",
            va="center",
            color="white",
            fontweight="bold",
            fontsize=9,
        )

    # Customize first y-axis (percentages)
    ax1.set_xlabel("Marketing Channel", fontsize=12, fontweight="bold")
    ax1.set_ylabel("Percentage (%)", fontsize=12, fontweight="bold", color="black")
    ax1.set_title(
        "Marketing Performance: Spend vs Contribution with ROAS Trend",
        fontsize=14,
        fontweight="bold",
        pad=20,
    )
    ax1.set_xticks(x)
    ax1.set_xticklabels(summary["channel"], rotation=45, ha="right")
    ax1.tick_params(axis="y", labelcolor="black")

    # Customize second y-axis (ROAS)
    ax2.set_ylabel("ROAS", fontsize=12, fontweight="bold", color="#006400")
    ax2.tick_params(axis="y", labelcolor="#006400")

    # Set ROAS axis limits for better visibility
    roas_min, roas_max = summary["roas"].min(), summary["roas"].max()
    roas_padding = (roas_max - roas_min) * 0.3
    ax2.set_ylim(max(0, roas_min - roas_padding), roas_max + roas_padding)

    # Combine legends from both axes
    lines1, labels1 = ax1.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    legend = ax1.legend(
        lines1 + lines2,
        labels1 + labels2,
        loc="upper left",
        fontsize=11,
        frameon=True,
        fancybox=True,
        shadow=True,
        framealpha=0.9,
        edgecolor="black",
        facecolor="white",
    )

    # Turn off grid lines
    ax1.grid(False)
    ax2.grid(False)

    # Highlight best and worst performers
    best_idx = summary["roas"].idxmax()
    worst_idx = summary["roas"].idxmin()

    best_pos = summary.index[summary["roas"].idxmax()]
    worst_pos = summary.index[summary["roas"].idxmin()]

    plt.tight_layout()
    plt.show()
