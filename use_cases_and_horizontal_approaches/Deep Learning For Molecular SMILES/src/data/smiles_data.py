import math

from rdkit import Chem
import torch
from torch.utils.data import Dataset


class SMILESTokenizer:
    """Character-level SMILES tokenizer based on unique characters in dataset"""

    def __init__(self):
        self.special_tokens = {"<PAD>": 0, "<UNK>": 1, "<START>": 2, "<END>": 3}
        self.char_to_idx = self.special_tokens.copy()
        self.idx_to_char = {v: k for k, v in self.special_tokens.items()}

    def tokenize(self, smiles):
        """Tokenize SMILES string into characters"""
        return list(smiles)

    @staticmethod
    def _coerce_smiles(smiles):
        """Map missing / non-string values to '' so encode() never crashes.

        Graph featurization already returns a dummy graph for non-strings (NaN,
        None, pd.NA). Sequence scoring must do the same: DataRobot's custom
        model test injects nulls, and ``Series.tolist()`` turns them into
        ``float('nan')``, which ``list(nan)`` raises TypeError on.
        """
        return smiles if isinstance(smiles, str) else ""

    def fit(self, smiles_list):
        """Build vocabulary from unique characters in SMILES strings"""
        unique_chars = set()
        valid_count = 0
        for smi in smiles_list:
            if not isinstance(smi, str):
                continue
            try:
                mol = Chem.MolFromSmiles(smi)
            except Exception:
                continue
            if mol is None:
                continue
            unique_chars.update(set(smi))
            valid_count += 1

        print(f"Found {len(unique_chars)} unique characters in {valid_count} valid SMILES")
        print(f"Unique characters: {sorted(unique_chars)}")

        # Continue past whatever is already mapped rather than restarting at
        # len(special_tokens): re-fitting the same instance would otherwise
        # hand an id that is already taken to the first new character, so two
        # characters would share one embedding row.
        idx = max(self.char_to_idx.values()) + 1 if self.char_to_idx else 0
        for char in sorted(unique_chars):
            if char not in self.char_to_idx:
                self.char_to_idx[char] = idx
                self.idx_to_char[idx] = char
                idx += 1

        print(f"Vocabulary size: {len(self.char_to_idx)}")
        return self

    def encode(self, smiles, max_length=None):
        """Convert SMILES to character indices"""
        smiles = self._coerce_smiles(smiles)
        chars = self.tokenize(smiles)
        indices = [self.special_tokens["<START>"]]
        for char in chars:
            if char in self.char_to_idx:
                indices.append(self.char_to_idx[char])
            else:
                indices.append(self.special_tokens["<UNK>"])
        indices.append(self.special_tokens["<END>"])

        if max_length:
            if len(indices) > max_length:
                indices = indices[: max_length - 1] + [self.special_tokens["<END>"]]
            else:
                indices.extend([self.special_tokens["<PAD>"]] * (max_length - len(indices)))
        return indices

    def decode(self, indices):
        """Convert character indices back to SMILES"""
        chars = []
        for idx in indices:
            if idx in self.idx_to_char:
                char = self.idx_to_char[idx]
                if char not in ["<PAD>", "<START>", "<END>", "<UNK>"]:
                    chars.append(char)
        return "".join(chars)


class SMILESDataset(Dataset):
    """Dataset for SMILES sequences"""

    def __init__(self, smiles_list, targets=None, tokenizer=None, max_length=200):
        self.smiles_list = smiles_list
        self.targets = targets
        self.tokenizer = tokenizer
        self.max_length = max_length
        # Reject unusable labels up front. A blank Tc cell arrives as NaN,
        # which torch happily wraps in a tensor; the first batch containing it
        # NaNs every weight and the run only fails later, inside sklearn, with
        # no hint that one empty cell caused it.
        if targets is not None:
            for i, t in enumerate(targets):
                try:
                    t_float = float(t)
                except (TypeError, ValueError):
                    raise ValueError(f"Target at row {i} is not numeric: {t!r}")
                if not math.isfinite(t_float):
                    raise ValueError(f"Target at row {i} is not finite: {t!r}")
        # START + SMILES + END must fit in max_length; anything longer is
        # silently truncated by encode() and can drop chemically important
        # tails (e.g. a polymer attachment point). Warn once at construction.
        n_trunc = 0
        longest = 0
        for s in smiles_list:
            n = len(s) if isinstance(s, str) else 0
            if n > longest:
                longest = n
            if n + 2 > max_length:
                n_trunc += 1
        if n_trunc:
            print(
                f"WARNING: {n_trunc} SMILES exceed max_length={max_length} "
                f"(longest string is {longest} chars, needs {longest + 2} "
                f"tokens with <START>/<END>) and will be truncated"
            )

    def __len__(self):
        return len(self.smiles_list)

    def __getitem__(self, idx):
        smiles = self.smiles_list[idx]
        encoded = self.tokenizer.encode(smiles, self.max_length)
        encoded_tensor = torch.tensor(encoded, dtype=torch.long)
        if self.targets is not None:
            target = torch.tensor([float(self.targets[idx])], dtype=torch.float)
            return encoded_tensor, target
        else:
            return encoded_tensor
