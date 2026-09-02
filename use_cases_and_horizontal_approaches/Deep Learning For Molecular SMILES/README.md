# Deep learning for molecular SMILES: train and deploy on DataRobot

**Author:** senkin.zhan@datarobot.com

[Example data](input/train.csv) · [held-out test set](input/test.csv) — polymer SMILES strings
labelled with the target property `Tc`.

Read this as a standalone page: **[English](docs/README_EN.html)** · **[日本語](docs/README_JP.html)**

## Problem framing

SMILES (Simplified Molecular Input Line Entry System) is a textual representation of molecular
structures. The companion accelerator
[Feature engineering for molecular SMILES](https://github.com/datarobot-community/ai-accelerators/tree/main/use_cases_and_horizontal_approaches/Feature%20Engineering%20For%20Molecular%20SMILES)
turns those strings into tabular features (descriptors, fingerprints, TF-IDF, pretrained
embeddings) and hands them to DataRobot Autopilot.

This accelerator takes the other route: rather than engineering features up front, it learns the
representation end-to-end with a PyTorch model that reads the molecule directly — either as a
**molecular graph** (DMPNN over RDKit-built graphs) or as a **character sequence**
(LSTM / CNN / Transformer over a SMILES tokenizer).

The point is that **both halves run on DataRobot**. A custom deep learning architecture normally
lives outside the platform, which means training it somewhere else and hand-rolling a serving
stack. Here the whole lifecycle stays in one place:

* **Train on DataRobot** — the notebooks run as-is in a DataRobot codespace or on DataRobot
  Notebooks, on CPU or on a GPU environment.
* **Deploy on DataRobot** — the trained PyTorch model is packaged as a **custom inference model**,
  registered in the Model Registry, and deployed to a DataRobot deployment, where it is governed,
  monitored, and scored through the standard prediction API like any DataRobot model.

## Accelerator overview

Everything is driven by a single config file, [`config/config.yaml`](config/config.yaml) — model
architecture, training hyper-parameters, **and** the deployment compute. Switch `model.type`
between `dmpnn`, `lstm`, `cnn`, `transformer` (or a `+`-joined combination such as
`lstm+cnn+transformer`) and rerun — no code changes. It is recommended to run these notebooks in a
DataRobot codespace; a GPU environment speeds up training but is not required.

```
train.ipynb                        deploy.ipynb                     predict.ipynb
─────────────                      ────────────                     ─────────────
input/*.csv  ──►  model/smiles_model.pth  ──►  Registry → Workshop  ──►  Deployment
  (data)          src/**  ──►  deploy/model_lib.py   (custom model)      (batch scoring)
                  (rebuilt by deploy.ipynb §3)
```

This accelerator's workflow is summarized below.

1. Featurize SMILES with RDKit — either into PyTorch Geometric molecular graphs with
   chemistry-aware atom and bond features, or into token sequences with a character-level
   SMILES tokenizer.
2. Train the selected architecture in two stages: hold out 20 % of `train.csv` to locate the
   epoch at which validation MAE bottoms out, then refit on the full training set for exactly
   that many epochs.
3. Save a self-contained **bundle artifact** — weights plus the config, atom map, and tokenizer
   vocabulary — so inference never depends on the training CSVs and the vocabulary cannot drift.
4. Flatten the inference subset of `src/` into a single `deploy/model_lib.py` and package it with
   the DRUM hooks in `deploy/custom.py`.
5. Upload to the DataRobot Custom Model Workshop, build dependencies, run the built-in custom
   model test, and register the model version.
6. Deploy the registered version onto a resource bundle chosen from the config, then score the
   held-out test set through the deployment and compare it against local predictions.

---

## 1. Repository layout

| Path | What it is |
|---|---|
| `config/config.yaml` | Single source of truth: target, model architecture, training hyper-parameters, **and deployment compute** |
| `input/` | Pre-materialized `train.csv` / `test.csv` (columns: `SMILES`, `Tc`). The old `valid.csv` was merged into `train.csv`; `train.ipynb` carves its own holdout. |
| `model/` | Training output: `smiles_model.pth` (bundle) and `test_preds_*.csv` |
| `src/` | Library code — data, models, trainer (see below) |
| `train.ipynb` | Train + save the best model bundle |
| `predict.ipynb` | **Score through the DataRobot deployment** (no torch needed) |
| `deploy.ipynb` | Rebuild `model_lib.py` → upload → build deps → test → register → deploy → verify predictions |
| `deploy/` | Exactly what gets uploaded: `custom.py`, `model_lib.py`, `model-metadata.yaml`, `requirements.txt` |
| `Deep_Learning_For_Molecular_SMILES.config.yaml` | AI Accelerator metadata (title, entry notebook, maintainers) |
| `docs/` | Standalone HTML renderings of this README — [English](docs/README_EN.html) / [日本語](docs/README_JP.html) |

### `src/` modules

```
src/config.py               load_config (YAML path or dict passthrough)
src/utils.py                seed_everything
src/data/loader.py          load_split / load_or_split, split_train_valid,
                            build_atom_map, build_tokenizer
                            + in-memory variants used by custom.fit
src/data/smiles_data.py     SMILESTokenizer, SMILESDataset
src/data/graph_features.py  smiles_to_graph + chemistry-aware atom/bond features
src/models/_scatter.py      torch_scatter-independent scatter_add (see §8)
src/models/dmpnn.py         EnhancedChemPropDMPNN; create_enhanced_chemprop_dmpnn
                            is the factory _build_model uses
src/models/sequence.py      SequenceNN (lstm / cnn / transformer, combinable)
src/models/pooling.py       attention / global_attention / set2set graph readouts
src/training/trainer.py     _parse_model_type, _build_model, _build_bundle,
                            run_train, run_train_full, load_bundle, predict
```

---

## 2. Environments

A DataRobot codespace is the intended environment for all three notebooks.

| Notebook | Needs |
|---|---|
| `train.ipynb` | torch (preinstalled on the PyTorch image); the first cell installs `rdkit`, `torch-geometric` and `PyYAML` from `deploy/requirements.txt` |
| `deploy.ipynb`, `predict.ipynb` | `datarobot>=3.4`, pandas, numpy, PyYAML — nothing is trained or scored locally, so no torch or rdkit |

### DataRobot credentials

Read in this order by both notebooks:

1. `DATAROBOT_ENDPOINT` / `DATAROBOT_API_TOKEN` environment variables
2. `~/.config/datarobot/drconfig.yaml`

```yaml
# ~/.config/datarobot/drconfig.yaml
endpoint: https://app.datarobot.com/api/v2
token: <your API key>
```

> The endpoint must match the cluster the key was issued on. A key from another cluster
> returns `401 {"message": "Invalid Authorization header"}`, which looks identical to an
> expired key. Keys are managed at `<app>/account/developer-tools`.

---

## 3. Configuration reference (`config/config.yaml`)

```yaml
seed: 42
target: Tc

paths:
  input: input/
  model: model/
  artifact_name: smiles_model.pth          # what train.ipynb writes / deploy.ipynb uploads
  stage1_artifact_name: smiles_model_stage1.pth

data:
  smiles_column: SMILES
  max_length: 200          # sequence models: max token length (START+SMILES+END)
  valid_ratio: 0.2         # stage-1 holdout carved out of train.csv (0.2 -> 4:1)

model:
  type: lstm               # dmpnn | lstm | cnn | transformer, or "+"-joined: lstm+cnn+transformer
  hidden_dim: 300
  dropout: 0.1
  pooling: mean            # graph: mean|max|sum|attention|global_attention|set2set
                           # sequence: mean|max|last (lstm, cnn, and transformer)
  dmpnn: {...}             # depth, activation, ffn_*, norms, residuals
  sequence: {...}          # embedding_dim, num_layers, num_heads, cnn_kernels

training:
  epochs: 400
  batch_size_train: 16
  lr: 0.001
  scheduler: {factor: 0.5, patience: 20, min_lr: 1.0e-6}   # ReduceLROnPlateau on valid MAE
  early_stopping: {patience: 200, min_delta: 0.00001}
  criterion: L1Loss

predict:                   # read by predict.ipynb
  scoring_csv: input/test.csv   # DR_SCORING_CSV overrides
  row_limit:               # empty = all rows

deploy:                    # read by deploy.ipynb / predict.ipynb
  model_name: smiles_deep_learning_regression   # custom model name = deployment label
  model_description: SMILES -> Tc regression ...
  base_environment_search: pytorch   # substring match; or pin base_environment_id
  is_major_update: true    # version bump on re-upload: v2.0 vs v1.1
  dependency_build_max_wait: 3600
  scoring_sample_csv: input/test.csv   # smoke test through the deployment
  scoring_sample_rows: 20
  steps: {rebuild_model_lib: true, create_new_version: true, ...}  # DR_* env vars override
  instance: cpu            # cpu | gpu
  cpu_cores: 2             # minimum cores
  memory_gb: 6             # minimum memory
  gpu_count: 0             # >= 1 when instance: gpu
  replicas: 1
  resource_bundle_id:      # optional: pin a bundle and skip auto-selection
  deployment_id: 6a68...   # cache written back by hand; label lookup is the fallback
```

Every tunable the notebooks use lives here — the notebooks define no parameters of
their own beyond code layout (`deploy/`, `model/`, `config/config.yaml` paths).

`model.type` decides **both** the model and the data pipeline
(`trainer._parse_model_type` → PyG `DataLoader` for graphs, plain `DataLoader` for sequences).
The notebooks branch on the same flag; no code changes are needed to switch.

`deploy.instance` + `cpu_cores` + `memory_gb` + `gpu_count` are treated as **minimums** —
deploy.ipynb picks the *smallest* DataRobot resource bundle that satisfies all of them.
The full bundle catalogue is listed as comments at the bottom of `config/config.yaml`
and printed live by section 7 of the notebook.

---

## 4. Step 1 — Train (`train.ipynb`)

Training runs in **two stages**. `input/test.csv` is never touched.

1. `load_split(cfg)` reads `input/{train,test}.csv`, then `split_train_valid(train_df, cfg)`
   carves a 4:1 holdout out of `train.csv` (`data.valid_ratio`, seeded by `seed`).
2. Builds the featurizer from **`train.csv` only** — held-out `test.csv` never
   contributes atom types or characters. Unseen symbols at score time land on a
   zero one-hot / `<UNK>`:
   * graph models → `build_atom_map` → `smiles_to_graph`
   * sequence models → `build_tokenizer` → `SMILESDataset`
3. **Stage 1** — `run_train(...)` trains on the 80 % sub-train with `L1Loss`,
   `ReduceLROnPlateau` on holdout MAE and early stopping. It returns `best_epoch` (the epoch
   where holdout MAE bottomed out) plus `lr_history`; its checkpoint goes to
   `model/smiles_model_stage1.pth` so it does not clobber the deployable artifact.
4. **Stage 2** — `run_train_full(...)` retrains from scratch on **all** of `train.csv` for
   exactly `best_epoch` epochs, replaying stage 1's per-epoch learning rate via
   `lr_schedule=`. No validation set, so no early stopping: the weights at the final epoch
   are saved to `model/smiles_model.pth`.

> The epoch count carries over as-is. The full set is ~25 % larger than stage 1's sub-train,
> so each stage-2 epoch is ~25 % more gradient steps.

### The artifact is a bundle, not bare weights

```python
{
  "state_dict": ...,        # model weights
  "cfg": ...,               # the config used for training
  "target": "Tc",
  "smiles_col": "SMILES",
  "atom_map": {...},        # graph models
  "tokenizer_vocab": {...}, # sequence models
}
```

Because the featurizer state travels inside the artifact, inference never needs the
training CSVs and vocabulary drift is impossible. Built by `trainer._build_bundle`,
loaded by `trainer.load_bundle`. The DRUM `fit` hook writes the exact same shape.

Local inference, without going through DataRobot (still supported):

```python
from src.training.trainer import predict
preds = predict(["*CC(*)C(=O)c1ccc(C)cc1"], "model/smiles_model.pth")
```

---

## 5. Step 2 — Build the deployment bundle

DataRobot custom model uploads don't reliably preserve subdirectories, so `src/**` is
concatenated into one flat module. **This runs automatically in section 3 of
`deploy.ipynb`** — there is no separate build script to remember.

The generated `deploy/model_lib.py`:

* concatenates the modules listed in `MODEL_LIB_SOURCES` **in topological order**,
* strips intra-package imports (`from .pooling import ...`, `from src... import ...`)
  since everything ends up in one namespace,
* preserves every external import and every class/function body verbatim,
* rewrites legacy `torch_scatter` imports to the PyG-based fallback,
* prepends an env prelude (`USER` / `HOME` / `TORCHINDUCTOR_CACHE_DIR`) because the DRUM
  container runs under a uid with no `/etc/passwd` entry, while `torch._dynamo` calls
  `getpass.getuser()` at import time.

The rebuilt file is syntax-checked before upload. Set `DR_REBUILD_MODEL_LIB=0` to upload
the existing `deploy/model_lib.py` untouched.

`deploy/` — the complete upload set:

| File | Role |
|---|---|
| `custom.py` | DRUM hooks: `fit`, `load_model(code_dir)`, `score(data, model)` |
| `model_lib.py` | Generated flat library (~70 KB) |
| `model-metadata.yaml` | `type: inference`, `targetType: regression`, `targetName: Tc` |
| `requirements.txt` | `torch==2.12.1`, `rdkit`, `torch-geometric`, `PyYAML` (numpy/pandas/sklearn come from the base image; `torch-scatter` deliberately omitted — see §8) |

There is **no `.pth` in `deploy/`** — the notebook always uploads the freshest artifact
from `model/smiles_model.pth` and prints its mtime.

`load_model` is registered because the artifact is a dict bundle; without it DRUM's
default `.pth` autoloader would try to call it as a `nn.Module`. `score()` delegates to
`trainer._predict_with_bundle`, i.e. the identical inference path used locally.

### Optional: test DRUM locally

```bash
drum fit --code-dir . --input input/train.csv --target-type regression \
         --target Tc --output /tmp/drum_out
```

`fit` uses the same splitter as `train.ipynb` (`split_train_valid`, seeded
permutation, `data.valid_ratio` default 0.2 → 80/20) and the same two-stage
schedule: holdout to locate `best_epoch`, then a full-data refit for that many
epochs replaying stage 1's learning-rate trajectory. The deployable bundle is
written to DRUM's output dir as `smiles_model.pth`.

---

## 6. Step 3 — Deploy (`deploy.ipynb`)

Sections:

| § | Step |
|---|---|
| 1 | Connect (prints SDK version, endpoint, app root) |
| 2 | Settings — names, target, compute read from `config/config.yaml`, step toggles |
| 3 | **Rebuild `deploy/model_lib.py` from `src/`** (see §5) |
| 4 | Collect files — code from `deploy/` (any `.pth` skipped) + `model/smiles_model.pth` |
| 5 | Pick base execution environment (`[DataRobot] Python 3.12 PyTorch Drop-In`) |
| 6 | **Pick the compute** — smallest resource bundle satisfying the config minimums |
| 7 | Create *or reuse* the custom model `smiles_deep_learning_regression` |
| 8 | Upload the files as a new version (with `resourceBundleId` + `replicas`) |
| 9 | Build the dependency image from `requirements.txt` (skipped if already built) |
| 10 | Print the workshop URL |
| 11 | Custom model test (the same checks as the workshop *Test* tab) |
| 12 | Register in the Registry + deploy (model replacement on re-run) |
| 13 | Final test — real predictions through the deployment, MAE vs. ground truth |

### Step toggles

Defaults come from `deploy.steps` in `config/config.yaml`; each can still be
overridden at runtime with an environment variable (`1/true/yes` = on):

| Variable | Default | Effect when `0` |
|---|---|---|
| `DR_REBUILD_MODEL_LIB` | on | Upload `deploy/model_lib.py` as-is instead of regenerating it from `src/` |
| `DR_CREATE_NEW_VERSION` | on | Reuse the latest existing version instead of uploading a new one |
| `DR_BUILD_DEPENDENCIES` | on | Skip the dependency image build |
| `DR_RUN_MODEL_TEST` | on | Skip the workshop test |
| `DR_REGISTER_AND_DEPLOY` | on | Stop after the workshop (no registry / deployment) |
| `DR_RUN_PREDICTION_TEST` | on | Skip the final scoring check |

```bash
# resume after a transient network failure without stacking a new version
export DR_CREATE_NEW_VERSION=0     # then re-run deploy.ipynb
```

### Compute selection

```
instance: cpu → only CPU bundles;  instance: gpu → only bundles with GPUs
filter: cores >= cpu_cores AND memory >= memory_gb AND gpus >= gpu_count
pick:   the smallest remaining bundle (prints every candidate)
```

With `cpu / 2 cores / 6 GB` the notebook selects `cpu.4xlarge` (4XL: 2 cores, 6 GB).
If nothing matches, it raises an error listing every available bundle.

Bundles come from `datarobot.models.resource_bundle.ResourceBundle.list()` filtered on
`"customModel" in use_cases`. The SDK's `create_clean()` has no `resource_bundle_id`
parameter, so the notebook passes it through `CustomModelVersion._create(..., extra_upload_data=[("resourceBundleId", ...)])`
and falls back to `create_clean` + `PATCH` if that private API changes.
Without an explicit bundle DataRobot defaults to `cpu.medium` (1 core / 1 GB), which is
too small for torch + rdkit.

### Idempotency

* The custom model is looked up by name and reused.
* On re-run the existing deployment (matched by label) gets a **model replacement**
  instead of a second deployment.
* An already-built dependency image is detected and not rebuilt.

---

## 7. Step 4 — Predict (`predict.ipynb`)

Scores through the deployment, so it needs **no torch / rdkit / `src.training`** —
only the DataRobot SDK.

| § | Step |
|---|---|
| 1 | Connect |
| 2 | Settings from `config/config.yaml` (`target`, `data.smiles_column`, `deploy.model_name`) |
| 3 | Resolve the deployment **on the connected cluster** (id hint → label lookup), print label / status / model / console URL |
| 4 | Load scoring data (default `input/test.csv`) |
| 5 | `BatchPredictionJob.score_pandas` → picks the `*_PREDICTION` column automatically |
| 6 | Metrics: MAE / RMSE / R² + `describe()` |
| 7 | Save `model/test_preds_{model_type}.csv` |

Defaults come from the `predict:` block in `config/config.yaml` (`scoring_csv`,
`row_limit`); `DR_SCORING_CSV` and `DR_DEPLOYMENT_ID` override at runtime.

**Cluster-independent by design.** The deployment is identified by its **label**
(`deploy.model_name`, default `smiles_deep_learning_regression`), which `deploy.ipynb` sets
when it creates the deployment. `deploy.deployment_id` is only a cache to skip the lookup —
ids belong to one cluster, so a value from `app.datarobot.com` will not resolve on
`app.jp.datarobot.com`, and the notebook silently falls back to the label lookup instead of
failing. Only when no deployment carries that label on the connected cluster does it stop and
tell you to run `deploy.ipynb` there first.

---

## 8. Running the training on DataRobot Notebooks

This folder is self-contained (`config/`, `input/`, `src/`, `train.ipynb`,
`predict.ipynb`, `deploy.ipynb`, `deploy/`). Upload it to a DataRobot Notebook session or
open it in a codespace and run `train.ipynb` there — no other setup is required.

Two portability fixes make the same code run locally and on DataRobot:

1. **`torch_scatter` is optional, and cannot be installed via `requirements.txt`.**
   `src/models/_scatter.py` provides `scatter_add` with a three-level fallback —
   `torch_scatter` → `torch_geometric.utils.scatter(reduce="sum")` → pure-torch
   `scatter_add_`. A mismatched `torch_scatter` wheel raises **`OSError`** when loading
   `_scatter_cuda.so` (not `ImportError`), so both are caught. Verified to be numerically
   identical to the reference implementation.

   > DataRobot's dependency manager parses `requirements.txt` itself and accepts only
   > `name` + version-constraint lines; a `--find-links` line fails the build with
   > `422 ... does not contain a valid package name for python`. Since `torch-scatter`
   > ships **no wheels on PyPI** (sdist only) and its prebuilt wheels live behind exactly
   > that index, it is left out of the file entirely. To get the compiled fast path anyway,
   > build a **custom environment** (a Dockerfile, where arbitrary `pip` flags are allowed)
   > instead of relying on dependency management.
2. **No `verbose=` on `ReduceLROnPlateau`.** That argument was deprecated in torch 2.2 and
   removed later (`TypeError` on DataRobot Notebooks). `trainer.py` now compares the LR
   before/after `scheduler.step()` and prints `LR reduced: ... -> ...` itself.

---

## 9. Common workflows

```bash
# A. Change architecture and retrain
#    edit config/config.yaml -> model.type: dmpnn
#    run train.ipynb
#    run deploy.ipynb   (§3 rebuilds model_lib.py, then uploads + replaces the deployed model)
#    run predict.ipynb  (scores input/test.csv through the deployment)

# B. Only bump the deployment compute
#    edit config/config.yaml -> deploy.instance / cpu_cores / memory_gb / gpu_count
#    run deploy.ipynb

# C. Score a different file
#    export DR_SCORING_CSV=input/test.csv, then run predict.ipynb
```

> Switching `deploy.instance` to `gpu` selects a GPU bundle, but the base execution
> environment stays the same — confirm the drop-in image ships a CUDA-enabled torch
> before relying on GPU inference.
