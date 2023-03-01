
from sklearn.pipeline import Pipeline
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
import numpy as np
import pandas as pd
from catboost import CatBoostClassifier
from typing import List, Optional
from feature_selection import DataSelector


class CatBoostClassifier_wrapper:
    """
    A wrapper is not required in typical cases, but is valuable for catboost
    it allows to automatically identify and pass categorical/text features
    to CatBoostClassifier.fit while working with DR custom tasks logic
    """

    model = None

    def model(self):
        return self.model

    def fit(self, X, y):
        data = pd.DataFrame(X, columns=map(str, range(len(X[0]))))
        cat_features = DataSelector.CatSelector(data)
        text_features = DataSelector.TxtSelector(data)
        self.model = CatBoostClassifier(
            allow_writing_files=False,
            #train_dir="catboost_info", 
            iterations=50
            ).fit(
            X, y, cat_features=cat_features, text_features=text_features
        )
        return self.model

    def predict_proba(self, data: pd.DataFrame):
        return pd.DataFrame(
            data=self.model.predict_proba(data), columns=self.model.classes_
        )


def catboost_pipeline(X):
    catboost_preprocessing = ColumnTransformer(
        transformers=[
            ("num", "passthrough", DataSelector.NumSelector),
            (
                "cat",
                SimpleImputer(strategy="constant", fill_value=""),
                DataSelector.CatSelector,
            ),
            # ("txt", SimpleImputer(strategy="constant", fill_value=""), DataSelector.TxtSelector),
        ],
        remainder="drop",
    )

    return Pipeline(
        steps=[
            ("preprocessing", catboost_preprocessing),
            ("model", CatBoostClassifier_wrapper()),
        ]
    )
