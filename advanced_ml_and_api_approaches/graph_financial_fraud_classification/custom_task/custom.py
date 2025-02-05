# -*- coding: utf-8 -*-
"""
Custom Hooks for Prediction
---------------------------

This module provides custom hooks for prediction when DRUM's standard assumptions are incorrect for your model.
It supports several hooks for custom inference code.

**Warning:** The code here is just for example purposes. Further hyperparameter selection and tuning are required.

Authors
-------
    - Ouadie GHARROUDI <ouadie.gharroudi@datarobot.com>
    - Elise Sainderichin <elise.sainderichin@datarobot.com>
    - Timothy Whittaker <timothy.whittaker@datarobot.com>
"""


import json
from pathlib import Path
import pickle
from typing import Any, Dict, List, Tuple

from GIN_model import GIN
import dgl
import pandas as pd
import torch
from torch.utils.data import DataLoader

# Section: Global Variables and Utility Functions
# ###############################################

DGL_COLUMN_NAME = "dgl_graph"


def graph_2_dgl(df: pd.DataFrame, graph_col: str) -> pd.DataFrame:
    """
    Converts a DataFrame with JSON-like graph data into a DataFrame with serialized DGL graphs.

    Parameters
    ----------
    df : pd.DataFrame
        Input DataFrame containing JSON graph structures.
    graph_col : str
        Name of the column storing graph JSON data.

    Returns
    -------
    pd.DataFrame
        DataFrame with a new column 'dgl_graph' containing Pickle-serialized DGLGraph objects.

    Raises
    ------
    ValueError
        If the required column is missing or data format is invalid.
    """
    if graph_col not in df.columns:
        raise ValueError(
            f"Missing required column '{graph_col}'. Available columns: {list(df.columns)}."
        )

    def process_row(row: str) -> bytes:
        try:
            graph_dict = json.loads(row)  # Ensure valid JSON
            edges = graph_dict.get("edges", [])
            if not isinstance(edges, list):
                raise ValueError("Invalid edges format. Expected a list of (u, v) tuples.")

            num_nodes = max(max(u, v) for u, v in edges) + 1 if edges else 0
            src, dst = zip(*edges) if edges else ([], [])

            g = dgl.graph((torch.tensor(src), torch.tensor(dst)), num_nodes=num_nodes)
            g.ndata["attr"] = torch.rand(
                num_nodes, 1
            )  # TODO: Replace with actual node features if available

            return pickle.dumps(g)
        except Exception as e:
            raise ValueError(f"Error processing graph row: {e}")

    df[DGL_COLUMN_NAME] = df[graph_col].apply(process_row)

    return df.drop(columns=[graph_col])


def graph_column_selector(dataframe: pd.DataFrame, graph_column_type: Any) -> str:
    """
    Selects the name of the column containing the graph data based on the type.

    Parameters
    ----------
    dataframe : pd.DataFrame
        The input DataFrame.
    graph_column_type : str, dict, or dgl.DGLGraph
        The type of the graph column. Can be a string, a dictionary, or a DGL graph.

    Returns
    -------
    str
        The name of the column containing the graph data.

    Raises
    ------
    ValueError
        If the graph_column_type is invalid.
    """
    return "graph"
    if graph_column_type == "dict":
        for column in dataframe.columns:
            if dataframe[column].apply(lambda x: isinstance(x, dict)).mean() >= 0.8:
                return column
    elif graph_column_type == "str":
        for column in dataframe.columns:
            try:
                json_data = json.loads(dataframe[column].iloc[0])
                if "vertices" in json_data and "edges" in json_data:
                    return column
            except (ValueError, TypeError):
                continue
    elif graph_column_type == dgl.DGLGraph:
        for column in dataframe.columns:
            if dataframe[column].apply(lambda x: isinstance(x, dgl.DGLGraph)).mean() >= 0.8:
                return column
    else:
        raise ValueError("Invalid graph_column_type provided.")
    raise ValueError("No suitable graph column found.")


def collate(samples: List[Any]) -> Tuple[dgl.DGLGraph, torch.Tensor]:
    """
    Collate function for DGL graphs, handling both labeled and unlabeled data.

    Parameters
    ----------
    samples : list
        A list of tuples (graph, label) for labeled data or a list of graphs for unlabeled data.

    Returns
    -------
    dgl.DGLGraph
        A batched graph of all input samples.
    torch.Tensor, optional
        Batched labels if labels are provided.
    """
    if not samples:
        raise ValueError("Empty sample batch received in collate function.")

    if isinstance(samples[0], tuple):  # Labeled data
        graphs, labels = map(list, zip(*samples))
        batched_graph = dgl.batch(graphs)
        batched_labels = torch.tensor(labels)
        return batched_graph, batched_labels
    else:  # Unlabeled data
        return dgl.batch(samples), None


# Section: DataRobot Custom Models Hooks
# ######################################


def load_model(code_dir: str) -> Any:
    """
    Loads the trained GIN model from the provided directory.

    This hook is used when the model requires multiple artifacts or is not natively supported by DRUM.

    Parameters
    ----------
    code_dir : str
        The directory where the model artifact and additional code are provided.

    Returns
    -------
    Any
        A loaded model object that will be used for scoring.

    Raises
    ------
    FileNotFoundError
        If the expected model file is missing.
    """
    model_path = Path(code_dir) / "gin_model"
    return GIN.load_model(model_path)


def transform(data: pd.DataFrame, model: Any) -> pd.DataFrame:
    """
    Transforms the input data before prediction by converting graphs to DGL format.

    This function is useful when additional preprocessing is required before making predictions.
    Specifically, it converts graph data from string format to DGL format.

    Parameters
    ----------
    data : pd.DataFrame
        DataFrame containing raw input data for prediction.
    model : Any
        The deserialized model object, loaded by `load_model`.

    Returns
    -------
    pd.DataFrame
        Transformed DataFrame with a serialized DGL graph column.
    """
    graph_column = graph_column_selector(data, "str")  # The expected column containing graph data
    return graph_2_dgl(data, graph_column)


def fit(X: pd.DataFrame, y: pd.Series, output_dir: str, **kwargs: Dict[str, Any]) -> None:
    """
    Trains the GIN model using the provided data and saves the trained model to the specified output directory.

    Parameters
    ----------
    X : pd.DataFrame
        DataFrame containing the input data with serialized DGL graphs.
    y : pd.Series
        Series containing the labels for the input data.
    output_dir : str
        Directory where the trained model will be saved.
    **kwargs : dict
        Additional keyword arguments (not used in this function).

    Raises
    ------
    ValueError
        If the output directory does not exist or is not a directory.
    """
    # Create datasets and dataloaders
    train_dataset = [
        (pickle.loads(graph_pickle), label) for graph_pickle, label in zip(X[DGL_COLUMN_NAME], y)
    ]
    train_loader = DataLoader(train_dataset, batch_size=8, shuffle=True, collate_fn=collate)

    # Initialize the GIN model
    model = GIN(
        num_layers=2,
        num_mlp_layers=2,
        input_dim=1,  # Each node has 1 feature
        hidden_dim=16,
        output_dim=2,  # Binary classification
        final_dropout=0.3,
        learn_eps=False,
        graph_pooling_type="sum",
        neighbor_pooling_type="sum",
    )
    optimizer = torch.optim.Adam(model.parameters(), lr=0.01)

    # Train the model
    print("=== Training the GIN model ===")
    model.fit(train_loader, optimizer, epochs=5, device="cpu")

    # Save the trained model
    output_dir_path = Path(output_dir)
    if output_dir_path.exists() and output_dir_path.is_dir():
        model.save_model(f"{output_dir}/gin_model")
    else:
        raise ValueError(f"Output directory '{output_dir}' does not exist or is not a directory.")


def score(data: pd.DataFrame, model: Any, **kwargs: Dict[str, Any]) -> pd.DataFrame:
    """
    Uses the trained model to predict class probabilities on new data.

    Parameters
    ----------
    data : pd.DataFrame
        DataFrame containing the input data with serialized DGL graphs.
    model : Any
        The trained model object.
    **kwargs : dict
        Additional keyword arguments (not used in this function).

    Returns
    -------
    pd.DataFrame
        DataFrame with two columns representing the probabilities for each class.
    """
    # Select the column containing serialized DGL graphs
    dgl_column = "dgl_graph"

    # Create dataset for prediction (no labels)
    prediction_dataset = [
        pickle.loads(graph_pickle) for graph_pickle in data[dgl_column]  # Deserialize each graph
    ]
    prediction_loader = DataLoader(
        prediction_dataset, batch_size=8, shuffle=False, collate_fn=collate
    )

    # Make the prediction
    preds, probs = model.predict(prediction_loader)
    return pd.DataFrame(probs, columns=["0", "1"])
