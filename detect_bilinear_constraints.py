#!/usr/bin/env python3
"""
Bilinear Constraint Detection Script
This script identifies and outputs only bilinear constraints from the URBS model.
"""

import pyomo.environ as pyomo
from pyomo.core.expr.visitor import identify_variables
from pyomo.core.expr.numvalue import NumericValue
import os
import datetime


def is_bilinear_expression(expr):
    """
    Check if an expression contains bilinear terms (products of two variables).
    Returns True if bilinear, False otherwise.
    """
    if expr is None:
        return False

    try:
        # Get all variables in the expression
        variables = list(identify_variables(expr))

        if len(variables) < 2:
            return False

        # The most reliable way is to check the expression tree structure
        return check_expression_tree_for_bilinearity(expr, variables)

    except Exception as e:
        print(f"Error analyzing expression: {e}")
        return False


def check_expression_tree_for_bilinearity(expr, variables):
    """
    Recursively check expression tree for bilinear terms by examining the mathematical structure.
    This is more reliable than string pattern matching.
    """
    try:
        # Check if this expression has args (subexpressions)
        if hasattr(expr, 'args') and expr.args:
            # Check each argument
            for arg in expr.args:
                # Recursively check subexpressions
                if check_expression_tree_for_bilinearity(arg, variables):
                    return True

        # Check if this is a multiplication expression
        if hasattr(expr, '_name') and expr._name == 'ProductExpression':
            # Count unique variables in this product
            vars_in_product = list(identify_variables(expr))
            if len(vars_in_product) >= 2:
                return True

        # Alternative check using expression type
        expr_type = str(type(expr))
        if 'ProductExpression' in expr_type or 'MonomialTermExpression' in expr_type:
            # Check if this product involves multiple variables
            vars_in_product = list(identify_variables(expr))
            if len(vars_in_product) >= 2:
                # Additional check: make sure it's actually variable*variable, not variable*constant
                return has_variable_multiplication(expr, vars_in_product)

        return False

    except Exception as e:
        return False


def has_variable_multiplication(expr, variables):
    """
    Check if the expression actually contains variable*variable multiplication,
    not just variable*constant or other linear operations.
    """
    try:
        # Convert to string and look for actual multiplication patterns
        expr_str = str(expr)

        # If we have multiple variables, check if they appear in a multiplication context
        if len(variables) >= 2:
            # Look for patterns where two different variable references are multiplied
            # This is a more conservative approach to avoid false positives

            # Create a set of variable names for comparison
            var_names = set()
            for var in variables:
                # Extract the base variable name (without indices)
                var_name = str(var).split('[')[0] if '[' in str(var) else str(var)
                var_names.add(var_name)

            # If we have at least 2 different base variable names in a product, it might be bilinear
            # But we need to be more careful about the detection
            if len(var_names) >= 2:
                # Only flag as bilinear if we can confirm actual multiplication
                # Check for explicit multiplication operators between different variables
                import re

                # Look for patterns like var1 * var2 (with actual multiplication)
                for i, var1 in enumerate(variables):
                    for j, var2 in enumerate(variables):
                        if i != j:  # Different variables
                            var1_str = str(var1).replace('[', r'\[').replace(']', r'\]')
                            var2_str = str(var2).replace('[', r'\[').replace(']', r'\]')

                            # Check for direct multiplication patterns
                            pattern1 = f"{var1_str}\\s*\\*\\s*{var2_str}"
                            pattern2 = f"{var2_str}\\s*\\*\\s*{var1_str}"

                            if re.search(pattern1, expr_str) or re.search(pattern2, expr_str):
                                return True

                # Additional check for implicit multiplication in product expressions
                # This is more conservative and should reduce false positives
                return False

        return False

    except Exception:
        return False


def detect_bilinear_constraints(model, output_file=None):
    """
    Detect and print all bilinear constraints in the model.
    """
    bilinear_constraints = []
    bilinear_constraint_names = set()  # Track unique constraint names

    print("\n" + "="*80)
    print("BILINEAR CONSTRAINT DETECTION")
    print("="*80)
    print(f"Analysis started at: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*80 + "\n")

    constraint_count = 0
    bilinear_count = 0

    # Check all constraints in the model
    for constraint_name in model.component_objects(pyomo.Constraint, active=True):
        constraint = getattr(model, constraint_name.name)
        constraint_count += 1

        print(f"Analyzing constraint: {constraint_name.name}...")

        found_bilinear_in_this_constraint = False

        # Handle indexed and non-indexed constraints
        if constraint.is_indexed():
            for index in constraint:
                try:
                    constraint_expr = constraint[index]
                    if constraint_expr.body is not None:
                        if is_bilinear_expression(constraint_expr.body):
                            bilinear_count += 1
                            constraint_info = {
                                'name': constraint_name.name,
                                'index': index,
                                'expression': str(constraint_expr.body),
                                'bounds': (constraint_expr.lower, constraint_expr.upper)
                            }
                            bilinear_constraints.append(constraint_info)

                            # Only print the constraint name once, not for every index
                            if not found_bilinear_in_this_constraint:
                                bilinear_constraint_names.add(constraint_name.name)
                                print(f"🔴 BILINEAR CONSTRAINT FOUND: {constraint_name.name}")
                                print(f"   Example expression: {constraint_expr.body}")
                                if constraint_expr.lower is not None:
                                    print(f"   Lower bound: {constraint_expr.lower}")
                                if constraint_expr.upper is not None:
                                    print(f"   Upper bound: {constraint_expr.upper}")
                                print("-" * 60)
                                found_bilinear_in_this_constraint = True

                except Exception as e:
                    print(f"   Error processing index {index}: {e}")
        else:
            try:
                if constraint.body is not None:
                    if is_bilinear_expression(constraint.body):
                        bilinear_count += 1
                        constraint_info = {
                            'name': constraint_name.name,
                            'index': None,
                            'expression': str(constraint.body),
                            'bounds': (constraint.lower, constraint.upper)
                        }
                        bilinear_constraints.append(constraint_info)
                        bilinear_constraint_names.add(constraint_name.name)

                        print(f"🔴 BILINEAR CONSTRAINT FOUND: {constraint_name.name}")
                        print(f"   Expression: {constraint.body}")
                        if constraint.lower is not None:
                            print(f"   Lower bound: {constraint.lower}")
                        if constraint.upper is not None:
                            print(f"   Upper bound: {constraint.upper}")
                        print("-" * 60)

            except Exception as e:
                print(f"   Error processing constraint {constraint_name.name}: {e}")

    # Summary
    print("\n" + "="*80)
    print("BILINEAR CONSTRAINT DETECTION SUMMARY")
    print("="*80)
    print(f"Total constraints analyzed: {constraint_count}")
    print(f"Total bilinear constraint instances found: {bilinear_count}")
    print(f"Unique bilinear constraint types: {len(bilinear_constraint_names)}")
    print("\nBilinear constraint names:")
    for name in sorted(bilinear_constraint_names):
        print(f"  - {name}")
    print(f"Analysis completed at: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*80 + "\n")

    # Write to file if specified
    if output_file:
        write_bilinear_constraints_to_file(bilinear_constraints, output_file)

    return bilinear_constraints


def write_bilinear_constraints_to_file(bilinear_constraints, output_file):
    """
    Write bilinear constraints to a text file.
    """
    try:
        with open(output_file, 'w') as f:
            f.write("BILINEAR CONSTRAINTS DETECTED\n")
            f.write("="*80 + "\n")
            f.write(f"Analysis date: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Total bilinear constraints found: {len(bilinear_constraints)}\n")
            f.write("="*80 + "\n\n")

            for i, constraint in enumerate(bilinear_constraints, 1):
                f.write(f"BILINEAR CONSTRAINT #{i}\n")
                f.write("-" * 40 + "\n")
                f.write(f"Name: {constraint['name']}")
                if constraint['index'] is not None:
                    f.write(f"[{constraint['index']}]")
                f.write("\n")
                f.write(f"Expression: {constraint['expression']}\n")
                if constraint['bounds'][0] is not None:
                    f.write(f"Lower bound: {constraint['bounds'][0]}\n")
                if constraint['bounds'][1] is not None:
                    f.write(f"Upper bound: {constraint['bounds'][1]}\n")
                f.write("\n")

        print(f"✅ Bilinear constraints written to: {output_file}")

    except Exception as e:
        print(f"❌ Error writing to file: {e}")


def analyze_model_bilinearity(model, output_dir="bilinear_analysis"):
    """
    Main function to analyze model for bilinear constraints.
    """
    # Create output directory
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    # Generate output filename with timestamp
    timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
    output_file = os.path.join(output_dir, f"bilinear_constraints_{timestamp}.txt")

    # Detect bilinear constraints
    bilinear_constraints = detect_bilinear_constraints(model, output_file)

    return bilinear_constraints


if __name__ == "__main__":
    print("This script is designed to be imported and used with a Pyomo model.")
    print("Usage:")
    print("  from detect_bilinear_constraints import analyze_model_bilinearity")
    print("  bilinear_constraints = analyze_model_bilinearity(your_model)")
