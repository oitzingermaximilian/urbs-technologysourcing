import pyomo.environ as pyomo
import os


def apply_sets_and_params(m, data_urbsextensionv1):
    ###############################################
    # universal sets and params for extension v1.0#
    ###############################################

    # Learning rate selection via environment variable
    LEARNING_RATE = os.environ.get('URBS_LR', 'LR5')  # Default to LR5
    print(f"Using Learning Rate: {LEARNING_RATE}")

    # Excel read in
    base_params = data_urbsextensionv1["base_params"]
    # hard coded cost_types
    m.cost_type_new = pyomo.Set(
        initialize=m.cost_new_list, doc="Set of cost types (hard-coded)"
    )
    # Base sheet read in
    m.timesteps_ext = pyomo.Set(initialize=range(1, 13), doc="Timesteps")
    m.y0 = pyomo.Param(initialize=base_params["y0"], mutable=True)  # Initial year
    m.y_end = pyomo.Param(initialize=base_params["y_end"], mutable=True)  # End year
    m.hours = pyomo.Param(
        m.timesteps_ext, initialize=base_params["hours"]
    )  # Hours per year
    # locations sheet read in
    m.location = pyomo.Set(
        initialize=data_urbsextensionv1["locations_list"]
    )  # sites to be modelled

    # Extract all unique technologies across all locations
    all_techs = set()
    for loc in data_urbsextensionv1["technologies"]:
        all_techs.update(data_urbsextensionv1["technologies"][loc].keys())

    # Define the technology set
    m.tech = pyomo.Set(initialize=all_techs)

    #
    # Helper function to initialize parameters with default values
    def initialize_param(param_name, default_value=0):
        return {
            (loc, t): data_urbsextensionv1["technologies"]
            .get(loc, {})
            .get(t, {})
            .get(param_name, default_value)
            for loc in m.location
            for t in m.tech
        }

    # Define parameters using the helper function
    m.n = pyomo.Param(
        m.location,
        m.tech,
        initialize=initialize_param("n turnover stockpile", default_value=0),
    )  # Turnover of stockpile
    m.l = pyomo.Param(
        m.location, m.tech, initialize=initialize_param("l", default_value=0)
    )

    m.Installed_Capacity_Q_s = pyomo.Param(
        m.location,
        m.tech,
        initialize=initialize_param("InitialCapacity", default_value=0),
    )  # Initial installed capacity MW
    m.Existing_Stock_Q_stock = pyomo.Param(
        m.location,
        m.tech,
        initialize=initialize_param("InitialStockpile", default_value=0),
    )  # Initial stocked capacity
    m.FT = pyomo.Param(
        m.location, m.tech, initialize=initialize_param("FT", default_value=0)
    )  # Factor
    m.anti_dumping_index = pyomo.Param(
        m.location,
        m.tech,
        initialize=initialize_param("anti duping Index", default_value=0),
    )  # Anti-dumping index
    m.deltaQ_EUprimary = pyomo.Param(
        m.location,
        m.tech,
        initialize=initialize_param("dQ EU Primary", default_value=0),
    )  # ΔQ EU Primary
    m.deltaQ_EUsecondary = pyomo.Param(
        m.location,
        m.tech,
        initialize=initialize_param("dQ EU Secondary", default_value=0),
    )  # ΔQ EU Secondary
    m.IR_EU_primary = pyomo.Param(
        m.location,
        m.tech,
        initialize=initialize_param("IR EU Primary", default_value=0),
    )  # IR EU Primary
    m.IR_EU_secondary = pyomo.Param(
        m.location,
        m.tech,
        initialize=initialize_param("IR EU Secondary", default_value=0),
    )  # IR EU Secondary
    m.DR_primary = pyomo.Param(
        m.location, m.tech, initialize=initialize_param("DR Primary", default_value=0)
    )  # DR Primary
    m.DR_secondary = pyomo.Param(
        m.location, m.tech, initialize=initialize_param("DR Secondary", default_value=0)
    )  # DR Secondary
    m.STORAGECOST = pyomo.Param(
        m.location, m.tech, initialize=initialize_param("Storagecost", default_value=0)
    )
    m.logisticcost = pyomo.Param(
        m.location, m.tech, initialize=initialize_param("logisticcost", default_value=0)
    )

    # cost sheet read in
    m.IMPORTCOST = pyomo.Param(
        m.stf, m.location, m.tech, initialize=data_urbsextensionv1["importcost_dict"]
    )
    m.EU_primary_costs = pyomo.Param(
        m.stf,
        m.location,
        m.tech,
        initialize=data_urbsextensionv1["manufacturingcost_dict"],
    )
    m.EU_secondary_costs = pyomo.Param(
        m.stf,
        m.location,
        m.tech,
        initialize=data_urbsextensionv1["remanufacturingcost_dict"],
    )

    # instalable_capacity_sheet read in
    m.Q_ext_new = pyomo.Param(
        m.stf,
        m.location,
        m.tech,
        initialize=data_urbsextensionv1["installable_capacity_dict"],
    )
    # DCR sheet read in
    m.DCR_solar = pyomo.Param(
        m.stf, m.location, m.tech, initialize=data_urbsextensionv1["dcr_dict"]
    )  # DCR Solar
    # stocklvl sheet read in
    m.min_stocklvl = pyomo.Param(
        m.stf, m.location, m.tech, initialize=data_urbsextensionv1["stocklvl_dict"]
    )
    # loadfactors sheet read in
    # Capacity to Balance with loadfactor and h/a
    m.lf_solar = pyomo.Param(
        m.timesteps_ext,
        m.stf,
        m.location,
        m.tech,
        initialize=data_urbsextensionv1["loadfactors_dict"],
    )  # lf Solar

    ########################################
    # dynamic feedback loop EEM sets and params#     13. January 2025
    ########################################

    # -------EU-Primary-------# ToDo enable if needed
    # index set for n (=steps of linearization)
    # m.nsteps_pri = pyomo.Set(initialize=range(0, 7))
    # param def for price reduction
    # m.P_pri = pyomo.Param(m.nsteps_pri, initialize={0: 0, 1: 172444.8, 2: 246826.8
    #    , 3: 279008.4, 4: 292974, 5: 299046, 6: 301656.96})
    # m.capacityperstep_pri = pyomo.Param(m.nsteps_pri, initialize={0: 0, 1: 100, 2: 1000, 3: 10000, 4: 100000, 5:1000000, 6:10000000})
    # param for gamma
    # m.gamma_pri = pyomo.Param(initialize=1e10)

    # -------EU-Secondary-------#
    # index set for n (=steps of linearization)
    m.nsteps_sec = pyomo.Set(initialize=range(0, 7))

    # Scale factor to make the numbers larger for numerical stability
    scaling_factor = 100000  # Scale up by 100,000

    # ========================================
    # LEARNING RATE REDUCTION PERCENTAGES (sorted by learning rate %)
    # ========================================

    # 1% Learning Rate reduction percentage
    reduction_percentage_1 = {
        0: 1,
        1: 0.967164685,
        2: 0.935407528,
        3: 0.904693127,
        4: 0.874987243,
        5: 0.846256761,
        6: 0.818469654,
    }

    # 3.5% Learning Rate reduction percentage
    reduction_percentage_3_5 = {
        0: 1,
        1: 0.888384244,
        2: 0.789226565,
        3: 0.701136445,
        4: 0.622878571,
        5: 0.553355508,
        6: 0.491592315,
    }

    # 4% Learning Rate reduction percentage
    reduction_percentage_4 = {
        0: 1,
        1: 0.873185089,
        2: 0.7624522,
        3: 0.665761892,
        4: 0.581333357,
        5: 0.507611619,
        6: 0.443238897,
    }

    # 5% Learning Rate reduction percentage
    reduction_percentage_5 = {
        0: 1,
        1: 0.843333629,
        2: 0.711211609,
        3: 0.599788667,
        4: 0.505821953,
        5: 0.426576663,
        6: 0.359746445,
    }

    # 6% Learning Rate reduction percentage
    reduction_percentage_6 = {
        0: 1,
        1: 0.814202932,
        2: 0.662926414,
        3: 0.53975663,
        4: 0.439471431,
        5: 0.357818927,
        6: 0.29133722,
    }

    # 7% Learning Rate reduction percentage
    reduction_percentage_7 = {
        0: 1,
        1: 0.785782986,
        2: 0.617454902,
        3: 0.485185557,
        4: 0.381250556,
        5: 0.2995802,
        6: 0.235405024,
    }

    # 8% Learning Rate reduction percentage
    reduction_percentage_8 = {
        0: 1,
        1: 0.758063814,
        2: 0.574660746,
        3: 0.435629517,
        4: 0.330234973,
        5: 0.250339183,
        6: 0.189773076,
    }

    # 9% Learning Rate reduction percentage
    reduction_percentage_9 = {
        0: 1,
        1: 0.731035472,
        2: 0.534412861,
        3: 0.390674758,
        4: 0.285597106,
        5: 0.208781615,
        6: 0.152626766,
    }

    # 10% Learning Rate reduction percentage
    reduction_percentage_10 = {
        0: 1,
        1: 0.70468805,
        2: 0.496585247,
        3: 0.349937689,
        4: 0.246596908,
        5: 0.173773894,
        6: 0.122456386,
    }

    # 25% Learning Rate reduction percentage
    reduction_percentage_25 = {
        0: 1,
        1: 0.384558576,
        2: 0.147885298,
        3: 0.05687056,
        4: 0.021870061,
        5: 0.00841032,
        6: 0.003234261,
    }

    # ========================================
    # SCALED REDUCTIONS (sorted by learning rate %)
    # Convert percentage multipliers to scaled reduction amounts
    # Since we want cost reduction to INCREASE from 0 to 6, we calculate (1 - percentage) and scale
    # ========================================

    # 1% Learning Rate scaled reduction
    scaled_reduction1 = {
        n: (1 - reduction_percentage_1[n]) * scaling_factor
        for n in reduction_percentage_1.keys()
    }

    # 3.5% Learning Rate scaled reduction
    scaled_reduction3_5 = {
        n: (1 - reduction_percentage_3_5[n]) * scaling_factor
        for n in reduction_percentage_3_5.keys()
    }

    # 4% Learning Rate scaled reduction
    scaled_reduction4 = {
        n: (1 - reduction_percentage_4[n]) * scaling_factor
        for n in reduction_percentage_4.keys()
    }

    # 5% Learning Rate scaled reduction
    scaled_reduction5 = {
        n: (1 - reduction_percentage_5[n]) * scaling_factor
        for n in reduction_percentage_5.keys()
    }

    # 6% Learning Rate scaled reduction
    scaled_reduction6 = {
        n: (1 - reduction_percentage_6[n]) * scaling_factor
        for n in reduction_percentage_6.keys()
    }

    # 7% Learning Rate scaled reduction
    scaled_reduction7 = {
        n: (1 - reduction_percentage_7[n]) * scaling_factor
        for n in reduction_percentage_7.keys()
    }

    # 8% Learning Rate scaled reduction
    scaled_reduction8 = {
        n: (1 - reduction_percentage_8[n]) * scaling_factor
        for n in reduction_percentage_8.keys()
    }

    # 9% Learning Rate scaled reduction
    scaled_reduction9 = {
        n: (1 - reduction_percentage_9[n]) * scaling_factor
        for n in reduction_percentage_9.keys()
    }

    # 10% Learning Rate scaled reduction
    scaled_reduction10 = {
        n: (1 - reduction_percentage_10[n]) * scaling_factor
        for n in reduction_percentage_10.keys()
    }

    # 25% Learning Rate scaled reduction
    scaled_reduction25 = {
        n: (1 - reduction_percentage_25[n]) * scaling_factor
        for n in reduction_percentage_25.keys()
    }

    # ========================================
    # DYNAMIC LEARNING RATE SELECTION
    # ========================================

    # Create learning rate mapping for dynamic selection
    lr_mapping = {
        'LR1': scaled_reduction1,
        'LR3_5': scaled_reduction3_5,
        'LR4': scaled_reduction4,
        'LR5': scaled_reduction5,
        'LR6': scaled_reduction6,
        'LR7': scaled_reduction7,
        'LR8': scaled_reduction8,
        'LR9': scaled_reduction9,
        'LR10': scaled_reduction10,
        'LR25': scaled_reduction25
    }

    # Select the appropriate reduction based on environment variable
    selected_reduction = lr_mapping.get(LEARNING_RATE, scaled_reduction5)
    print(f"Selected reduction values: {selected_reduction}")

    # Store the scaling factor as a parameter for use in cost calculations
    m.scaling_factor = pyomo.Param(initialize=scaling_factor, doc="Scaling factor for price reductions")

    # Initialize P_sec with dynamically selected scaled values
    m.P_sec = pyomo.Param(
        m.location,  # Locations
        m.tech,  # Technologies
        m.nsteps_sec,  # Steps
        initialize=lambda m, loc, tech, n: selected_reduction[n],
        doc=f"Scaled price reduction values for {LEARNING_RATE} (to be divided by scaling_factor in cost function)"
    )


    # Define the step values (same for all technologies)
    uniform_step_values = {
        0: 0,
        1: 100,
        2: 1000,
        3: 10000,
        4: 100000,
        5: 1000000,
        6: 10000000,
    }

    # Initialize the dictionary with uniform values for all (n, loc, tech)
    capacity_init_values = {
        (loc, tech, n): uniform_step_values.get(n, 0)
        for loc in m.location
        for tech in m.tech
        for n in m.nsteps_sec
    }

    # Initialize the Pyomo Param
    m.capacityperstep_sec = pyomo.Param(
        m.location,  # First dimension
        m.tech,  # Second dimension
        m.nsteps_sec,  # Third dimension
        initialize=capacity_init_values,
    )

    # param for gamma
    m.gamma_sec = pyomo.Param(initialize=1e10)

    m.total_secondary_cap_inital = pyomo.Param(
        m.location,
        m.tech,
        initialize=initialize_param("Initial_secondary_cap", default_value=0),
    )

    ##########----------end EEM Addition-----------###############
    ##########----------    urbs-scrap  -----------###############
    m.f_scrap = pyomo.Param(
        m.location,
        m.tech,
        initialize=initialize_param("scrap", default_value=0),
        doc="tons per MW",
    )
    m.f_mining = pyomo.Param(
        m.location,
        m.tech,
        initialize=initialize_param("mining"),
        doc="tons per MW",
    )
    m.f_recycling = pyomo.Param(
        m.location,
        m.tech,
        initialize=initialize_param("recycling_efficiency"),
        doc="recycling efficiency in %",
    )
    m.f_scrap_rec = pyomo.Param(
        m.stf,
        m.location,
        m.tech,
        initialize=data_urbsextensionv1["recyclingcost_dict"],
        doc="cost for recycling in EUR/ton",
    )
    m.f_increase = pyomo.Param(
        m.location,
        m.tech,
        initialize=initialize_param("IR_recycling", default_value=0),
        doc="Fraction of increase in production",
    )
    m.capacity_dec_start = pyomo.Param(
        m.location,
        m.tech,
        initialize=initialize_param("Initial_decommisions", default_value=0),
        doc="initial decommisions",
    )

    ##########----------end urbs-scrap  -----------###############
    # added for carry over.
    m.pricereduction_sec_init = pyomo.Param(
        m.location,
        m.tech,
        initialize=initialize_param("price_reduction_init", default_value=0),
        doc="price_reduction_init",
    )

    m.cap_prim_prior = pyomo.Param(
        m.location,
        m.tech,
        initialize=initialize_param("last_prim_cap", default_value=0),
        doc="last_prim_cap",
    )
    m.cap_sec_prior = pyomo.Param(
        m.location,
        m.tech,
        initialize=initialize_param("last_sec_cap", default_value=0),
        doc="last_sec_cap",
    )

    m.factor_bess = pyomo.Param(
        m.location,
        m.tech,
        initialize=initialize_param("factor_bess", default_value=0),
        doc="factor_bess",
    )

    m.scrap_total = pyomo.Param(
        m.location,
        m.tech,
        initialize=initialize_param("capacity_scrap_total", default_value=0),
        doc="capacity_scrap_total",
    )
    m.total_facility_cap_initial = pyomo.Param(
        m.location,
        m.tech,
        initialize=initialize_param("total_facility_cap_initial", default_value=0),
        doc="total_facility_cap_initial",
    )

