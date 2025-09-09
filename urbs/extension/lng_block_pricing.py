from abc import ABC, abstractmethod
import pyomo.core as pyomo

# -----------------------------
# Abstract Base Constraint
# -----------------------------
class AbstractConstraint(ABC):
    @abstractmethod
    def apply_rule(self, m, *args):
        pass

# -----------------------------
# LNG Block Capacity Constraint (timestep-aware)
# -----------------------------
class LNGBlockCapConstraint(AbstractConstraint):
    def apply_rule(self, m, tm, stf, sit, com, com_type, b):
        if com != "LNG":
            return pyomo.Constraint.Skip

        # Per timestep limit = yearly limit / number of timesteps
        lhs = m.e_co_stock_block[tm, stf, sit, com, com_type, b]
        rhs = m.block_limits[b] / len(m.tm)

        # Debug
        print(f"[LNG Block Cap] tm={tm}, stf={stf}, sit={sit}, block={b}, allocated={lhs}, cap={rhs}")

        return lhs <= rhs

# -----------------------------
# LNG Cost Constraint (yearly)
# -----------------------------
class LNGCostConstraint(AbstractConstraint):
    def apply_rule(self, m, stf):
        # Sum over all timesteps, sites, and blocks for this year
        yearly_lng_cost = sum(
            m.block_price[b] * m.e_co_stock_block[tm, stf, sit, "LNG", "Stock", b]
            for tm in m.tm
            for sit in m.sit
            for b in m.blocks
        )

        # Debug print
        print(f"[LNG Cost] Year {stf}, cost = {yearly_lng_cost}")

        return m.lng_costs[stf] == yearly_lng_cost

# -----------------------------
# LNG Total Cost Constraint (optional: sum over all years)
# -----------------------------
class LNGTotalCostConstraint(AbstractConstraint):
    def apply_rule(self, m):
        return m.lng_total_costs == sum(m.lng_costs[stf] for stf in m.stf)

# -----------------------------
# Apply LNG Block Pricing to Model
# -----------------------------
def apply_lng_block_pricing(m, data):
    # --- Sets ---
    m.blocks = pyomo.Set(initialize=list(range(1, 15)))  # 14 blocks

    # --- Parameters ---
    m.block_limits = pyomo.Param(
        m.blocks,
        initialize={b: data["lng_block_limits"][b] for b in m.blocks},
        doc="Max LNG volume per block (yearly)"
    )

    m.block_price = pyomo.Param(
        m.blocks,
        initialize=data["lng_block_price"],
        doc="LNG block price €/MWh"
    )

    # --- Variables ---
    m.e_co_stock_block = pyomo.Var(
        m.tm, m.stf, m.sit, m.com, m.com_type, m.blocks,
        within=pyomo.NonNegativeReals,
        doc="LNG usage per timestep, site, commodity, type, block"
    )

    # LNG costs per year
    m.lng_costs = pyomo.Var(
        m.stf,
        within=pyomo.NonNegativeReals,
        doc="LNG costs per year"
    )

    # Total LNG cost (scalar)
    m.lng_total_costs = pyomo.Var(
        within=pyomo.NonNegativeReals,
        doc="Total LNG cost over all years"
    )

    # --- Constraints ---
    # 1. Block capacities per timestep
    m.lng_block_caps = pyomo.Constraint(
        m.tm, m.stf, m.sit, m.com, m.com_type, m.blocks,
        rule=lambda m, tm, stf, sit, com, com_type, b:
        LNGBlockCapConstraint().apply_rule(m, tm, stf, sit, com, com_type, b)
    )

    # 2. Yearly LNG cost
    m.lng_cost_constraint = pyomo.Constraint(
        m.stf,
        rule=lambda m, stf: LNGCostConstraint().apply_rule(m, stf)
    )

    # 3. Total LNG cost
    m.lng_total_cost_constraint = pyomo.Constraint(
        rule=lambda m: LNGTotalCostConstraint().apply_rule(m)
    )

    print("✅ LNG block pricing applied successfully.")

# -----------------------------
# Optional: Upstream Emissions (keep for later)
# -----------------------------
"""
class LNGEmissionsCostConstraint(AbstractConstraint):
    def apply_rule(self, m, stf):
        tuples_this_year = [c for c in m.LNG_tuples if c[0] == stf]
        if not tuples_this_year:
            return m.lng_emissions_costs[stf] == 0

        co2_price = 0
        try:
            for (st, si, co, co_type) in m.com_tuples:
                if st == stf and co == "CO2" and co_type == "Env":
                    co2_price = m.commodity_dict["price"][st, si, co, co_type]
                    break
        except:
            co2_price = 0

        yearly_upstream_emissions_cost = sum(
            m.block_emissions[b] * m.e_co_stock_block[c, b] * co2_price
            for c in tuples_this_year
            for b in m.blocks
        )

        return m.lng_emissions_costs[stf] == yearly_upstream_emissions_cost
"""
