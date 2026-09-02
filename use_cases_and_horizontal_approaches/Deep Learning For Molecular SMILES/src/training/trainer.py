import os

import numpy as np
from sklearn.metrics import mean_absolute_error
import torch
from torch.optim import Adam
from torch.utils.data import DataLoader as TorchDataLoader
from torch_geometric.loader import DataLoader as PyGDataLoader

from ..data.graph_features import smiles_to_graph
from ..data.smiles_data import SMILESDataset, SMILESTokenizer
from ..models.dmpnn import create_enhanced_chemprop_dmpnn
from ..models.sequence import SequenceNN

ARTIFACT_NAME = "smiles_model.pth"


def _parse_model_type(model_type):
    """Parse model type string into (is_graph, sequence_flags)."""
    model_type = model_type.lower().strip()
    if model_type == "dmpnn":
        return True, {}

    parts = set(model_type.split("+"))
    valid = {"lstm", "cnn", "transformer"}
    unknown = parts - valid
    if unknown:
        raise ValueError(
            f"Unknown model type component: {unknown}. "
            f"Valid: dmpnn, lstm, cnn, transformer (combinable with '+')"
        )
    return False, {
        "use_lstm": "lstm" in parts,
        "use_cnn": "cnn" in parts,
        "use_transformer": "transformer" in parts,
    }


def _build_model(cfg, data_list=None, tokenizer=None):
    """Build model based on config. Returns (model, is_graph)."""
    mcfg = cfg["model"]
    is_graph, seq_flags = _parse_model_type(mcfg["type"])

    if is_graph:
        if not data_list:
            raise ValueError("Cannot build a DMPNN model from an empty data_list")
        dmpnn_cfg = mcfg.get("dmpnn", {})
        model = create_enhanced_chemprop_dmpnn(
            data_list,
            hidden_size=mcfg["hidden_dim"],
            depth=dmpnn_cfg.get("depth", 3),
            dropout=mcfg["dropout"],
            activation=dmpnn_cfg.get("activation", "ReLU"),
            undirected=dmpnn_cfg.get("undirected", False),
            ffn_hidden_size=dmpnn_cfg.get("ffn_hidden_size", mcfg["hidden_dim"]),
            ffn_num_layers=dmpnn_cfg.get("ffn_num_layers", 3),
            use_layer_norm=dmpnn_cfg.get("use_layer_norm", False),
            use_batch_norm=dmpnn_cfg.get("use_batch_norm", False),
            use_message_residual=dmpnn_cfg.get("use_message_residual", True),
            use_ffn_residual=dmpnn_cfg.get("use_ffn_residual", False),
            pooling=mcfg.get("pooling", "mean"),
        )
    else:
        seq_cfg = mcfg.get("sequence", {})
        model = SequenceNN(
            vocab_size=len(tokenizer.char_to_idx),
            embedding_dim=seq_cfg.get("embedding_dim", 128),
            hidden_dim=mcfg["hidden_dim"],
            num_layers=seq_cfg.get("num_layers", 1),
            num_heads=seq_cfg.get("num_heads", 4),
            dropout=mcfg["dropout"],
            use_lstm=seq_flags["use_lstm"],
            use_cnn=seq_flags["use_cnn"],
            cnn_kernels=seq_cfg.get("cnn_kernels", [3]),
            use_transformer=seq_flags["use_transformer"],
            pooling=mcfg.get("pooling", "mean"),
        )

    return model, is_graph


def _eval_loader(model, loader, is_graph, device):
    """Run model on a loader. Returns (preds, targets_or_none)."""
    model.eval()
    all_preds = []
    all_true = []
    has_target = None

    with torch.no_grad():
        for batch in loader:
            if is_graph:
                batch = batch.to(device)
                out = model(batch)
                all_preds.append(out.cpu())
                if hasattr(batch, "y") and batch.y is not None:
                    all_true.append(batch.y.cpu())
                    has_target = True
            else:
                if isinstance(batch, (list, tuple)) and len(batch) == 2:
                    x, y = batch
                    x, y = x.to(device), y.to(device)
                    out = model(x)
                    all_preds.append(out.cpu())
                    all_true.append(y.cpu())
                    has_target = True
                else:
                    x = (
                        batch.to(device)
                        if not isinstance(batch, (list, tuple))
                        else batch[0].to(device)
                    )
                    out = model(x)
                    all_preds.append(out.cpu())
                    has_target = False

    if not all_preds:
        # Empty loader (0-row score payload). torch.cat([]) raises.
        return np.zeros((0,), dtype=np.float32), None

    preds = torch.cat(all_preds, dim=0).numpy().reshape(-1)
    if has_target and all_true:
        true = torch.cat(all_true, dim=0).numpy().reshape(-1)
        return preds, true
    return preds, None


def _build_bundle(model, cfg, atom_map=None, tokenizer=None):
    """Assemble the on-disk artifact: state_dict plus everything needed to
    re-featurize new SMILES and rebuild the same model at inference."""
    return {
        "state_dict": {k: v.cpu() for k, v in model.state_dict().items()},
        "cfg": cfg,
        "target": cfg.get("target"),
        "smiles_col": cfg.get("data", {}).get("smiles_column", "SMILES"),
        "atom_map": atom_map,
        "tokenizer_vocab": tokenizer.char_to_idx if tokenizer is not None else None,
    }


def _restore_tokenizer(vocab):
    """Rebuild a SMILESTokenizer from a saved char_to_idx mapping."""
    tok = SMILESTokenizer()
    tok.char_to_idx = dict(vocab)
    tok.idx_to_char = {v: k for k, v in tok.char_to_idx.items()}
    return tok


def run_train(
    train_data,
    valid_data,
    cfg,
    data_list=None,
    tokenizer=None,
    atom_map=None,
    artifact_name=ARTIFACT_NAME,
):
    """Train model on train set, validate on valid set, save best bundle.

    Args:
        train_data: Training data (PyG list or PyTorch Dataset).
        valid_data: Validation data.
        cfg: Config dict.
        data_list: PyG data list for dmpnn feature dim inference. If None, uses train_data.
        tokenizer: Fitted SMILESTokenizer (for sequence models).
        atom_map: Symbol -> index map (for dmpnn). Bundled into the artifact
            so re-featurization at predict time uses the exact same indexing.
        artifact_name: File name to write the bundle under, inside
            ``cfg['paths']['model']``. Override it to keep a holdout-stage
            checkpoint from clobbering the deployable artifact.

    Returns:
        dict with keys: train_preds, valid_preds, train_mae, valid_mae,
        best_epoch, best_val_mae, lr_history, best_model_path
    """
    tcfg = cfg["training"]
    mcfg = cfg["model"]
    model_save_dir = cfg["paths"].get("model", "model/")

    epochs = tcfg["epochs"]
    lr = tcfg["lr"]
    patience = tcfg["early_stopping"]["patience"]
    min_delta = tcfg["early_stopping"]["min_delta"]

    is_graph, _ = _parse_model_type(mcfg["type"])
    if data_list is None:
        data_list = train_data
    if is_graph and not atom_map:
        raise ValueError(
            "atom_map is empty; no valid SMILES were parsed. " "Check RDKit and data.smiles_column."
        )

    DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
    os.makedirs(model_save_dir, exist_ok=True)

    Loader = PyGDataLoader if is_graph else TorchDataLoader

    train_loader = Loader(train_data, batch_size=tcfg["batch_size_train"], shuffle=True)
    valid_loader = Loader(valid_data, batch_size=tcfg["batch_size_valid"], shuffle=False)

    print(f"train: {len(train_data)}, valid: {len(valid_data)}")

    model, _ = _build_model(cfg, data_list=data_list, tokenizer=tokenizer)
    model = model.to(DEVICE)

    optimizer = Adam(model.parameters(), lr=lr)
    # NOTE: no `verbose=` — deprecated in torch 2.2 and removed in later releases
    # (TypeError: ReduceLROnPlateau.__init__() got an unexpected keyword argument
    # 'verbose'). LR is printed every epoch below, plus an explicit note on each drop.
    scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(
        optimizer,
        mode="min",
        factor=tcfg["scheduler"]["factor"],
        patience=tcfg["scheduler"]["patience"],
        min_lr=tcfg["scheduler"]["min_lr"],
    )
    criterion = getattr(torch.nn, tcfg.get("criterion", "L1Loss"))()

    best_val_mae = float("inf")
    best_epoch = 0
    patience_counter = 0
    lr_history = []
    best_model_path = os.path.join(model_save_dir, artifact_name)

    for epoch in range(1, epochs + 1):
        model.train()
        total_loss = 0
        n_samples = 0

        for batch in train_loader:
            optimizer.zero_grad()
            if is_graph:
                batch = batch.to(DEVICE)
                out = model(batch)
                loss = criterion(out, batch.y)
                bs = batch.num_graphs
            else:
                x, y = batch
                x, y = x.to(DEVICE), y.to(DEVICE)
                out = model(x)
                loss = criterion(out, y)
                bs = x.size(0)

            loss.backward()
            optimizer.step()
            total_loss += loss.item() * bs
            n_samples += bs

        train_loss = total_loss / n_samples

        # Validation
        valid_preds, valid_true = _eval_loader(model, valid_loader, is_graph, DEVICE)
        valid_mae = mean_absolute_error(valid_true, valid_preds)

        epoch_lr = optimizer.param_groups[0]["lr"]
        lr_history.append(epoch_lr)
        scheduler.step(valid_mae)
        next_lr = optimizer.param_groups[0]["lr"]

        # Report the LR this epoch actually trained at. Printing the value the
        # scheduler had just installed made every drop appear one epoch early,
        # so this log disagreed with stage 2's replay of lr_history - which
        # made a correct replay look broken.
        print(
            f"Epoch: {epoch:02d}, Train Loss: {train_loss:.4f}, "
            f"Valid MAE: {valid_mae:.4f}, LR: {epoch_lr:.2e}"
        )
        if next_lr < epoch_lr:
            print(f"  LR reduced: {epoch_lr:.2e} -> {next_lr:.2e} (from the next epoch)")

        if valid_mae < best_val_mae - min_delta:
            best_val_mae = valid_mae
            best_epoch = epoch
            patience_counter = 0
            torch.save(
                _build_bundle(model, cfg, atom_map=atom_map, tokenizer=tokenizer),
                best_model_path,
            )
            print(f"  -> New best: {best_val_mae:.4f}")
        else:
            patience_counter += 1
            if patience_counter % 20 == 0 or patience_counter >= patience - 5:
                print(f"  No improvement. Patience: {patience_counter}/{patience}")

        if patience_counter >= patience:
            print(f"Early stopping at epoch {epoch}")
            break

    if best_epoch == 0:
        # Nothing beat the initial `inf`, i.e. validation MAE was NaN or
        # infinite in every epoch. Fail here rather than fall through: the
        # old `os.path.exists` check would happily load a LEFTOVER checkpoint
        # from an earlier run and the metrics printed below would describe
        # that model instead of this run.
        raise RuntimeError(
            "Training produced no usable checkpoint: validation MAE was NaN or "
            "infinite in every epoch. Check the target column for missing or "
            "non-numeric values, and the learning rate."
        )

    # Reload best weights (from the bundle this run saved).
    bundle = torch.load(best_model_path, map_location=DEVICE, weights_only=False)
    model.load_state_dict(bundle["state_dict"])
    print(f"Loaded best model (valid MAE: {best_val_mae:.4f})")

    # Final evaluation on train and valid. Do NOT reuse train_loader:
    # it was built with shuffle=True, so train_preds would not line up
    # with the input row order (run_train_full already uses a fresh
    # unshuffled loader for the same reason).
    eval_train_loader = Loader(train_data, batch_size=tcfg["batch_size_valid"], shuffle=False)
    train_preds, train_true = _eval_loader(model, eval_train_loader, is_graph, DEVICE)
    valid_preds, valid_true = _eval_loader(model, valid_loader, is_graph, DEVICE)

    train_mae = mean_absolute_error(train_true, train_preds)
    valid_mae = mean_absolute_error(valid_true, valid_preds)

    print(f"\n=== Final Results ===")
    print(f"Train MAE: {train_mae:.4f}")
    print(f"Valid MAE: {valid_mae:.4f}")
    print(f"Best epoch: {best_epoch}")
    print(f"Model saved: {best_model_path}")

    return {
        "train_preds": train_preds,
        "valid_preds": valid_preds,
        "train_mae": train_mae,
        "valid_mae": valid_mae,
        "best_epoch": best_epoch,
        "best_val_mae": best_val_mae,
        "lr_history": lr_history,
        "best_model_path": best_model_path,
    }


def run_train_full(
    train_data,
    cfg,
    epochs,
    data_list=None,
    tokenizer=None,
    atom_map=None,
    lr_schedule=None,
    artifact_name=ARTIFACT_NAME,
):
    """Refit on the *whole* training set for a fixed number of epochs.

    Stage 2 of the notebook flow: stage 1 holds out a validation split to find
    the epoch at which validation MAE bottoms out; this function then throws the
    holdout back in and reruns for exactly that many epochs. There is no
    validation set here, so there is no early stopping and no "best" checkpoint
    to pick - the model as of the final epoch is what gets saved.

    Args:
        train_data: The full training data (PyG list or PyTorch Dataset).
        cfg: Config dict.
        epochs: Number of epochs to run (the best epoch found in stage 1).
        data_list: PyG data list for dmpnn feature dim inference. If None, uses train_data.
        tokenizer: Fitted SMILESTokenizer (for sequence models).
        atom_map: Symbol -> index map (for dmpnn).
        lr_schedule: Optional per-epoch learning rates recorded by ``run_train``
            (its ``lr_history``). When given, the stage-1 LR trajectory is
            replayed verbatim so the run that produced ``epochs`` is reproduced
            as closely as possible. When None, ``ReduceLROnPlateau`` is stepped
            on the *training* loss instead, since no validation metric exists.
        artifact_name: File name for the saved bundle.

    Returns:
        dict with keys: train_preds, train_mae, epochs, best_model_path
    """
    tcfg = cfg["training"]
    mcfg = cfg["model"]
    model_save_dir = cfg["paths"].get("model", "model/")

    epochs = int(epochs)
    if epochs < 1:
        raise ValueError(f"epochs must be >= 1, got {epochs}")

    lr = tcfg["lr"]

    is_graph, _ = _parse_model_type(mcfg["type"])
    if data_list is None:
        data_list = train_data
    if is_graph and not atom_map:
        raise ValueError(
            "atom_map is empty; no valid SMILES were parsed. " "Check RDKit and data.smiles_column."
        )

    DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
    os.makedirs(model_save_dir, exist_ok=True)

    Loader = PyGDataLoader if is_graph else TorchDataLoader
    train_loader = Loader(train_data, batch_size=tcfg["batch_size_train"], shuffle=True)

    print(f"Refit on full train set: {len(train_data)} samples, {epochs} epochs")

    model, _ = _build_model(cfg, data_list=data_list, tokenizer=tokenizer)
    model = model.to(DEVICE)

    optimizer = Adam(model.parameters(), lr=lr)
    scheduler = None
    if lr_schedule:
        lr_schedule = [float(v) for v in lr_schedule]
        print(
            f"Replaying stage-1 LR schedule "
            f"({lr_schedule[0]:.2e} -> {lr_schedule[min(epochs, len(lr_schedule)) - 1]:.2e})"
        )
    else:
        # No validation metric available - plateau on the training loss instead.
        scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(
            optimizer,
            mode="min",
            factor=tcfg["scheduler"]["factor"],
            patience=tcfg["scheduler"]["patience"],
            min_lr=tcfg["scheduler"]["min_lr"],
        )
        print("No LR schedule supplied - stepping ReduceLROnPlateau on train loss")

    criterion = getattr(torch.nn, tcfg.get("criterion", "L1Loss"))()
    model_path = os.path.join(model_save_dir, artifact_name)

    for epoch in range(1, epochs + 1):
        if lr_schedule:
            # Clamp: stage 1 may have stopped earlier than `epochs` (it cannot
            # be shorter than best_epoch, but stay safe) - hold the last LR.
            epoch_lr = lr_schedule[min(epoch, len(lr_schedule)) - 1]
            for group in optimizer.param_groups:
                group["lr"] = epoch_lr

        model.train()
        total_loss = 0
        n_samples = 0

        for batch in train_loader:
            optimizer.zero_grad()
            if is_graph:
                batch = batch.to(DEVICE)
                out = model(batch)
                loss = criterion(out, batch.y)
                bs = batch.num_graphs
            else:
                x, y = batch
                x, y = x.to(DEVICE), y.to(DEVICE)
                out = model(x)
                loss = criterion(out, y)
                bs = x.size(0)

            loss.backward()
            optimizer.step()
            total_loss += loss.item() * bs
            n_samples += bs

        train_loss = total_loss / n_samples

        epoch_lr = optimizer.param_groups[0]["lr"]
        print(f"Epoch: {epoch:02d}/{epochs}, Train Loss: {train_loss:.4f}, " f"LR: {epoch_lr:.2e}")

        if scheduler is not None:
            scheduler.step(train_loss)
            next_lr = optimizer.param_groups[0]["lr"]
            if next_lr < epoch_lr:
                print(f"  LR reduced: {epoch_lr:.2e} -> {next_lr:.2e} " f"(from the next epoch)")

    torch.save(
        _build_bundle(model, cfg, atom_map=atom_map, tokenizer=tokenizer),
        model_path,
    )

    # Fresh unshuffled loader so predictions line up with the input rows.
    eval_loader = Loader(train_data, batch_size=tcfg["batch_size_valid"], shuffle=False)
    train_preds, train_true = _eval_loader(model, eval_loader, is_graph, DEVICE)
    train_mae = mean_absolute_error(train_true, train_preds)

    print(f"\n=== Full-data Refit ===")
    print(f"Epochs: {epochs}")
    print(f"Train MAE: {train_mae:.4f}  (in-sample - not a generalization estimate)")
    print(f"Model saved: {model_path}")

    return {
        "train_preds": train_preds,
        "train_mae": train_mae,
        "epochs": epochs,
        "best_model_path": model_path,
    }


def load_bundle(model_path):
    """Load a bundle saved by run_train / custom.fit."""
    return torch.load(str(model_path), map_location="cpu", weights_only=False)


def _featurize_for_inference(smiles_list, bundle):
    """Reconstruct dataset and the data_list/tokenizer needed by _build_model."""
    cfg = bundle["cfg"]
    is_graph, _ = _parse_model_type(cfg["model"]["type"])

    if is_graph:
        atom_map = bundle["atom_map"]
        if not atom_map:
            raise ValueError("Bundle is missing atom_map; the artifact is not a valid graph model.")
        graphs = [smiles_to_graph(s, atom_map, None) for s in smiles_list]
        return graphs, graphs, None  # eval_data, data_list, tokenizer
    tokenizer = _restore_tokenizer(bundle["tokenizer_vocab"])
    ds = SMILESDataset(
        list(smiles_list),
        None,
        tokenizer,
        max_length=cfg["data"]["max_length"],
    )
    return ds, None, tokenizer


def _predict_with_bundle(smiles_list, bundle):
    """Run inference given an already-loaded bundle. Returns np.ndarray."""
    if len(smiles_list) == 0:
        # Graph models infer input dim from data_list[0]; an empty payload
        # would raise in _build_model before _eval_loader's empty-loader guard.
        return np.zeros((0,), dtype=np.float32)

    cfg = bundle["cfg"]
    is_graph, _ = _parse_model_type(cfg["model"]["type"])

    eval_data, data_list, tokenizer = _featurize_for_inference(smiles_list, bundle)

    DEVICE = "cuda" if torch.cuda.is_available() else "cpu"

    # Build once per loaded bundle. DRUM hands score() the same object that
    # load_model returned on every request, so rebuilding here re-ran Xavier
    # init over the whole network (~550k parameters for the shipped DMPNN)
    # and reprinted the sequence model's init banner on each prediction,
    # only to overwrite it all with load_state_dict microseconds later.
    model = bundle.get("_model")
    if model is None:
        model, _ = _build_model(cfg, data_list=data_list, tokenizer=tokenizer)
        model.load_state_dict(bundle["state_dict"])
        model = model.to(DEVICE)
        bundle["_model"] = model

    Loader = PyGDataLoader if is_graph else TorchDataLoader
    loader = Loader(
        eval_data,
        batch_size=cfg["training"].get("batch_size_test", 128),
        shuffle=False,
    )

    preds, _ = _eval_loader(model, loader, is_graph, DEVICE)
    return preds


def predict(smiles_list, model_path):
    """Predict from a list of SMILES strings using a saved bundle artifact.

    The bundle (written by run_train) carries the cfg, atom_map / tokenizer
    vocabulary, and state_dict needed to rebuild the exact training model
    and re-featurize new inputs identically.

    Returns:
        numpy array of predictions (shape [N]).
    """
    bundle = load_bundle(model_path)
    preds = _predict_with_bundle(smiles_list, bundle)
    print(f"Predicted {len(preds)} samples")
    return preds
