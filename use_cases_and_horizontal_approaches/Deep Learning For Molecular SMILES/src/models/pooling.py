import math

import torch
import torch.nn as nn
from torch_geometric.utils import softmax

from ._scatter import scatter_add


class AttentionPooling(nn.Module):
    """Attention-based pooling for molecular graphs"""

    def __init__(self, hidden_dim, num_heads=1, dropout=0.1):
        super().__init__()
        self.hidden_dim = hidden_dim
        self.num_heads = num_heads
        self.head_dim = hidden_dim // num_heads

        assert hidden_dim % num_heads == 0, "hidden_dim must be divisible by num_heads"

        self.query = nn.Linear(hidden_dim, hidden_dim)
        self.key = nn.Linear(hidden_dim, hidden_dim)
        self.value = nn.Linear(hidden_dim, hidden_dim)

        self.dropout = nn.Dropout(dropout)
        self.scale = math.sqrt(self.head_dim)

    def forward(self, x, batch):
        batch_size = int(batch.max().item()) + 1
        num_nodes = x.size(0)
        H, d = self.num_heads, self.head_dim

        # Lay the heads out first: [N, hidden] -> [H, N, d]. Keeping the node
        # dimension inside (i.e. [N, H, d]) makes the matmul below produce
        # [N, H, H] and the softmax normalise across heads within one node,
        # which is not attention pooling at all.
        Q = self.query(x).view(num_nodes, H, d).transpose(0, 1)
        K = self.key(x).view(num_nodes, H, d).transpose(0, 1)
        V = self.value(x).view(num_nodes, H, d).transpose(0, 1)

        scores = torch.matmul(Q, K.transpose(-2, -1)) / self.scale  # [H, N, N]

        # A node may only attend to nodes of its own molecule.
        # NOTE: this materialises an [H, N, N] matrix — O(N²·H) memory. That is
        # cheap at this project's scale (batch of 16 molecules ≈ 320 nodes, 1
        # head), but it is the hot spot if batch_size or num_heads grow.
        same_graph = batch.unsqueeze(0) == batch.unsqueeze(1)  # [N, N]
        scores = scores.masked_fill(~same_graph.unsqueeze(0), float("-inf"))

        attn = torch.softmax(scores, dim=-1)  # over nodes of the same graph
        attn = self.dropout(attn)

        attended = torch.matmul(attn, V)  # [H, N, d]
        attended = attended.transpose(0, 1).reshape(num_nodes, self.hidden_dim)

        # Graph-level readout: mean over each graph's nodes. Done with scatter
        # rather than a Python loop so empty graphs still occupy their slot
        # (the old loop skipped them, which silently shifted every later graph).
        summed = scatter_add(attended, batch, dim=0, dim_size=batch_size)
        counts = scatter_add(
            torch.ones(num_nodes, 1, device=x.device, dtype=attended.dtype),
            batch,
            dim=0,
            dim_size=batch_size,
        )
        return summed / counts.clamp(min=1)


class GlobalAttentionPooling(nn.Module):
    """Global attention pooling with learnable query"""

    def __init__(self, hidden_dim, dropout=0.1):
        super().__init__()
        self.attention = nn.Sequential(
            nn.Linear(hidden_dim, hidden_dim), nn.Tanh(), nn.Linear(hidden_dim, 1)
        )
        self.dropout = nn.Dropout(dropout)

    def forward(self, x, batch):
        batch_size = batch.max().item() + 1
        attn_logits = self.attention(x).squeeze(-1)
        attn_weights = softmax(attn_logits, batch, dim=0)
        attn_weights = self.dropout(attn_weights.unsqueeze(-1))
        weighted_x = attn_weights * x
        pooled = scatter_add(weighted_x, batch, dim=0, dim_size=batch_size)
        return pooled


class SetToSetPooling(nn.Module):
    """Set2Set pooling for variable-size graphs"""

    def __init__(self, hidden_dim, num_iters=3, num_layers=1):
        super().__init__()
        self.hidden_dim = hidden_dim
        self.num_iters = num_iters

        self.lstm = nn.LSTM(2 * hidden_dim, hidden_dim, num_layers, batch_first=True)
        self.attention = nn.Linear(hidden_dim, hidden_dim)

    def forward(self, x, batch):
        batch_size = batch.max().item() + 1
        h = x.new_zeros(batch_size, self.hidden_dim)
        c = x.new_zeros(batch_size, self.hidden_dim)
        r = x.new_zeros(batch_size, self.hidden_dim)

        for _ in range(self.num_iters):
            h_expanded = h[batch]
            attn_input = self.attention(h_expanded)
            attn_logits = (x * attn_input).sum(dim=-1)
            attn_weights = softmax(attn_logits, batch, dim=0)

            r = scatter_add(attn_weights.unsqueeze(-1) * x, batch, dim=0, dim_size=batch_size)

            q_star = torch.cat([h, r], dim=-1).unsqueeze(1)
            _, (h, c) = self.lstm(q_star, (h.unsqueeze(0), c.unsqueeze(0)))
            h, c = h.squeeze(0), c.squeeze(0)

        return torch.cat([h, r], dim=-1)
