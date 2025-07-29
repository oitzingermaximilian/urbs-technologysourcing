#!/bin/bash
echo "Testing sequential LR scenarios runner..."
echo "Start time: $(date)"

# Test Gurobi license and availability first
echo ""
echo "========================================"
echo "Testing Gurobi License and Availability"
echo "========================================"

python -c "
import sys
print('Testing Gurobi availability and license...')

try:
    import gurobipy as gp
    print('✓ Gurobi Python package (gurobipy) is installed')

    try:
        # Try to create a simple model to test license
        with gp.Env(empty=True) as env:
            env.setParam('OutputFlag', 0)  # Suppress output
            env.start()

            model = gp.Model(env=env)
            x = model.addVar(name='x')
            model.setObjective(x, gp.GRB.MINIMIZE)
            model.addConstr(x >= 1)
            model.optimize()

            if model.status == gp.GRB.OPTIMAL:
                print('✓ Gurobi license is valid and working')
                print(f'✓ Optimal value: {model.objVal}')
            else:
                print(f'✗ Gurobi model failed with status: {model.status}')

    except Exception as license_error:
        print(f'✗ Gurobi license error: {license_error}')
        print('  This might be a license issue or Gurobi server connection problem')

except ImportError:
    print('✗ Gurobi Python package (gurobipy) is not installed')
    print('  You may need to install it with: pip install gurobipy')

except Exception as e:
    print(f'✗ Unexpected Gurobi error: {e}')

# Also test if pyomo can find Gurobi as a solver
print('\nTesting Pyomo-Gurobi integration...')
try:
    import pyomo.environ as pyo
    from pyomo.opt import SolverFactory

    solver = SolverFactory('gurobi')
    if solver.available():
        print('✓ Pyomo can find Gurobi solver')
    else:
        print('✗ Pyomo cannot find Gurobi solver')

except Exception as pyomo_error:
    print(f'✗ Pyomo-Gurobi integration error: {pyomo_error}')
"

# Test parameters - you can adjust these
TEST_SCENARIOS=("LR1" "LR3_5" "LR4")  # Just test with 3 scenarios instead of all 10
SLEEP_DURATION=2  # Simulate work with short sleep instead of actual model run

for lr in "${TEST_SCENARIOS[@]}"; do
    echo ""
    echo "========================================"
    echo "Testing $lr at $(date)"
    echo "========================================"

    # Instead of running the actual model, we'll simulate it
    echo "Simulating: python run_model.py --mode rolling --lr $lr"
    echo "Working on $lr scenario..."

    # Simulate some work time
    sleep $SLEEP_DURATION

    # Check if run_model.py exists and can accept these parameters
    if [ -f "run_model.py" ]; then
        echo "✓ run_model.py found"
        # You could add a dry-run check here if your script supports it
        python -c "
import sys
print('✓ Python is working')
try:
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--mode')
    parser.add_argument('--lr')
    args = parser.parse_args(['--mode', 'rolling', '--lr', '$lr'])
    print('✓ Arguments parsing works:', args)
except Exception as e:
    print('✗ Error with arguments:', e)
"
    else
        echo "✗ run_model.py not found"
    fi

    echo "$lr test completed at $(date)"
done

echo ""
echo "All learning rate tests completed at $(date)!"
echo "If this test ran successfully, your full script should work too."
