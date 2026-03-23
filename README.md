# urbs-extension (technology sourcing)

This repository contains a research fork/extension of the **urbs** energy system optimization model (TUM-ENS) with additional functionality for technology sourcing / learning-rate (LR) scenario analysis.

- Upstream/base project: https://github.com/tum-ens/urbs
- License: GNU GPL v3 (see `LICENSE`)

## What this repo does (high-level)

This code runs an **intertemporal energy system optimization** and produces results (including Excel outputs) for different *learning rate* assumptions. The main entry point for reviewers is:

- `run_model.py` (CLI runner)

A typical run is:

```bash
python run_model.py --mode perfect --lr LR1
```

## Repository structure

- `urbs/` – core urbs model code (Pyomo model, IO, reporting, plotting)
- `urbs/extension` - core extension model code (defined as abstract interoperable scripts)
- `Input/` – model input datasets (the default run expects `Input/urbs_intertemporal_2050/`)
- `run_model.py` – main command-line runner for the LR scenarios
- `run_all_after_another.sh` – convenience script to run multiple LR scenarios sequentially
- `urbs-env.yml` – conda environment definition used in CI and for local installation
- `requirements.txt` – pip-style dependency list (kept for convenience; conda env is recommended)

## Quickstart (recommended)

### 1) Clone the repository

```bash
git clone https://github.com/oitzingermaximilian/urbs-technologysourcing.git
cd urbs-technologysourcing
```

### 2) Create the conda environment

This repository ships an environment file `urbs-env.yml`.

```bash
conda env create -f urbs-env.yml
conda activate urbs-env
```

Sanity-check the environment:

```bash
python --version
python -c "import pyomo; print('pyomo:', pyomo.__version__)"
```

### 3) Run the model (example used for review)

Run **perfect foresight** with learning rate scenario **LR1**:

```bash
python run_model.py --mode perfect --lr LR1
```

This will:

- set `URBS_LR` internally based on `--lr`
- load the default input folder: `Input/urbs_intertemporal_2050`
- create a timestamped output directory under `result/` (via `urbs.prepare_result_directory`)
- run the scenario(s) defined inside `run_model.py` (currently `scenario_min_min_min` is enabled)

### 4) Outputs

After a run, look in:

- `result/` – each run creates a timestamped run folder (name includes the learning rate)

The run copies the used input data and the used run script into the result folder for reproducibility.

## CLI options (run_model.py)

`run_model.py` supports:

- `--mode {perfect}` (default: `perfect`)
- `--lr {LR1,LR3_5,LR4,LR5,LR6,LR7,LR8,LR9,LR10,LR25}` (default: `LR5`)
- `--window N` (used by the alternative myopic mode code path)

Examples:

```bash
# perfect foresight, LR1
python run_model.py --mode perfect --lr LR1

# rolling horizon (runs multiple windows), LR5
python run_model.py --mode rolling --lr LR5
```

## Solver notes

The default solver in `run_model.py` is currently set to:

- `gurobi`

If you do not have a Gurobi license available, you have two options:

1. Install and configure Gurobi properly (and ensure `gurobipy` works in the environment).
2. Switch to an open-source solver (e.g. `glpk`) by editing `run_model.py` and changing:

```python
solver = "gurobi"
```

to

```python
solver = "glpk"
```

## Reproducing results / changing scenarios

The list of scenarios executed is defined in `run_model.py` in the `scenarios = [...]` list.

To run additional scenarios, uncomment the desired entries in that list.

## Troubleshooting

- **Environment creation fails:** try updating conda and using conda-forge (or recreate from scratch):
  ```bash
  conda env remove -n urbs-env
  conda env create -f urbs-env.yml
  ```
- **Gurobi errors:** verify you can run:
  ```bash
  python -c "import gurobipy; print(gurobipy.gurobi.version())"
  ```
- **Missing input data:** the default run expects `Input/urbs_intertemporal_2050/` to exist.

## Citation

If you use this work academically, please also cite the original **urbs** model by TUM-ENS and any related publications.
