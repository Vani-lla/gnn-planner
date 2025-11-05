import numpy as np
from ortools.sat.python import cp_model
from backend.models import Requirement, StudentGroup, Teacher, Room, RequirementSet
from collections import defaultdict
from backend.helpers import get_teacher_block_indexes, get_group_block_indexes


def solve_schedule(req_set: RequirementSet, block_list, specimen):
    horizon = 12

    group_block_indexes = get_group_block_indexes(
        block_list, StudentGroup.objects.filter(pool=req_set.group_pool)
    )
    teacher_block_indexes = get_teacher_block_indexes(
        block_list, Teacher.objects.filter(pool=req_set.teacher_pool)
    )
    rooms = list(Room.objects.filter(pool=req_set.room_pool))
    room_names = list(room.name for room in rooms)
    required_no_of_rooms = list(len(block) for block in block_list)

    all_intervals = []
    return_plan: list[tuple[tuple[Requirement], int, int, int, list[str]]] = []

    daily_plans = defaultdict(list)

    for day_index, day in enumerate(specimen):
        minimization_vars = []
        model = cp_model.CpModel()
        solver = cp_model.CpSolver()
        task_intervals = []
        interval_blocks = {}
        task_starts = {}
        task_ends = {}
        task_duration = {}
        task_border_vars = defaultdict(tuple)
        task_rooms = {}  # Map intervals to room variables

        for block, duration, room_count in zip(block_list, day, required_no_of_rooms):
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

                # Create room variables
                room_vars = [
                    model.NewBoolVar(f"{tuple(map(str, block))}_room_{room.name}")
                    for room in rooms
                ]
                task_rooms[interval_var] = room_vars

                # Ensure the correct number of rooms are assigned
                model.Add(sum(room_vars) == room_count)

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

        # Add room no-overlap constraints
        for room_index, room in enumerate(rooms):
            room_intervals = []
            for interval, room_vars in task_rooms.items():
                # Create a conditional interval for the room
                room_active = room_vars[room_index]
                room_start = task_starts[interval]
                room_end = task_ends[interval]
                room_duration = task_duration[interval]
                room_interval = model.NewOptionalIntervalVar(
                    room_start,
                    room_duration,
                    room_end,
                    room_active,
                    f"{room.name}_interval",
                )
                room_intervals.append(room_interval)

            # Add no-overlap constraint for the room
            model.AddNoOverlap(room_intervals)

        model.minimize(sum(minimization_vars))
        status = solver.Solve(model)

        if status == cp_model.OPTIMAL or status == cp_model.FEASIBLE:
            print("constructed day")
            # Save the plan for each student group for the current day
            for interval in filter(lambda interval: interval, task_intervals):
                assigned_rooms = [
                    room.name
                    for room, room_var in zip(rooms, task_rooms[interval])
                    if solver.Value(room_var)
                ]
                return_plan.append(
                    (
                        interval_blocks[interval],
                        solver.Value(interval.StartExpr()),
                        solver.Value(interval.EndExpr()),
                        day_index,
                        assigned_rooms,
                    )
                )
            for group_index, group_intervals in group_intervals_dict.items():
                for interval in group_intervals:
                    start = solver.Value(interval.StartExpr())
                    end = solver.Value(interval.EndExpr())
                    daily_plans[day_index].append(
                        (group_index, interval_blocks[interval], start, end)
                    )

    print(return_plan)
    return return_plan, daily_plans


# def solve_schedule(req_set: RequirementSet, block_list, specimen):
#     horizon = 12

#     group_block_indexes = get_group_block_indexes(
#         block_list, StudentGroup.objects.filter(pool=req_set.group_pool)
#     )
#     teacher_block_indexes = get_teacher_block_indexes(
#         block_list, Teacher.objects.filter(pool=req_set.teacher_pool)
#     )
#     rooms = list(Room.objects.filter(pool=req_set.room_pool))
#     room_names = [room.name for room in rooms]
#     required_no_of_rooms = [len(block) for block in block_list]

#     all_intervals = []
#     return_plan: list[tuple[tuple[Requirement], int, int, int, list[str]]] = []

#     daily_plans = defaultdict(list)

#     # Precompute room combinations to avoid repeated calculations
#     room_combinations = {}
#     max_rooms_needed = max(required_no_of_rooms) if required_no_of_rooms else 0
#     room_indices = list(range(len(rooms)))

#     # Generate valid room combinations for each room count
#     for room_count in range(1, max_rooms_needed + 1):
#         if room_count <= len(rooms):
#             # Use combinations instead of permutations for room assignment
#             from itertools import combinations

#             room_combinations[room_count] = list(combinations(room_indices, room_count))

#     for day_index, day in enumerate(specimen):
#         minimization_vars = []
#         model = cp_model.CpModel()
#         solver = cp_model.CpSolver()

#         # Reduce solver logging and enable more aggressive strategies
#         solver.parameters.log_search_progress = False
#         # solver.parameters.num_search_workers = (
#         #     1  # Single worker often faster for small problems
#         # )
#         solver.parameters.max_time_in_seconds = 30.0  # Limit solving time per day

#         task_intervals = []
#         interval_blocks = {}
#         task_starts = {}
#         task_ends = {}
#         task_duration = {}
#         task_border_vars = defaultdict(tuple)
#         task_room_combinations = {}  # Use room combination variables

#         # Pre-filter blocks with duration > 0
#         active_blocks = []
#         for i, (block, duration, room_count) in enumerate(
#             zip(block_list, day, required_no_of_rooms)
#         ):
#             if duration > 0:
#                 active_blocks.append((i, block, duration, room_count))

#         for i, block, duration, room_count in active_blocks:
#             start_var = model.NewIntVar(0, horizon, f"start_{i}")
#             end_var = model.NewIntVar(0, horizon, f"end_{i}")
#             interval_var = model.NewIntervalVar(
#                 start_var, duration, end_var, f"interval_{i}"
#             )

#             task_starts[interval_var] = start_var
#             task_ends[interval_var] = end_var
#             task_duration[interval_var] = duration

#             if all(req.subject.border for req in block):
#                 task_border_vars[interval_var] = (start_var, end_var)

#             task_intervals.append(interval_var)
#             all_intervals.append(interval_var)
#             interval_blocks[interval_var] = block

#             # Optimized room assignment using combination variables
#             if room_count > 0 and room_count <= len(rooms):
#                 if room_count in room_combinations:
#                     combos = room_combinations[room_count]
#                     room_combo_var = model.NewIntVar(
#                         0, len(combos) - 1, f"room_combo_{i}"
#                     )
#                     task_room_combinations[interval_var] = (room_combo_var, combos)

#                     # Link room combination to room usage
#                     for room_idx in range(len(rooms)):
#                         room_used = model.NewBoolVar(f"room_{i}_{room_idx}_used")
#                         # Room is used if it appears in the selected combination
#                         model.AddElement(
#                             room_combo_var,
#                             [1 if room_idx in combo else 0 for combo in combos],
#                             room_used,
#                         )

#         # Optimized no-overlap constraints
#         teacher_intervals_dict = defaultdict(list)
#         group_intervals_dict = defaultdict(list)

#         for interval, (i, block, duration, room_count) in zip(
#             task_intervals, active_blocks
#         ):
#             teacher_indexes = teacher_block_indexes[i]
#             for teacher_index in teacher_indexes:
#                 teacher_intervals_dict[teacher_index].append(interval)

#             group_indexes = group_block_indexes[i]
#             for group_index in group_indexes:
#                 group_intervals_dict[group_index].append(interval)

#         # Process teacher constraints
#         for teacher_index, teacher_intervals in teacher_intervals_dict.items():
#             if len(teacher_intervals) > 1:
#                 model.AddNoOverlap(teacher_intervals)

#             if teacher_intervals:  # Only create duration vars if there are intervals
#                 day_start = model.NewIntVar(0, horizon, f"t_start_{teacher_index}")
#                 day_end = model.NewIntVar(0, horizon, f"t_end_{teacher_index}")

#                 model.AddMinEquality(
#                     day_start, [task_starts[interval] for interval in teacher_intervals]
#                 )
#                 model.AddMaxEquality(
#                     day_end, [task_ends[interval] for interval in teacher_intervals]
#                 )

#                 teacher_duration = model.NewIntVar(0, horizon, f"t_dur_{teacher_index}")
#                 model.Add(teacher_duration == day_end - day_start)
#                 minimization_vars.append(teacher_duration)

#         # Process group constraints
#         for group_index, group_intervals in group_intervals_dict.items():
#             if len(group_intervals) > 1:
#                 model.AddNoOverlap(group_intervals)

#             if group_intervals:
#                 # Continuous constraint
#                 day_start = model.NewIntVar(0, horizon, f"g_start_{group_index}")
#                 day_end = model.NewIntVar(0, horizon, f"g_end_{group_index}")

#                 model.AddMinEquality(
#                     day_start, [task_starts[interval] for interval in group_intervals]
#                 )
#                 model.AddMaxEquality(
#                     day_end, [task_ends[interval] for interval in group_intervals]
#                 )

#                 total_duration = sum(
#                     task_duration[interval] for interval in group_intervals
#                 )
#                 model.Add(day_end - day_start == total_duration)

#                 # Border constraints - only create if needed
#                 border_intervals = [
#                     interval
#                     for interval in group_intervals
#                     if interval in task_border_vars
#                 ]
#                 if border_intervals:
#                     for interval in border_intervals:
#                         start_bool = model.NewBoolVar(f"start_border_{group_index}")
#                         end_bool = model.NewBoolVar(f"end_border_{group_index}")

#                         model.Add(
#                             day_start == task_border_vars[interval][0]
#                         ).OnlyEnforceIf(start_bool)
#                         model.Add(
#                             day_start != task_border_vars[interval][0]
#                         ).OnlyEnforceIf(start_bool.Not())
#                         model.Add(
#                             day_end == task_border_vars[interval][1]
#                         ).OnlyEnforceIf(end_bool)
#                         model.Add(
#                             day_end != task_border_vars[interval][1]
#                         ).OnlyEnforceIf(end_bool.Not())

#                         model.AddBoolOr([start_bool, end_bool])

#         # Optimized room constraints using combination-based approach
#         room_usage_intervals = defaultdict(list)

#         for interval in task_intervals:
#             if interval in task_room_combinations:
#                 room_combo_var, combos = task_room_combinations[interval]
#                 start_var = task_starts[interval]
#                 end_var = task_ends[interval]
#                 duration = task_duration[interval]

#                 # For each room, create conditional interval based on combination selection
#                 for room_idx in range(len(rooms)):
#                     room_used = model.NewBoolVar(f"room_used_{room_idx}_{id(interval)}")

#                     # Room is used if it appears in selected combination
#                     model.AddElement(
#                         room_combo_var,
#                         [1 if room_idx in combo else 0 for combo in combos],
#                         room_used,
#                     )

#                     # Create optional interval for this room
#                     room_interval = model.NewOptionalIntervalVar(
#                         start_var,
#                         duration,
#                         end_var,
#                         room_used,
#                         f"room_{room_idx}_interval_{id(interval)}",
#                     )
#                     room_usage_intervals[room_idx].append(room_interval)

#         # Add no-overlap for each room
#         for room_idx, intervals in room_usage_intervals.items():
#             if len(intervals) > 1:
#                 model.AddNoOverlap(intervals)

#         # Add symmetry breaking for identical blocks
#         for i, (interval1, (idx1, block1, dur1, room_count1)) in enumerate(
#             zip(task_intervals, active_blocks)
#         ):
#             for j, (interval2, (idx2, block2, dur2, room_count2)) in enumerate(
#                 zip(task_intervals, active_blocks)
#             ):
#                 if (
#                     i < j
#                     and block1 == block2
#                     and dur1 == dur2
#                     and room_count1 == room_count2
#                 ):
#                     # Break symmetry by ordering starts
#                     model.Add(task_starts[interval1] <= task_starts[interval2])

#         # model.minimize(sum(minimization_vars))
#         status = solver.Solve(model)

#         if status == cp_model.OPTIMAL or status == cp_model.FEASIBLE:
#             print(f"constructed day {day_index}")
#             # Save the plan
#             for interval in task_intervals:
#                 assigned_rooms = []
#                 if interval in task_room_combinations:
#                     room_combo_var, combos = task_room_combinations[interval]
#                     combo_index = solver.Value(room_combo_var)
#                     assigned_room_indices = combos[combo_index]
#                     assigned_rooms = [rooms[idx].name for idx in assigned_room_indices]

#                 return_plan.append(
#                     (
#                         interval_blocks[interval],
#                         solver.Value(task_starts[interval]),
#                         solver.Value(task_ends[interval]),
#                         day_index,
#                         assigned_rooms,
#                     )
#                 )

#             for group_index, group_intervals in group_intervals_dict.items():
#                 for interval in group_intervals:
#                     start = solver.Value(task_starts[interval])
#                     end = solver.Value(task_ends[interval])
#                     daily_plans[day_index].append(
#                         (group_index, interval_blocks[interval], start, end)
#                     )
#         else:
#             print(f"Day {day_index} failed to solve")

#     return return_plan, daily_plans


def solve_schedule(req_set, block_list, specimen):
    horizon = 12

    group_block_indexes = get_group_block_indexes(
        block_list, StudentGroup.objects.filter(pool=req_set.group_pool)
    )
    teacher_block_indexes = get_teacher_block_indexes(
        block_list, Teacher.objects.filter(pool=req_set.teacher_pool)
    )

    rooms = list(Room.objects.filter(pool=req_set.room_pool))
    room_names = [room.name for room in rooms]
    room_count = len(rooms)

    # Each block’s required number of rooms
    required_no_of_rooms = [len(block) for block in block_list]

    all_intervals = []
    return_plan: list[tuple[tuple[Requirement], int, int, int, list[str]]] = []

    daily_plans = defaultdict(list)

    for day_index, day in enumerate(specimen):
        model = cp_model.CpModel()
        minimization_vars = []

        task_intervals = []
        interval_blocks = {}
        task_starts = {}
        task_ends = {}
        task_duration = {}
        task_border_vars = defaultdict(tuple)

        # --- Build intervals for each block on this day ---
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

        # --- No overlap: teachers & groups ---
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

        # Teacher no-overlap + compactness minimization
        for teacher_intervals in teacher_intervals_dict.values():
            model.AddNoOverlap(teacher_intervals)
            day_start = model.NewIntVar(0, horizon, "teacher_start")
            day_end = model.NewIntVar(0, horizon, "teacher_end")
            model.AddMinEquality(day_start, [task_starts[i] for i in teacher_intervals])
            model.AddMaxEquality(day_end, [task_ends[i] for i in teacher_intervals])
            teacher_duration = model.NewIntVar(0, horizon, "teacher_total_time")
            model.Add(teacher_duration == day_end - day_start)
            minimization_vars.append(teacher_duration)

        # Group no-overlap + continuity + border
        for group_intervals in group_intervals_dict.values():
            model.AddNoOverlap(group_intervals)
            day_start = model.NewIntVar(0, horizon, "group_start")
            day_end = model.NewIntVar(0, horizon, "group_end")
            model.AddMinEquality(day_start, [task_starts[i] for i in group_intervals])
            model.AddMaxEquality(day_end, [task_ends[i] for i in group_intervals])
            model.Add(
                day_end - day_start == sum([task_duration[i] for i in group_intervals])
            )
            # Handle border subjects
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

        # --- ROOM ASSIGNMENT SECTION ---
        block_room_vars = []
        for interval, num_rooms_needed in zip(task_intervals, required_no_of_rooms):
            if interval:
                # Assign one or more rooms to each block
                room_vars = [
                    model.NewIntVar(0, room_count - 1, f"room_{i}_{interval}")
                    for i in range(num_rooms_needed)
                ]
                # Ensure distinct rooms if multiple required
                if num_rooms_needed > 1:
                    model.AddAllDifferent(room_vars)
                block_room_vars.append(room_vars)
            else:
                block_room_vars.append([])

        # Room no-overlap constraints
        for room_index in range(room_count):
            room_intervals = []
            for interval, room_vars in zip(task_intervals, block_room_vars):
                if not interval:
                    continue
                for rv in room_vars:
                    assigned = model.NewBoolVar(f"assigned_{room_index}_{interval}")
                    model.Add(rv == room_index).OnlyEnforceIf(assigned)
                    model.Add(rv != room_index).OnlyEnforceIf(assigned.Not())

                    room_interval = model.NewOptionalIntervalVar(
                        task_starts[interval],
                        task_duration[interval],
                        task_ends[interval],
                        assigned,
                        f"room_interval_{room_index}_{interval}",
                    )
                    room_intervals.append(room_interval)

            # Ensure no two lessons overlap in the same room
            model.AddNoOverlap(room_intervals)

        # --- Optimization target ---
        model.Minimize(sum(minimization_vars))

        # --- Solve ---
        solver = cp_model.CpSolver()
        solver.parameters.log_search_progress = True
        solver.parameters.relative_gap_limit = 0.2
        status = solver.Solve(model)

        if status in (cp_model.OPTIMAL, cp_model.FEASIBLE):
            print("constructed day")

            for interval, room_vars in zip(task_intervals, block_room_vars):
                if interval:
                    assigned_rooms = [solver.Value(rv) for rv in room_vars]
                    return_plan.append(
                        (
                            interval_blocks[interval],
                            solver.Value(interval.StartExpr()),
                            solver.Value(interval.EndExpr()),
                            day_index,
                            [room_names[i] for i in assigned_rooms],
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
