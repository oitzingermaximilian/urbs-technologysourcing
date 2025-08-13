"""
Simple and easy methods to identify large RHS constraints in URBS model
"""

import pyomo.core as pyomo
import pandas as pd


def quick_rhs_check(model, threshold=1e7):
    """
    Super simple way to find large RHS constraints.
    Just prints them out - no complex analysis.

    Args:
        model: Your Pyomo model instance
        threshold: What you consider "large" (default 1 million)
    """
    print(f"Constraints with RHS > {threshold:.0e}:")
    print("-" * 50)

    large_constraints = []

    # Loop through all constraints
    for constraint in model.component_objects(pyomo.Constraint):
        constraint_name = constraint.name

        for index in constraint:
            try:
                con = constraint[index]

                # Check upper bound
                if hasattr(con, 'upper') and con.upper is not None:
                    if abs(con.upper) > threshold:
                        large_constraints.append((constraint_name, index, 'upper', con.upper))

                # Check lower bound
                if hasattr(con, 'lower') and con.lower is not None:
                    if abs(con.lower) > threshold:
                        large_constraints.append((constraint_name, index, 'lower', con.lower))

            except:
                continue

    # Print results
    if large_constraints:
        for name, idx, bound_type, value in large_constraints:
            print(f"{name}[{idx}] ({bound_type}): {value:.2e}")
    else:
        print("No large RHS constraints found!")

    return large_constraints


def find_largest_rhs(model, top_n=10):
    """
    Even simpler - just find the N largest RHS values.

    Args:
        model: Your Pyomo model
        top_n: How many to show (default 10)
    """
    all_rhs = []

    for constraint in model.component_objects(pyomo.Constraint):
        for index in constraint:
            try:
                con = constraint[index]

                if hasattr(con, 'upper') and con.upper is not None:
                    all_rhs.append((constraint.name, index, 'upper', abs(con.upper)))

                if hasattr(con, 'lower') and con.lower is not None:
                    all_rhs.append((constraint.name, index, 'lower', abs(con.lower)))

            except:
                continue

    # Sort by RHS value (largest first)
    all_rhs.sort(key=lambda x: x[3], reverse=True)

    print(f"Top {top_n} largest RHS values:")
    print("-" * 40)
    for i, (name, idx, bound_type, value) in enumerate(all_rhs[:top_n]):
        print(f"{i+1:2d}. {name}[{idx}] ({bound_type}): {value:.2e}")

    return all_rhs[:top_n]


def solver_scaling_check(model):
    """
    Quick check for common scaling issues that cause solver problems.
    Looks for RHS values that are very different magnitudes.
    """
    rhs_values = []

    for constraint in model.component_objects(pyomo.Constraint):
        for index in constraint:
            try:
                con = constraint[index]

                if hasattr(con, 'upper') and con.upper is not None:
                    rhs_values.append(abs(con.upper))
                if hasattr(con, 'lower') and con.lower is not None:
                    rhs_values.append(abs(con.lower))

            except:
                continue

    if rhs_values:
        rhs_values = [v for v in rhs_values if v > 0]  # Remove zeros
        if rhs_values:
            min_rhs = min(rhs_values)
            max_rhs = max(rhs_values)
            ratio = max_rhs / min_rhs

            print("RHS Scaling Analysis:")
            print(f"  Smallest RHS: {min_rhs:.2e}")
            print(f"  Largest RHS:  {max_rhs:.2e}")
            print(f"  Range ratio:  {ratio:.2e}")

            if ratio > 1e12:
                print("  ⚠️  WARNING: Very large scaling ratio! This can cause solver issues.")
            elif ratio > 1e8:
                print("  ⚠️  CAUTION: Large scaling ratio. Consider rescaling units.")
            else:
                print("  ✓ Scaling looks reasonable.")


def one_liner_check(model):
    """
    One-liner to quickly spot large constraints.
    """
    large = [(c.name, i, getattr(c[i], 'upper', getattr(c[i], 'lower', 0)))
             for c in model.component_objects(pyomo.Constraint)
             for i in c
             if (hasattr(c[i], 'upper') and c[i].upper and abs(c[i].upper) > 1e6) or
                (hasattr(c[i], 'lower') and c[i].lower and abs(c[i].lower) > 1e6)]

    print("Large constraints (one-liner method):")
    for name, idx, value in large[:10]:  # Show first 10
        print(f"  {name}[{idx}]: {value:.2e}")

    return large


if __name__ == "__main__":
    print("Simple constraint checking tools for URBS")
    print("\nUsage examples:")
    print("  quick_rhs_check(model)           # Find all RHS > 1e6")
    print("  find_largest_rhs(model)         # Show top 10 largest")
    print("  solver_scaling_check(model)     # Check for scaling issues")
    print("  one_liner_check(model)          # Quick and dirty check")
