from ortools.sat.python import cp_model


def solve_scheduling_problem():
    # Create the model
    model = cp_model.CpModel()

    # Define the tasks with their durations
    tasks = {
        "Task A": 3,
        "Task B": 2,
        "Task C": 2,
        "Task D": 4,
        "Task E": 1,
    }

    # Define the horizon (maximum time limit)
    horizon = 15

    # Define the machine groups
    group_1_machines = [0, 1]  # Group 1 machines
    group_2_machines = [2, 3]  # Group 2 machines
    all_machines = group_1_machines + group_2_machines

    # Create variables for start times, intervals, and machine assignments
    task_intervals = {}
    task_starts = {}
    task_ends = {}
    task_machines = {}

    all_intervals = []

    for task, duration in tasks.items():
        start_var = model.NewIntVar(0, horizon, f"{task}_start")
        end_var = model.NewIntVar(0, horizon, f"{task}_end")
        machine_1_var = model.NewIntVar(0, len(all_machines) - 1, f"{task}_machine_1")
        machine_2_var = model.NewIntVar(0, len(all_machines) - 1, f"{task}_machine_2")
        interval_var = model.NewIntervalVar(
            start_var, duration, end_var, f"{task}_interval"
        )
        task_starts[task] = start_var
        task_ends[task] = end_var
        task_machines[task] = (machine_1_var, machine_2_var)
        task_intervals[task] = (interval_var, machine_1_var, machine_2_var)
        all_intervals.append((interval_var, machine_1_var, machine_2_var))

    # Add constraints: No overlapping tasks on the same machine
    for machine in all_machines:
        machine_intervals = [
            interval
            for interval, machine_1, machine_2 in all_intervals
            if machine_1 == machine or machine_2 == machine
        ]
        model.AddNoOverlap(machine_intervals)

    # Add constraints: Machines in group 1 must work continuously
    for machine in group_1_machines:
        machine_intervals = [
            interval
            for interval, machine_1, machine_2 in all_intervals
            if machine_1 == machine or machine_2 == machine
        ]
        if machine_intervals:
            model.AddNoOverlap(machine_intervals)
            model.AddCumulative(machine_intervals, [1] * len(machine_intervals), 1)

    # Add additional constraints (optional)
    # Example: Task A must start after Task B ends
    model.Add(task_starts["Task A"] >= task_ends["Task B"])

    # Define the objective: Minimize the makespan (end of the last task across all machines)
    makespan = model.NewIntVar(0, horizon, "makespan")
    model.AddMaxEquality(makespan, list(task_ends.values()))
    model.Minimize(makespan)

    # Solve the model
    solver = cp_model.CpSolver()
    status = solver.Solve(model)

    # Print the solution
    if status == cp_model.OPTIMAL or status == cp_model.FEASIBLE:
        print("Solution found!")
        for task in tasks:
            machine_1 = solver.Value(task_machines[task][0])
            machine_2 = solver.Value(task_machines[task][1])
            print(
                f"{task}: Start at {solver.Value(task_starts[task])}, "
                f"End at {solver.Value(task_ends[task])}, "
                f"Machines {machine_1} and {machine_2}"
            )
        print(f"Makespan: {solver.Value(makespan)}")
    else:
        print("No solution found.")


solve_scheduling_problem()
