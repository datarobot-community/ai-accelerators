from collections import defaultdict
from datetime import datetime
import itertools
import logging
import re
import time
from typing import Dict, List, Optional, Tuple

from datasketch import MinHash, MinHashLSH
import numpy as np
import pandas as pd
import pytz
from scipy import stats
import streamlit as st

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def check_missing_values(df: pd.DataFrame) -> Dict:
    """Check for missing values in each column of the DataFrame."""
    total_rows = len(df)

    # Create list to store missing value info
    missing_data = []

    for col in df.columns:
        missing_count = df[col].isna().sum()
        if missing_count > 0:
            missing_percentage = (missing_count / total_rows) * 100
            severity = (
                "High"
                if missing_percentage > 25
                else "Moderate"
                if missing_percentage > 5
                else "Low"
            )

            missing_data.append(
                {
                    "Column": col,
                    "Missing Count": missing_count,
                    "Missing %": f"{missing_percentage:.1f}%",
                    "Severity": severity,
                }
            )

    if missing_data:
        # Create and sort DataFrame
        results_df = pd.DataFrame(missing_data)
        results_df = results_df.sort_values(
            by=["Severity", "Missing Count"],
            ascending=[False, False],
            key=lambda x: pd.Categorical(
                x, categories=["High", "Moderate", "Low"], ordered=True
            )
            if x.name == "Severity"
            else x,
        )

        # Add total row
        total_row = pd.DataFrame(
            [
                {
                    "Column": "TOTAL",
                    "Missing Count": results_df["Missing Count"].sum(),
                    "Missing %": f"{(results_df['Missing Count'].sum() / (total_rows * len(df.columns)) * 100):.1f}%",
                    "Severity": "",
                }
            ]
        )
        results_df = pd.concat([results_df, total_row])

        return {
            "issue_detected": True,
            "missing_info": missing_data,  # Keep original format for compatibility
            "results_df": results_df,  # Add DataFrame format
            "recommendation": "Missing values detected in multiple columns. Review the table above for details.",
        }

    return {
        "issue_detected": False,
        "missing_info": {},
        "results_df": pd.DataFrame(),
        "recommendation": "No missing values detected in any column.",
    }


def check_duplicates(df: pd.DataFrame) -> Dict:
    """Check for duplicate rows in the DataFrame."""
    # Check for exact duplicates (all columns)
    duplicates = df.duplicated(keep="first")
    duplicate_count = duplicates.sum()

    if duplicate_count > 0:
        # Get the duplicate rows
        duplicate_rows = df[duplicates].copy()

        # Create summary data
        duplicate_data = [
            {
                "Type": "Exact Duplicates",
                "Count": duplicate_count,
                "Percentage": f"{(duplicate_count / len(df)) * 100:.1f}%",
                "Sample Row": str(duplicate_rows.iloc[i].to_dict()),
            }
            for i in range(min(3, len(duplicate_rows)))
        ]

        # Check for potential subset duplicates (rows that are duplicates when considering only a subset of columns)
        subset_duplicates = []
        for subset_size in range(
            2, min(5, len(df.columns))
        ):  # Check subsets of 2-4 columns
            for cols in itertools.combinations(df.columns, subset_size):
                subset_dups = df.duplicated(subset=list(cols), keep="first")
                subset_count = subset_dups.sum()

                if (
                    subset_count > duplicate_count
                ):  # Only report if we found more duplicates than exact matches
                    subset_duplicates.append(
                        {
                            "Type": "Partial Duplicates",
                            "Columns": ", ".join(cols),
                            "Count": subset_count,
                            "Percentage": f"{(subset_count / len(df)) * 100:.1f}%",
                            "Sample Row": str(df[subset_dups].iloc[0].to_dict()),
                        }
                    )

        # Sort subset duplicates by count and take top 3
        subset_duplicates.sort(key=lambda x: int(x["Count"]), reverse=True)
        duplicate_data.extend(subset_duplicates[:3])

        # Create DataFrame
        results_df = pd.DataFrame(duplicate_data)

        return {
            "issue_detected": True,
            "results_df": results_df,
            "duplicate_rows": duplicates[
                duplicates
            ].index.tolist(),  # Keep for compatibility
            "recommendation": "Duplicate rows detected. Review the table above for details.",
        }

    return {
        "issue_detected": False,
        "results_df": pd.DataFrame(),
        "duplicate_rows": [],
        "recommendation": "No duplicate rows detected.",
    }


def is_potential_date(value: str) -> bool:
    """Check if a string might represent a date."""
    # Common date patterns
    date_patterns = [
        r"\d{4}-\d{2}-\d{2}",  # YYYY-MM-DD
        r"\d{2}-\d{2}-\d{4}",  # DD-MM-YYYY or MM-DD-YYYY
        r"\d{2}/\d{2}/\d{4}",  # DD/MM/YYYY or MM/DD/YYYY
        r"\d{4}/\d{2}/\d{2}",  # YYYY/MM/DD
        r"\d{2}\.\d{2}\.\d{4}",  # DD.MM.YYYY
        r"\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{4}",  # 1 Jan 2020
        r"\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}",  # YYYY-MM-DD HH:MM:SS
        r"\d{2}/\d{2}/\d{2}",  # DD/MM/YY
    ]

    if not isinstance(value, str):
        return False

    return any(re.match(pattern, value) for pattern in date_patterns)


def detect_date_format(sample_dates: List[str]) -> Optional[str]:
    """
    Detect the most likely date format from a list of date strings.
    Returns a format string that can be used with pd.to_datetime.
    """
    common_formats = [
        ("%Y-%m-%d", "YYYY-MM-DD"),
        ("%d-%m-%Y", "DD-MM-YYYY"),
        ("%m-%d-%Y", "MM-DD-YYYY"),
        ("%Y/%m/%d", "YYYY/MM/DD"),
        ("%d/%m/%Y", "DD/MM/YYYY"),
        ("%m/%d/%Y", "MM/DD/YYYY"),
        ("%d.%m.%Y", "DD.MM.YYYY"),
        ("%Y-%m-%d %H:%M:%S", "YYYY-MM-DD HH:MM:SS"),
        ("%d/%m/%y", "DD/MM/YY"),
    ]

    for date_format, format_name in common_formats:
        try:
            # Try to parse all sample dates with this format
            all_valid = all(
                bool(datetime.strptime(date, date_format))
                for date in sample_dates
                if isinstance(date, str) and date.strip()
            )
            if all_valid:
                return format_name
        except ValueError:
            continue

    return None


def check_date_consistency(df: pd.DataFrame) -> Dict:
    """Check for date consistency issues in the DataFrame."""
    date_data = []

    # Check each column that's not already datetime
    for col in df.columns:
        if df[col].dtype == "datetime64[ns]":
            # Already datetime, check for timezone consistency
            has_timezone = df[col].dt.tz is not None
            if not has_timezone:
                date_data.append(
                    {
                        "Column": col,
                        "Current Type": "datetime64[ns]",
                        "Issue": "Missing timezone information",
                        "Sample Values": ", ".join(str(x) for x in df[col].head(3)),
                        "Action Required": "Add timezone information",
                    }
                )

        elif df[col].dtype == "object":
            # Sample non-null values
            sample_values = df[col].dropna().head(10).tolist()

            # Check if values look like dates
            date_like_values = [
                str(v) for v in sample_values if is_potential_date(str(v))
            ]

            if date_like_values and len(date_like_values) / len(sample_values) > 0.5:
                detected_format = detect_date_format(date_like_values)
                if detected_format:
                    date_data.append(
                        {
                            "Column": col,
                            "Current Type": "object",
                            "Issue": f"String values in {detected_format} format",
                            "Sample Values": ", ".join(
                                str(x) for x in date_like_values[:3]
                            ),
                            "Action Required": "Convert to datetime",
                        }
                    )

    if date_data:
        # Create DataFrame
        results_df = pd.DataFrame(date_data)

        return {
            "issue_detected": True,
            "results_df": results_df,
            "date_columns": {
                row["Column"]: {
                    "current_type": row["Current Type"],
                    "detected_format": row["Issue"].split(" in ")[-1]
                    if "format" in row["Issue"]
                    else None,
                    "needs_conversion": row["Current Type"] == "object",
                    "has_timezone": "timezone" not in row["Issue"],
                    "sample_values": row["Sample Values"].split(", "),
                }
                for _, row in results_df.iterrows()
            },  # Keep for compatibility
            "recommendation": "Date format issues detected. Review the table above for details.",
        }

    return {
        "issue_detected": False,
        "results_df": pd.DataFrame(),
        "date_columns": {},
        "recommendation": "No date format issues detected.",
    }


def check_column_names(df: pd.DataFrame) -> Dict:
    """Check column names for spacing issues."""
    column_data = []

    for col in df.columns:
        issues = []
        cleaned_name = col

        # Check for leading spaces
        if col.startswith(" "):
            issues.append("leading spaces")
            cleaned_name = cleaned_name.lstrip()

        # Check for trailing spaces
        if col.endswith(" "):
            issues.append("trailing spaces")
            cleaned_name = cleaned_name.rstrip()

        # Check for consecutive spaces
        if "  " in col:
            issues.append("consecutive spaces")
            cleaned_name = " ".join(cleaned_name.split())

        if issues:
            column_data.append(
                {
                    "Column": col,
                    "Issues": ", ".join(issues),
                    "Suggested Name": cleaned_name,
                    "Changes Required": "Yes" if cleaned_name != col else "No",
                }
            )

    if column_data:
        # Create DataFrame
        results_df = pd.DataFrame(column_data)

        return {
            "issue_detected": True,
            "results_df": results_df,
            "problematic_columns": {  # Keep for compatibility
                row["Column"]: {
                    "issues": row["Issues"].split(", "),
                    "suggested_name": row["Suggested Name"],
                }
                for _, row in results_df.iterrows()
            },
            "recommendation": "Column naming issues detected. Review the table above for details.",
        }

    return {
        "issue_detected": False,
        "results_df": pd.DataFrame(),
        "problematic_columns": {},
        "recommendation": "No column naming issues detected.",
    }


def check_string_values(df: pd.DataFrame) -> Dict:
    """Check string/object columns for spacing issues in their values."""
    string_data = []

    # Check only string/object columns
    string_columns = df.select_dtypes(include=["object"]).columns

    for col in string_columns:
        # Skip if column has no string values
        if not df[col].dtype == "object" or df[col].isna().all():
            continue

        # Convert to string and check non-null values
        string_values = df[col].astype(str).dropna()
        total_rows = len(string_values)

        # Check for various spacing issues
        leading_spaces = string_values.str.startswith(" ").sum()
        trailing_spaces = string_values.str.endswith(" ").sum()
        consecutive_spaces = string_values.str.contains("  ").sum()

        if any(
            count > 0 for count in [leading_spaces, trailing_spaces, consecutive_spaces]
        ):
            # Get sample values for each issue
            samples = {
                "leading": ", ".join(
                    repr(x) for x in df[col][string_values.str.startswith(" ")].head(3)
                ),
                "trailing": ", ".join(
                    repr(x) for x in df[col][string_values.str.endswith(" ")].head(3)
                ),
                "consecutive": ", ".join(
                    repr(x) for x in df[col][string_values.str.contains("  ")].head(3)
                ),
            }

            # Add row for each type of issue found
            if leading_spaces > 0:
                string_data.append(
                    {
                        "Column": col,
                        "Issue Type": "Leading spaces",
                        "Affected Rows": leading_spaces,
                        "Percentage": f"{(leading_spaces / total_rows) * 100:.1f}%",
                        "Sample Values": samples["leading"],
                    }
                )

            if trailing_spaces > 0:
                string_data.append(
                    {
                        "Column": col,
                        "Issue Type": "Trailing spaces",
                        "Affected Rows": trailing_spaces,
                        "Percentage": f"{(trailing_spaces / total_rows) * 100:.1f}%",
                        "Sample Values": samples["trailing"],
                    }
                )

            if consecutive_spaces > 0:
                string_data.append(
                    {
                        "Column": col,
                        "Issue Type": "Consecutive spaces",
                        "Affected Rows": consecutive_spaces,
                        "Percentage": f"{(consecutive_spaces / total_rows) * 100:.1f}%",
                        "Sample Values": samples["consecutive"],
                    }
                )

    if string_data:
        # Create DataFrame
        results_df = pd.DataFrame(string_data)
        results_df = results_df.sort_values(
            ["Column", "Affected Rows"], ascending=[True, False]
        )

        return {
            "issue_detected": True,
            "results_df": results_df,
            "problematic_columns": {  # Keep for compatibility
                row["Column"]: {
                    "issues": {
                        "leading_spaces": row["Affected Rows"]
                        if row["Issue Type"] == "Leading spaces"
                        else 0,
                        "trailing_spaces": row["Affected Rows"]
                        if row["Issue Type"] == "Trailing spaces"
                        else 0,
                        "consecutive_spaces": row["Affected Rows"]
                        if row["Issue Type"] == "Consecutive spaces"
                        else 0,
                    },
                    "samples": {
                        "leading_spaces": row["Sample Values"].split(", ")
                        if row["Issue Type"] == "Leading spaces"
                        else [],
                        "trailing_spaces": row["Sample Values"].split(", ")
                        if row["Issue Type"] == "Trailing spaces"
                        else [],
                        "consecutive_spaces": row["Sample Values"].split(", ")
                        if row["Issue Type"] == "Consecutive spaces"
                        else [],
                    },
                    "total_rows": len(
                        df
                    ),  # Use actual DataFrame length instead of calculating
                }
                for _, row in results_df.iterrows()
            },
            "recommendation": "String value spacing issues detected. Review the table above for details.",
        }

    return {
        "issue_detected": False,
        "results_df": pd.DataFrame(),
        "problematic_columns": {},
        "recommendation": "No string value spacing issues detected.",
    }


def check_for_special_characters(df: pd.DataFrame) -> Dict:
    """Check column names and values for problematic special characters."""
    SPECIAL_CHARS = {
        ";": "semicolon",
        "'": "single quote",
        '"': "double quote",
        "`": "backtick",
        "*": "asterisk",
        "/": "forward slash",
        "\\": "backslash",
        "#": "number sign",
        "&": "ampersand",
        "$": "dollar sign",
        "%": "percent sign",
        "^": "caret",
        "~": "tilde",
        "|": "vertical bar",
        ">": "greater-than sign",
        "<": "less-than sign",
    }

    special_char_data = []

    # Check column names
    for col in df.columns:
        found_chars = []
        for char, description in SPECIAL_CHARS.items():
            if char in col:
                safe_name = col.replace(char, "_")
                special_char_data.append(
                    {
                        "Location": "Column Name",
                        "Column": col,
                        "Character": char,
                        "Description": description,
                        "Occurrences": 1,
                        "Sample Values": col,
                        "Suggested Fix": safe_name,
                    }
                )

    # Check values in string columns
    string_columns = df.select_dtypes(include=["object"]).columns
    for col in string_columns:
        if df[col].isna().all():
            continue

        string_values = df[col].astype(str).dropna()
        total_values = len(string_values)

        for char, description in SPECIAL_CHARS.items():
            # Count occurrences
            has_char = string_values.str.contains(char, regex=False)
            count = has_char.sum()

            if count > 0:
                sample_values = df[col][has_char].head(3).tolist()
                special_char_data.append(
                    {
                        "Location": "Column Values",
                        "Column": col,
                        "Character": char,
                        "Description": description,
                        "Occurrences": count,
                        "Percentage": f"{(count / total_values) * 100:.1f}%",
                        "Sample Values": ", ".join(repr(x) for x in sample_values),
                        "Suggested Fix": "Review and clean special characters",
                    }
                )

    if special_char_data:
        # Create DataFrame
        results_df = pd.DataFrame(special_char_data)
        results_df = results_df.sort_values(
            ["Location", "Column", "Occurrences"], ascending=[True, True, False]
        )

        return {
            "issue_detected": True,
            "results_df": results_df,
            # Keep compatibility with old format
            "column_issues": {
                row["Column"]: {
                    "special_chars": [(row["Character"], row["Description"])]
                }
                for _, row in results_df[
                    results_df["Location"] == "Column Name"
                ].iterrows()
            },
            "value_issues": {
                row["Column"]: {
                    "char_counts": {
                        row["Character"]: {
                            "count": row["Occurrences"],
                            "description": row["Description"],
                            "percentage": float(row["Percentage"].rstrip("%"))
                            if "Percentage" in row
                            else 0,
                        }
                    },
                    "sample_values": {
                        row["Character"]: row["Sample Values"].split(", ")
                    },
                    "total_rows": len(
                        df
                    ),  # Use actual DataFrame length instead of calculating
                }
                for _, row in results_df[
                    results_df["Location"] == "Column Values"
                ].iterrows()
            },
            "recommendation": "Special character issues detected. Review the table above for details.",
        }

    return {
        "issue_detected": False,
        "results_df": pd.DataFrame(),
        "column_issues": {},
        "value_issues": {},
        "recommendation": "No special character issues detected.",
    }


def check_data_types(df: pd.DataFrame, summary_stats: Optional[Dict] = None) -> Dict:
    """Check for incorrect or suboptimal data types in the DataFrame."""
    type_data = []

    # Define yes/no variations
    YES_VALUES = {"yes", "y", "true", "1", "Yes", "YES", "Y"}
    NO_VALUES = {"no", "n", "false", "0", "No", "NO", "N"}

    for col in df.columns:
        current_type = df[col].dtype

        # Use summary stats if available, otherwise compute
        if summary_stats and col in summary_stats:
            col_stats = summary_stats[col]
            sample_values = [col_stats.get(f"{i}%", None) for i in [0, 25, 50, 75, 100]]
            sample_values = [v for v in sample_values if v is not None]
        else:
            sample_values = df[col].dropna().head(5).tolist()

        # Skip if column is empty
        if df[col].isna().all():
            continue

        # Check for potential type conversions
        suggested_types = []

        # Check if object/string column might be numeric or binary
        if current_type == "object":
            # Check if values are yes/no-like
            unique_values = set(df[col].dropna().astype(str).str.strip().str.lower())
            if unique_values and unique_values <= (YES_VALUES | NO_VALUES):
                type_data.append(
                    {
                        "Column": col,
                        "Current Type": str(current_type),
                        "Suggested Type": "boolean",
                        "Sample Values": ", ".join(repr(x) for x in sample_values[:3]),
                        "Reason": "Contains only yes/no values",
                    }
                )
            else:
                # Try converting to numeric
                try:
                    cleaned_samples = (
                        df[col]
                        .dropna()
                        .head(100)
                        .astype(str)
                        .str.replace(",", "")
                        .str.replace("$", "")
                    )
                    numeric_conversion = pd.to_numeric(cleaned_samples)
                    # If successful, check if all values are integers
                    if all(numeric_conversion.astype(int) == numeric_conversion):
                        type_data.append(
                            {
                                "Column": col,
                                "Current Type": str(current_type),
                                "Suggested Type": "int64",
                                "Sample Values": ", ".join(
                                    repr(x) for x in sample_values[:3]
                                ),
                                "Reason": "Contains only integer values",
                            }
                        )
                    else:
                        type_data.append(
                            {
                                "Column": col,
                                "Current Type": str(current_type),
                                "Suggested Type": "float64",
                                "Sample Values": ", ".join(
                                    repr(x) for x in sample_values[:3]
                                ),
                                "Reason": "Contains numeric values",
                            }
                        )
                except:
                    pass

        # Check if float column might be integer
        elif current_type == "float64":
            values_to_check = [v for v in sample_values if pd.notna(v)]
            if values_to_check and all(float(v).is_integer() for v in values_to_check):
                type_data.append(
                    {
                        "Column": col,
                        "Current Type": str(current_type),
                        "Suggested Type": "Int64",
                        "Sample Values": ", ".join(repr(x) for x in sample_values[:3]),
                        "Reason": "Contains only integer values",
                    }
                )

        # Check if integer column might be boolean
        elif "int" in str(current_type):
            unique_values = set(df[col].dropna().unique())
            if unique_values <= {0, 1}:
                type_data.append(
                    {
                        "Column": col,
                        "Current Type": str(current_type),
                        "Suggested Type": "boolean",
                        "Sample Values": ", ".join(repr(x) for x in sample_values[:3]),
                        "Reason": "Contains only 0/1 values",
                    }
                )

    if type_data:
        # Create DataFrame
        results_df = pd.DataFrame(type_data)

        return {
            "issue_detected": True,
            "results_df": results_df,
            "type_issues": {  # Keep for compatibility
                row["Column"]: {
                    "current_type": row["Current Type"],
                    "issues": [{"suggested_type": row["Suggested Type"]}],
                    "sample_values": row["Sample Values"].split(", "),
                }
                for _, row in results_df.iterrows()
            },
            "recommendation": "Data type issues detected. Review the table above for details.",
        }

    return {
        "issue_detected": False,
        "results_df": pd.DataFrame(),
        "type_issues": {},
        "recommendation": "No data type issues detected.",
    }


def check_outliers(df: pd.DataFrame) -> Dict:
    """Check for outliers in numeric columns using the z-score method."""
    outlier_data = []

    # Get numeric columns excluding boolean/binary columns
    numeric_cols = df.select_dtypes(include=["int64", "float64"]).columns
    numeric_cols = [col for col in numeric_cols if len(df[col].unique()) > 2]

    for col in numeric_cols:
        # Skip if column is empty or all values are the same
        if df[col].isna().all() or df[col].nunique() <= 1:
            continue

        # Get clean series (no nulls)
        clean_series = df[col].dropna()

        # Calculate z-scores
        mean = clean_series.mean()
        std = clean_series.std()
        z_scores = (clean_series - mean) / std

        # Find outliers (|z-score| > 3)
        outliers = clean_series[abs(z_scores) > 3]

        if len(outliers) > 0:
            # Calculate percentage
            outlier_percent = (len(outliers) / len(clean_series)) * 100

            outlier_data.append(
                {
                    "Column": col,
                    "Outlier Count": len(outliers),
                    "Percentage": f"{outlier_percent:.1f}%",
                    "Valid Range": f"[{mean - 3*std:.2f}, {mean + 3*std:.2f}]",
                    "Mean": f"{mean:.2f}",
                    "Std Dev": f"{std:.2f}",
                    "Sample Values": ", ".join(str(x) for x in outliers.head(3)),
                }
            )

    if outlier_data:
        # Create DataFrame
        results_df = pd.DataFrame(outlier_data)
        results_df = results_df.sort_values("Outlier Count", ascending=False)

        return {
            "issue_detected": True,
            "results_df": results_df,
            "outlier_info": {  # Keep for compatibility
                row["Column"]: {
                    "total_outliers": row["Outlier Count"],
                    "outlier_percent": float(row["Percentage"].rstrip("%")),
                    "z_score_bounds": {
                        "lower": float(row["Valid Range"].strip("[]").split(",")[0]),
                        "upper": float(row["Valid Range"].strip("[]").split(",")[1]),
                    },
                    "sample_outliers": row["Sample Values"].split(", "),
                }
                for _, row in results_df.iterrows()
            },
            "recommendation": "Outliers detected in numeric columns. Review the table above for details.",
        }

    return {
        "issue_detected": False,
        "results_df": pd.DataFrame(),
        "outlier_info": {},
        "recommendation": "No outliers detected using z-score method (|z| > 3).",
    }


def check_statistical_quality(df: pd.DataFrame) -> Dict:
    """Check statistical properties of numeric columns."""
    distribution_data = []
    correlation_data = []

    # Get numeric columns excluding binary/boolean
    numeric_cols = df.select_dtypes(include=["int64", "float64"]).columns
    numeric_cols = [col for col in numeric_cols if len(df[col].unique()) > 2]

    # Skip if not enough numeric columns
    if len(numeric_cols) < 1:
        return {
            "issue_detected": False,
            "results_df": pd.DataFrame(),
            "correlation_df": pd.DataFrame(),
            "recommendation": "No numeric columns available for statistical analysis.",
        }

    # Distribution Analysis
    for col in numeric_cols:
        clean_series = df[col].dropna()
        if len(clean_series) < 3:  # Need at least 3 values for statistical tests
            continue

        # Basic statistics
        mean = clean_series.mean()
        median = clean_series.median()
        std = clean_series.std()
        skew = clean_series.skew()
        kurtosis = clean_series.kurtosis()

        issues = []

        # Test for normality (Shapiro-Wilk test)
        if len(clean_series) <= 5000:  # Shapiro-Wilk limited to 5000 samples
            _, normality_p = stats.shapiro(clean_series)
            if normality_p <= 0.05:
                issues.append("Non-normal distribution")

        # Check for severe skewness
        if abs(skew) > 1:
            issues.append("Highly skewed")

        # Check for unusual distribution shape
        if abs(kurtosis) > 2:
            issues.append("Unusual peaks/tails")

        # Check mean-median difference
        mean_median_diff = abs(mean - median) / std if std > 0 else 0
        if mean_median_diff > 0.5:
            issues.append("Large mean-median gap")

        # Coefficient of variation
        cv = std / mean if mean != 0 else 0
        if cv > 1:
            issues.append("High variance relative to mean")

        if issues:
            distribution_data.append(
                {
                    "Column": col,
                    "Issues": ", ".join(issues),
                    "Mean": f"{mean:.2f}",
                    "Median": f"{median:.2f}",
                    "Std Dev": f"{std:.2f}",
                    "Skewness": f"{skew:.2f}",
                    "Kurtosis": f"{kurtosis:.2f}",
                    "CV": f"{cv:.2f}",
                }
            )

    # Correlation Analysis
    if len(numeric_cols) > 1:
        correlation_matrix = df[numeric_cols].corr()
        for i in range(len(numeric_cols)):
            for j in range(i + 1, len(numeric_cols)):
                correlation = correlation_matrix.iloc[i, j]
                if abs(correlation) > 0.8:
                    correlation_data.append(
                        {
                            "Column 1": numeric_cols[i],
                            "Column 2": numeric_cols[j],
                            "Correlation": f"{correlation:.2f}",
                            "Strength": "Very Strong"
                            if abs(correlation) > 0.9
                            else "Strong",
                        }
                    )

    # Create DataFrames
    results_df = (
        pd.DataFrame(distribution_data) if distribution_data else pd.DataFrame()
    )
    correlation_df = (
        pd.DataFrame(correlation_data) if correlation_data else pd.DataFrame()
    )

    if not results_df.empty or not correlation_df.empty:
        return {
            "issue_detected": True,
            "results_df": results_df,
            "correlation_df": correlation_df,
            "distribution_issues": {  # Keep for compatibility
                row["Column"]: {
                    "issues": row["Issues"].split(", "),
                    "statistics": {
                        "mean": float(row["Mean"]),
                        "median": float(row["Median"]),
                        "std": float(row["Std Dev"]),
                        "skewness": float(row["Skewness"]),
                        "kurtosis": float(row["Kurtosis"]),
                        "cv": float(row["CV"]),
                    },
                }
                for _, row in results_df.iterrows()
            },
            "correlation_issues": {  # Keep for compatibility
                "high_correlations": [
                    {
                        "columns": (row["Column 1"], row["Column 2"]),
                        "correlation": float(row["Correlation"]),
                    }
                    for _, row in correlation_df.iterrows()
                ]
            },
            "recommendation": "Statistical issues detected. Review the tables above for details.",
        }

    return {
        "issue_detected": False,
        "results_df": pd.DataFrame(),
        "correlation_df": pd.DataFrame(),
        "distribution_issues": {},
        "correlation_issues": {},
        "recommendation": "No significant statistical issues detected.",
    }


def check_inliers(df: pd.DataFrame) -> Dict:
    """Check for potential inlier issues in numeric columns."""
    inlier_data = []

    # Get numeric columns excluding binary/boolean
    numeric_cols = df.select_dtypes(include=["int64", "float64"]).columns
    numeric_cols = [col for col in numeric_cols if len(df[col].unique()) > 2]

    for col in numeric_cols:
        clean_series = df[col].dropna()
        if len(clean_series) < 10:  # Need sufficient data
            continue

        # Calculate basic statistics
        mean = clean_series.mean()
        std = clean_series.std()

        # Find values very close to mean (within 0.1 std)
        close_to_mean = clean_series[abs(clean_series - mean) < 0.1 * std]
        close_count = len(close_to_mean)

        if close_count > len(clean_series) * 0.2:  # More than 20% very close to mean
            inlier_data.append(
                {
                    "Column": col,
                    "Close Count": close_count,
                    "Total Count": len(clean_series),
                    "Percentage": f"{(close_count / len(clean_series)) * 100:.1f}%",
                    "Mean": f"{mean:.2f}",
                    "Std Dev": f"{std:.2f}",
                    "Range": f"[{mean - 0.1*std:.2f}, {mean + 0.1*std:.2f}]",
                    "Sample Values": ", ".join(str(x) for x in close_to_mean.head(3)),
                }
            )

    if inlier_data:
        # Create DataFrame
        results_df = pd.DataFrame(inlier_data)
        results_df = results_df.sort_values("Percentage", ascending=False)

        return {
            "issue_detected": True,
            "results_df": results_df,
            "inlier_info": {  # Keep for compatibility
                row["Column"]: {
                    "close_count": row["Close Count"],
                    "total_count": row["Total Count"],
                    "percentage": float(row["Percentage"].rstrip("%")),
                    "mean_value": float(row["Mean"]),
                    "std_dev": float(row["Std Dev"]),
                    "sample_values": row["Sample Values"].split(", "),
                }
                for _, row in results_df.iterrows()
            },
            "recommendation": "Inlier patterns detected. Review the table above for details.",
        }

    return {
        "issue_detected": False,
        "results_df": pd.DataFrame(),
        "inlier_info": {},
        "recommendation": "No significant inlier patterns detected.",
    }


def check_format_consistency(df: pd.DataFrame) -> Dict:
    """Check for format consistency issues in string/text columns."""
    format_data = []

    # Get string columns
    string_cols = df.select_dtypes(include=["object"]).columns

    for col in string_cols:
        if df[col].isna().all():
            continue

        string_values = df[col].astype(str).dropna()
        total_values = len(string_values)

        # Case Consistency Analysis
        case_patterns = {
            "lowercase": string_values.str.islower(),
            "uppercase": string_values.str.isupper(),
            "titlecase": string_values.str.istitle(),
            "mixed_case": ~(
                string_values.str.islower()
                | string_values.str.isupper()
                | string_values.str.istitle()
            ),
        }

        case_counts = {pattern: mask.sum() for pattern, mask in case_patterns.items()}
        active_patterns = [p for p, c in case_counts.items() if c > 0]

        if len(active_patterns) > 1:
            for pattern in active_patterns:
                format_data.append(
                    {
                        "Column": col,
                        "Issue Type": "Case Pattern",
                        "Pattern": pattern.replace("_", " ").title(),
                        "Count": case_counts[pattern],
                        "Percentage": f"{(case_counts[pattern] / total_values) * 100:.1f}%",
                        "Sample Values": ", ".join(
                            repr(x)
                            for x in string_values[case_patterns[pattern]].head(3)
                        ),
                    }
                )

        # Number Presence in Text
        if not pd.api.types.is_numeric_dtype(df[col]):
            has_numbers = string_values.str.contains(r"\d", regex=True)
            number_count = has_numbers.sum()

            if number_count > 0:
                format_data.append(
                    {
                        "Column": col,
                        "Issue Type": "Numbers in Text",
                        "Pattern": "Contains Numbers",
                        "Count": number_count,
                        "Percentage": f"{(number_count / total_values) * 100:.1f}%",
                        "Sample Values": ", ".join(
                            repr(x) for x in string_values[has_numbers].head(3)
                        ),
                    }
                )

        # Pattern Consistency Checks
        patterns = {
            "Email": r"^[\w\.-]+@[\w\.-]+\.\w+$",
            "Phone": r"^\+?[\d\-\(\)\s\.]+$",
            "Postal Code": r"^\d{5}(?:-\d{4})?$",
            "Date-like": r"\d{1,4}[-/\.]\d{1,2}[-/\.]\d{1,4}",
            "URL": r"^https?://\S+$",
        }

        for pattern_name, regex in patterns.items():
            matches = string_values.str.match(regex, na=False)
            match_count = matches.sum()
            non_match_count = len(string_values) - match_count

            if 0 < match_count < total_values:
                format_data.append(
                    {
                        "Column": col,
                        "Issue Type": "Format Inconsistency",
                        "Pattern": pattern_name,
                        "Count": non_match_count,  # Count non-matching as issues
                        "Percentage": f"{(non_match_count / total_values) * 100:.1f}%",
                        "Sample Values": (
                            f"Matching: {', '.join(repr(x) for x in string_values[matches].head(2))} | "
                            f"Non-matching: {', '.join(repr(x) for x in string_values[~matches].head(2))}"
                        ),
                    }
                )

    if format_data:
        # Create DataFrame with better column ordering
        results_df = pd.DataFrame(format_data)
        results_df = results_df.sort_values(
            ["Column", "Issue Type", "Count"], ascending=[True, True, False]
        )

        return {
            "issue_detected": True,
            "results_df": results_df,
            "recommendation": "Format consistency issues detected. Review the table above for details.",
        }

    return {
        "issue_detected": False,
        "results_df": pd.DataFrame(),
        "recommendation": "No format consistency issues detected.",
    }


def check_text_variations(df: pd.DataFrame) -> Dict:
    """Check for potential text variations and misspellings in string columns."""
    variation_data = []

    # Check string columns
    string_cols = df.select_dtypes(include=["object"]).columns

    for col in string_cols:
        if df[col].isna().all():
            continue

        # Get value counts and filter out rare values
        value_counts = df[col].value_counts()
        min_occurrences = max(
            2, len(df) * 0.001
        )  # At least 2 occurrences or 0.1% of data
        frequent_values = value_counts[value_counts >= min_occurrences]

        if len(frequent_values) < 2:
            continue

        # Find similar groups using LSH
        similar_groups = find_similar_groups(frequent_values, value_counts)

        if similar_groups:
            group_id = 0
            for group in similar_groups:
                group_id += 1
                total_count = sum(value_counts[value] for value in group)
                most_common = max(group, key=lambda x: value_counts[x])

                # Add row for the group summary
                variation_data.append(
                    {
                        "Column": col,
                        "Group": f"Group {group_id}",
                        "Value Type": "Group Summary",
                        "Total Variations": len(group),
                        "Total Occurrences": total_count,
                        "Most Common": most_common,
                        "Most Common Count": value_counts[most_common],
                        "Percentage": f"{(value_counts[most_common] / total_count) * 100:.1f}%",
                    }
                )

                # Add rows for each variation
                for value in sorted(group, key=lambda x: (-value_counts[x], x)):
                    if value != most_common:
                        variation_data.append(
                            {
                                "Column": col,
                                "Group": f"Group {group_id}",
                                "Value Type": "Variation",
                                "Total Variations": len(group),
                                "Total Occurrences": value_counts[value],
                                "Most Common": value,
                                "Most Common Count": value_counts[value],
                                "Percentage": f"{(value_counts[value] / total_count) * 100:.1f}%",
                            }
                        )

    if variation_data:
        # Create DataFrame with better structure
        results_df = pd.DataFrame(variation_data)
        results_df = results_df.sort_values(
            ["Column", "Group", "Value Type", "Most Common Count"],
            ascending=[True, True, False, False],
        )

        return {
            "issue_detected": True,
            "results_df": results_df,
            "recommendation": "Text variations detected. Review the table above for details.",
        }

    return {
        "issue_detected": False,
        "results_df": pd.DataFrame(),
        "recommendation": "No significant text variations detected.",
    }


def normalize_text(text: str) -> str:
    """Normalize text for comparison."""
    if not isinstance(text, str):
        return str(text)
    text = text.lower()
    text = re.sub(r"\s+", " ", text)
    text = re.sub(
        r"(?<!\w)[-.,](?!\w)|(?<=\w)[-.,](?!\w)|(?<=\w)[-.,](?!\w)", " ", text
    )
    return text.strip()


def find_similar_groups(frequent_values, value_counts):
    """Helper function to find groups of similar text values."""
    # Initialize LSH
    lsh = MinHashLSH(threshold=0.8, num_perm=128)
    minhashes = {}
    norm_to_orig = defaultdict(set)

    # First pass: collect normalized forms
    for value in frequent_values.index:
        norm_text = normalize_text(str(value))
        norm_to_orig[norm_text].add(value)

        # Create MinHash
        m = MinHash(num_perm=128)
        m.update(norm_text.encode("utf8"))
        for token in norm_text.split():
            m.update(token.encode("utf8"))
        minhashes[norm_text] = m

        try:
            lsh.insert(norm_text, m)
        except ValueError:
            continue

    # Find similar groups
    similar_groups = []
    processed = set()

    # Add groups from identical normalized forms
    for norm_text, orig_values in norm_to_orig.items():
        if len(orig_values) > 1:
            similar_groups.append(orig_values)
            processed.update([normalize_text(str(v)) for v in orig_values])

    # Find similar but not identical strings
    for norm_text, m in minhashes.items():
        if norm_text in processed:
            continue

        similar = lsh.query(m)
        if len(similar) > 1:
            group = set()
            for sim_text in similar:
                group.update(norm_to_orig[sim_text])

            if len(group) > 1:
                similar_groups.append(group)
                processed.update(similar)

    return similar_groups


def run_data_quality_checks(
    df: pd.DataFrame, summary_stats: Optional[Dict] = None
) -> Dict:
    """Run all data quality checks on the DataFrame."""
    logger.info("Starting data quality checks...")
    results = {}

    # Define all checks with their display names
    checks = [
        ("missing_values", "Checking Missing Values"),
        ("duplicates", "Checking Duplicates"),
        ("date_consistency", "Checking Date Consistency"),
        ("column_names", "Checking Column Names"),
        ("string_values", "Checking String Values"),
        ("special_characters", "Checking Special Characters"),
        ("data_types", "Checking Data Types"),
        ("outliers", "Checking Outliers"),
        ("statistical_quality", "Running Statistical Analysis"),
        ("inliers", "Checking Inliers"),
        ("format_consistency", "Checking Format Consistency"),
        ("text_variations", "Checking Text Variations"),
    ]

    total_checks = len(checks)
    logger.info(f"Total checks to run: {total_checks}")

    # Run each check
    for i, (check_name, display_name) in enumerate(checks, 1):
        logger.info(f"Running check {i}/{total_checks}: {display_name}")

        if check_name == "missing_values":
            results[check_name] = check_missing_values(df)
        elif check_name == "duplicates":
            results[check_name] = check_duplicates(df)
        elif check_name == "date_consistency":
            results[check_name] = check_date_consistency(df)
        elif check_name == "column_names":
            results[check_name] = check_column_names(df)
        elif check_name == "string_values":
            results[check_name] = check_string_values(df)
        elif check_name == "special_characters":
            results[check_name] = check_for_special_characters(df)
        elif check_name == "data_types":
            results[check_name] = check_data_types(df, summary_stats)
        elif check_name == "outliers":
            results[check_name] = check_outliers(df)
        elif check_name == "statistical_quality":
            results[check_name] = check_statistical_quality(df)
        elif check_name == "inliers":
            results[check_name] = check_inliers(df)
        elif check_name == "format_consistency":
            results[check_name] = check_format_consistency(df)
        elif check_name == "text_variations":
            results[check_name] = check_text_variations(df)

    logger.info("Data quality checks completed")
    return results
