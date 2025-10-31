import numpy as np
from ortools.sat.python import cp_model
from backend.models import Requirement, StudentGroup, Teacher
from collections import defaultdict
from backend.helpers import get_teacher_block_indexes, get_group_block_indexes


def solve_schedule(req_set, block_list, specimen):
    horizon = 12

    group_block_indexes = get_group_block_indexes(
        block_list, StudentGroup.objects.filter(pool=req_set.group_pool)
    )
    teacher_block_indexes = get_teacher_block_indexes(
        block_list, Teacher.objects.filter(pool=req_set.teacher_pool)
    )

    all_intervals = []
    return_plan: list[tuple[tuple[Requirement], int, int, int]] = []

    daily_plans = defaultdict(list)

    for day_index, day in enumerate(specimen):
        minimization_vars = []
        model = cp_model.CpModel()
        task_intervals = []
        interval_blocks = {}
        task_starts = {}
        task_ends = {}
        task_duration = {}
        task_border_vars = defaultdict(tuple)
        for block, duration in zip(block_list, day):
            if duration == 0:
                task_intervals.append(None)
                all_intervals.append(None)
            else:
                start_var = model.NewIntVar(
                    0, horizon, f"{tuple(map(str, block))}_start"
                )
                end_var = model.NewIntVar(0, horizon, f"{tuple(map(str, block))}_end")
                interval_var = model.NewIntervalVar(
                    start_var, duration, end_var, f"{tuple(map(str, block))}_interval"
                )
                task_starts[interval_var] = start_var
                task_ends[interval_var] = end_var
                task_duration[interval_var] = duration
                if all(req.subject.border for req in block):
                    task_border_vars[interval_var] = (start_var, end_var)
                task_intervals.append(interval_var)
                all_intervals.append(interval_var)
                interval_blocks[interval_var] = block

        # Adding no overlaps
        teacher_intervals_dict = defaultdict(list)
        group_intervals_dict = defaultdict(list)

        for interval, teacher_indexs in zip(task_intervals, teacher_block_indexes):
            for teacher_index in teacher_indexs:
                if interval:
                    teacher_intervals_dict[teacher_index].append(interval)

        for interval, group_indexs in zip(task_intervals, group_block_indexes):
            for group_index in group_indexs:
                if interval:
                    group_intervals_dict[group_index].append(interval)

        for teacher_intervals in teacher_intervals_dict.values():
            model.AddNoOverlap(teacher_intervals)

            day_start = model.NewIntVar(0, horizon, "teacher_start")
            day_end = model.NewIntVar(0, horizon, "teacher_end")

            model.AddMinEquality(
                day_start, [task_starts[interval] for interval in teacher_intervals]
            )
            model.AddMaxEquality(
                day_end, [task_ends[interval] for interval in teacher_intervals]
            )
            teacher_duration = model.NewIntVar(0, horizon, "teacher_total_time")
            model.Add(teacher_duration == day_end - day_start)

            minimization_vars.append(teacher_duration)

        for group_intervals in group_intervals_dict.values():
            model.AddNoOverlap(group_intervals)

            # Continuous
            day_start = model.NewIntVar(0, horizon, "group_start")
            day_end = model.NewIntVar(0, horizon, "group_end")

            model.AddMinEquality(
                day_start, [task_starts[interval] for interval in group_intervals]
            )
            model.AddMaxEquality(
                day_end, [task_ends[interval] for interval in group_intervals]
            )

            model.Add(
                day_end - day_start
                == sum([task_duration[interval] for interval in group_intervals])
            )

            # Border
            for interval in group_intervals:
                if task_border_vars[interval]:
                    start_bool = model.NewBoolVar("start_border")
                    end_bool = model.NewBoolVar("end_border")
                    model.Add(day_start == task_border_vars[interval][0]).OnlyEnforceIf(
                        start_bool
                    )
                    model.Add(day_start != task_border_vars[interval][0]).OnlyEnforceIf(
                        start_bool.Not()
                    )
                    model.Add(day_end == task_border_vars[interval][1]).OnlyEnforceIf(
                        end_bool
                    )
                    model.Add(day_end != task_border_vars[interval][1]).OnlyEnforceIf(
                        end_bool.Not()
                    )

                    model.AddBoolOr([start_bool, end_bool])

        model.Minimize(sum(minimization_vars))
        solver = cp_model.CpSolver()
        status = solver.Solve(model)

        if status == cp_model.OPTIMAL or status == cp_model.FEASIBLE:
            print("constructed day")
            # Save the plan for each student group for the current day
            for interval in filter(lambda interval: interval, task_intervals):
                return_plan.append(
                    (
                        interval_blocks[interval],
                        solver.Value(interval.StartExpr()),
                        solver.Value(interval.EndExpr()),
                        day_index,
                    )
                )
            for group_index, group_intervals in group_intervals_dict.items():
                for interval in group_intervals:
                    start = solver.Value(interval.StartExpr())
                    end = solver.Value(interval.EndExpr())
                    daily_plans[day_index].append(
                        (group_index, interval_blocks[interval], start, end)
                    )

    return return_plan, daily_plans


# # Print the sorted plan for each day
# for day_index, intervals in daily_plans.items():
#     print(f"Day {day_index + 1}:")
#     # Group intervals by student group
#     group_plans = defaultdict(list)
#     for group_index, name, start, end in intervals:
#         group_plans[group_index].append((name, start, end))

#     # Sort and print intervals for each group
#     for group_index, group_intervals in sorted(group_plans.items()):
#         if group_index == 0:
#             print(f"  Student Group {group_index}:")
#             sorted_intervals = sorted(
#                 group_intervals, key=lambda x: x[1]
#             )  # Sort by start time
#             for name, start, end in sorted_intervals:
#                 print(f"    Interval: {name} | Start: {start}, End: {end}")
#             print()
