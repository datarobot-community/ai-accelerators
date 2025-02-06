from pathlib import Path

from datarobot_drum.custom_task_interfaces import TransformerInterface
import numpy as np
import pandas as pd
import scipy.sparse as sp
from sklearn.neighbors import kneighbors_graph
import torch
import torch.nn as nn
import torch.nn.functional as F
from torch_geometric.data import Data
from torch_geometric.nn import SAGEConv


###########################################
# Helper Function: Build a kNN Graph
###########################################
def build_knn_graph(X_data, n_neighbors):
    """
    Build a k-nearest neighbor (kNN) graph from the input data.
    This assumes the input data is normalized (e.g., with StandardScaler()).
    Normalization helps improve performance of kNN [1]

    Parameters
    ----------
    X_data : np.ndarray
        A NumPy array of shape [n_samples, n_features] containing the normalized feature data.
    n_neighbors : int
        The number of nearest neighbors to use for constructing the graph.

    Returns
    -------
    Data
        A PyTorch Geometric Data object with two attributes:
          - x: a tensor of node features of shape [n_samples, n_features]
          - edge_index: a tensor of shape [2, num_edges] that contains the graph edges
            in COO format.

    References
    ----------
    [1] https://scikit-learn.org/stable/auto_examples/preprocessing/plot_scaling_importance.html#sphx-glr-auto-examples-preprocessing-plot-scaling-importance-py
    """
    # Compute the k-nearest neighbor connectivity matrix (binary adjacency)
    A = kneighbors_graph(X_data, n_neighbors=n_neighbors, mode="connectivity", include_self=False)

    # Convert the sparse matrix to COO format for easy extraction of indices
    A_coo = sp.coo_matrix(A)

    # Stack row and column indices to form the edge index
    edge_index_np = np.vstack((A_coo.row, A_coo.col))
    edge_index = torch.tensor(edge_index_np, dtype=torch.long)

    # Convert the input data to a torch tensor.
    x_tensor = torch.tensor(X_data, dtype=torch.float)

    return Data(x=x_tensor, edge_index=edge_index)


###########################################
# Define the GraphSAGE Model
###########################################
class GraphSAGE(nn.Module):
    """
    A simple GraphSAGE model with two SAGEConv layers for unsupervised feature learning.

    The model outputs node embeddings of dimension `out_channels`.

    Parameters
    ----------
    in_channels : int
        The number of input features per node.
    hidden_channels : int
        The number of hidden units in the first layer.
    out_channels : int
        The number of output features (embedding dimension) per node.
    """

    def __init__(self, in_channels, hidden_channels, out_channels):
        super(GraphSAGE, self).__init__()
        self.conv1 = SAGEConv(in_channels, hidden_channels)
        self.conv2 = SAGEConv(hidden_channels, out_channels)

    def forward(self, x, edge_index):
        """
        Forward pass through the model.

        Parameters
        ----------
        x : torch.Tensor
            Input node features of shape [n_nodes, in_channels].
        edge_index : torch.Tensor
            Graph edge indices in COO format of shape [2, num_edges].

        Returns
        -------
        torch.Tensor
            Node embeddings of shape [n_nodes, out_channels].
        """
        x = self.conv1(x, edge_index)
        x = F.relu(x)
        x = self.conv2(x, edge_index)
        return x


###########################################
# Unsupervised Training with Simple Contrastive Loss
###########################################
def train_unsupervised(model, data, epochs, num_neg_samples, lr, seed):
    """
    Train the GraphSAGE model in an unsupervised manner using a simple contrastive loss.

    For each edge (positive pair), the loss encourages the dot product of the two node embeddings
    to be high (via -logsigmoid). For negative pairs (random node pairings), the loss encourages
    a low dot product (via -logsigmoid of the negative).

    Parameters
    ----------
    model : nn.Module
        The GraphSAGE model.
    data : Data
        A PyTorch Geometric Data object containing node features and edge_index.
    epochs : int
        The number of training epochs.
    num_neg_samples : int
        The number of negative samples to average per edge.
    lr : float
        The learning rate for the optimizer.

    Returns
    -------
    nn.Module
        The trained GraphSAGE model.
    """
    # Set a manual seed for reproducibility
    torch.manual_seed(seed)
    optimizer = torch.optim.Adam(model.parameters(), lr=lr)
    model.train()
    for epoch in range(epochs):
        optimizer.zero_grad()

        # Compute embeddings for all nodes
        embeddings = model(data.x, data.edge_index)

        # Positive loss: for each edge, maximize the dot product similarity
        row, col = data.edge_index
        pos_scores = (embeddings[row] * embeddings[col]).sum(dim=1)
        pos_loss = -F.logsigmoid(pos_scores).mean()

        # Negative loss: for each edge, sample random negative nodes and minimize their similarity
        neg_loss = 0
        n_edges = data.edge_index.size(1)
        n_nodes = data.x.size(0)
        for _ in range(num_neg_samples):
            neg_idx = torch.randint(0, n_nodes, (n_edges,))
            neg_scores = (embeddings[row] * embeddings[neg_idx]).sum(dim=1)
            neg_loss += -F.logsigmoid(-neg_scores).mean()
        neg_loss = neg_loss / num_neg_samples

        # Combine loss and iterate
        loss = pos_loss + neg_loss
        loss.backward()
        optimizer.step()

        if (epoch + 1) % 20 == 0:
            print(f"Epoch {epoch+1:3d}/{epochs}, Loss: {loss.item():.4f}")
    return model


###########################################
# Custom Transformer Class
###########################################
class CustomTask(TransformerInterface):
    """
    A DataRobot DRUM custom transformer that implements unsupervised graph-based feature engineering.

    The transformer:
      - In fit(): Converts the input DataFrame to a NumPy array, builds a kNN graph from the training features,
        trains a GraphSAGE model using a simple contrastive loss, and stores the trained model along with the training data.
      - In transform(): Combines the stored training data with new data to build a new kNN graph, runs the trained model
        in an inductive setting, and outputs a DataFrame containing only the computed node embeddings.
    """

    def __init__(self):
        self.X_train = None  # Placeholder for input training data
        self.train_data = None  # placeholder to knn_data
        self.model = None  # Placeholder for model

    def set_seed(self):
        """Ensure reproducibility by setting the random seed."""

        torch.manual_seed(self.random_seed)
        torch.cuda.manual_seed_all(self.random_seed)
        np.random.seed(self.random_seed)
        torch.use_deterministic_algorithms(True)
        torch.backends.cudnn.deterministic = True
        torch.backends.cudnn.benchmark = False

    def fit(self, X: pd.DataFrame, y: pd.Series, parameters=None, **kwargs) -> None:
        """
        Fit the transformer on training data.

        The flow is as follows:
          1. Convert the input DataFrame to a NumPy array.
          2. Build a k-nearest neighbor graph from the training data.
          3. Instantiate and train a GraphSAGE model with a simple contrastive loss (unsupervised).
          4. Store the trained model, the original training data, and training embeddings (for use in transform).

        Parameters
        ----------
        X : pd.DataFrame
            Training features
        y : pd.Series
            Target info
        parameters (dict, optional):
            Hyperparameters

        """
        # Ensuring we're passing the hyperparameters
        if parameters is None:
            raise ValueError(
                "Parameters were not passed into the custom task. "
                "Ensure your model metadata contains hyperparameter definitions"
            )

        # Define hyperparameters
        self.hidden_channels = parameters["hidden_channels"]  # Number of hidden units in GraphSAGE
        self.out_channels = parameters["out_channels"]  # Dimension of the learned embedding
        self.k_neighbors = parameters["k_neighbors"]  # Number of neighbors for kneighbors_graph
        self.learning_rate = parameters["learning_rate"]  # Learning rate for optimizer
        self.epochs = parameters["epochs"]  # Number of training epochs to run
        self.num_neg_samples = parameters[
            "num_neg_samples"
        ]  # Number negative samples to include for contrastive loss
        self.random_seed = parameters["random_seed"]  # random seed for operations

        # For reproducibility
        self.set_seed()

        # Convert training data to a NumPy array and store it for later use
        X_np = X.to_numpy()
        self.X_train = X_np.copy()

        # Build a kNN graph from the training features
        self.train_data = build_knn_graph(X_np, n_neighbors=self.k_neighbors)

        # Define model parameters
        in_channels = X_np.shape[1]
        hidden_channels = self.hidden_channels
        out_channels = self.out_channels  # Dimension of the learned embedding

        # Instantiate the GraphSAGE model
        self.model = GraphSAGE(in_channels, hidden_channels, out_channels)

        # Train the model using unsupervised contrastive loss
        self.model = train_unsupervised(
            model=self.model,
            data=self.train_data,
            epochs=self.epochs,
            num_neg_samples=self.num_neg_samples,
            lr=self.learning_rate,
            seed=self.random_seed,
        )

        # Save embedding on the training data for later use
        self.train_embeddings = (
            self.model(self.train_data.x, self.train_data.edge_index).cpu().detach().numpy()
        )

    def transform(self, X: pd.DataFrame) -> pd.DataFrame:
        """
        Transform new data by computing GraphSAGE embeddings.

        The process is:
          1. Convert new data to a NumPy array.
          2. Combine the stored training data with the new data.
          3. Build a new kNN graph on the combined data.
          4. Run the trained GraphSAGE model on the combined graph.
          5. Extract and return only the embeddings corresponding to the new data.

        Parameters
        ----------
        X : pd.DataFrame
            New data to be transformed

        Returns
        -------
        pd.DataFrame
            A DataFrame of shape [n_new, embedding_dim] containing the graph embeddings,
            with column names 'g0', 'g1', ..., etc.
        """
        # Convert new data to a NumPy array
        X_new = X.to_numpy()

        if np.array_equal(X_new, self.X_train):
            print("Detected training data, returning precomputed embeddings...")

            # Extra embeddings from training data
            new_embeddings = self.train_embeddings.copy()

        else:
            print("Computing embeddings on test data...")

            # Combine stored training data with new data
            X_combined = np.concatenate([self.X_train, X_new], axis=0)

            # Build a kNN graph from the combined data
            combined_data = build_knn_graph(X_combined, n_neighbors=10)

            # Use the trained model to compute embeddings on the combined graph
            self.model.eval()
            with torch.no_grad():
                combined_embeddings = (
                    self.model(combined_data.x, combined_data.edge_index).cpu().detach().numpy()
                )

            # Extract embeddings corresponding to the new data only
            new_embeddings = combined_embeddings[self.X_train.shape[0] :, :]

        # Return the embeddings as a DataFrame with column names g0, g1, ...
        col_names = [f"g{i}" for i in range(new_embeddings.shape[1])]

        print("Done!")
        return pd.DataFrame(new_embeddings, columns=col_names)

    def save(self, artifact_directory):
        """
        Serializes the trained model and other necessary attributes to disk.

        Parameters
        ----------
        artifact_directory : str
            Path to the directory where the artifact(s) should be saved.

        Returns
        -------
        self
        """
        # Save model
        torch.save(self.model, Path(artifact_directory) / "model.pth")
        self.save_task(artifact_directory, exclude=["model"])
        return self

    @classmethod
    def load(cls, artifact_directory):
        """
        Deserializes the stored artifact(s) from disk and reloads the transformer.

        Parameters
        ----------
        artifact_directory : str
            Path to the directory where the artifact(s) are stored.

        Returns
        -------
        CustomTask
            The loaded transformer object.
        """
        # Load task and model
        custom_task = cls.load_task(artifact_directory)
        custom_task.model = torch.load(Path(artifact_directory) / "model.pth", weights_only=False)
        return custom_task
