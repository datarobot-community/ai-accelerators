import math

import torch
import torch.nn as nn
import torch.nn.functional as F

# Upper bound for the cached positional table. data.max_length is 200 in the
# shipped config; the table is sliced to the batch's actual length.
_MAX_POSITIONS = 5000


def _sinusoidal_positional_encoding(max_positions, dim):
    """Standard fixed sin/cos positional encoding, shape [max_positions, dim]."""
    position = torch.arange(max_positions, dtype=torch.float).unsqueeze(1)
    div_term = torch.exp(torch.arange(0, dim, 2, dtype=torch.float) * (-math.log(10000.0) / dim))
    pe = torch.zeros(max_positions, dim)
    pe[:, 0::2] = torch.sin(position * div_term)
    # An odd embedding_dim leaves one fewer cosine column than sine column.
    pe[:, 1::2] = torch.cos(position * div_term)[:, : pe[:, 1::2].size(1)]
    return pe


class SequenceNN(nn.Module):
    """
    Configurable sequence-based model for property prediction.
    Supports LSTM, CNN, Transformer, or combinations.
    """

    def __init__(
        self,
        vocab_size,
        embedding_dim=128,
        hidden_dim=256,
        num_layers=2,
        num_heads=8,
        dropout=0.2,
        use_lstm=True,
        use_cnn=True,
        use_transformer=True,
        cnn_kernels=[2],
        pooling="mean",
    ):
        super(SequenceNN, self).__init__()

        self.embedding_dim = embedding_dim
        self.hidden_dim = hidden_dim
        self.use_lstm = use_lstm
        self.use_cnn = use_cnn
        self.use_transformer = use_transformer
        self.pooling = pooling
        # `model.pooling` is one config key shared with the graph pipeline, so
        # a graph-only value like `attention` reaches here. Say what happens
        # instead of quietly routing to a different mode in each branch.
        if pooling not in ("mean", "max", "last"):
            print(
                f"WARNING: pooling={pooling!r} is not a sequence pooling mode "
                f"(mean | max | last); using mean"
            )

        self.embedding = nn.Embedding(vocab_size, embedding_dim, padding_idx=0)
        self.dropout = nn.Dropout(dropout)

        feature_dims = []

        if self.use_lstm:
            # nn.LSTM's dropout only applies between stacked layers; with a
            # single layer it is a no-op and torch warns about it. Pass 0 in
            # that case - behaviour is identical, the warning goes away.
            self.lstm = nn.LSTM(
                embedding_dim,
                hidden_dim,
                num_layers,
                batch_first=True,
                dropout=dropout if num_layers > 1 else 0.0,
                bidirectional=True,
            )
            feature_dims.append(hidden_dim * 2)

        if self.use_cnn:
            self.conv1d_layers = nn.ModuleList(
                [
                    nn.Conv1d(embedding_dim, hidden_dim, kernel_size=k, padding=k // 2)
                    for k in cnn_kernels
                ]
            )
            feature_dims.append(hidden_dim * len(cnn_kernels))

        if self.use_transformer:
            encoder_layer = nn.TransformerEncoderLayer(
                d_model=embedding_dim,
                nhead=num_heads,
                dim_feedforward=hidden_dim * 2,
                dropout=dropout,
                batch_first=True,
            )
            # Nested-tensor fast path + padding masks has been wrong in several
            # 2.x releases (PAD positions leak into the representation). Force
            # the dense path; TypeError covers torch builds that lack the kwarg.
            try:
                self.transformer = nn.TransformerEncoder(
                    encoder_layer, num_layers=num_layers, enable_nested_tensor=False
                )
            except TypeError:
                self.transformer = nn.TransformerEncoder(encoder_layer, num_layers=num_layers)
            # nn.TransformerEncoderLayer carries no notion of position, and
            # self-attention plus the masked-mean readout below are both
            # permutation-invariant - so without this the branch scores any
            # anagram of a SMILES identically, i.e. it is a bag of characters
            # and ring-closure/branch order (the actual connectivity) is
            # invisible. Sinusoidal rather than learned so it adds no
            # parameters and existing checkpoints keep loading.
            self.register_buffer(
                "positional_encoding",
                _sinusoidal_positional_encoding(_MAX_POSITIONS, embedding_dim),
                persistent=False,
            )
            self.attention = nn.MultiheadAttention(
                embedding_dim, num_heads, dropout=dropout, batch_first=True
            )
            feature_dims.append(embedding_dim)

        total_features = sum(feature_dims)
        if total_features == 0:
            raise ValueError("At least one of use_lstm, use_cnn, or use_transformer must be True")

        self.feature_fusion = nn.Sequential(
            nn.Linear(total_features, hidden_dim * 2),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(hidden_dim * 2, hidden_dim),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(hidden_dim, 1),
        )

        print(
            f"Model initialized with: LSTM={use_lstm}, CNN={use_cnn}, "
            f"Transformer={use_transformer}, Total features={total_features}"
        )

    def forward(self, x):
        padding_mask = x == 0

        # Guard against fully padded rows. SMILESTokenizer.encode() always emits
        # <START> and <END>, so such a row cannot come from the normal pipeline -
        # but a caller handing raw tensors can produce one, and a fully masked row
        # makes nn.TransformerEncoder crash (or emit NaN, depending on the code
        # path) and the LSTM mean pooling divide by zero. Unmasking position 0
        # computes on the PAD embedding, which is the zero vector (padding_idx=0):
        # a deterministic "empty molecule" representation, mirroring the
        # zero-graph fallback of the graph pipeline. Real rows are untouched.
        all_pad = padding_mask.all(dim=1)
        if all_pad.any():
            padding_mask[all_pad, 0] = False

        embedded = self.embedding(x)
        embedded = self.dropout(embedded)

        features = []

        if self.use_lstm:
            # Pack so the recurrence never runs over PAD. Without packing, the
            # backward direction of the bidirectional LSTM starts inside the
            # padding, so hidden states at *real* positions - and therefore the
            # pooled features - depend on how much padding follows the sequence.
            lengths = (~padding_mask).sum(dim=1).cpu()
            packed = nn.utils.rnn.pack_padded_sequence(
                embedded, lengths, batch_first=True, enforce_sorted=False
            )
            lstm_out, _ = self.lstm(packed)
            lstm_out, _ = nn.utils.rnn.pad_packed_sequence(
                lstm_out, batch_first=True, total_length=x.size(1)
            )
            mask_expanded = padding_mask.unsqueeze(-1).expand_as(lstm_out)
            if self.pooling == "max":
                # pad_packed_sequence zeroes PAD positions, but LSTM outputs
                # can be negative: max(real, 0_pad) is not max(real). Fill
                # PAD with -inf so a short SMILES is not length-biased.
                lstm_features = lstm_out.masked_fill(mask_expanded, float("-inf")).max(dim=1).values
            elif self.pooling == "last":
                # The LSTM is bidirectional, so lstm_out is [B, L, 2*hidden]:
                # the forward half has consumed the whole sequence at
                # lengths-1, but the backward half runs from the end, so its
                # full-sequence state is at position 0. Taking lengths-1 for
                # both halves left the backward half as the state after a
                # single token - and since encode() always emits <END> last,
                # that was the SAME constant for every molecule.
                lengths = (~padding_mask).sum(dim=1)
                forward, backward = lstm_out.chunk(2, dim=-1)
                last_forward = forward[torch.arange(forward.size(0), device=x.device), lengths - 1]
                lstm_features = torch.cat([last_forward, backward[:, 0]], dim=-1)
            else:
                lstm_masked = lstm_out.masked_fill(mask_expanded, 0)
                lstm_features = (
                    lstm_masked.sum(dim=1) / (~padding_mask).sum(dim=1, keepdim=True).float()
                )
            features.append(lstm_features)

        if self.use_cnn:
            cnn_features = []
            embedded_t = embedded.transpose(1, 2)
            # PAD embeddings are zero vectors, but conv bias + ReLU turn every
            # PAD position into a nonzero constant. Zero / -inf those positions
            # so mean and max never see them. `last` indexes the final real
            # token instead, matching the LSTM branch - previously `last` fell
            # through to mean and the documented pooling mode was a no-op.
            conv_mask = padding_mask.unsqueeze(1)  # [B, 1, L]
            n_real = (~padding_mask).sum(dim=1, keepdim=True).float().clamp(min=1)
            last_idx = n_real.squeeze(1).long() - 1
            batch_idx = torch.arange(embedded.size(0), device=x.device)
            for conv_layer in self.conv1d_layers:
                conv_out = F.relu(conv_layer(embedded_t))
                # Even kernel sizes with padding=k//2 emit L+1 positions; the
                # extra one is a window fully inside the right padding - drop it
                # so the mask lines up.
                conv_out = conv_out[..., : x.size(1)]
                if self.pooling == "max":
                    # ReLU makes this equivalent to filling 0 today, but
                    # filling -inf is the length-invariant max regardless of
                    # the activation (same bug the LSTM branch had).
                    pooled = conv_out.masked_fill(conv_mask, float("-inf")).max(dim=-1).values
                elif self.pooling == "last":
                    pooled = conv_out[batch_idx, :, last_idx]
                else:
                    conv_out = conv_out.masked_fill(conv_mask, 0)
                    pooled = conv_out.sum(dim=-1) / n_real
                cnn_features.append(pooled)
            cnn_features = torch.cat(cnn_features, dim=1)
            features.append(cnn_features)

        if self.use_transformer:
            seq_len = x.size(1)
            if seq_len > self.positional_encoding.size(0):
                raise ValueError(
                    f"sequence length {seq_len} exceeds the positional encoding "
                    f"table ({self.positional_encoding.size(0)})"
                )
            positioned = embedded + self.positional_encoding[:seq_len].unsqueeze(0)
            transformer_out = self.transformer(positioned, src_key_padding_mask=padding_mask)
            mask_expanded = padding_mask.unsqueeze(-1).expand_as(transformer_out)
            if self.pooling == "max":
                transformer_features = (
                    transformer_out.masked_fill(mask_expanded, float("-inf")).max(dim=1).values
                )
            elif self.pooling == "last":
                lengths = (~padding_mask).sum(dim=1)
                transformer_features = transformer_out[
                    torch.arange(transformer_out.size(0), device=x.device), lengths - 1
                ]
            else:
                # Masked mean for the attention query. A plain mean(dim=1)
                # would average PAD positions too, so short SMILES would be
                # dominated by padding and the representation would carry
                # sequence length instead of chemistry.
                transformer_masked = transformer_out.masked_fill(mask_expanded, 0)
                n_real = (~padding_mask).sum(dim=1, keepdim=True).float().clamp(min=1)
                query = (transformer_masked.sum(dim=1) / n_real).unsqueeze(1)
                attended_out, _ = self.attention(
                    query, transformer_out, transformer_out, key_padding_mask=padding_mask
                )
                transformer_features = attended_out.squeeze(1)
            features.append(transformer_features)

        combined_features = torch.cat(features, dim=1)
        output = self.feature_fusion(combined_features)
        return output
