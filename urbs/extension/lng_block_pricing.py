from abc import ABC, abstractmethod
import pyomo.core as pyomo

class AbstractConstraint(ABC):
    @abstractmethod
    def apply_rule(self, m, *args):
        pass


class LNGYearlyDemandConstraint(AbstractConstraint):
    def apply_rule(self, m, stf, sit, com, com_type):
        # Sum LNG demand for this year from all processes
        yearly_demand = sum(
            m.e_pro_in[tm, stf, sit, pro, com]
            for tm in m.tm
            for pro in m.pro
            if (tm, stf, sit, pro, com) in m.e_pro_in.index_set()
        )

        # Debug print
        print(f"[LNG Demand] Year {stf}, site {sit}, demand = {yearly_demand}")

        return sum(m.e_co_stock_block[(stf, sit, com, com_type), b] for b in m.blocks) == yearly_demand


class LNGBlockCapConstraint(AbstractConstraint):
    def apply_rule(self, m, stf, b):
        tuples_this_year = [(stf, sit, com, com_type) for (stf, sit, com, com_type) in m.LNG_tuples if stf == stf]
        if not tuples_this_year:
            return pyomo.Constraint.Skip

        lhs = sum(m.e_co_stock_block[c, b] for c in tuples_this_year)
        rhs = m.block_limits[b]

        # Debug print
        print(f"[Block Cap] Year {stf}, block {b}, allocated = {lhs}, cap = {rhs}")

        return lhs <= rhs


class LNGCostConstraint(AbstractConstraint):
    def apply_rule(self, m, stf):
        """Calculate LNG costs for a specific year (stf)"""
        # Filter LNG tuples for this specific year
        tuples_this_year = [c for c in m.LNG_tuples if c[0] == stf]

        if not tuples_this_year:
            return m.lng_costs[stf] == 0

        # Calculate LNG cost for this year
        yearly_lng_cost = sum(
            m.block_price[b] * m.e_co_stock_block[c, b]
            for c in tuples_this_year
            for b in m.blocks
        )

        # Debug print
        print(f"[LNG Cost] Year {stf}, cost = {yearly_lng_cost}")

        return m.lng_costs[stf] == yearly_lng_cost

class LNGEmissionsCostConstraint(AbstractConstraint):
    def apply_rule(self, m, stf):
        """Calculate CO2 emissions costs for LNG for a specific year (stf)"""
        # Filter LNG tuples for this specific year
        tuples_this_year = [c for c in m.LNG_tuples if c[0] == stf]

        if not tuples_this_year:
            return m.lng_emissions_costs[stf] == 0

        # Get CO2 price for this year (assuming CO2 commodity exists)
        # This follows the pattern from your environmental cost calculation
        co2_price = 0
        try:
            # Look for CO2 price in commodity_dict
            for (st, si, co, co_type) in m.com_tuples:
                if st == stf and co == "CO2" and co_type == "Env":
                    co2_price = m.commodity_dict["price"][st, si, co, co_type]
                    break
        except:
            co2_price = 0

        # Calculate CO2 emissions cost for this year
        yearly_upstream_emissions_cost = sum(
            m.block_emissions[b] * m.e_co_stock_block[c, b] * co2_price
            for c in tuples_this_year
            for b in m.blocks
        )

        # Debug print
        print(f"[LNG Emissions Cost] Year {stf}, CO2 price = {co2_price}, emissions cost = {yearly_upstream_emissions_cost}")

        return m.lng_emissions_costs[stf] == yearly_upstream_emissions_cost

class LNGTotalCostConstraint(AbstractConstraint):
    def apply_rule(self, m, stf):
        """Calculate total LNG costs (fuel + emissions) for a specific year (stf)"""
        return m.lng_total_costs[stf] == m.lng_costs[stf] + m.lng_emissions_costs[stf]


def apply_lng_block_pricing(m, data):
    # --- Sets and Params ---
    m.years_lng = pyomo.Set(initialize=list(range(2024, 2051)))
    m.blocks = pyomo.Set(initialize=list(range(1, 15)))  # Updated to include all 14 blocks
    m.LNG_tuples = pyomo.Set(
        within=m.years_lng * m.sit * m.com * m.com_type,
        initialize=[(y, "EU27", "LNG", "Stock") for y in m.years_lng
                    if y in m.years_lng and "EU27" in m.sit and "LNG" in m.com and "Stock" in m.com_type],
        doc="LNG tuples (year, site, commodity, type)"
    )

    m.block_limits = pyomo.Param(
        m.blocks,
        initialize={b: data["lng_block_limits"][b] for b in m.blocks},
        doc="Max LNG volume per block (same for all years)"
    )
    m.block_price = pyomo.Param(
        m.blocks,
        initialize=data["lng_block_price"],
        doc="LNG block price €/MWh"
    )
    m.block_emissions = pyomo.Param(
        m.blocks,
        initialize=data["lng_block_emissions"],
        doc="LNG block emissions tCO2/MWh"
    )

    # --- Variables ---
    m.e_co_stock_block = pyomo.Var(
        m.LNG_tuples, m.blocks, within=pyomo.NonNegativeReals, doc="LNG usage per block per year"
    )

    # LNG cost variables for each year
    m.lng_costs = pyomo.Var(
        m.stf, within=pyomo.NonNegativeReals, doc="LNG fuel costs per year"
    )
    m.lng_emissions_costs = pyomo.Var(
        m.stf, within=pyomo.NonNegativeReals, doc="LNG CO2 emissions costs per year"
    )
    m.lng_total_costs = pyomo.Var(
        m.stf, within=pyomo.NonNegativeReals, doc="Total LNG costs (fuel + emissions) per year"
    )

    # --- Constraints ---
    m.lng_yearly_demand = pyomo.Constraint(
        m.LNG_tuples,
        rule=lambda m, y, site, com, com_type:
        LNGYearlyDemandConstraint().apply_rule(m, y, site, com, com_type)
    )

    m.lng_block_caps = pyomo.Constraint(
        m.years_lng, m.blocks,
        rule=lambda m, y, b: LNGBlockCapConstraint().apply_rule(m, y, b)
    )

    # LNG fuel cost constraint
    m.lng_cost_constraint = pyomo.Constraint(
        m.stf,
        rule=lambda m, stf: LNGCostConstraint().apply_rule(m, stf)
    )

    # LNG emissions cost constraint
    m.lng_emissions_cost_constraint = pyomo.Constraint(
        m.stf,
        rule=lambda m, stf: LNGEmissionsCostConstraint().apply_rule(m, stf)
    )

    # Total LNG cost constraint
    m.lng_total_cost_constraint = pyomo.Constraint(
        m.stf,
        rule=lambda m, stf: LNGTotalCostConstraint().apply_rule(m, stf)
    )

    print("✅ LNG block pricing with emissions costs applied successfully.")