# -*- coding: utf-8 -*-
"""
Custom class for Graph Isomorphism Network (GIN)
-----------------------------------------------

This module implements a Graph Isomorphism Network (GIN) for graph classification tasks.
It includes supporting classes for Multi-Layer Perceptron (MLP) and node function application, as well as
the main GIN class with training, prediction, and model persistence methods.
This implementation is based on the following papers:
- "How Powerful are Graph Neural Networks" (https://arxiv.org/abs/1810.00826)
- "How Powerful are Graph Neural Networks" (https://openreview.net/forum?id=ryGs6iA5Km)
Author's implementation: https://github.com/weihua916/powerful-gnns

This class has been adapted to allow a simple interface with `fit` and `predict` methods, which is not part of the best practice when working with PyTorch models. Alongside the `load` and `save` methods, this is to follow compatibility with DataRobot hooks with minimal code. This is an example of the integration.

Authors
-------
    - Ouadie GHARROUDI <ouadie.gharroudi@datarobot.com>
    - Elise Sainderichin <elise.sainderichin@datarobot.com>
    - Timothy Whittaker <timothy.whittaker@datarobot.com>
"""


import pickle

from dgl.nn.pytorch.conv import GINConv
from dgl.nn.pytorch.glob import AvgPooling, MaxPooling, SumPooling
import torch
import torch.nn as nn
import torch.nn.functional as F

##############################################################################
# Supporting Classes: MLP, ApplyNodeFunc
##############################################################################


class MLP(nn.Module):
    def __init__(self, num_layers, input_dim, hidden_dim, output_dim):
        super(MLP, self).__init__()
        self.num_layers = num_layers
        self.output_dim = output_dim

        if num_layers < 1:
            raise ValueError("Number of layers should be positive!")
        elif num_layers == 1:
            # Linear model
            self.linear = nn.Linear(input_dim, output_dim)
        else:
            # Multi-layer model
            self.linears = nn.ModuleList()
            self.batch_norms = nn.ModuleList()

            self.linears.append(nn.Linear(input_dim, hidden_dim))
            for _ in range(num_layers - 2):
                self.linears.append(nn.Linear(hidden_dim, hidden_dim))
            self.linears.append(nn.Linear(hidden_dim, output_dim))

            for _ in range(num_layers - 1):
                self.batch_norms.append(nn.BatchNorm1d(hidden_dim))

    def forward(self, x):
        if self.num_layers == 1:
            return self.linear(x)
        else:
            h = x
            for i in range(self.num_layers - 1):
                h = self.linears[i](h)
                h = self.batch_norms[i](h)
                h = F.relu(h)
            return self.linears[-1](h)


class ApplyNodeFunc(nn.Module):
    def __init__(self, mlp):
        super(ApplyNodeFunc, self).__init__()
        self.mlp = mlp
        self.bn = nn.BatchNorm1d(self.mlp.output_dim)

    def forward(self, h):
        h = self.mlp(h)
        h = self.bn(h)
        h = F.relu(h)
        return h


##############################################################################
# Main GIN class with fit, predict, save_model, load_model
##############################################################################


class GIN(nn.Module):
    """
    GIN (Graph Isomorphism Network) model for graph classification.

    This class implements a GIN model with multiple layers of GINConv,
    batch normalization, and graph pooling. It supports training,
    prediction, and saving/loading the model.

    Parameters
    ----------
    num_layers : int
        Number of GIN layers in the model.
    num_mlp_layers : int
        Number of layers in the MLP used in each GIN layer.
    input_dim : int
        Dimensionality of input node features.
    hidden_dim : int
        Dimensionality of hidden layers.
    output_dim : int
        Dimensionality of the output layer (number of classes).
    final_dropout : float
        Dropout rate applied to the final layer.
    learn_eps : bool
        Whether to learn the epsilon parameter in GINConv.
    graph_pooling_type : str
        Type of graph pooling to apply ('sum', 'mean', or 'max').
    neighbor_pooling_type : str
        Type of neighbor pooling to apply in GINConv ('sum', 'mean', or 'max').

    Methods
    -------
    forward(g, h)
        Forward pass of the model.
    fit(dataloader, optimizer, epochs=10, device="cpu")
        Trains the model using the provided dataloader and optimizer.
    predict(dataloader, device="cpu")
        Predicts class probabilities for the input data.
    save_model(path)
        Saves the model configuration and weights to the specified path.
    load_model(path, map_location="cpu")
        Loads a GIN model from the specified path.
    """

    def __init__(
        self,
        num_layers,
        num_mlp_layers,
        input_dim,
        hidden_dim,
        output_dim,
        final_dropout,
        learn_eps,
        graph_pooling_type,
        neighbor_pooling_type,
    ):
        super(GIN, self).__init__()
        self.num_layers = num_layers
        self.learn_eps = learn_eps

        # Store the config in a private dict (for easier saving)
        self._config = {
            "num_layers": num_layers,
            "num_mlp_layers": num_mlp_layers,
            "input_dim": input_dim,
            "hidden_dim": hidden_dim,
            "output_dim": output_dim,
            "final_dropout": final_dropout,
            "learn_eps": learn_eps,
            "graph_pooling_type": graph_pooling_type,
            "neighbor_pooling_type": neighbor_pooling_type,
        }

        # GIN Conv layers
        self.ginlayers = nn.ModuleList()
        self.batch_norms = nn.ModuleList()

        for layer in range(num_layers - 1):
            if layer == 0:
                mlp = MLP(num_mlp_layers, input_dim, hidden_dim, hidden_dim)
            else:
                mlp = MLP(num_mlp_layers, hidden_dim, hidden_dim, hidden_dim)

            self.ginlayers.append(
                GINConv(ApplyNodeFunc(mlp), neighbor_pooling_type, 0, learn_eps)
            )
            self.batch_norms.append(nn.BatchNorm1d(hidden_dim))

        # Prediction heads for each layer
        self.linears_prediction = nn.ModuleList()
        for layer in range(num_layers):
            if layer == 0:
                self.linears_prediction.append(nn.Linear(input_dim, output_dim))
            else:
                self.linears_prediction.append(nn.Linear(hidden_dim, output_dim))

        self.drop = nn.Dropout(final_dropout)

        # Graph pooling
        if graph_pooling_type == "sum":
            self.pool = SumPooling()
        elif graph_pooling_type == "mean":
            self.pool = AvgPooling()
        elif graph_pooling_type == "max":
            self.pool = MaxPooling()
        else:
            raise NotImplementedError

    def forward(self, g, h):
        hidden_rep = [h]
        for i in range(self.num_layers - 1):
            h = self.ginlayers[i](g, h)
            h = self.batch_norms[i](h)
            h = F.relu(h)
            hidden_rep.append(h)

        score_over_layer = 0
        for i, h in enumerate(hidden_rep):
            pooled_h = self.pool(g, h)
            score_over_layer += self.drop(self.linears_prediction[i](pooled_h))

        return score_over_layer

    def fit(self, dataloader, optimizer, epochs=10, device="cpu"):
        self.to(device)
        self.train()
        for epoch in range(epochs):
            total_loss = 0
            for batched_graph, labels in dataloader:
                batched_graph = batched_graph.to(device)
                labels = labels.to(device)
                feats = batched_graph.ndata["attr"].float()

                logits = self(batched_graph, feats)
                loss = F.cross_entropy(logits, labels)

                optimizer.zero_grad()
                loss.backward()
                optimizer.step()
                total_loss += loss.item()

            avg_loss = total_loss / len(dataloader)
            print(f"Epoch [{epoch+1}/{epochs}], Loss: {avg_loss:.4f}")

    def predict(self, dataloader, device="cpu"):
        self.eval()
        self.to(device)
        all_preds = []
        all_probs = []

        with torch.no_grad():
            for batch in dataloader:
                if isinstance(
                    batch, tuple
                ):  # To provide the flexibility to do class validation and prediction with laberls in the bact
                    batched_graph, labels = batch
                else:
                    batched_graph = batch

                batched_graph = batched_graph.to(device)
                feats = batched_graph.ndata["attr"].float()
                logits = self(batched_graph, feats)

                probs = F.softmax(logits, dim=1)
                preds = torch.argmax(probs, dim=1)

                all_preds.append(preds.cpu())
                all_probs.append(probs.cpu())

        all_preds = torch.cat(all_preds, dim=0)
        all_probs = torch.cat(all_probs, dim=0)
        return all_preds, all_probs

    def save_model(self, path):
        """
        Saves two files:
          1) {path}.params -> pickled hyperparameters
          2) {path}.weights -> model's state_dict
        """
        # 1) Save the config
        with open(f"{path}.params", "wb") as f:
            pickle.dump(self._config, f)

        # 2) Save the state_dict
        torch.save(self.state_dict(), f"{path}.weights")
        print(f"Model saved as {path}.params and {path}.weights")

    @classmethod
    def load_model(cls, path, map_location="cpu"):
        """
        Loads a GIN model from two files:
          1) {path}.params (pickled config)
          2) {path}.weights (model state_dict)

        Returns
        -------
        model : GIN
            A new GIN instance loaded with the saved state_dict.
        """
        # 1) Load the config
        with open(f"{path}.params", "rb") as f:
            config = pickle.load(f)

        # 2) Create model with the same config
        model = cls(**config)

        # 3) Load the weights
        state_dict = torch.load(f"{path}.weights", map_location=map_location)
        model.load_state_dict(state_dict)
        print(f"Model loaded from {path}.params and {path}.weights")
        return model
