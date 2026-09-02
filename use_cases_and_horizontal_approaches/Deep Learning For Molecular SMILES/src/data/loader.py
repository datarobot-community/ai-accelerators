import os

import numpy as np
import pandas as pd
from rdkit import Chem

from .smiles_data import SMILESTokenizer


def _training_smiles(input_path, smiles_col="SMILES"):
    """Collect SMILES from ``train.csv`` only.

    The atom map and tokenizer must not see ``test.csv``: those rows are the
    held-out scoring set. ``valid.csv`` is no longer part of the layout (it was
    merged into train.csv) and is ignored here, matching :func:`load_split`.
    Unseen symbols at score time get an all-zero one-hot / ``<UNK>``.
    """
    path = os.path.join(input_path, "train.csv")
    df = pd.read_csv(path)
    return df[smiles_col].tolist()


def build_atom_map_from_smiles(smiles_iter):
    """Build atom map from any iterable of SMILES strings.

    Used by the notebook pipeline (via ``train.csv``) and by the DRUM
    ``custom.fit`` hook (via the in-memory training frame). Test SMILES never
    contribute atom types.
    """
    atoms_set = set()
    n_invalid = 0
    for s in smiles_iter:
        if not isinstance(s, str):
            n_invalid += 1
            continue
        try:
            mol = Chem.MolFromSmiles(s)
        except Exception:
            n_invalid += 1
            continue
        if mol is None:
            n_invalid += 1
            continue
        for atom in mol.GetAtoms():
            atoms_set.add(atom.GetSymbol())
    if n_invalid:
        # smiles_to_graph turns each of these into the same all-zero one-node
        # graph while keeping its real target, so the model is fit against
        # contradictory labels on an identical input. Say how many.
        print(
            f"WARNING: {n_invalid} SMILES could not be parsed by RDKit and will "
            f"featurize as empty graphs"
        )
    return {atom: idx for idx, atom in enumerate(sorted(atoms_set))}


def build_tokenizer_from_smiles(smiles_iter):
    """Fit a SMILESTokenizer on any iterable of SMILES strings."""
    print("Fitting tokenizer...")
    tokenizer = SMILESTokenizer()
    tokenizer.fit(list(smiles_iter))
    return tokenizer


def _smiles_col(cfg):
    return cfg.get("data", {}).get("smiles_column", "SMILES")


def load_split(cfg):
    """Load the train and test CSVs.

    There is no separate ``valid.csv`` any more - the old validation rows were
    merged into ``train.csv``. Carve a validation set out of the training frame
    with :func:`split_train_valid`.

    Returns:
        (train_df, test_df)
    """
    input_path = cfg["paths"]["input"]

    train_df = pd.read_csv(os.path.join(input_path, "train.csv"))
    test_df = pd.read_csv(os.path.join(input_path, "test.csv"))

    print(f"Loaded data from {input_path}:")
    print(f"  train: {len(train_df)}, test: {len(test_df)}")

    return train_df, test_df


def load_or_split(cfg):
    """Backwards-compatible alias for :func:`load_split`."""
    return load_split(cfg)


def split_train_valid(train_df, cfg, valid_ratio=None):
    """Randomly carve a validation set out of ``train_df``.

    Default ratio comes from ``cfg['data']['valid_ratio']`` (0.2 -> a 4:1
    train/valid split). The split is seeded with ``cfg['seed']`` so stage 1 of
    the notebook is reproducible.

    Returns:
        (sub_train_df, valid_df)
    """
    if valid_ratio is None:
        valid_ratio = cfg.get("data", {}).get("valid_ratio", 0.2)

    rng = np.random.RandomState(cfg.get("seed", 42))
    idx = rng.permutation(len(train_df))
    n_valid = int(round(len(train_df) * valid_ratio))

    valid_idx = idx[:n_valid]
    train_idx = idx[n_valid:]

    sub_train_df = train_df.iloc[train_idx].reset_index(drop=True)
    valid_df = train_df.iloc[valid_idx].reset_index(drop=True)

    print(
        f"Split train.csv {1 - valid_ratio:.0%}/{valid_ratio:.0%}: "
        f"train {len(sub_train_df)}, valid {len(valid_df)}"
    )

    return sub_train_df, valid_df


def build_atom_map(cfg):
    """Build atom map for GNN pipeline (honours data.smiles_column)."""
    return build_atom_map_from_smiles(_training_smiles(cfg["paths"]["input"], _smiles_col(cfg)))


def build_tokenizer(cfg):
    """Build and fit tokenizer for sequence pipeline (honours data.smiles_column)."""
    return build_tokenizer_from_smiles(_training_smiles(cfg["paths"]["input"], _smiles_col(cfg)))
