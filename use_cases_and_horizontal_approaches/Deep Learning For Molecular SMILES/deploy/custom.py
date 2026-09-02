"""DataRobot DRUM hooks for SMILES regression — flat-layout edition.

Structurally modeled on
task_templates/3_pipelines/11_python3_pytorch_regression in datarobot-user-models,
but with the entire inference dependency tree flattened into model_lib.py so
the DataRobot upload UI can't drop any subdirectories on the floor.

Files expected in /opt/code after upload:
    custom.py            (this file)
    model_lib.py         (auto-generated from src/ by deploy.ipynb section 4)
    model-metadata.yaml
    smiles_model.pth     (the trained bundle)

Local usage:
    drum fit \\
        --code-dir . \\
        --input input/train.csv \\
        --target-type regression \\
        --target Tc \\
        --output /tmp/drum_out
"""

from __future__ import annotations

# DataRobot's container runs as uid=1000 with no /etc/passwd entry, so
# `getpass.getuser()` raises KeyError. torch._dynamo eagerly initializes a
# disk cache dir at import time and calls getuser() — so we have to set these
# env vars BEFORE any torch / torch_geometric import below.
import os

os.environ.setdefault("USER", "drum")
os.environ.setdefault("HOME", "/tmp")
os.environ.setdefault("TORCHINDUCTOR_CACHE_DIR", "/tmp/torchinductor")

from pathlib import Path  # noqa: E402
from typing import Any, Dict, List, Optional  # noqa: E402

from model_lib import (  # noqa: E402
    _parse_model_type,
    _predict_with_bundle,
    ARTIFACT_NAME,
    build_atom_map_from_smiles,
    load_bundle,
    run_train,
    run_train_full,
    seed_everything,
    smiles_to_graph,
    SMILESDataset,
    SMILESTokenizer,
    split_train_valid,
)
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
import torch  # noqa: E402

# Inlined config — was previously read from config/config.yaml, but DataRobot's
# upload UI sometimes drops subdirectories. Inlining means deployment needs
# nothing but the four root files.
DEFAULT_CFG: Dict[str, Any] = {
    "seed": 42,
    "target": "Tc",
    "paths": {
        "input": "input/",
        "model": "model/",
        "artifact_name": "smiles_model.pth",
        "stage1_artifact_name": "smiles_model_stage1.pth",
    },
    "data": {
        "smiles_column": "SMILES",
        "max_length": 200,
        "valid_ratio": 0.2,
    },
    "model": {
        # Keep in sync with `model.type` in config/config.yaml by hand: that file
        # is not part of the DRUM upload set, so it cannot be read here. Only the
        # `drum fit` path uses these values - deployed scoring reads the cfg
        # stored inside model/smiles_model.pth.
        "type": "dmpnn",
        "hidden_dim": 300,
        "dropout": 0.1,
        "pooling": "mean",
        "dmpnn": {
            "depth": 2,
            "activation": "PReLU",
            "undirected": False,
            "ffn_hidden_size": 300,
            "ffn_num_layers": 3,
            "use_layer_norm": False,
            "use_batch_norm": False,
            "use_message_residual": True,
            "use_ffn_residual": False,
        },
        "sequence": {
            "embedding_dim": 128,
            "num_layers": 1,
            "num_heads": 4,
            "cnn_kernels": [3],
        },
    },
    "training": {
        "epochs": 400,
        "batch_size_train": 16,
        "batch_size_valid": 64,
        "batch_size_test": 128,
        "lr": 0.001,
        "scheduler": {"factor": 0.5, "patience": 20, "min_lr": 1.0e-6},
        "early_stopping": {"patience": 200, "min_delta": 0.00001},
        "criterion": "L1Loss",
    },
}


def _deepcopy_cfg() -> Dict[str, Any]:
    import copy

    return copy.deepcopy(DEFAULT_CFG)


def fit(
    X: pd.DataFrame,
    y: pd.Series,
    output_dir: str,
    class_order: Optional[List[str]] = None,
    row_weights: Optional[np.ndarray] = None,
    **kwargs,
) -> None:
    """DRUM training hook. Trains on (X, y) and writes a bundle to output_dir."""
    if class_order is not None:
        raise ValueError("regression task; got class_order=" + str(class_order))

    cfg = _deepcopy_cfg()
    seed_everything(cfg["seed"])

    smiles_col = cfg["data"]["smiles_column"]
    if smiles_col not in X.columns:
        raise ValueError(f"Expected SMILES column '{smiles_col}' in X. Got: {list(X.columns)}")

    target_col = y.name if y.name is not None else cfg["target"]
    cfg["target"] = target_col
    cfg["paths"]["model"] = str(output_dir)

    df = X[[smiles_col]].copy()
    df[target_col] = np.asarray(y.values, dtype=float)
    # Same splitter as train.ipynb (seeded permutation, not sklearn), then the
    # same two-stage schedule: holdout to find best_epoch, refit on all of X
    # for that many epochs replaying stage 1's LR trajectory.
    train_df, valid_df = split_train_valid(df, cfg)

    is_graph, _ = _parse_model_type(cfg["model"]["type"])
    all_smiles = df[smiles_col].tolist()

    atom_map = None
    tokenizer = None
    if is_graph:
        atom_map = build_atom_map_from_smiles(all_smiles)
        train_data = [
            smiles_to_graph(row[smiles_col], atom_map, row[target_col])
            for _, row in train_df.iterrows()
        ]
        valid_data = [
            smiles_to_graph(row[smiles_col], atom_map, row[target_col])
            for _, row in valid_df.iterrows()
        ]
        full_data = [
            smiles_to_graph(row[smiles_col], atom_map, row[target_col]) for _, row in df.iterrows()
        ]
        stage1_data_list = train_data
        full_data_list = full_data
    else:
        tokenizer = SMILESTokenizer().fit(all_smiles)
        ml = cfg["data"]["max_length"]
        train_data = SMILESDataset(
            train_df[smiles_col].tolist(),
            train_df[target_col].tolist(),
            tokenizer,
            max_length=ml,
        )
        valid_data = SMILESDataset(
            valid_df[smiles_col].tolist(),
            valid_df[target_col].tolist(),
            tokenizer,
            max_length=ml,
        )
        full_data = SMILESDataset(
            df[smiles_col].tolist(),
            df[target_col].tolist(),
            tokenizer,
            max_length=ml,
        )
        stage1_data_list = None
        full_data_list = None

    stage1_name = cfg["paths"].get("stage1_artifact_name", "smiles_model_stage1.pth")
    artifact_name = cfg["paths"].get("artifact_name", ARTIFACT_NAME)

    stage1 = run_train(
        train_data,
        valid_data,
        cfg,
        data_list=stage1_data_list,
        tokenizer=tokenizer,
        atom_map=atom_map,
        artifact_name=stage1_name,
    )
    result = run_train_full(
        full_data,
        cfg,
        epochs=stage1["best_epoch"],
        data_list=full_data_list,
        tokenizer=tokenizer,
        atom_map=atom_map,
        lr_schedule=stage1["lr_history"],
        artifact_name=artifact_name,
    )
    print(f"Saved DRUM artifact: {result['best_model_path']}")


def load_model(code_dir: str) -> Dict[str, Any]:
    """DRUM model-loading hook. Returns the bundle dict produced by fit()."""
    return load_bundle(Path(code_dir) / ARTIFACT_NAME)


def score(data: pd.DataFrame, model: Any, **kwargs: Dict[str, Any]) -> pd.DataFrame:
    """DRUM scoring hook. Returns a single-column 'Predictions' DataFrame."""
    bundle = model
    smiles_col = bundle["smiles_col"]
    if smiles_col not in data.columns:
        raise ValueError(
            f"Scoring input is missing SMILES column '{smiles_col}'. " f"Got: {list(data.columns)}"
        )
    preds = _predict_with_bundle(data[smiles_col].tolist(), bundle)
    return pd.DataFrame({"Predictions": preds})
