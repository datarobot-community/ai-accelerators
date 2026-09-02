import os
import random

import numpy as np
import torch

INPUT_PATH = "input/"
FEATURE_PATH = "feature/"
MODEL_PATH = "model/"
SUB_PATH = "sub/"


def seed_everything(seed=42):
    """Set random seeds for reproducible results across different libraries"""
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    torch.cuda.manual_seed(seed)
    torch.cuda.manual_seed_all(seed)
    torch.backends.cudnn.deterministic = True
    torch.backends.cudnn.benchmark = False
    os.environ["PYTHONHASHSEED"] = str(seed)

    try:
        import torch_geometric

        torch_geometric.seed_everything(seed)
    except ImportError:
        pass

    print(f"Random seed set to {seed} for reproducible results")
