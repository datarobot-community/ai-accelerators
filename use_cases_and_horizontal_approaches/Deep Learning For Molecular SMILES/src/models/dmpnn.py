import torch
import torch.nn as nn
from torch_geometric.nn import global_add_pool, global_max_pool, global_mean_pool

from ._scatter import scatter_add
from .pooling import AttentionPooling, GlobalAttentionPooling, SetToSetPooling

_GRAPH_POOLING_MODES = (
    "mean",
    "max",
    "sum",
    "attention",
    "global_attention",
    "set2set",
)


class EnhancedChemPropDMPNN(nn.Module):
    """Enhanced ChemPropDMPNN with normalization and attention pooling"""

    def __init__(
        self,
        atom_fdim,
        bond_fdim,
        hidden_size=300,
        depth=3,
        dropout=0.0,
        activation="ReLU",
        undirected=False,
        ffn_hidden_size=300,
        ffn_num_layers=2,
        output_size=1,
        use_layer_norm=True,
        use_batch_norm=False,
        use_message_residual=True,
        use_ffn_residual=True,
        pooling="attention",
        attention_heads=4,
        set2set_iters=3,
        init_type="xavier_uniform",
        init_gain=1.0,
        bias_init="zeros",
    ):
        super(EnhancedChemPropDMPNN, self).__init__()

        self.atom_fdim = atom_fdim
        self.bond_fdim = bond_fdim
        self.hidden_size = hidden_size
        self.depth = depth
        self.dropout = dropout
        self.undirected = undirected
        self.use_layer_norm = use_layer_norm
        self.use_batch_norm = use_batch_norm
        self.use_message_residual = use_message_residual
        self.use_ffn_residual = use_ffn_residual

        self.init_type = init_type
        self.init_gain = init_gain
        self.bias_init = bias_init

        if pooling not in _GRAPH_POOLING_MODES:
            print(
                f"WARNING: pooling={pooling!r} is not a graph pooling mode "
                f"(mean | max | sum | attention | global_attention | set2set); "
                f"using mean"
            )
            pooling = "mean"
        self.pooling = pooling

        self.activation = _get_activation(activation)

        self.W_i = nn.Linear(atom_fdim + bond_fdim, hidden_size)

        self.message_layers = nn.ModuleList()
        self.update_layers = nn.ModuleList()
        self.layer_norms = nn.ModuleList()
        self.batch_norms = nn.ModuleList()

        # ChemProp does depth-1 directed message steps, then one atom readout.
        # Allocating `depth` message Linears left message_layers[depth-1] unused
        # but still in the state_dict.
        for _ in range(max(depth - 1, 0)):
            self.message_layers.append(nn.Linear(hidden_size, hidden_size))
        for _ in range(depth):
            self.update_layers.append(nn.Linear(atom_fdim + hidden_size, hidden_size))
            if use_layer_norm:
                self.layer_norms.append(nn.LayerNorm(hidden_size))
            if use_batch_norm:
                self.batch_norms.append(nn.BatchNorm1d(hidden_size))

        if pooling == "attention":
            self.pooling_layer = AttentionPooling(hidden_size, attention_heads, dropout)
            pool_output_dim = hidden_size
        elif pooling == "global_attention":
            self.pooling_layer = GlobalAttentionPooling(hidden_size, dropout)
            pool_output_dim = hidden_size
        elif pooling == "set2set":
            self.pooling_layer = SetToSetPooling(hidden_size, set2set_iters)
            pool_output_dim = 2 * hidden_size
        else:
            self.pooling_layer = None
            pool_output_dim = hidden_size

        self.dropout_layer = nn.Dropout(dropout)

        self.ffn_num_layers = ffn_num_layers
        if ffn_num_layers == 1:
            self.ffn = nn.Sequential(nn.Dropout(dropout), nn.Linear(pool_output_dim, output_size))
            self.ffn_layers = None
            self.ffn_norms = None
        else:
            self.ffn_input = nn.Linear(pool_output_dim, ffn_hidden_size)
            self.ffn_layers = nn.ModuleList()
            self.ffn_layer_norms = nn.ModuleList()
            self.ffn_batch_norms = nn.ModuleList()
            for i in range(ffn_num_layers - 2):
                self.ffn_layers.append(nn.Linear(ffn_hidden_size, ffn_hidden_size))
                if use_layer_norm:
                    self.ffn_layer_norms.append(nn.LayerNorm(ffn_hidden_size))
                if use_batch_norm:
                    self.ffn_batch_norms.append(nn.BatchNorm1d(ffn_hidden_size))
            self.ffn_output = nn.Linear(ffn_hidden_size, output_size)

        self.apply(self._init_weights)

    def _init_weights(self, module):
        if isinstance(module, nn.Linear):
            if self.init_type == "xavier_uniform":
                nn.init.xavier_uniform_(module.weight, gain=self.init_gain)
            elif self.init_type == "xavier_normal":
                nn.init.xavier_normal_(module.weight, gain=self.init_gain)
            elif self.init_type == "kaiming_uniform":
                nn.init.kaiming_uniform_(module.weight, mode="fan_in", nonlinearity="relu")
            elif self.init_type == "kaiming_normal":
                nn.init.kaiming_normal_(module.weight, mode="fan_in", nonlinearity="relu")
            elif self.init_type == "orthogonal":
                nn.init.orthogonal_(module.weight, gain=self.init_gain)
            else:
                nn.init.xavier_uniform_(module.weight, gain=self.init_gain)
            if module.bias is not None:
                if self.bias_init == "zeros":
                    nn.init.zeros_(module.bias)
                elif self.bias_init == "ones":
                    nn.init.ones_(module.bias)
                else:
                    nn.init.zeros_(module.bias)

    def forward(self, data):
        x, edge_index, edge_attr = data.x, data.edge_index, data.edge_attr
        batch = (
            data.batch
            if hasattr(data, "batch") and data.batch is not None
            else torch.zeros(x.size(0), dtype=torch.long, device=x.device)
        )

        # NOTE: no `to_undirected` here. smiles_to_graph already emits both
        # directions of every bond, so it cannot add an edge - but its
        # `coalesce(reduce='add')` silently SUMS each 21-dim bond feature
        # vector with itself. `undirected` is instead handled the way
        # ChemProp does it, by tying the two directed bond states together
        # inside encode_with_normalization.
        node_repr = self.encode_with_normalization(x, edge_index, edge_attr)

        if self.pooling_layer is not None:
            mol_repr = self.pooling_layer(node_repr, batch)
        else:
            if self.pooling == "mean":
                mol_repr = global_mean_pool(node_repr, batch)
            elif self.pooling == "max":
                mol_repr = global_max_pool(node_repr, batch)
            elif self.pooling == "sum":
                mol_repr = global_add_pool(node_repr, batch)
            else:
                # Unknown values are coerced to mean in __init__; this branch
                # is only reached if self.pooling is mutated after construction.
                mol_repr = global_mean_pool(node_repr, batch)

        return self.forward_ffn(mol_repr)

    def encode_with_normalization(self, x, edge_index, edge_attr):
        row, col = edge_index
        bond_input = torch.cat([x[row], edge_attr], dim=1)
        hidden = self.W_i(bond_input)
        hidden = self.activation(hidden)
        hidden = self.dropout_layer(hidden)

        # Twin lookup for the D-MPNN message: edge (v, w) must aggregate the
        # bonds arriving at v *minus* the reverse bond (w, v). Without that
        # subtraction a bond immediately reads back what it sent one step
        # earlier, and - because the remaining sum depends only on `row` -
        # every out-edge of an atom receives an identical message, which
        # collapses the directed formulation into a node-centric one.
        reverse = _reverse_edge_index(edge_index, x.size(0))
        reverse_safe = reverse.clamp(min=0)
        has_reverse = (reverse >= 0).unsqueeze(-1).to(hidden.dtype)

        for layer_idx in range(self.depth - 1):
            if self.undirected:
                # ChemProp's `--undirected`: tie the two directions together.
                hidden = hidden + has_reverse * (hidden[reverse_safe] - hidden) / 2
            hidden_residual = hidden
            nei_message = scatter_add(hidden, col, dim=0, dim_size=x.size(0))
            bond_message = nei_message[row] - has_reverse * hidden[reverse_safe]
            bond_input = torch.cat([x[row], bond_message], dim=1)
            hidden_new = self.message_layers[layer_idx](hidden) + self.update_layers[layer_idx](
                bond_input
            )
            if self.use_layer_norm:
                hidden_new = self.layer_norms[layer_idx](hidden_new)
            if self.use_batch_norm:
                hidden_new = self.batch_norms[layer_idx](hidden_new)
            hidden_new = self.activation(hidden_new)
            hidden_new = self.dropout_layer(hidden_new)
            if self.use_message_residual:
                hidden = hidden_new + hidden_residual
            else:
                hidden = hidden_new

        nei_message = scatter_add(hidden, col, dim=0, dim_size=x.size(0))
        atom_input = torch.cat([x, nei_message], dim=1)
        atom_hidden = self.update_layers[-1](atom_input)
        if self.use_layer_norm:
            atom_hidden = self.layer_norms[-1](atom_hidden)
        if self.use_batch_norm:
            atom_hidden = self.batch_norms[-1](atom_hidden)
        atom_hidden = self.activation(atom_hidden)
        atom_hidden = self.dropout_layer(atom_hidden)
        return atom_hidden

    def forward_ffn(self, x):
        if self.ffn_num_layers == 1:
            return self.ffn(x)

        h = self.ffn_input(x)
        h = self.activation(h)
        h = self.dropout_layer(h)

        for i in range(len(self.ffn_layers)):
            h_residual = h
            h_new = self.ffn_layers[i](h)
            if self.use_layer_norm and i < len(self.ffn_layer_norms):
                h_new = self.ffn_layer_norms[i](h_new)
            if self.use_batch_norm and i < len(self.ffn_batch_norms):
                h_new = self.ffn_batch_norms[i](h_new)
            h_new = self.activation(h_new)
            h_new = self.dropout_layer(h_new)
            if self.use_ffn_residual:
                h = h_new + h_residual
            else:
                h = h_new

        output = self.ffn_output(h)
        return output


def _reverse_edge_index(edge_index, num_nodes):
    """For every directed edge (v, w), the index of its twin (w, v).

    D-MPNN's message for edge (v, w) sums the incoming edges of v *except*
    the reverse edge (w, v), so the twin has to be locatable. Matching on
    (row, col) keys rather than assuming the featurizer's consecutive
    ``[(i, j), (j, i)]`` layout keeps this correct after any reordering
    (PyG batching, ``to_undirected``, hand-built graphs).

    Returns a long tensor of twin indices, ``-1`` where a twin is absent.
    """
    row, col = edge_index
    num_edges = row.numel()
    if num_edges == 0:
        return torch.empty(0, dtype=torch.long, device=row.device)

    keys = row * num_nodes + col
    twins = col * num_nodes + row

    order = torch.argsort(keys)
    sorted_keys = keys[order]
    pos = torch.searchsorted(sorted_keys, twins).clamp(max=num_edges - 1)
    reverse = order[pos]
    return reverse.masked_fill(sorted_keys[pos] != twins, -1)


def _get_activation(activation):
    """Get activation function by name"""
    if activation == "ReLU":
        return nn.ReLU()
    elif activation == "LeakyReLU":
        return nn.LeakyReLU(0.1)
    elif activation == "PReLU":
        return nn.PReLU()
    elif activation == "ELU":
        return nn.ELU()
    elif activation == "tanh":
        return nn.Tanh()
    elif activation == "SELU":
        return nn.SELU()
    elif activation == "GELU":
        return nn.GELU()
    elif activation == "Swish":
        return nn.SiLU()
    else:
        raise ValueError(f"Activation {activation} not supported.")


def create_enhanced_chemprop_dmpnn(data_list, **kwargs):
    """Factory function to create Enhanced ChemPropDMPNN"""
    node_dim = data_list[0].num_node_features
    edge_dim = data_list[0].edge_attr.size(1) if hasattr(data_list[0], "edge_attr") else 0

    model = EnhancedChemPropDMPNN(
        atom_fdim=node_dim,
        bond_fdim=edge_dim,
        hidden_size=kwargs.get("hidden_size", 300),
        depth=kwargs.get("depth", 3),
        dropout=kwargs.get("dropout", 0.1),
        activation=kwargs.get("activation", "ReLU"),
        undirected=kwargs.get("undirected", False),
        ffn_hidden_size=kwargs.get("ffn_hidden_size", 300),
        ffn_num_layers=kwargs.get("ffn_num_layers", 2),
        output_size=kwargs.get("output_size", 1),
        use_layer_norm=kwargs.get("use_layer_norm", True),
        use_batch_norm=kwargs.get("use_batch_norm", False),
        use_message_residual=kwargs.get("use_message_residual", True),
        use_ffn_residual=kwargs.get("use_ffn_residual", True),
        pooling=kwargs.get("pooling", "attention"),
        attention_heads=kwargs.get("attention_heads", 4),
        set2set_iters=kwargs.get("set2set_iters", 3),
        init_type=kwargs.get("init_type", "xavier_uniform"),
        init_gain=kwargs.get("init_gain", 1.0),
        bias_init=kwargs.get("bias_init", "zeros"),
    )
    return model
