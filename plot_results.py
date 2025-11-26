from matplotlib import ticker as mticker
from pathlib import Path
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import seaborn as sns
from sklearn.preprocessing import StandardScaler
from sklearn.cluster import DBSCAN
import plotly.graph_objects as go
import matplotlib.patches as mpatches
from matplotlib.lines import Line2D
from plotly.subplots import make_subplots
import math
import matplotlib.patheffects as pe

# -------------------------------
# Configuration
# -------------------------------

plt.rcParams["font.family"] = "Arial"
plt.rcParams["font.size"] = 8  # around 6–8 pt target at print size
plt.rcParams["pdf.fonttype"] = 42  # ensures fonts are embedded properly in vector outputs
plt.rcParams["ps.fonttype"] = 42
print(plt.rcParams["font.family"])

BASE_PATH = Path("C:/Users/maxoi/OneDrive/Desktop/results_crm_paper/base")
NZIA_PATH = Path("C:/Users/maxoi/OneDrive/Desktop/results_crm_paper/NZIA")
LNG_LOWEST_PATH = Path("C:/Users/maxoi/OneDrive/Desktop/results_crm_paper/lng_lowest")

LR_FOLDERS = ["LR1", "LR3_5", "LR4", "LR5", "LR6", "LR7", "LR8", "LR9", "LR10"]

SCENARIO_NAMES = [
    "scenario_min_min_min", "scenario_min_min_avg", "scenario_min_min_high",
    "scenario_min_avg_min", "scenario_min_avg_avg", "scenario_min_avg_high",
    "scenario_min_high_min", "scenario_min_high_avg", "scenario_min_high_high",
    "scenario_avg_min_min", "scenario_avg_min_avg", "scenario_avg_min_high",
    "scenario_avg_avg_min", "scenario_avg_avg_avg", "scenario_avg_avg_high",
    "scenario_avg_high_min", "scenario_avg_high_avg", "scenario_avg_high_high",
    "scenario_high_min_min", "scenario_high_min_avg", "scenario_high_min_high",
    "scenario_high_avg_min", "scenario_high_avg_avg", "scenario_high_avg_high",
    "scenario_high_high_min", "scenario_high_high_avg", "scenario_high_high_high",
]

GROUPS = {
    "Fossil fuels": [
        "Coal Plant", "Coal Plant CCUS", "Gas Plant (CCGT)", "Gas Plant (CCGT) CCUS",
        "Lignite Plant", "Lignite Plant CCUS", "Oil Plant", "Other non-res"
    ],
    "Renewables":[
        "Hydro (reservoir)", "Hydro (run-of-river)", "solarPV", "windoff", "windon","Biomass Plant"
    ],
    "Thermal nuclear": ["Nuclear Plant"]
}

GROUP_COLORS = {
    "Fossil fuels": "#8C564B", #F4C20D"
    "Renewables": "#009688",
    "Thermal nuclear": "#E6AC00"
}

IMPROVED_RENEWABLE_COLORS = {
    "Hydro (reservoir)": "#0072B2",      # strong blue
    "Hydro (run-of-river)": "#56B4E9",   # lighter blue
    "Solar PV": "#E69F00",               # bright orange/gold
    "Wind onshore": "#66C2A5",           # light vibrant green
    "Wind offshore": "#00876C",          # darker rich green
    "Biomass": "#CC79A7",                # magenta for contrast
    "Non-renewables": "#595959"          # dark neutral grey
}


PROCESS_MAP = {
    "Hydro (reservoir)": "Hydro (reservoir)",
    "Hydro (run-of-river)": "Hydro (run-of-river)",
    "Solar PV": "solarPV",
    "Wind onshore": "windon",
    "Wind offshore": "windoff",
    "Biomass": "Biomass Plant"
}


# -------------------------------
# Centralized Data Loading Functions
# -------------------------------
def build_scenario_dict():
    """Build dictionary of all NZIA scenarios"""
    nzia_scenarios = {}
    for lr in LR_FOLDERS:
        lr_path = NZIA_PATH / lr
        for scenario in SCENARIO_NAMES:
            scenario_file = lr_path / f"{scenario}.xlsx"
            nzia_scenarios[(lr, scenario)] = scenario_file
    return nzia_scenarios


def get_base_scenario():
    """Get base scenario path"""
    return BASE_PATH / "LR1" / "scenario_high_high_high.xlsx"

def get_lng_best_case_scenario():
    """Get LNG best-case scenario path"""
    return LNG_LOWEST_PATH / "scenario_min_min_min.xlsx"

def mwh_to_bcm(mwh):
    """Convert MWh to BCM (billion cubic meters of natural gas equivalent)"""
    mmbtu = mwh * 3.412  # 1 MWh = 3.412 MMBtu
    bcm = mmbtu / 35_315_000  # 1 BCM = 35,315,000 MMBtu
    return bcm


def load_lng(file_path, years=range(2024, 2041)):
    """Centralized LNG data loading function"""
    df = pd.read_excel(file_path, sheet_name="gas demand per block")
    df["blocks"] = df["blocks"].astype(str).str.strip()
    df["stf"] = df["stf"].ffill()
    lng_df = df[~df["blocks"].str.lower().str.contains("pipegas")]
    lng_df = lng_df[lng_df["stf"].between(min(years), max(years))]

    yearly = lng_df.groupby("stf")["gas_usage_block"].sum().reset_index()
    yearly["lng_bcm"] = yearly["gas_usage_block"].apply(mwh_to_bcm)

    series = pd.Series(0, index=years, dtype=float)
    for _, row in yearly.iterrows():
        series[int(row["stf"])] = row["lng_bcm"]
    return series


def load_generation_data(file_path, sheet_name="extension_balance", years=range(2025, 2041)):
    """Load generation data from Excel file"""
    df = pd.read_excel(file_path, sheet_name=sheet_name)
    return df[df["Stf"].isin(years)]


def load_scrap_data(file_path, sheet_name="scrap", years=range(2024, 2041)):
    """Load scrap data from Excel file"""
    df = pd.read_excel(file_path, sheet_name=sheet_name)

    # Handle column name variations
    year_col = next((col for col in ["stf", "Stf", "year", "Year"] if col in df.columns), None)
    tech_col = next((col for col in ["tech", "Tech", "key_1", "key1", "technology", "Process","pro"] if col in df.columns),
                    None)
    value_col = next((col for col in ["capacity_scrap_total", "value", "capacity_scrap", "capacity_scrap_tonnes"] if
                      col in df.columns), None)

    if not all([year_col, tech_col, value_col]):
        raise ValueError(f"Missing required columns in {file_path}")

    df[year_col] = df[year_col].ffill()
    df[year_col] = pd.to_numeric(df[year_col], errors="coerce")
    df = df.dropna(subset=[year_col])
    df[year_col] = df[year_col].astype(int)
    df = df[df[year_col].between(min(years), max(years))]

    df[value_col] = pd.to_numeric(df[value_col], errors="coerce").fillna(0)
    return df, year_col, tech_col, value_col


def load_system_costs(file_path, sheet_name="extension_cost", years=range(2024, 2041)):
    """Load system costs data"""
    df = pd.read_excel(file_path, sheet_name=sheet_name)
    df = df[df["stf"].isin(years)]
    df_done = df.groupby("stf")["Total_Cost"].sum()
    return df_done

def load_installed_capacity(file_path):
    """Load installed capacity from 'extension_total_caps' sheet."""
    xls = pd.ExcelFile(file_path)
    df = pd.read_excel(xls, sheet_name="extension_total_caps")
    return df

def identify_capacity_clusters(df, eps=0.7, min_samples=4):
    """
    Identify DBSCAN clusters in a given DataFrame (single tech).
    Groups by year and clusters using Manufacturing + Remanufacturing.
    Returns summary and full DataFrame with cluster_id.
    """
    cluster_summary = []
    clustered_dfs = []

    for year, df_group in df.groupby("year"):
        if len(df_group) < min_samples:
            cluster_summary.append({
                "year": year,
                "num_clusters": 0,
                "num_points": len(df_group),
                "note": "too few points"
            })
            continue

        X = df_group[["Remanufacturing", "Manufacturing"]].values
        X_scaled = StandardScaler().fit_transform(X)

        db = DBSCAN(eps=eps, min_samples=min_samples)
        labels = db.fit_predict(X_scaled)

        df_group = df_group.copy()
        df_group["cluster_id"] = labels
        clustered_dfs.append(df_group)

        n_clusters = len(set(labels)) - (1 if -1 in labels else 0)
        cluster_summary.append({
            "year": year,
            "num_clusters": n_clusters,
            "num_points": len(df_group),
            "noise_points": np.sum(labels == -1)
        })

    df_summary = pd.DataFrame(cluster_summary)
    df_with_clusters = pd.concat(clustered_dfs, ignore_index=True) if clustered_dfs else pd.DataFrame()
    return df_summary, df_with_clusters

def identify_yearly_capacity_clusters(df, years_of_interest=[2025, 2030, 2035, 2040],
                                      eps=0.7, min_samples=2):
    """
    DBSCAN clustering on yearly values, returns summary + DataFrame with cluster_id.
    """
    df_yearly = df[df["year"].isin(years_of_interest)].copy()
    if df_yearly.empty:
        raise ValueError("No data for the specified years_of_interest.")

    X = df_yearly[["Manufacturing", "Remanufacturing"]].values
    X_scaled = StandardScaler().fit_transform(X)

    db = DBSCAN(eps=eps, min_samples=min_samples)
    labels = db.fit_predict(X_scaled)
    df_yearly["cluster_id"] = labels

    # Create summary
    n_clusters = len(set(labels)) - (1 if -1 in labels else 0)
    n_noise = np.sum(labels == -1)
    summary = pd.DataFrame({
        "year": df_yearly["year"],
        "cluster_id": labels,
        "num_clusters": n_clusters,
        "noise_points": n_noise,
        "Manufacturing": df_yearly["Manufacturing"],
        "Remanufacturing": df_yearly["Remanufacturing"]
    })

    return summary, df_yearly

def aggregate_and_cluster_yearly(df, windows=None, eps=0.7, min_samples=2):
    """
    Aggregate yearly data into fixed windows, then run DBSCAN.

    Args:
        df (DataFrame): Must have columns ['year', 'Manufacturing', 'Remanufacturing']
        windows (list of tuples): [(start_year, end_year), ...]
        eps (float): DBSCAN eps
        min_samples (int): DBSCAN min_samples

    Returns:
        summary_df: summary of clusters for each window
        df_with_clusters: aggregated values with cluster_id
    """
    if windows is None:
        windows = [(2024, 2025), (2026, 2030), (2031, 2035), (2036, 2040)]

    records = []
    for i, (start, end) in enumerate(windows, start=1):
        df_window = df[(df["year"] >= start) & (df["year"] <= end)]
        if df_window.empty:
            continue
        records.append({
            "window_id": i,
            "start_year": start,
            "end_year": end,
            "Manufacturing": df_window["Manufacturing"].sum(),
            "Remanufacturing": df_window["Remanufacturing"].sum()
        })

    agg_df = pd.DataFrame(records)
    X = agg_df[["Manufacturing", "Remanufacturing"]].values
    X_scaled = StandardScaler().fit_transform(X)

    db = DBSCAN(eps=eps, min_samples=min_samples)
    labels = db.fit_predict(X_scaled)
    agg_df["cluster_id"] = labels

    # Summary
    n_clusters = len(set(labels)) - (1 if -1 in labels else 0)
    n_noise = np.sum(labels == -1)
    summary_df = pd.DataFrame({
        "window_id": agg_df["window_id"],
        "start_year": agg_df["start_year"],
        "end_year": agg_df["end_year"],
        "Manufacturing": agg_df["Manufacturing"],
        "Remanufacturing": agg_df["Remanufacturing"],
        "cluster_id": labels,
        "num_clusters": n_clusters,
        "noise_points": n_noise
    })

    return summary_df, agg_df

# -------------------------------
# Plotting Functions
# -------------------------------
def plot_base_generation_mix(base_file=None, output_dir="plots"):
    """Plot base scenario generation mix - donut charts and stacked bars"""
    if base_file is None:
        base_file = get_base_scenario()

    years = list(range(2025, 2041))
    df = load_generation_data(base_file, years=years)

    # Prepare yearly aggregated data
    yearly_data = {}
    for year in years:
        year_df = df[df["Stf"] == year]
        summary = {}
        for group, processes in GROUPS.items():
            value = year_df[year_df["Process"].isin(processes)]["Value"].sum() / 1_000_000  # Convert to TWh
            summary[group] = value
        yearly_data[year] = summary

    # 1. Donut Charts (4x4)
    fig, axes = plt.subplots(4, 4, figsize=(16, 16))
    axes = axes.flatten()

    for i, year in enumerate(years):
        data = yearly_data[year]
        total = sum(data.values())
        sizes = [v / total for v in data.values()]

        axes[i].pie(
            sizes,
            labels=list(data.keys()),
            colors=[GROUP_COLORS[k] for k in data.keys()],
            startangle=90,
            wedgeprops=dict(width=0.4, edgecolor="w")
        )
        axes[i].set_title(f"{year} (TWh)", fontsize=12)

    for j in range(i + 1, 16):
        fig.delaxes(axes[j])

    plt.suptitle("Base Scenario Generation Mix (TWh)", fontsize=16)
    plt.tight_layout(rect=[0, 0, 1, 0.96])

    output_path = Path(output_dir) / "base_generation_mix_donut.png"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(output_path, dpi=300)
    plt.show()
    print(f"✔ Base scenario donut chart saved → {output_path}")

    # 2. 100% Stacked Horizontal Bar Chart
    records = []
    group_order = list(GROUPS.keys())
    for year in years:
        year_df = df[df["Stf"] == year]
        totals = {g: year_df[year_df["Process"].isin(GROUPS[g])]["Value"].sum() for g in group_order}
        total_all = sum(totals.values())
        shares = {g: totals[g] / total_all if total_all > 0 else 0 for g in group_order}
        records.append({"year": year, **shares})

    data = pd.DataFrame(records)

    n = len(years)
    fig, ax = plt.subplots(figsize=(10, max(10, 0.52 * n + 3.5)))
    y_pos = np.arange(n)
    left = np.zeros(n)
    bar_height = 0.6

    for g in group_order:
        width = data[g].values * 100
        ax.barh(y_pos, width, left=left, height=bar_height, color=GROUP_COLORS[g],
                edgecolor="white", linewidth=1.2, zorder=5)
        left += width

    ax.set_yticks(y_pos, [str(y) for y in years])
    ax.invert_yaxis()
    ax.set_xlim(0, 100)
    ax.xaxis.set_major_locator(mticker.MultipleLocator(10))
    ax.xaxis.set_major_formatter(mticker.PercentFormatter(xmax=100))
    ax.xaxis.set_ticks_position("top")

    ax.vlines(np.arange(0, 101, 10), -0.5, n - 0.5, colors="white", linewidth=1.5, zorder=7)
    ax.set_facecolor("#E6E6E6")

    #ax.set_title("Current Policies Scenario Generation Share by Year (%)", loc="left",
                 #fontsize=18, fontweight="bold", color="#1F4E79")

    handles = [plt.Rectangle((0, 0), 1, 1, color=GROUP_COLORS[g]) for g in group_order]
    ax.legend(handles, group_order, loc="upper center", bbox_to_anchor=(0.5, -0.06),
              ncol=len(group_order), frameon=False, fontsize=18)

    plt.tight_layout(rect=[0.02, 0.04, 0.98, 0.94])
    ax.tick_params(axis="x", labelsize=18)  # increase x tick label size
    ax.tick_params(axis="y", labelsize=18) # increase y tick label size
    output_path = Path(output_dir) / "Fig1.png"
    plt.savefig(output_path, dpi=300)
    plt.show()
    print(f"✔ Base scenario stacked bar chart saved → {output_path}")

def plot_renewables_breakdown_100pct(
    base_file=None,
    output_dir="plots",
    colors=IMPROVED_RENEWABLE_COLORS,
    years=None
):
    """100% stacked horizontal bar chart showing renewable breakdown.
    - Uses a more readable pastel palette by default.
    - Larger tick-labels and clearer legend patches.
    """
    if base_file is None:
        base_file = get_base_scenario()

    if years is None:
        years = list(range(2025, 2041))

    df = load_generation_data(base_file, years=years)

    # --- Prepare data --- #
    records = []
    group_order = [
        "Hydro (reservoir)", "Hydro (run-of-river)", "Solar PV",
        "Wind onshore", "Wind offshore", "Biomass", "Non-renewables"
    ]

    for year in years:
        year_df = df[df["Stf"] == year]

        totals = {}
        totals["Hydro (reservoir)"] = year_df[year_df["Process"] == "Hydro (reservoir)"]["Value"].sum()
        totals["Hydro (run-of-river)"] = year_df[year_df["Process"] == "Hydro (run-of-river)"]["Value"].sum()
        totals["Solar PV"] = year_df[year_df["Process"] == "solarPV"]["Value"].sum()
        totals["Wind onshore"] = year_df[year_df["Process"] == "windon"]["Value"].sum()
        totals["Wind offshore"] = year_df[year_df["Process"] == "windoff"]["Value"].sum()
        totals["Biomass"] = year_df[year_df["Process"] == "Biomass Plant"]["Value"].sum()

        renewable_processes = [
            "Hydro (reservoir)", "Hydro (run-of-river)", "solarPV",
            "windon", "windoff", "Biomass Plant"
        ]
        totals["Non-renewables"] = year_df[~year_df["Process"].isin(renewable_processes)]["Value"].sum()

        total_all = sum(totals.values())
        shares = {g: (totals[g] / total_all if total_all > 0 else 0) for g in group_order}
        records.append({"year": year, **shares})

    data = pd.DataFrame(records)

    # --- Plot --- #
    n = len(years)
    fig, ax = plt.subplots(figsize=(10, max(10, 0.52 * n + 3.5)))
    y_pos = np.arange(n)
    left = np.zeros(n)
    bar_height = 0.6

    for g in group_order:
        width = data[g].values * 100
        ax.barh(
            y_pos, width, left=left, height=bar_height,
            color=colors[g], edgecolor="white", linewidth=1.2, zorder=5
        )
        left += width

    # Formatting
    ax.set_yticks(y_pos)
    ax.set_yticklabels([str(y) for y in years])
    ax.invert_yaxis()
    ax.set_xlim(0, 100)
    ax.xaxis.set_major_locator(mticker.MultipleLocator(10))
    ax.xaxis.set_major_formatter(mticker.PercentFormatter(xmax=100))
    ax.xaxis.set_ticks_position("top")

    # Increase tick label sizes and padding
    ax.tick_params(axis="x", labelsize=18, pad=8)
    ax.tick_params(axis="y", labelsize=18)

    for lbl in ax.get_yticklabels():
        lbl.set_fontweight("medium")

    # Vertical white grid lines and background
    ax.vlines(np.arange(0, 101, 10), -0.5, n - 0.5, colors="white", linewidth=1.5, zorder=7)
    ax.set_facecolor("#EFEFEF")

    #ax.set_title(
    #    "Renewable Generation Share Breakdown (%)",
    #    loc="left",
    #    fontsize=20,
    #    fontweight="bold",
    #    color="#1F4E79"
    #)

    # Legend: build explicit colored Patch objects so colors show reliably
    # Use a multi-column layout (ncol) to avoid one long single-line legend.
    handles = [
        mpatches.Patch(facecolor=colors[g], edgecolor="#666666", linewidth=0.6, label=g)
        for g in group_order
    ]

    # Choose ncol so legend wraps into multiple rows. With 7 items ncol=3 gives 3 rows.
    ncol = 3
    legend = ax.legend(
        handles=handles,
        loc="upper center",
        bbox_to_anchor=(0.5, -0.16),
        ncol=ncol,
        frameon=False,
        fontsize=18,
        handlelength=1.5,
        handletextpad=0.6,
        columnspacing=1.2
    )

    # Slightly enlarge patch displayed in legend by adjusting legend handlers' sizes (if available)
    # This will affect how large the color boxes look in the legend.
    for lh in legend.legendHandles:
        # most handlers are Patch objects; set a visible edge to help contrast
        try:
            lh.set_linewidth(0.6)
        except Exception:
            pass

    # Give space for legend below the figure and ensure layout isn't clipped
    plt.tight_layout(rect=[0.02, 0.06, 0.98, 0.96])
    plt.subplots_adjust(bottom=0.24)

    output_path = Path(output_dir) / "Fig2.png"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(output_path, dpi=300)
    plt.show()
    print(f"✔ Renewable 100% stacked bar chart saved → {output_path}")
def plot_renewables_installed_capacity_vertical(base_file, output_dir="plots", region="EU27", colors=IMPROVED_RENEWABLE_COLORS):
    """
    Vertical stacked bar plot of renewable installed capacities (GW) 2024-2040.
    - Uses improved color palette
    - Larger tick & label sizes
    - Compact multi-column legend as colored patches (4 columns x wrap)
    """
    # Load data
    df = pd.read_excel(base_file, sheet_name="extension_total_caps")
    df["stf"] = df["stf"].ffill()
    df["sit"] = df["sit"].ffill()
    if region:
        df = df[df["sit"] == region]

    years = list(range(2024, 2041))
    group_order = list(PROCESS_MAP.keys())

    # Prepare data
    records = {g: [] for g in group_order}
    for year in years:
        year_df = df[df["stf"] == year]
        for name, pro in PROCESS_MAP.items():
            records[name].append(year_df[year_df["pro"] == pro]["cap_pro"].sum() / 1000)  # MW → GW

    # Plot
    fig, ax = plt.subplots(figsize=(14, 8))
    bottom = [0] * len(years)

    for g in group_order:
        color = colors.get(g, "#BDBDBD")
        ax.bar(years, records[g], bottom=bottom, color=color, label=g,
               edgecolor="white", width=0.7)
        bottom = [b + v for b, v in zip(bottom, records[g])]

    ax.set_xticks([2024, 2030, 2035, 2040])
    ax.set_xticklabels([str(y) for y in [2024, 2030, 2035, 2040]], fontsize=25)
    # Axis labels and sizing
    #ax.set_xlabel("Year", fontsize=16)
    ax.set_ylabel("Installed Capacity (GW)", fontsize=22)
    #ax.set_title(
    #    "Renewable Installed Capacity by Technology (2024-2040)",
    #    fontsize=20, fontweight="bold", color="#1F4E79", loc="left"
    #)

    # Face and grid
    ax.set_facecolor("#F3F3F3")
    ax.grid(axis="y", color="white", linewidth=1.5, zorder=7)

    # Tick sizes
    ax.tick_params(axis="x", labelsize=22, rotation=0, pad=6)
    ax.tick_params(axis="y", labelsize=22)

    # Legend: use explicit colored Patch objects so colors show reliably
    handles = [
        mpatches.Patch(facecolor=colors.get(g, "#BDBDBD"), edgecolor="#666666", linewidth=0.6, label=g)
        for g in group_order
    ]

    # Place legend below the chart; 4 columns -> will wrap to 2 rows for 7 items
    ncol = 4
    legend = ax.legend(
        handles=handles,
        loc="upper center",
        bbox_to_anchor=(0.5, -0.16),
        ncol=ncol,
        frameon=False,
        fontsize=22,
        handlelength=1.5,
        handletextpad=0.6,
        columnspacing=1.2
    )

    # Make legend boxes more visible
    for lh in legend.legendHandles:
        try:
            lh.set_linewidth(0.6)
        except Exception:
            pass

    plt.tight_layout(rect=[0.02, 0.06, 0.98, 0.94])  # leave extra bottom space
    plt.subplots_adjust(bottom=0.25)  # increase bottom margin

    # Save plot
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / "Fig3.png"
    plt.savefig(output_path, dpi=300)
    plt.show()
    print(f"✔ Vertical stacked bar chart saved → {output_path}")



def plot_scrap_comparison(base_file=None, nzia_scenarios_dict=None, output_dir="plots/scrap_range"):
    """Plot scrap volume comparison between base and NZIA scenarios"""
    if base_file is None:
        base_file = get_base_scenario()
    if nzia_scenarios_dict is None:
        nzia_scenarios_dict = build_scenario_dict()

    years = list(range(2024, 2041))
    out_path = Path(output_dir)
    out_path.mkdir(parents=True, exist_ok=True)

    def _load_scrap_pivot(file_path):
        """Helper to load and pivot scrap data"""
        try:
            df, year_col, tech_col, value_col = load_scrap_data(file_path, years=years)
        except Exception as e:
            print(f"⚠ Could not read {file_path}: {e}")
            return pd.DataFrame(index=years)

        grouped = df.groupby([year_col, tech_col], as_index=True)[value_col].sum().reset_index()
        pivot = grouped.pivot(index=year_col, columns=tech_col, values=value_col).fillna(0)
        pivot = pivot.reindex(years, fill_value=0)
        return pivot / 1e6  # Convert to Mt

    # Load base data
    base_pivot = _load_scrap_pivot(base_file)

    # Load NZIA data
    nzia_files = [f for f in nzia_scenarios_dict.values() if f.exists()]
    nzia_pivots = [_load_scrap_pivot(f) for f in nzia_files]

    # Plot for each technology
    tech_set = set(base_pivot.columns.tolist())
    for p in nzia_pivots:
        tech_set.update(p.columns.tolist())

    for tech in sorted(tech_set):
        # Base series
        base_series = base_pivot[tech].reindex(years).fillna(0) if tech in base_pivot.columns else pd.Series(0.0,
                                                                                                             index=years)

        # NZIA series
        nzia_series_list = []
        for p in nzia_pivots:
            s = p[tech].reindex(years).fillna(0) if tech in p.columns else pd.Series(0.0, index=years)
            nzia_series_list.append(s)

        if not nzia_series_list:
            continue

        nzia_df = pd.DataFrame(nzia_series_list).T
        nz_min = nzia_df.min(axis=1)
        nz_max = nzia_df.max(axis=1)
        nz_mean = nzia_df.mean(axis=1)

        if (base_series.sum() == 0) and (nz_max.max() == 0):
            continue

        # Plot
        fig, ax = plt.subplots(figsize=(6, 4))
        ax.plot(years, base_series.values, color="darkred", linewidth=2.2, label="Base scenario")
        ax.fill_between(years, nz_min.values, nz_max.values, color="seagreen", alpha=0.25, label="NZIA min–max range")
        ax.plot(years, nz_mean.values, color="seagreen", linestyle="--", linewidth=1.5, label="NZIA mean")

        ax.set_title(f"Scrap volume — {tech}")
        ax.set_xlabel("Year")
        ax.set_ylabel("Scrap [Mt]")
        ax.set_xlim(min(years) - 1, max(years) + 1)
        ax.set_xticks([2025, 2030, 2035, 2040])
        ax.grid(True, linestyle="--", alpha=0.3)
        ax.legend()

        plt.tight_layout()
        safe_tech = str(tech).replace("/", "_").replace(" ", "_")
        fname = out_path / f"scrap_range_{safe_tech}.png"
        fig.savefig(fname, dpi=300)
        plt.close(fig)
        print(f"✔ Saved: {fname}")



def plot_lng_analysis(base_file=None, nzia_scenarios_dict=None, lng_file=None,
                      output_dir="plots/lng_analysis"):
    """Comprehensive LNG analysis with NZIA scenario range, LTC overlay, and boxplot"""

    if base_file is None:
        base_file = get_base_scenario()
    if nzia_scenarios_dict is None:
        nzia_scenarios_dict = build_scenario_dict()
    if lng_file is None:
        lng_file = get_lng_best_case_scenario()

    years = range(2025, 2041)
    target_years = [2025, 2030, 2035, 2040]
    out_path = Path(output_dir)
    out_path.mkdir(parents=True, exist_ok=True)

    nzia_files = [f for f in nzia_scenarios_dict.values() if f.exists()]

    # ----------------------------------------------------------------------
    # 1. RANGE PLOT — NZIA scenario range, LTC area, and main trajectories
    # ----------------------------------------------------------------------

    # Long-term contract data (BCM)
    ltc_data = {
        2025: 82, 2026: 85, 2027: 99, 2028: 92, 2029: 92,
        2030: 88, 2031: 86, 2032: 84, 2035: 57, 2040: 48
    }
    ltc_series = pd.Series(ltc_data).sort_index()
    ltc_series = ltc_series.reindex(years).interpolate()

    plt.figure(figsize=(9, 5))
    ax = plt.gca()

    # --- Aggregate NZIA scenario data for range plot ---
    nzia_arrays = []
    for f in nzia_files:
        series = load_lng(f, years)
        nzia_arrays.append(series.values)
    if nzia_arrays:
        nzia_array = np.vstack(nzia_arrays)
        min_vals = np.nanmin(nzia_array, axis=0)
        max_vals = np.nanmax(nzia_array, axis=0)
    else:
        # fallback: empty arrays (avoid errors)
        min_vals = np.zeros(len(list(years)))
        max_vals = np.zeros(len(list(years)))

    # --- NZIA range band ---
    ax.fill_between(
        years, min_vals, max_vals,
        color="#B0C4DE", alpha=0.45,
        label="NZIA scenario range", zorder=1
    )

    # --- Long-term contracts (grey area + dashed line) ---
    ax.fill_between(
        ltc_series.index, 0, ltc_series.values,
        color="#BEBEBE", alpha=0.25, zorder=2
    )
    ax.plot(
        ltc_series.index, ltc_series.values,
        color="#6E6E6E", linewidth=1.6, linestyle="--",
        label="long-term contracts", zorder=3
    )

    # --- Base and Best-case trajectories ---
    base_series = load_lng(base_file, years)
    best_case_series = load_lng(lng_file, years)
    ax.plot(base_series.index, base_series.values,
            color="#1F3A93", linewidth=2.4, label="current policies", zorder=4)
    ax.plot(best_case_series.index, best_case_series.values,
            color="#008080", linewidth=2.4, linestyle="--",
            label="best-case scenario", zorder=5)

    # --- Formatting ---
    ax.set_xlim(min(years) - 1, max(years) + 1)
    ax.set_xticks([2025, 2030, 2035, 2040])
    ax.set_xlabel("Year", fontsize=10)
    ax.set_ylabel("LNG Demand and Supply [bcm]", fontsize=10)
    ax.set_title("LNG demand trajectories vs. long-term contracts",
                 fontsize=12, weight="bold")

    ax.grid(axis="y", linestyle=":", color="0.8", linewidth=0.8)
    ax.legend(frameon=True, fontsize=9, loc="upper right")

    # increase tick label size
    ax.tick_params(axis="x", labelsize=10)
    ax.tick_params(axis="y", labelsize=10)

    plt.tight_layout()
    plt.savefig(out_path / "lng_demand_range_plot.pdf", dpi=600, bbox_inches="tight")
    plt.show()
    print("✔ LNG demand range plot saved")

    # ----------------------------------------------------------------------
    # 2. CUMULATIVE PERCENTAGE DEVIATION BOXPLOT (no outliers shown)
    # ----------------------------------------------------------------------
    base_cumulative = load_lng(base_file, years).cumsum()
    nzia_cumulative = [load_lng(f, years).cumsum() for f in nzia_files]

    # prepare DataFrame where each column is one scenario cumulative series
    # if nzia_cumulative empty, handle gracefully
    if nzia_cumulative:
        data = pd.DataFrame({i: s for i, s in enumerate(nzia_cumulative)}).T
        # pct_dev: columns for target years (we want distribution across scenarios)
        pct_dev = pd.DataFrame({
            y: 100 * (data[y] - base_cumulative[y]) / base_cumulative[y]
            for y in target_years
        })
    else:
        pct_dev = pd.DataFrame({y: pd.Series(dtype=float) for y in target_years})

    plt.figure(figsize=(9, 5))
    ax = plt.gca()
    positions = np.arange(len(target_years))
    box_data = [pct_dev[y].dropna() for y in target_years]

    # draw boxplot without fliers/outliers (showfliers=False)
    median_color = "#1F78B4"
    median_linewidth = 2.0
    bp = ax.boxplot(
        box_data, positions=positions, widths=0.35, patch_artist=True,
        showfliers=False,  # hide outliers
        boxprops=dict(facecolor="#A6CEE3", alpha=0.75, linewidth=1.2),
        medianprops=dict(color=median_color, linewidth=median_linewidth),
        whiskerprops=dict(color="#666666", linestyle="--", linewidth=1.2),
        capprops=dict(color="#666666", linewidth=1.2),
        flierprops=dict(marker='o', markersize=4, markeredgecolor='none')  # not shown since showfliers=False
    )

    # Formatting for readability (larger fonts etc.)
    ax.set_title("Cumulative LNG demand – Compared to current policies",
                 fontsize=12, weight="bold")
    ax.set_xlabel("Year", fontsize=10)
    ax.set_ylabel("Deviation from base [%]", fontsize=10)
    ax.set_xticks(positions)
    ax.set_xticklabels(target_years, fontsize=10)
    ax.grid(axis="y", linestyle=":", color="0.8", linewidth=0.8)

    ax.tick_params(axis="x", labelsize=10)
    ax.tick_params(axis="y", labelsize=10)

    # Draw thin dashed horizontal lines from each median to the y-axis (no numeric text)
    # Use the same color and thickness as the median, with slightly lower alpha
    # We'll draw from the left axis limit to the box x position.
    x_left = ax.get_xlim()[0]  # left axis coordinate
    for i, med_line in enumerate(bp.get('medians', [])):
        # median line y data; average the y-values to get a single median y
        ydata = med_line.get_ydata()
        if len(ydata) == 0:
            continue
        median_val = float(np.mean(ydata))

        # horizontal dashed line from left axis to the box position using median style
        ax.plot([x_left, positions[i]], [median_val, median_val],
                color=median_color, linestyle="--", linewidth=median_linewidth, alpha=0.65, zorder=2)

        # small tick at the y-axis to indicate the median point (no numeric label)
        ax.plot([x_left], [median_val], marker='|', markersize=14,
                color=median_color, markeredgewidth=1.6, alpha=0.9, zorder=3)

    plt.tight_layout()
    plt.savefig(out_path / "lng_cumulative_pct_deviation.pdf", dpi=600, bbox_inches="tight")
    plt.show()
    print("✔ LNG cumulative deviation plot saved")


def export_lng_data(base_file=None, nzia_scenarios_dict=None, lng_file=None,
                    output_dir="plots/lng_data"):
    """
    Collects yearly LNG data for NZIA scenarios, base case, best-case scenario,
    and long-term contracts (LTC), and exports them to CSV files.

    CSV files format:
    - Years as rows
    - Scenarios or series as columns
    """

    if base_file is None:
        base_file = get_base_scenario()
    if nzia_scenarios_dict is None:
        nzia_scenarios_dict = build_scenario_dict()
    if lng_file is None:
        lng_file = get_lng_best_case_scenario()

    years = range(2025, 2041)
    out_path = Path(output_dir)
    out_path.mkdir(parents=True, exist_ok=True)


    # --------------------------
    # NZIA scenarios
    # --------------------------
    nzia_arrays = []
    nzia_files = [f for f in nzia_scenarios_dict.values() if f.exists()]
    for f in nzia_files:
        series = load_lng(f, years)
        nzia_arrays.append(series.values)

    if nzia_arrays:
        nzia_array = np.vstack(nzia_arrays)
        nzia_df = pd.DataFrame({
    name: load_lng(path, years)
    for name, path in nzia_scenarios_dict.items()
})
    else:
        nzia_df = pd.DataFrame(index=years)

    # --------------------------
    # Base case
    # --------------------------
    base_series = load_lng(base_file, years)
    base_df = pd.DataFrame({"Base": base_series.values}, index=years)

    # --------------------------
    # Best-case scenario
    # --------------------------
    best_case_series = load_lng(lng_file, years)
    best_case_df = pd.DataFrame({"Best_Case": best_case_series.values}, index=years)

    # --------------------------
    # Long-term contracts
    # --------------------------
    ltc_data = {2025: 82, 2026: 85, 2027: 99, 2028: 92, 2029: 92,
                2030: 88, 2031: 86, 2032: 84, 2035: 57, 2040: 48}
    ltc_series = pd.Series(ltc_data).sort_index().reindex(years).interpolate()
    ltc_df = pd.DataFrame({"LTC": ltc_series.values}, index=years)

    # --------------------------
    # Export CSVs
    # --------------------------
    print("NZIA df head:\n", nzia_df.head())
    print("Base df head:\n", base_df.head())
    print("Best case df head:\n", best_case_df.head())
    print("LTC df head:\n", ltc_df.head())

    nzia_df.to_csv(out_path / "NZIA_Scenarios_Yearly.csv", index_label="Year")
    base_df.to_csv(out_path / "Base_Series_Yearly.csv", index_label="Year")
    best_case_df.to_csv(out_path / "Best_Case_Series_Yearly.csv", index_label="Year")
    ltc_df.to_csv(out_path / "LongTermContracts_Yearly.csv", index_label="Year")

    print("✔ LNG data exported to CSV files (yearly values)")
    return {
        "NZIA": nzia_df,
        "Base": base_df,
        "Best_Case": best_case_df,
        "LTC": ltc_df
    }


def plot_system_costs_boxplot(base_file=None, nzia_scenarios_dict=None, output_dir="plots/system_costs"):
    """Boxplot of yearly system costs (in bn€) with Base scenario as a line."""
    if base_file is None:
        base_file = get_base_scenario()
    if nzia_scenarios_dict is None:
        nzia_scenarios_dict = build_scenario_dict()

    years = list(range(2024, 2041))
    out_path = Path(output_dir)
    out_path.mkdir(parents=True, exist_ok=True)

    # Load Base costs and convert to bn€
    base_costs = load_system_costs(base_file)
    base_yearly = [base_costs.get(y, 0)/1e9 for y in years]  # Convert to bn€

    # Load NZIA costs
    nzia_data = []
    for scenario_name, file_path in nzia_scenarios_dict.items():
        if file_path.exists():
            costs = load_system_costs(file_path)
            yearly_bn = [costs.get(y, 0)/1e9 for y in years]  # Convert to bn€
            nzia_data.append(yearly_bn)

    # Convert to DataFrame
    df = pd.DataFrame(nzia_data, columns=years)

    # Boxplot for each year
    plt.figure(figsize=(12, 6))
    box_data = [df[y] for y in years]
    plt.boxplot(
        box_data,
        labels=years,
        patch_artist=True,
        boxprops=dict(facecolor='lightblue', color='blue'),
        medianprops=dict(color='darkblue')
    )

    # Overlay Base scenario as a line
    plt.plot(range(1, len(years)+1), base_yearly, 'r-', linewidth=2.5, label='Base Scenario')

    plt.xlabel("Year")
    plt.ylabel("System Costs [bn€]")
    plt.title("Yearly System Costs: NZIA Scenario Deviations vs Base")
    plt.grid(True, linestyle="--", alpha=0.3)
    plt.legend()
    plt.tight_layout()

    plt.savefig(out_path / "system_costs_boxplot_bn.png", dpi=300)
    plt.show()
    print("✔ Boxplot of system costs (bn€) saved")


def plot_nzia_boxplots(
        tech_list,
        nzia_scenarios_dict,
        target_years=[2025, 2030, 2035, 2040],
        output_dir="plots/nzia_boxplots"
):
    """
    Plots grouped boxplots for each technology:
    - One plot for yearly capacity additions
    - One plot for cumulative capacity additions
    Each target year has 3 boxes (Manufacturing, Remanufacturing, Stockpile)
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Updated components and colors
    components = ["Manufacturing", "Remanufacturing", "Stockpile Out"]  # original column names
    components_legend = ["Manufacturing", "Remanufacturing", "Stockpile"]  # for legend
    colors = ["#FF8C42", "#4CB5AE", "#FF6B6B"]  # harmonious palette

    for tech_name in tech_list:
        all_data_yearly = []
        all_data_cumulative = []

        for (lr, scenario_name), file_path in nzia_scenarios_dict.items():
            if not file_path.exists():
                continue
            try:
                df = pd.read_excel(file_path, sheet_name="extension_only_caps")
            except Exception as e:
                print(f"⚠ Could not read {file_path}: {e}")
                continue

            df.columns = df.columns.str.strip()
            df["tech"] = df["tech"].astype(str).str.strip()
            df["stf"] = df["stf"].ffill()
            if "location" in df.columns:
                df["location"] = df["location"].ffill()

            df_tech = df[df["tech"] == tech_name].copy()
            if df_tech.empty:
                continue

            # Ensure all target years exist
            for year in target_years:
                if year not in df_tech["stf"].values:
                    df_tech = pd.concat([df_tech, pd.DataFrame([{
                        "tech": tech_name,
                        "stf": year,
                        "location": df_tech["location"].iloc[-1] if "location" in df_tech.columns else None,
                        "capacity_ext_eusecondary": 0,
                        "capacity_ext_stockout": 0,
                        "capacity_ext_euprimary": 0
                    }])], ignore_index=True)

            df_tech = df_tech.sort_values("stf")
            df_tech["cum_eusecondary"] = df_tech["capacity_ext_eusecondary"].cumsum()
            df_tech["cum_stockout"] = df_tech["capacity_ext_stockout"].cumsum()
            df_tech["cum_euprimary"] = df_tech["capacity_ext_euprimary"].cumsum()

            for year in target_years:
                row = df_tech[df_tech["stf"] == year]
                all_data_yearly.append({
                    "year": year,
                    "scenario": scenario_name,
                    "Manufacturing": row["capacity_ext_euprimary"].sum() / 1e3,
                    "Remanufacturing": row["capacity_ext_eusecondary"].sum() / 1e3,
                    "Stockpile Out": row["capacity_ext_stockout"].sum() / 1e3
                })
                all_data_cumulative.append({
                    "year": year,
                    "scenario": scenario_name,
                    "Manufacturing": row["cum_euprimary"].sum() / 1e3,
                    "Remanufacturing": row["cum_eusecondary"].sum() / 1e3,
                    "Stockpile Out": row["cum_stockout"].sum() / 1e3
                })

        if not all_data_yearly:
            print(f"No data found for {tech_name}. Skipping.")
            continue

        df_yearly = pd.DataFrame(all_data_yearly)
        df_cum = pd.DataFrame(all_data_cumulative)

        # Helper to plot grouped boxplots
        def plot_grouped_boxplot(df_plot, title, filename):
            plt.figure(figsize=(10, 6))
            box_width = 0.2
            positions = np.arange(len(target_years))

            for i, comp in enumerate(components):
                data = [df_plot[df_plot["year"] == year][comp].values for year in target_years]
                pos = positions + (i - 1) * box_width  # shift each component
                bp = plt.boxplot(data, positions=pos, widths=box_width, patch_artist=True,
                                 boxprops=dict(facecolor=colors[i], alpha=0.7, linewidth=1.2),
                                 medianprops=dict(color='black', linewidth=2),
                                 whiskerprops=dict(color='grey', linestyle='--', linewidth=1.2),
                                 capprops=dict(color='grey', linewidth=1.2))

            plt.xticks(positions, target_years)
            plt.xlabel("Year")
            plt.ylabel("Capacity Additions (GW)")
            plt.title(f"{title} for {tech_name}")
            plt.grid(axis="y", linestyle="--", alpha=0.3)

            # Legend with black outline and padding
            for i, comp_name in enumerate(components_legend):
                plt.plot([], color=colors[i], label=comp_name, linewidth=4)  # smaller width
            plt.legend(frameon=True, edgecolor='black', borderpad=0.5, labelspacing=0.5)

            plt.tight_layout()
            plt.savefig(output_dir / filename, dpi=300)
            plt.show()

        plot_grouped_boxplot(df_yearly, "Yearly Capacity Additions", f"{tech_name}_yearly_boxplot.png")
        plot_grouped_boxplot(df_cum, "Cumulative Capacity Additions", f"{tech_name}_cumulative_boxplot.png")



def plot_cumulative_capacity_scatter(
    tech_list,
    nzia_scenarios_dict,
    target_years=[2025, 2030, 2035, 2040],
    output_dir="plots/cumulative_scatter",
    save_csv=True,
    perform_clustering=True,
    eps=0.7,
    min_samples=4
):
    """
    Scatter plot of cumulative capacities:
    - X-axis: Remanufacturing
    - Y-axis: Manufacturing
    - Different colors for each target year
    - Optional tracer lines connecting the same scenario over time
    - Optional DBSCAN clustering (used only for benchmarking, not plotted)
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # RGB color palette for years
    year_colors = {
        2025: (223 / 255, 221 / 255, 25 / 255),
        2030: (239 / 255, 119 / 255, 72 / 255),
        2035: (231 / 255, 35 / 255, 133 / 255),
        2040: (91 / 255, 47 / 255, 104 / 255),
    }

    for tech_name in tech_list:
        all_data = []

        # -----------------------------
        # Load and process NZIA files
        # -----------------------------
        for (lr, scenario_name), file_path in nzia_scenarios_dict.items():
            if not file_path.exists():
                continue
            try:
                df = pd.read_excel(file_path, sheet_name="extension_only_caps")
            except Exception as e:
                print(f"⚠ Could not read {file_path}: {e}")
                continue

            df.columns = df.columns.str.strip()
            df["tech"] = df["tech"].astype(str).str.strip()
            df["stf"] = df["stf"].ffill()
            if "location" in df.columns:
                df["location"] = df["location"].ffill()

            df_tech = df[df["tech"] == tech_name].copy()
            if df_tech.empty:
                continue

            df_tech = df_tech.sort_values("stf")
            df_tech["cum_eusecondary"] = df_tech["capacity_ext_eusecondary"].cumsum()
            df_tech["cum_stockout"] = df_tech["capacity_ext_stockout"].cumsum()
            df_tech["cum_euprimary"] = df_tech["capacity_ext_euprimary"].cumsum()
            df_tech["cum_newly_added_capacity"] = df_tech["newly_added_capacity"].cumsum()

            for year in target_years:
                row = df_tech[df_tech["stf"] == year]
                all_data.append({
                    "tech": tech_name,
                    "year": year,
                    "learning_rate": lr,
                    "scenario": scenario_name,
                    "Remanufacturing": row["cum_eusecondary"].sum() / 1e3,
                    "Manufacturing": row["cum_euprimary"].sum() / 1e3,
                    "Stockpile": row["cum_stockout"].sum() / 1e3,
                    "Totals (incl. Imports)": row["cum_newly_added_capacity"].sum() / 1e3
                })

        if not all_data:
            print(f"No data for {tech_name}. Skipping.")
            continue

        df_all = pd.DataFrame(all_data)

        # -----------------------------
        # Save CSV if requested
        # -----------------------------
        if save_csv:
            csv_path = Path(output_dir) / f"cumulative_data_{tech_name}.csv"
            df_all.to_csv(csv_path, index=False)
            print(f"✔ Data exported for {tech_name}: {csv_path}")

        # -----------------------------
        # Simple scatter (points only)
        # -----------------------------
        plt.figure(figsize=(8, 6))
        for year in target_years:
            subset = df_all[df_all["year"] == year]
            plt.scatter(
                subset["Remanufacturing"], subset["Manufacturing"],
                color=year_colors[year],
                s=50,
                label=str(year)
            )

        plt.xlabel("Remanufacturing Capacity (GW)")
        plt.ylabel("Manufacturing Capacity (GW)")
        plt.title(f"Cumulative Capacity for {tech_name}")
        plt.grid(True, linestyle="--", alpha=0.3)
        plt.legend(title="Year", frameon=True, edgecolor='black')
        plt.tight_layout(rect=[0.02, 0.06, 0.98, 0.94])  # leave extra bottom space
        plt.subplots_adjust(bottom=0.25)  # increase bottom margin
        fig_path = Path(output_dir) / f"cumulative_scatter_points_{tech_name}.png"
        plt.savefig(fig_path, dpi=300)
        plt.show()
        print(f"✔ Simple scatter plot saved for {tech_name}: {fig_path}")

        # -----------------------------
        # Scatter with tracers (lines connecting scenarios)
        # -----------------------------
        plt.figure(figsize=(8, 6))
        for (lr, scenario_name), group_df in df_all.groupby(['learning_rate', 'scenario']):
            group_df = group_df.sort_values('year')
            plt.plot(
                group_df['Remanufacturing'], group_df['Manufacturing'],
                color='gray', alpha=0.3, linestyle='--', zorder=1
            )
            for year in target_years:
                point = group_df[group_df['year'] == year]
                if not point.empty:
                    plt.scatter(
                        point['Remanufacturing'], point['Manufacturing'],
                        color=year_colors[year],
                        s=50,
                        label=str(year) if f"{year}" not in plt.gca().get_legend_handles_labels()[1] else None,
                        zorder=2
                    )

        plt.xlabel("Remanufacturing Capacity (GW)")
        plt.ylabel("Manufacturing Capacity (GW)")
        plt.title(f"Cumulative Capacity with Tracers for {tech_name}")
        plt.grid(True, linestyle="--", alpha=0.3)
        plt.legend(title="Year", frameon=True, edgecolor='black')
        plt.tight_layout(rect=[0.02, 0.06, 0.98, 0.94])  # leave extra bottom space
        plt.subplots_adjust(bottom=0.25)  # increase bottom margin
        fig_path = Path(output_dir) / f"cumulative_scatter_tracer_{tech_name}.png"
        plt.savefig(fig_path, dpi=300)
        plt.show()
        print(f"✔ Scatter + tracer plot saved for {tech_name}: {fig_path}")

        # -----------------------------
        # Run clustering if requested (used for benchmarking only)
        # -----------------------------
        if perform_clustering:
            df_summary, df_with_clusters = identify_capacity_clusters(
                df_all, eps=eps, min_samples=min_samples
            )
            cluster_dir = output_dir / "clusters"
            cluster_dir.mkdir(exist_ok=True)
            df_summary.to_csv(cluster_dir / f"cluster_summary_{tech_name}.csv", index=False)
            df_with_clusters.to_csv(cluster_dir / f"clustered_data_{tech_name}.csv", index=False)
            print(f"✅ Clustering done for {tech_name}. Results saved in {cluster_dir}")

            # Plot clustered benchmark & flows
            plot_clustered_benchmark_from_df(df_with_clusters, output_dir="plots/clustered_benchmark")
            #plot_all_cluster_flows(df_with_clusters)



def plot_window_capacity_scatter(
        tech_list,
        nzia_scenarios_dict,
        windows=[(2024, 2025), (2026, 2030), (2031, 2035), (2036, 2040)],
        output_dir="plots/window_scatter",
        save_csv=True,
        perform_clustering=True,
        eps=0.7,
        min_samples=2,
):
    """
    Scatter plot of capacities aggregated by windows (Remanufacturing vs Manufacturing)
    for selected technologies, with optional DBSCAN clustering and integrated ternary grid output.

    Added:
      - after clustering, produce an interactive ternary grid (2x2 default) per tech using clustered dataframe.
      - handles df_with_clusters that uses either 'year' or 'window_id'.
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # RGB color palette for windows (kept)
    window_colors = ["#DFDD19", "#EF7748", "#E72385", "#5B2F68"]

    for tech_name in tech_list:
        all_data = []

        # Load and process NZIA files
        for (lr, scenario_name), file_path in nzia_scenarios_dict.items():
            if not Path(file_path).exists():
                continue
            try:
                df = pd.read_excel(file_path, sheet_name="extension_only_caps")
            except Exception as e:
                print(f"⚠ Could not read {file_path}: {e}")
                continue

            df.columns = df.columns.str.strip()
            df["tech"] = df["tech"].astype(str).str.strip()
            df["stf"] = df["stf"].ffill()
            if "location" in df.columns:
                df["location"] = df["location"].ffill()

            df_tech = df[df["tech"] == tech_name].copy()
            if df_tech.empty:
                continue

            # Aggregate over windows
            for i, (start_year, end_year) in enumerate(windows, start=1):
                df_window = df_tech[(df_tech["stf"] >= start_year) & (df_tech["stf"] <= end_year)]
                all_data.append({
                    "tech": tech_name,
                    "window_id": i,
                    "window_label": f"{start_year}-{end_year}",
                    "learning_rate": lr,
                    "scenario": scenario_name,
                    "Remanufacturing": df_window["capacity_ext_eusecondary"].sum() / 1e3,  # GW
                    "Manufacturing": df_window["capacity_ext_euprimary"].sum() / 1e3,  # GW
                    "Stockpile": df_window["capacity_ext_stockout"].sum() / 1e3,
                    "Totals (incl. Imports)": df_window["newly_added_capacity"].sum() / 1e3
                })

        if not all_data:
            print(f"No data for {tech_name}. Skipping.")
            continue

        df_all = pd.DataFrame(all_data)

        # Save CSV if requested
        if save_csv:
            csv_path = Path(output_dir) / f"window_data_{tech_name}.csv"
            df_all.to_csv(csv_path, index=False)
            print(f"✔ Data exported for {tech_name}: {csv_path}")

        # Simple scatter plot (points only)
        plt.figure(figsize=(8, 6))
        for i, (_, group) in enumerate(df_all.groupby("window_id")):
            plt.scatter(
                group["Remanufacturing"], group["Manufacturing"],
                color=window_colors[i % len(window_colors)],
                s=50,
                label=group["window_label"].iloc[0]
            )

        plt.xlabel("Remanufacturing Capacity (GW)")
        plt.ylabel("Manufacturing Capacity (GW)")
        plt.title(f"Capacity by Window for {tech_name}")
        plt.grid(True, linestyle="--", alpha=0.3)
        plt.legend(title="Window", frameon=True, edgecolor='black')
        plt.tight_layout(rect=[0.02, 0.06, 0.98, 0.94])  # leave extra bottom space
        plt.subplots_adjust(bottom=0.25)  # increase bottom margin
        fig_path = Path(output_dir) / f"window_scatter_points_{tech_name}.png"
        plt.savefig(fig_path, dpi=300)
        plt.close()
        print(f"✔ Scatter plot saved for {tech_name}: {fig_path}")

        # Optional clustering (DBSCAN)
        if perform_clustering:
            # Keep all columns needed for plotting stacked bars and ternary
            df_for_clustering = df_all.copy()
            # For DBSCAN the upstream helper expects 'year' column; rename
            if "window_id" in df_for_clustering.columns:
                df_for_clustering = df_for_clustering.rename(columns={"window_id": "year"})

            # Call your clustering helper (assumed available in your environment)
            df_summary, df_with_clusters = identify_yearly_capacity_clusters(
                df_for_clustering,
                years_of_interest=df_for_clustering["year"].unique(),
                eps=eps,
                min_samples=min_samples
            )

            cluster_dir = output_dir / "clusters_window"
            cluster_dir.mkdir(exist_ok=True)
            df_summary.to_csv(cluster_dir / f"cluster_summary_{tech_name}.csv", index=False)
            df_with_clusters.to_csv(cluster_dir / f"clustered_data_{tech_name}.csv", index=False)
            print(f"✅ Clustering done for {tech_name}. Results saved in {cluster_dir}")

            # Call your existing clustered bar plotting if you still want it
            plot_clustered_benchmark_from_window_df(df_with_clusters, output_dir=output_dir / "clustered_benchmark_window")

    print("All done.")

def plot_window_scatter_relative_single(
        tech_list,
        nzia_scenarios_dict,
        windows=[(2024, 2025), (2026, 2030), (2031, 2035), (2036, 2040)],
        output_dir="plots/window_scatter_relative",
        save_csv=True,
        figsize=(7, 6),
        grid_mode=True,
        grid_figsize=(13, 10),   # Used if grid_mode=True
        target_lines=(0.40, 0.45, 0.50, 0.55, 0.60,0.65,0.7,0.75,0.8,0.85),
        project_with_stock=True,
        projection_color="#ff7f0e",
        barrier_color="#d62728",
        show_top_projections=0,
        scale_marker_by_totals=False,
        min_stock_frac_to_show=0.01,
        #tracer_step=0.05,                # draw tracer "L" lines every 5% by default
        #tracer_color="0.85",
        #tracer_lw=0.6,
        #tracer_alpha=0.28,
        global_tick_labelsize=13,       # increased tick label sizes
        global_xlabel_size=14,
        global_ylabel_size=14,
        global_title_size=16,
        legend_fontsize=10

):
    """
    Single-window fractional scatter.

    Important behavior:
    - Maximum used to determine dynamic barrier (target) line lengths is
      computed from the overall fraction we calculate: Rem_frac + Man_frac + Stock_frac
      (stored in LocalSourcing_frac). That per-window maximum sets how high
      dashed target lines are drawn (effective_p = min(requested_p, max_local_sourcing)).
    - The baseline 0.40 target is always shown (solid/thick). It is drawn up to
      min(0.40, axis_max) so it is visible in every subplot (but clipped by axis limits).
    - Other target_lines (e.g., 0.45, 0.50...) are dashed and capped by the
      per-window maximum LocalSourcing_frac.
    - Tracer "L" guides are drawn every tracer_step up to the per-window maximum.
    """

    # Tech color palette (add more as needed)
    tech_colors = {
        "solarPV": (223 / 255, 221 / 255, 25 / 255),  # yellow
        "windon": (44 / 255, 80 / 255, 180 / 255),    # blue
        "windoff": (143 / 255, 60 / 255, 175 / 255),  # purple
    }
    default_tech_color = (0.13, 0.13, 0.13)

    outdir = Path(output_dir)
    outdir.mkdir(parents=True, exist_ok=True)
    saved_paths = []


    def _draw_barrier_connect_axes(ax, p, max_point, axis_min, axis_max,
                                   color=barrier_color, linewidth=1.6, linestyle='--', alpha=0.6,
                                   baseline_value=0.40):
        """
        Draw the barrier line y = p - x in a 'connect-axes' style but with the visible
        height determined as follows:
         - if p is the baseline (baseline_value, default 0.40), draw it up to
           min(baseline_value, axis_max) so it's always present (but clipped by axis limits).
         - otherwise (dynamic targets), compute effective_p = min(p, max_point)
           and draw the segment from (0,effective_p) to (effective_p,0).

        This matches the visual of a full connect-axes target line while ensuring
        dynamic lines reflect the per-window overall LocalSourcing_frac maximum.
        """
        if axis_max <= axis_min:
            return

        # baseline: always present (but clipped by axis_max)
        if abs(p - baseline_value) < 1e-9:
            effective_p = min(baseline_value, axis_max)
            if effective_p <= axis_min:
                return
        else:
            # dynamic targets: capped by per-window max of LocalSourcing_frac
            effective_p = min(p, max_point)
            if effective_p <= axis_min:
                return

        xs = np.linspace(0.0, effective_p, 300)
        ys = effective_p - xs
        ys = np.clip(ys, axis_min, axis_max)
        ax.plot(xs, ys, color=color, linestyle=linestyle, linewidth=linewidth, alpha=alpha, zorder=1)

    for tech_name in tech_list:
        all_data = []
        tech_rgb = tech_colors.get(tech_name, default_tech_color)

        # Aggregate inputs (reads extension_only_caps sheet)
        for (lr, scenario_name), file_path in nzia_scenarios_dict.items():
            p = Path(file_path)
            if not p.exists():
                continue
            try:
                df = pd.read_excel(p, sheet_name="extension_only_caps")
            except Exception as e:
                print(f"⚠ Could not read {p}: {e}")
                continue

            df.columns = df.columns.str.strip()
            df["tech"] = df["tech"].astype(str).str.strip()
            df["stf"] = df["stf"].ffill()
            if "location" in df.columns:
                df["location"] = df["location"].ffill()

            df_tech = df[df["tech"] == tech_name].copy()
            if df_tech.empty:
                continue

            for i, (start_year, end_year) in enumerate(windows, start=1):
                df_window = df_tech[(df_tech["stf"] >= start_year) & (df_tech["stf"] <= end_year)]
                all_data.append({
                    "tech": tech_name,
                    "window_id": i,
                    "window_label": f"{start_year}-{end_year}",
                    "window_end_year": end_year,
                    "learning_rate": lr,
                    "scenario": scenario_name,
                    "Remanufacturing": df_window["capacity_ext_eusecondary"].sum() / 1e3,
                    "Manufacturing": df_window["capacity_ext_euprimary"].sum() / 1e3,
                    "Stockpile": df_window["capacity_ext_stockout"].sum() / 1e3,
                    "Totals (incl. Imports)": df_window["newly_added_capacity"].sum() / 1e3
                })

        if not all_data:
            print(f"No data for {tech_name}. Skipping.")
            continue

        df_all = pd.DataFrame(all_data)

        if save_csv:
            csv_path = outdir / f"window_data_{tech_name}.csv"
            df_all.to_csv(csv_path, index=False)
            print(f"✔ Data exported for {tech_name}: {csv_path}")

        totals = df_all["Totals (incl. Imports)"].replace(0, np.nan)
        df_all["Rem_frac"] = df_all["Remanufacturing"].div(totals).fillna(0)
        df_all["Man_frac"] = df_all["Manufacturing"].div(totals).fillna(0)
        df_all["Stock_frac"] = df_all["Stockpile"].div(totals).fillna(0)
        # overall fraction user requested to use for maxing target lines
        df_all["LocalSourcing_frac"] = df_all["Rem_frac"] + df_all["Man_frac"] + df_all["Stock_frac"]

        unique_windows = sorted(df_all["window_id"].unique())
        window_labels = [df_all[df_all["window_id"] == win]["window_label"].iloc[0] for win in unique_windows]

        if grid_mode:
            # --------- 2x2 grid mode (all windows for this tech) ----------
            fig, axes = plt.subplots(2, 2, figsize=grid_figsize, squeeze=True)
            axes = axes.flatten()

            # compute global axis scaling (still use global to keep grid comparable)
            all_local_max = float(df_all["LocalSourcing_frac"].max(skipna=True))
            all_proj_local_max = float((df_all["LocalSourcing_frac"]).max(skipna=True))
            global_max = np.nanmax([all_local_max, all_proj_local_max, 0.6])
            axis_max = min(1.0, max(global_max * 1.05, 0.6))
            axis_min = 0.0

            for ax_idx, win in enumerate(unique_windows):
                sub = df_all[df_all["window_id"] == win].copy()
                ax = axes[ax_idx]
                if sub.empty:
                    ax.set_visible(False)
                    continue

                plot_x = sub["Rem_frac"].to_numpy(copy=True)
                plot_y = sub["Man_frac"].to_numpy(copy=True)

                # jitter
                seed = abs(hash(f"{tech_name}_{win}")) % (2**32)
                rng = np.random.default_rng(seed)
                jitter_scale = 0.002
                jitter_x = rng.normal(scale=jitter_scale, size=len(sub))
                jitter_y = rng.normal(scale=jitter_scale, size=len(sub))
                small_mask_x = plot_x <= 1e-6
                small_mask_y = plot_y <= 1e-6
                plot_x[small_mask_x] += jitter_x[small_mask_x]
                plot_y[small_mask_y] += jitter_y[small_mask_y]
                plot_x = np.clip(plot_x, axis_min, axis_max)
                plot_y = np.clip(plot_y, axis_min, axis_max)

                # marker sizing
                if scale_marker_by_totals:
                    tot = sub["Totals (incl. Imports)"].fillna(0)
                    sizes = np.clip((tot / (tot.max() if tot.max() > 0 else 1)) * 120, 12, 120)
                else:
                    sizes = np.full(len(sub), 48)   # smaller markers for grid mode

                # determine per-window max using LocalSourcing_frac (overall)
                max_point = float(sub["LocalSourcing_frac"].max(skipna=True)) if len(sub) else 0.0
                max_point = max(max_point, 0.0)

                # draw tracer levels up to this subplot's max point
                #_draw_tracer_levels(ax, max_point, step=tracer_step, color=tracer_color, lw=tracer_lw, alpha=tracer_alpha)

                # barrier lines: baseline (0.40) drawn solid up to axis_max (so it's always present),
                # other dynamic target lines are dashed and capped at per-window max_point
                for p in target_lines:
                    linestyle = '-' if abs(p - 0.40) < 1e-9 else '--'
                    linewidth = 2.4 if abs(p - 0.40) < 1e-9 else 1.6
                    alpha = 0.98 if abs(p - 0.40) < 1e-9 else 0.6
                    # baseline always drawn (but clipped by axis_max); dynamic ones capped by max_point
                    if abs(p - 0.40) < 1e-9:
                        _draw_barrier_connect_axes(ax, p, max_point, axis_min, axis_max,
                                                   color=barrier_color, linewidth=linewidth, linestyle=linestyle, alpha=alpha,
                                                   baseline_value=0.40)
                    else:
                        _draw_barrier_connect_axes(ax, p, max_point, axis_min, axis_max,
                                                   color=barrier_color, linewidth=linewidth, linestyle=linestyle, alpha=alpha,
                                                   baseline_value=0.40)

                # projections (under markers)
                if project_with_stock:
                    for idx, r in sub.iterrows():
                        sf = r["Stock_frac"]
                        if sf >= min_stock_frac_to_show:
                            x = r["Rem_frac"]
                            y = r["Man_frac"]
                            proj_x = min(max(x + sf / 2.0, axis_min), axis_max)
                            proj_y = min(max(y + sf / 2.0, axis_min), axis_max)
                            ax.plot([x, proj_x], [y, proj_y], color=projection_color, linewidth=0.7, alpha=0.9, zorder=2)
                            ax.plot(proj_x, proj_y, marker='o', color=projection_color, markersize=4, markeredgecolor='white', zorder=2)

                # filled markers (smaller)
                edgecolor = tech_colors.get(tech_name, default_tech_color)
                facecolor = (edgecolor[0], edgecolor[1], edgecolor[2], 0.9)
                ax.scatter(plot_x, plot_y, s=sizes, facecolors=[facecolor], edgecolors=[edgecolor],
                           linewidths=0.7, zorder=4, marker='o')

                # axis/labels/titles
                ax.set_xlim(axis_min, axis_max)
                ax.set_ylim(axis_min, axis_max)
                ax.set_aspect('equal', adjustable='box')
                ax.set_xlabel("Remanufacturing (fraction of total)", fontsize=global_xlabel_size)
                ax.set_ylabel("Manufacturing (fraction of total)", fontsize=global_ylabel_size)
                ax.set_title(f"{window_labels[ax_idx]}", fontsize=global_title_size)
                ax.grid(True, linestyle='--', alpha=0.25)

                # tick sizing
                ax.tick_params(axis="x", labelsize=global_tick_labelsize, pad=6)
                ax.tick_params(axis="y", labelsize=global_tick_labelsize)

            # Legend (once)
            proxy_marker = Line2D([0], [0], marker='o', color='w',
                                  markerfacecolor=facecolor, markeredgecolor=edgecolor,
                                  markeredgewidth=1.0, markersize=7)
            proxy_proj = Line2D([0], [0], color=projection_color, lw=1.2)
            proxy_benchmark = Line2D([0], [0], color=barrier_color, lw=2.4)
            axes[-1].legend([proxy_marker, proxy_proj, proxy_benchmark],
                            [f"{tech_name} scenario", "stockpile projection (equal split)", "NZIA Benchmark (40%)"],
                            fontsize=legend_fontsize, frameon=True, loc='upper right')

            fig.suptitle(f"{tech_name} — Remanufacturing vs Manufacturing in all windows", fontsize=global_title_size, y=1.01)
            fig.tight_layout(rect=[0, 0, 1, 0.97])
            fname = outdir / f"{tech_name}_window_ALL_relative_grid.png"
            fig.savefig(fname, dpi=500)
            plt.close(fig)
            saved_paths.append(fname)
            print(f"✔ Saved 2x2 grid plot: {fname}")
        else:
            # --------- One plot per window (as before) ----------
            for win in unique_windows:
                sub = df_all[df_all["window_id"] == win].copy()
                if sub.empty:
                    continue

                try:
                    # local_max should be computed from LocalSourcing_frac (overall fraction)
                    local_max = float(sub["LocalSourcing_frac"].max(skipna=True))
                except Exception:
                    local_max = 0.6
                axis_max = min(1.0, max(local_max * 1.05, 0.6))
                axis_min = 0.0

                fig, ax = plt.subplots(figsize=figsize)

                # marker sizing: larger for trend visibility; can be scaled by totals if requested
                if scale_marker_by_totals:
                    tot = sub["Totals (incl. Imports)"].fillna(0)
                    sizes = np.clip((tot / (tot.max() if tot.max() > 0 else 1)) * 120, 24, 180)
                else:
                    sizes = np.full(len(sub), 80)

                # deterministic jitter for axis-packed points
                seed = abs(hash(f"{tech_name}_{win}")) % (2**32)
                rng = np.random.default_rng(seed)
                jitter_scale = 0.002
                jitter_x = rng.normal(scale=jitter_scale, size=len(sub))
                jitter_y = rng.normal(scale=jitter_scale, size=len(sub))
                plot_x = sub["Rem_frac"].to_numpy(copy=True)
                plot_y = sub["Man_frac"].to_numpy(copy=True)
                small_mask_x = plot_x <= 1e-6
                small_mask_y = plot_y <= 1e-6
                plot_x[small_mask_x] += jitter_x[small_mask_x]
                plot_y[small_mask_y] += jitter_y[small_mask_y]
                plot_x = np.clip(plot_x, axis_min, axis_max)
                plot_y = np.clip(plot_y, axis_min, axis_max)

                # draw tracer levels up to this subplot's max point (based on LocalSourcing_frac)
                max_point = float(sub["LocalSourcing_frac"].max(skipna=True)) if len(sub) else 0.0
                _draw_tracer_levels(ax, max_point, step=tracer_step, color=tracer_color, lw=tracer_lw, alpha=tracer_alpha)

                # draw barrier lines: baseline always present (solid, thicker) up to axis_max,
                # other target_lines dashed and capped by per-window LocalSourcing_frac (max_point)
                for p in target_lines:
                    linestyle = '-' if abs(p - 0.40) < 1e-9 else '--'
                    linewidth = 2.4 if abs(p - 0.40) < 1e-9 else 1.6
                    alpha = 0.98 if abs(p - 0.40) < 1e-9 else 0.6
                    _draw_barrier_connect_axes(ax, p, max_point, axis_min, axis_max,
                                               color=barrier_color, linewidth=linewidth, linestyle=linestyle, alpha=alpha,
                                               baseline_value=0.40)

                # projections
                proj_lw = 0.7
                for idx, r in sub.iterrows():
                    sf = r["Stock_frac"]
                    if sf >= min_stock_frac_to_show and project_with_stock:
                        x = r["Rem_frac"]
                        y = r["Man_frac"]
                        proj_x = min(max(x + sf / 2.0, axis_min), axis_max)
                        proj_y = min(max(y + sf / 2.0, axis_min), axis_max)
                        ax.plot([x, proj_x], [y, proj_y], color=projection_color, linewidth=proj_lw, alpha=0.9, zorder=2)
                        ax.plot(proj_x, proj_y, marker='o', color=projection_color, markersize=6, markeredgecolor='white', zorder=2)

                # filled markers
                edgecolor = tech_colors.get(tech_name, default_tech_color)
                facecolor = (edgecolor[0], edgecolor[1], edgecolor[2], 0.9)
                ax.scatter(plot_x, plot_y, s=sizes, facecolors=[facecolor], edgecolors=[edgecolor],
                           linewidths=1.4, zorder=4, marker='o')

                # annotate top projections if requested
                if show_top_projections and len(sub) > 0:
                    top = sub[sub["Stock_frac"] >= min_stock_frac_to_show].sort_values("Stock_frac", ascending=False).head(show_top_projections)
                    for _, trow in top.iterrows():
                        px = min(max(trow["Rem_frac"] + trow["Stock_frac"]/2.0, axis_min), axis_max)
                        py = min(max(trow["Man_frac"] + trow["Stock_frac"]/2.0, axis_min), axis_max)
                        label = f"+{trow['Stock_frac']*100:.1f}%\n{trow['Stockpile']:.1f} GW"
                        ax.text(px + 0.01*(axis_max-axis_min), py + 0.01*(axis_max-axis_min), label,
                                fontsize=8, bbox=dict(facecolor='white', alpha=0.85, edgecolor='none'))

                # aesthetics & equal axes
                ax.set_xlim(axis_min, axis_max)
                ax.set_ylim(axis_min, axis_max)
                ax.set_aspect('equal', adjustable='box')
                ax.set_xlabel("Remanufacturing (fraction of total)", fontsize=global_xlabel_size)
                ax.set_ylabel("Manufacturing (fraction of total)", fontsize=global_ylabel_size)
                window_label = sub["window_label"].iloc[0]
                ax.set_title(f"{tech_name} — {window_label}", fontsize=global_title_size)
                ax.grid(True, linestyle='--', alpha=0.25)

                # tick sizing
                ax.tick_params(axis="x", labelsize=global_tick_labelsize, pad=6)
                ax.tick_params(axis="y", labelsize=global_tick_labelsize)

                # Compact legend: tech marker, projection, NZIA Benchmark
                proxy_marker = Line2D([0], [0], marker='o', color='w',
                                      markerfacecolor=facecolor, markeredgecolor=edgecolor,
                                      markeredgewidth=1.4, markersize=8)
                proxy_proj = Line2D([0], [0], color=projection_color, lw=1.2)
                proxy_benchmark = Line2D([0], [0], color=barrier_color, lw=2.4)
                ax.legend([proxy_marker, proxy_proj, proxy_benchmark],
                          [f"{tech_name} scenario", "stockpile projection (equal split)", "NZIA Benchmark (40%)"],
                          fontsize=legend_fontsize, frameon=True, loc='upper right')

                # save the figure
                safe_label = window_label.replace(' ', '_').replace('/', '-')
                fname = outdir / f"{tech_name}_window_{safe_label}_relative.png"
                fig.tight_layout(rect=[0, 0, 1, 0.96])
                fig.savefig(fname, dpi=500)
                plt.close(fig)
                saved_paths.append(fname)
                print(f"✔ Saved relative fractional plot: {fname}")

    return saved_paths

def plot_clustered_benchmark_from_window_df(df_with_clusters, output_dir):
    """
    Plot clustered benchmark for windowed capacities instead of years.
    Adds grey bar for imports and colors windows in cluster overlays.

    Changes:
    - X axis and legends now use window labels (e.g., '2024-2025', '2026-2030', ...)
      instead of 'Window 1', 'Window 2', etc.
    - Increased tick / tick-label sizes and axis/title font sizes for readability.
    - Legend order changed so the Imports (grey) patch appears at the top of the legend for bar plots.
    - Scatter overlay: cluster centroid overlays are drawn as colored outlines (no fill).
      Scatter points are now filled (one fill color per window) and slightly smaller.
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    components = ["Remanufacturing", "Stockpile", "Manufacturing"]
    labels = ["Remanufacturing", "Stock", "Manufacturing"]
    colors = ["#FDC5B5", "#F99B7D", "#F76C5E"]
    hatches = ["..", "//", "xx"]

    # Define window colors for cluster overlays
    window_colors = ["#DFDD19", "#EF7748", "#E72385", "#5B2F68"]
    # Markers per window for scatter points (triangle, circle, square, diamond)
    window_markers = ["^", "o", "s", "D"]

    for tech in df_with_clusters["tech"].unique():
        df_tech = df_with_clusters[df_with_clusters["tech"] == tech].copy()

        # Use window_label for ticks/legends
        windows = sorted(df_tech["year"].unique())
        winid_to_label = {row["year"]: row["window_label"]
                          for _, row in df_tech.drop_duplicates(subset=["year", "window_label"]).iterrows()}
        window_labels = [winid_to_label[w] for w in windows]
        x_base = np.arange(len(windows))

        # --- Determine global max cluster count ---
        max_clusters = max(df_tech.groupby("year")["cluster_id"].nunique())

        total_width = 0.8
        gap = 0.02
        width = (total_width - (max_clusters - 1) * gap) / max_clusters

        # =====================================================
        # RELATIVE PLOT
        # =====================================================
        fig_rel, ax_rel = plt.subplots(figsize=(11, 6))

        for i, win in enumerate(windows):
            df_win = df_tech[df_tech["year"] == win]
            clusters_this_win = sorted(df_win["cluster_id"].unique())
            n_clusters = len(clusters_this_win)

            group_width = n_clusters * width + (n_clusters - 1) * gap
            start_offset = -group_width / 2 + width / 2

            for j, cluster in enumerate(clusters_this_win):
                df_cluster = df_win[df_win["cluster_id"] == cluster]
                row = df_cluster[["Remanufacturing", "Stockpile", "Manufacturing", "Totals (incl. Imports)"]].mean()

                x_pos = x_base[i] + start_offset + j * (width + gap)

                # Grey background for Imports
                ax_rel.bar(
                    x_pos,
                    1,
                    width=width,
                    bottom=0,
                    facecolor="#D3D3D3",
                    edgecolor="black",
                    linewidth=0.8,
                    zorder=0
                )

                bottom = 0
                total = row["Totals (incl. Imports)"] if row["Totals (incl. Imports)"] > 0 else 1
                for comp, color, hatch in zip(components, colors, hatches):
                    frac = row[comp] / total
                    ax_rel.bar(
                        x_pos,
                        frac,
                        width=width,
                        bottom=bottom,
                        facecolor=color,
                        edgecolor="black",
                        linewidth=0.8,
                        hatch=hatch,
                        zorder=1
                    )
                    bottom += frac

                ax_rel.text(x_pos, bottom + 0.02, f"C{int(cluster)}", ha="center", fontsize=16)

        # benchmark line
        ax_rel.axhline(0.4, color="red", linestyle="--", alpha=0.7, linewidth=2.5)

        # ticks and labels: larger for readability
        ax_rel.set_xticks(x_base)
        ax_rel.set_xticklabels(window_labels, fontsize=22, rotation=0)
        ax_rel.tick_params(axis="x", labelsize=22, pad=6)
        ax_rel.tick_params(axis="y", labelsize=22)
        ax_rel.set_ylim(0, 1)
        ax_rel.yaxis.set_major_formatter(plt.FuncFormatter(lambda y, _: f"{int(y * 100)}%"))

        # titles and axis labels: increase font sizes
        #ax_rel.set_title(f"Clustered Local Sourcing % - {tech}", pad=15, fontsize=18, fontweight="bold")
        #ax_rel.set_xlabel("Window", fontsize=22)
        ax_rel.set_ylabel("% of Total Capacity Additions", fontsize=22)
        ax_rel.grid(axis="y", alpha=0.3)

        # Legend including Imports — ensure Imports patch is first (top of legend)
        legend_patches = [
            mpatches.Patch(facecolor=fc, edgecolor="black", hatch=h, label=lab)
            for fc, h, lab in zip(colors, hatches, labels)
        ]
        imports_patch = mpatches.Patch(facecolor="#D3D3D3", edgecolor="black", label="Imports")
        nzia_line = Line2D([0], [0], color="red", linestyle="--", linewidth=2, label="NZIA Benchmark")

        # Put Imports first so it appears on top of the legend
        rel_handles = [imports_patch] + legend_patches + [nzia_line]
        ax_rel.legend(handles=rel_handles, frameon=True, loc="upper right", fontsize=12, handlelength=1.5)

        fig_rel.tight_layout()
        fig_rel.savefig(output_dir / f"{tech}_clustered_relative_window.png", dpi=300)
        plt.close(fig_rel)

        # =====================================================
        # ABSOLUTE PLOT
        # =====================================================
        fig_abs, ax_abs = plt.subplots(figsize=(11, 6))

        for i, win in enumerate(windows):
            df_win = df_tech[df_tech["year"] == win]
            clusters_this_win = sorted(df_win["cluster_id"].unique())
            n_clusters = len(clusters_this_win)

            group_width = n_clusters * width + (n_clusters - 1) * gap
            start_offset = -group_width / 2 + width / 2

            for j, cluster in enumerate(clusters_this_win):
                df_cluster = df_win[df_win["cluster_id"] == cluster]
                row = df_cluster[["Remanufacturing", "Stockpile", "Manufacturing", "Totals (incl. Imports)"]].mean()

                x_pos = x_base[i] + start_offset + j * (width + gap)

                # Grey background for Imports (absolute)
                ax_abs.bar(
                    x_pos,
                    row["Totals (incl. Imports)"],
                    width=width,
                    bottom=0,
                    facecolor="#D3D3D3",
                    edgecolor="black",
                    linewidth=0.8,
                    zorder=0
                )

                bottom = 0
                for comp, color, hatch in zip(components, colors, hatches):
                    val = row[comp]
                    ax_abs.bar(
                        x_pos,
                        val,
                        width=width,
                        bottom=bottom,
                        facecolor=color,
                        edgecolor="black",
                        linewidth=0.8,
                        hatch=hatch,
                        zorder=1
                    )
                    bottom += val

                ax_abs.text(x_pos, bottom + 0.5, f"C{int(cluster)}", ha="center", fontsize=8)

        # ticks and labels: larger for readability
        ax_abs.set_xticks(x_base)
        ax_abs.set_xticklabels(window_labels, fontsize=13, rotation=0)
        ax_abs.tick_params(axis="x", labelsize=13, pad=6)
        ax_abs.tick_params(axis="y", labelsize=13)

        ax_abs.set_ylabel("Capacity (GW)", fontsize=14)
        ax_abs.set_xlabel("Window", fontsize=14)
        #ax_abs.set_title(f"Clustered Absolute Capacity - {tech}", pad=15, fontsize=18, fontweight="bold")
        ax_abs.grid(axis="y", alpha=0.3)

        # Legend: ensure Imports appears on top
        abs_handles = [imports_patch] + legend_patches
        ax_abs.legend(handles=abs_handles, frameon=True, loc="upper right", fontsize=12, handlelength=1.5)

        fig_abs.tight_layout()
        fig_abs.savefig(output_dir / f"{tech}_clustered_absolute_window.png", dpi=300)
        plt.close(fig_abs)

        print(f"✔ Clustered bar plots saved for {tech}")

        # =====================================================
        # SCATTER OVERLAY WITH CLUSTER LABELS
        # - scatter points: filled markers per window, slightly smaller
        # - cluster overlays: colored outlines (no fill)
        # =====================================================
        fig_scat, ax_scat = plt.subplots(figsize=(8, 6))

        # plot scatter points: different marker per window, filled with window color, smaller size
        for i, win in enumerate(windows):
            subset = df_tech[df_tech["year"] == win]
            marker = window_markers[i % len(window_markers)]
            col = window_colors[i % len(window_colors)]
            ax_scat.scatter(
                subset["Remanufacturing"],
                subset["Manufacturing"],
                marker=marker,
                facecolors=col,            # filled markers
                edgecolors="black",
                alpha=0.85,
                s=50,                      # slightly smaller than before
                linewidths=0.7,
                label=None  # we'll construct a custom legend below
            )

        # compute centroids and draw colored outline overlays (one color per window), no fill
        centroids = df_tech.groupby(["year", "cluster_id"])[["Remanufacturing", "Manufacturing"]].mean().reset_index()
        x_range = df_tech["Remanufacturing"].max() - df_tech["Remanufacturing"].min()
        y_range = df_tech["Manufacturing"].max() - df_tech["Manufacturing"].min()
        if x_range == 0 and y_range == 0:
            radius = 0.5  # fallback if there's no range
        else:
            radius = 0.05 * max(x_range if x_range > 0 else 1e-6, y_range if y_range > 0 else 1e-6)

        for _, row in centroids.iterrows():
            win_idx = windows.index(row["year"])
            color = window_colors[win_idx % len(window_colors)]
            circle = plt.Circle(
                (row["Remanufacturing"], row["Manufacturing"]),
                radius=radius,
                edgecolor=color,
                facecolor='none',   # no fill — outline only
                lw=2.0,
                alpha=0.95,
                zorder=5
            )
            ax_scat.add_patch(circle)

            # centroid label: use outline color for text, add light stroke for visibility
            txt = ax_scat.text(
                row["Remanufacturing"],
                row["Manufacturing"],
                f"C{int(row['cluster_id'])}",
                ha="center",
                va="center",
                fontsize=9,
                fontweight="bold",
                color=color,
                zorder=6
            )
            txt.set_path_effects([pe.Stroke(linewidth=2.5, foreground="white", alpha=0.8), pe.Normal()])

        # Labels, title, grid and sizing
        ax_scat.set_xlabel("Remanufacturing Capacity (GW)", fontsize=13)
        ax_scat.set_ylabel("Manufacturing Capacity (GW)", fontsize=13)
        #ax_scat.set_title(f"Cluster Overview - {tech}", fontsize=16, fontweight="bold")
        ax_scat.grid(True, linestyle="--", alpha=0.3)
        ax_scat.tick_params(axis="x", labelsize=12)
        ax_scat.tick_params(axis="y", labelsize=12)

        # Build a clean legend showing marker shapes filled and the overlay outline color:
        legend_handles = []
        for i, lbl in enumerate(window_labels):
            mk = window_markers[i % len(window_markers)]
            col = window_colors[i % len(window_colors)]
            legend_handles.append(
                Line2D([0], [0],
                       marker=mk,
                       color='black',
                       markerfacecolor=col,
                       markeredgecolor='black',
                       markeredgewidth=0.7,
                       markersize=8,
                       linestyle='',
                       label=lbl)
            )
        ax_scat.legend(handles=legend_handles, title="Window", frameon=True, fontsize=11, loc="best")

        fig_scat.tight_layout()
        fig_scat.savefig(output_dir / f"{tech}_scatter_cluster_overlay_window.png", dpi=300)
        plt.close(fig_scat)

        print(f"✔ Scatter with cluster overlays saved for {tech}")
def plot_clustered_benchmark_from_df(df_with_clusters, output_dir):
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    components = ["Remanufacturing", "Stockpile", "Manufacturing"]
    labels = ["Remanufacturing", "Stock", "Manufacturing"]
    colors = ["#FDC5B5", "#F99B7D", "#F76C5E"]
    hatches = ["..", "//", "xx"]

    for tech in df_with_clusters["tech"].unique():
        df_tech = df_with_clusters[df_with_clusters["tech"] == tech].copy()
        years = sorted(df_tech["year"].unique())
        x_base = np.arange(len(years))

        # --- Determine global max cluster count ---
        max_clusters = max(df_tech.groupby("year")["cluster_id"].nunique())

        total_width = 0.8     # width of the full "year group"
        gap = 0.02            # small visible gap between bars
        width = (total_width - (max_clusters - 1) * gap) / max_clusters

        # =====================================================
        # RELATIVE PLOT
        # =====================================================
        fig_rel, ax_rel = plt.subplots(figsize=(11, 6))

        for i, year in enumerate(years):
            df_year = df_tech[df_tech["year"] == year]
            clusters_this_year = sorted(df_year["cluster_id"].unique())
            n_clusters = len(clusters_this_year)

            group_width = n_clusters * width + (n_clusters - 1) * gap
            start_offset = -group_width / 2 + width / 2

            for j, cluster in enumerate(clusters_this_year):
                df_cluster = df_year[df_year["cluster_id"] == cluster]
                row = df_cluster[
                    ["Remanufacturing", "Stockpile", "Manufacturing", "Totals (incl. Imports)"]
                ].mean()

                x_pos = x_base[i] + start_offset + j * (width + gap)

                # Grey background bar for Imports (relative goes to 1.0)
                ax_rel.bar(
                    x_pos,
                    1,                  # 100%
                    width=width,
                    bottom=0,
                    facecolor="#D3D3D3",
                    edgecolor="black",
                    linewidth=0.8,
                    zorder=0
                )

                # Colored stacks
                bottom = 0
                total = row["Totals (incl. Imports)"] if row["Totals (incl. Imports)"] > 0 else 1
                for comp, color, hatch in zip(components, colors, hatches):
                    frac = row[comp] / total
                    ax_rel.bar(
                        x_pos,
                        frac,
                        width=width,
                        bottom=bottom,
                        facecolor=color,
                        edgecolor="black",
                        linewidth=0.8,
                        hatch=hatch,
                        zorder=1
                    )
                    bottom += frac

                ax_rel.text(x_pos, bottom + 0.02, f"C{int(cluster)}", ha="center", fontsize=8)

        ax_rel.axhline(0.4, color="red", linestyle="--", alpha=0.7, linewidth=2)
        ax_rel.set_xticks(x_base)
        ax_rel.set_xticklabels(years)
        ax_rel.set_ylim(0, 1)
        ax_rel.yaxis.set_major_formatter(plt.FuncFormatter(lambda y, _: f"{int(y * 100)}%"))
        ax_rel.set_title(f"Clustered Local Sourcing % - {tech}", pad=15)
        ax_rel.set_xlabel("Year")
        ax_rel.set_ylabel("% of Total Capacity Additions")
        ax_rel.grid(axis="y", alpha=0.3)

        legend_patches = [
            mpatches.Patch(facecolor=fc, edgecolor="black", hatch=h, label=lab)
            for fc, h, lab in zip(colors, hatches, labels)
        ]
        nzia_line = plt.Line2D([0], [0], color="red", linestyle="--", linewidth=2, label="NZIA Benchmark")
        ax_rel.legend(handles=legend_patches + [nzia_line], frameon=True, loc="upper right")

        fig_rel.tight_layout()
        fig_rel.savefig(output_dir / f"{tech}_clustered_relative.png", dpi=300)
        plt.close(fig_rel)

        # =====================================================
        # ABSOLUTE PLOT
        # =====================================================
        fig_abs, ax_abs = plt.subplots(figsize=(11, 6))

        for i, year in enumerate(years):
            df_year = df_tech[df_tech["year"] == year]
            clusters_this_year = sorted(df_year["cluster_id"].unique())
            n_clusters = len(clusters_this_year)

            group_width = n_clusters * width + (n_clusters - 1) * gap
            start_offset = -group_width / 2 + width / 2

            for j, cluster in enumerate(clusters_this_year):
                df_cluster = df_year[df_year["cluster_id"] == cluster]
                row = df_cluster[
                    ["Remanufacturing", "Stockpile", "Manufacturing", "Totals (incl. Imports)"]
                ].mean()

                x_pos = x_base[i] + start_offset + j * (width + gap)

                # Grey background bar for Imports (absolute value)
                ax_abs.bar(
                    x_pos,
                    row["Totals (incl. Imports)"],
                    width=width,
                    bottom=0,
                    facecolor="#D3D3D3",
                    edgecolor="black",
                    linewidth=0.8,
                    zorder=0
                )

                # Colored stacks
                bottom = 0
                for comp, color, hatch in zip(components, colors, hatches):
                    val = row[comp]
                    ax_abs.bar(
                        x_pos,
                        val,
                        width=width,
                        bottom=bottom,
                        facecolor=color,
                        edgecolor="black",
                        linewidth=0.8,
                        hatch=hatch,
                        zorder=1
                    )
                    bottom += val

                ax_abs.text(x_pos, bottom + 0.5, f"C{int(cluster)}", ha="center", fontsize=8)

        ax_abs.set_xticks(x_base)
        ax_abs.set_xticklabels(years)
        ax_abs.set_ylabel("Capacity (GW)")
        ax_abs.set_xlabel("Year")
        ax_abs.set_title(f"Clustered Absolute Capacity - {tech}", pad=15)
        ax_abs.grid(axis="y", alpha=0.3)

        legend_patches_abs = [
            mpatches.Patch(facecolor=fc, edgecolor="black", hatch=h, label=lab)
            for fc, h, lab in zip(colors, hatches, labels)
        ]
        ax_abs.legend(handles=legend_patches_abs, frameon=True, loc="upper right")

        fig_abs.tight_layout()
        fig_abs.savefig(output_dir / f"{tech}_clustered_absolute.png", dpi=300)
        plt.close(fig_abs)

        print(f"✔ Clustered bar plots saved for {tech}")

        # =====================================================
        # SCATTER OVERLAY WITH CLUSTER LABELS
        # =====================================================
        fig_scatter, ax_scat = plt.subplots(figsize=(8, 6))
        year_colors = {
            2025: (223 / 255, 221 / 255, 25 / 255),
            2030: (239 / 255, 119 / 255, 72 / 255),
            2035: (231 / 255, 35 / 255, 133 / 255),
            2040: (91 / 255, 47 / 255, 104 / 255),
        }

        for year, subset in df_tech.groupby("year"):
            ax_scat.scatter(
                subset["Remanufacturing"],
                subset["Manufacturing"],
                color=year_colors.get(year, "gray"),
                alpha=0.4,
                label=str(year),
            )

        centroids = (
            df_tech.groupby(["year", "cluster_id"])[["Remanufacturing", "Manufacturing"]]
            .mean()
            .reset_index()
        )

        # Adaptive circle radius based on data scale
        x_range = df_tech["Remanufacturing"].max() - df_tech["Remanufacturing"].min()
        y_range = df_tech["Manufacturing"].max() - df_tech["Manufacturing"].min()
        radius = 0.05 * max(x_range, y_range)  # 5% of max axis span

        for _, row in centroids.iterrows():
            circle = plt.Circle(
                (row["Remanufacturing"], row["Manufacturing"]),
                radius=radius,
                edgecolor="black",
                facecolor="none",
                lw=1.5,
                alpha=0.8,
            )
            ax_scat.add_patch(circle)
            ax_scat.text(
                row["Remanufacturing"],
                row["Manufacturing"],
                f"C{int(row['cluster_id'])}",
                ha="center",
                va="center",
                fontsize=9,
                fontweight="bold",
                color="black",
            )

        ax_scat.set_xlabel("Remanufacturing Capacity (GW)")
        ax_scat.set_ylabel("Manufacturing Capacity (GW)")
        ax_scat.set_title(f"Cluster Overview on Scatter - {tech}")
        ax_scat.grid(True, linestyle="--", alpha=0.3)
        ax_scat.legend(title="Year", frameon=True)
        fig_scatter.tight_layout()
        fig_scatter.savefig(output_dir / f"{tech}_scatter_cluster_overlay.png", dpi=300)
        plt.close(fig_scatter)

        print(f"✔ Scatter with cluster overlays saved for {tech}")


def plot_cluster_flow(df_with_clusters, tech, output_dir="plots/cluster_flows"):
    """
    Create a Sankey-style cluster flow diagram across years.
    - Cluster nodes: white boxes with black outlines and names.
    - Flows: colored based on first-year cluster assignment.
    - Cluster names are dynamic per year based on Remanufacturing capacity.
    - Colors remain consistent across all years from original (first-year) clusters.
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    df_tech = df_with_clusters[df_with_clusters["tech"] == tech].copy()
    df_tech["combo"] = df_tech["learning_rate"].astype(str) + "_" + df_tech["scenario"].astype(str)
    years = sorted(df_tech["year"].unique())

    # --------------------------------------------------
    # Fixed color mapping from first-year clusters
    # --------------------------------------------------
    first_year = years[0]
    first_clusters = (
        df_tech[df_tech["year"] == first_year]
        .groupby("cluster_id")["Remanufacturing"]
        .mean()
        .sort_values(ascending=False)
    )
    cluster_order = list(first_clusters.index)
    base_colors = ["#636EFA", "#EF553B", "#00CC96", "#AB63FA",
                   "#FFA15A", "#19D3F3", "#FF6692", "#B6E880"]
    cluster_colors = {cid: base_colors[i % len(base_colors)] for i, cid in enumerate(cluster_order)}

    # --------------------------------------------------
    # Assign color based on *first-year* cluster of each combo
    # --------------------------------------------------
    combo_to_first_cluster = (
        df_tech[df_tech["year"] == first_year][["combo", "cluster_id"]]
        .set_index("combo")["cluster_id"]
        .to_dict()
    )

    df_tech["origin_cluster"] = df_tech["combo"].map(combo_to_first_cluster)
    df_tech["origin_color"] = df_tech["origin_cluster"].map(cluster_colors)

    # --------------------------------------------------
    # Dynamic cluster names per year based on Remanufacturing
    # --------------------------------------------------
    year_cluster_names = {}
    for year in years:
        clusters_sorted = (
            df_tech[df_tech["year"] == year]
            .groupby("cluster_id")["Remanufacturing"]
            .mean()
            .sort_values(ascending=False)
        )
        year_cluster_names[year] = {cid: f"Cluster {i+1}" for i, cid in enumerate(clusters_sorted.index)}

    # --------------------------------------------------
    # Build flow data (color stays from origin)
    # --------------------------------------------------
    flows = []
    for i in range(len(years) - 1):
        year_from = years[i]
        year_to = years[i + 1]
        df_from = df_tech[df_tech["year"] == year_from][["combo", "cluster_id", "origin_color"]]
        df_to = df_tech[df_tech["year"] == year_to][["combo", "cluster_id"]]

        merged = df_from.merge(df_to, on="combo", suffixes=("_from", "_to"))
        grouped = merged.groupby(["cluster_id_from", "cluster_id_to", "origin_color"]).size().reset_index(name="count")

        for _, row in grouped.iterrows():
            flows.append({
                "source": f"{year_cluster_names[year_from][row['cluster_id_from']]}_{year_from}",
                "target": f"{year_cluster_names[year_to][row['cluster_id_to']]}_{year_to}",
                "value": row["count"],
                "color": row["origin_color"]
            })

    # --------------------------------------------------
    # Build nodes (white boxes)
    # --------------------------------------------------
    nodes = []
    node_set = set()
    for f in flows:
        for n in [f["source"], f["target"]]:
            if n not in node_set:
                nodes.append(n)
                node_set.add(n)
    node_indices = {n: i for i, n in enumerate(nodes)}

    # --------------------------------------------------
    # Sankey Diagram
    # --------------------------------------------------
    fig = go.Figure(go.Sankey(
        node=dict(
            label=nodes,
            color="white",  # white boxes
            line=dict(color="black", width=1)  # black outlines
        ),
        link=dict(
            source=[node_indices[f["source"]] for f in flows],
            target=[node_indices[f["target"]] for f in flows],
            value=[f["value"] for f in flows],
            color=[f["color"] for f in flows]
        )
    ))

    fig.update_layout(title_text=f"Cluster Flow for {tech}", font_size=10)
    fig.write_html(output_dir / f"{tech}_cluster_flow.html")

def plot_all_cluster_flows(df_with_clusters, output_dir="plots/cluster_flows"):
    """
    Plot Sankey diagrams for cluster transitions for all technologies in df_with_clusters.

    Parameters
    ----------
    df_with_clusters : pd.DataFrame
        Must contain columns: ['tech', 'year', 'learning_rate', 'scenario', 'cluster_id']
    output_dir : str
        Folder to save Sankey diagrams
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    for tech in df_with_clusters['tech'].unique():
        print(f"📊 Generating cluster flow for {tech}...")
        plot_cluster_flow(df_with_clusters, tech=tech, output_dir=output_dir)


# -------------------------------
# Main Execution
# -------------------------------

tech_list = ['solarPV', 'windon', 'windoff']

def run_all_analyses():
    """Run all analyses automatically"""
    print("🚀 Starting automated analysis...")

    # Build scenario dictionaries
    nzia_scenarios = build_scenario_dict()
    base_file = get_base_scenario()

    print(f"📁 Base scenario: {base_file}")
    print(f"📁 NZIA scenarios: {len(nzia_scenarios)} files")

    # Run analyses
    #plot_base_generation_mix(base_file)
    #plot_renewables_breakdown_100pct(base_file) #JA
    #plot_renewables_installed_capacity_vertical(base_file) #JA
    #plot_scrap_comparison(base_file, nzia_scenarios)
    #plot_lng_analysis(base_file, nzia_scenarios)
    export_lng_data(base_file, nzia_scenarios)
    #plot_system_costs_boxplot(base_file, nzia_scenarios)
    #plot_nzia_boxplots(
    #    tech_list=tech_list,
    #    nzia_scenarios_dict=nzia_scenarios,
    #    target_years=[2025, 2030, 2035, 2040],
    #    output_dir="plots/nzia_plots",
    #)
    #plot_window_scatter_relative_single(tech_list=tech_list,
    #    nzia_scenarios_dict=nzia_scenarios)

    #plot_window_capacity_scatter( #JA
    #    tech_list=tech_list,
    #    nzia_scenarios_dict=nzia_scenarios,
    #    perform_clustering=True,  # enable clustering
    #    eps=0.15,  # tune sensitivity
    #    min_samples=3
    #)
    #plot_cumulative_capacity_scatter(
    #    tech_list=tech_list,
    #    nzia_scenarios_dict=nzia_scenarios,
    #    perform_clustering=True,  # enable clustering
    #    eps=0.3,  # tune sensitivity
    #    min_samples=3
    #)


    print("✅ All analyses completed!")


if __name__ == "__main__":
    run_all_analyses()