import numpy as np
import pandas as pd


def is_numeric(x: pd.Series):
    try:
        sum(x)
        return True
    except:
        return False


# Helper function to use in text_selector
def is_text(x: pd.Series):
    """
    Decide if a pandas series is text, using a very simple heuristic:
    - Count the number of elements in the series that contain 1 or more whitespace character
    - If >75% of the elements have whitespace and # unique / # all values >0.1, the Series is text.
    - If # unique / # all values >0.8 then the series is text
    otherwise - non-text
    Parameters
    ----------
    x: Series to be analyzed for text
    Returns
    -------
    boolean: True for is text, False for not text
    """
    if pd.api.types.is_string_dtype(x):
        x_values = x.dropna()
        pct_rows_with_whitespace = (
            x_values.str.count(r"\s") > 0
        ).sum() / x_values.shape[0]
        pct_unique = float(x_values.unique().shape[0]) / x_values.shape[0]
        if pct_unique > 0.8:
            return True
        if pct_rows_with_whitespace > 0.75 and pct_unique > 0.1:
            return True
    return False


def is_datetime(x: pd.Series):
    if x.dtype != np.object:
        return False

    try:
        pd.to_datetime(x)
        return True
    except:
        return False


def get_columns_by_type(X: pd.DataFrame):
    """ "
    Creates a dictionary with a list of features for each data type
    """
    data = X.copy()
    dict = {}
    dict["num"] = data.columns[
        list(data.apply(is_numeric, result_type="expand"))
    ].tolist()
    data.drop(dict["num"], axis=1, inplace=True)

    dict["txt"] = data.columns[list(data.apply(is_text, result_type="expand"))].tolist()
    data.drop(dict["txt"], axis=1, inplace=True)

    dict["dat"] = data.columns[
        list(data.apply(is_datetime, result_type="expand"))
    ].tolist()
    data.drop(dict["dat"], axis=1, inplace=True)

    dict["cat"] = data.columns.tolist()
    return dict


class DataSelector:
    """
    Valueable for catboost
    Each method returns a list of column indices for a specific data type
    """

    def NumSelector(X: pd.DataFrame):
        return [X.columns.get_loc(c) for c in get_columns_by_type(X)["num"]]

    def CatSelector(X: pd.DataFrame):
        return [X.columns.get_loc(c) for c in get_columns_by_type(X)["cat"]]

    def TxtSelector(X: pd.DataFrame):
        return [X.columns.get_loc(c) for c in get_columns_by_type(X)["txt"]]
