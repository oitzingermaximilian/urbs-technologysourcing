from matplotlib import ticker as mticker
from pathlib import Path
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import seaborn as sns

# -------------------------------
# Configuration
# -------------------------------
BASE_PATH = Path("C:/Users/maxoi/OneDrive/Desktop/results_crm_paper/base")
NZIA_PATH = Path("C:/Users/maxoi/OneDrive/Desktop/results_crm_paper/NZIA")

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
    "Fossil fuels generation": [
        "Coal Plant", "Coal Plant CCUS", "Gas Plant (CCGT)", "Gas Plant (CCGT) CCUS",
        "Lignite Plant", "Lignite Plant CCUS", "Oil Plant", "Other non-res"
    ],
    "Renewable generation": [
        "Hydro (reservoir)", "Hydro (run-of-river)", "solarPV", "windoff", "windon"
    ],
    "Thermal nuclear generation": ["Nuclear Plant"]
}

GROUP_COLORS = {
    "Fossil fuels generation": "#F4C20D",
    "Renewable generation": "#009688",
    "Thermal nuclear generation": "#F57C00"
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

    ax.set_title("Base Scenario Generation Share by Year (%)", loc="left",
                 fontsize=18, fontweight="bold", color="#1F4E79")

    handles = [plt.Rectangle((0, 0), 1, 1, color=GROUP_COLORS[g]) for g in group_order]
    ax.legend(handles, group_order, loc="upper center", bbox_to_anchor=(0.5, -0.06),
              ncol=len(group_order), frameon=False, fontsize=11)

    plt.tight_layout(rect=[0.02, 0.04, 0.98, 0.94])
    output_path = Path(output_dir) / "base_generation_share_100pct.png"
    plt.savefig(output_path, dpi=300)
    plt.show()
    print(f"✔ Base scenario stacked bar chart saved → {output_path}")


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


def plot_lng_analysis(base_file=None, nzia_scenarios_dict=None, output_dir="plots/lng_analysis"):
    """Comprehensive LNG analysis with multiple plot types"""
    if base_file is None:
        base_file = get_base_scenario()
    if nzia_scenarios_dict is None:
        nzia_scenarios_dict = build_scenario_dict()

    years = range(2024, 2041)
    target_years = [2025, 2030, 2035, 2040]
    out_path = Path(output_dir)
    out_path.mkdir(parents=True, exist_ok=True)

    nzia_files = [f for f in nzia_scenarios_dict.values() if f.exists()]

    # 1. Spaghetti plot
    plt.figure(figsize=(8, 5))
    for f in nzia_files:
        series = load_lng(f, years)
        plt.plot(series.index, series.values, color="grey", alpha=0.3, linewidth=1)

    base_series = load_lng(base_file, years)
    plt.plot(base_series.index, base_series.values, color="lightsteelblue",
             linewidth=2.5, label="Base scenario")

    plt.xlabel("Year")
    plt.ylabel("LNG Demand [BCM]")
    plt.title("LNG Demand – NZIA scenarios vs. Base")
    plt.xlim(min(years) - 1, max(years) + 1)
    plt.xticks([2025, 2030, 2035, 2040])
    plt.grid(True, linestyle="--", alpha=0.3)
    plt.legend()
    plt.savefig(out_path / "lng_spaghetti.png", dpi=300)
    plt.show()
    print("✔ LNG spaghetti plot saved")

    # 2. Cumulative percentage deviation boxplot
    base_cumulative = load_lng(base_file, years).cumsum()
    nzia_cumulative = [load_lng(f, years).cumsum() for f in nzia_files]

    data = pd.DataFrame({i: s for i, s in enumerate(nzia_cumulative)}).T
    pct_dev = pd.DataFrame({
        y: 100 * (data[y] - base_cumulative[y]) / base_cumulative[y] for y in target_years
    })

    plt.figure(figsize=(8, 5))

    # Use 0,1,2,... for positions and then relabel
    positions = np.arange(len(target_years))
    box_data = [pct_dev[y].dropna() for y in target_years]

    # Make narrower boxes
    bp = plt.boxplot(box_data, positions=positions, widths=0.2, patch_artist=True,
                     boxprops=dict(facecolor="lightsteelblue", alpha=0.6, linewidth=1.2),
                     medianprops=dict(color="darkblue", linewidth=2),
                     whiskerprops=dict(color="grey", linestyle="--", linewidth=1.2),
                     capprops=dict(color="grey", linewidth=1.2))

    # Optional scatter points for individual scenario deviations
    # for i, year in enumerate(target_years):
    #     y_vals = pct_dev[year].dropna().values
    #     x_vals = positions[i] + 0.08 * (np.random.rand() - 0.5)
    #     plt.scatter(x_vals, y_vals, color="grey", alpha=0.6, s=30, zorder=3)

    plt.axhline(0, color="lightsteelblue", linewidth=2.5, linestyle="-", label="Base scenario")
    plt.title("Cumulative LNG Demand – Percentage Deviation from Base", fontsize=14, weight="bold")
    plt.xlabel("Year", fontsize=12)
    plt.ylabel("Deviation from Base [%]", fontsize=12)
    plt.xticks(positions, target_years, fontsize=11)
    plt.grid(axis="y", linestyle="--", alpha=0.4)
    plt.legend(frameon=False, fontsize=11)

    # Add margins to avoid touching edges
    plt.margins(x=0.1)  # 10% horizontal margin
    plt.tight_layout()
    plt.savefig(out_path / "lng_cumulative_pct_deviation.png", dpi=300)
    plt.show()
    print("✔ LNG cumulative deviation plot saved")


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
    save_csv=True
):
    """
    Scatter plot of cumulative capacities:
    - X-axis: Remanufacturing
    - Y-axis: Manufacturing
    - Different colors for each target year
    - Optionally export plotted data to CSV
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    year_colors = {2025: "#FF8C42", 2030: "#4CB5AE", 2035: "#FF6B6B", 2040: "#FFD166"}

    for tech_name in tech_list:
        all_data = []

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

            for year in target_years:
                row = df_tech[df_tech["stf"] == year]
                all_data.append({
                    "tech": tech_name,
                    "year": year,
                    "learning_rate": lr,
                    "scenario": scenario_name,
                    "Remanufacturing": row["cum_eusecondary"].sum() / 1e3,
                    "Manufacturing": row["cum_euprimary"].sum() / 1e3,
                    "Stockpile": row["cum_stockout"].sum() / 1e3
                })

        if not all_data:
            print(f"No data for {tech_name}. Skipping.")
            continue

        df_all = pd.DataFrame(all_data)

        # ===== Scatter plot =====
        plt.figure(figsize=(8,6))
        for year in target_years:
            subset = df_all[df_all["year"] == year]
            plt.scatter(subset["Remanufacturing"], subset["Manufacturing"],
                        color=year_colors[year], label=str(year), alpha=0.7, s=50)

        plt.xlabel("Remanufacturing Capacity (GW)")
        plt.ylabel("Manufacturing Capacity (GW)")
        plt.title(f"Cumulative Capacity for {tech_name}")
        plt.grid(True, linestyle="--", alpha=0.3)
        plt.legend(title="Year", frameon=True, edgecolor='black')
        plt.tight_layout()

        fig_path = Path(output_dir) / f"cumulative_scatter_{tech_name}.png"
        plt.savefig(fig_path, dpi=300)
        plt.show()
        print(f"✔ Scatter plot saved for {tech_name}: {fig_path}")

        # ===== Export plotted data to CSV =====
        if save_csv:
            csv_path = Path(output_dir) / f"cumulative_data_{tech_name}.csv"
            df_all.to_csv(csv_path, index=False)
            print(f"✔ Data exported for {tech_name}: {csv_path}")

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
    #plot_scrap_comparison(base_file, nzia_scenarios)
    plot_lng_analysis(base_file, nzia_scenarios)
    #plot_system_costs_boxplot(base_file, nzia_scenarios)
    #plot_nzia_boxplots(
    #    tech_list=tech_list,
    #    nzia_scenarios_dict=nzia_scenarios,
    #    target_years=[2025, 2030, 2035, 2040],
    #    output_dir="plots/nzia_plots",
    #)

    #plot_cumulative_capacity_scatter(
    #    tech_list=tech_list,
    #    nzia_scenarios_dict=nzia_scenarios,
    #    target_years=[2025, 2030, 2035, 2040],
    #    output_dir="plots/cumulative_scatter"
    #)

    print("✅ All analyses completed!")


if __name__ == "__main__":
    run_all_analyses()