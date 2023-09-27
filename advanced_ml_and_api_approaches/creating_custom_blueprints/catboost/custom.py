from pathlib import Path
import pickle
from typing import List, Optional

from catboost_pipeline import catboost_pipeline
import numpy as np
import pandas as pd
from sklearn.preprocessing import LabelEncoder


def fit(
    X: pd.DataFrame,
    y: pd.Series,
    output_dir: str,
    class_order: Optional[List[str]] = None,
    row_weights: Optional[np.ndarray] = None,
    **kwargs,
) -> None:
    estimator = catboost_pipeline(X)
    estimator.fit(X, y)

    output_dir_path = Path(output_dir)
    if output_dir_path.exists() and output_dir_path.is_dir():
        with open("{}/artifact.pkl".format(output_dir), "wb") as fp:
            pickle.dump(estimator, fp)


def score(data: pd.DataFrame, model, **kwargs) -> pd.DataFrame:
    return model.predict_proba(data)
