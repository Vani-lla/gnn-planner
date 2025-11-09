import numpy as np
from ortools.sat.python import cp_model
from backend.models import (
    Requirement,
    StudentGroup,
    Teacher,
    Room,
    RequirementSet,
    Subject,
)
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
    rooms = Room.objects.filter(pool=req_set.room_pool)
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
                # room_vars = [
                #     model.NewBoolVar(f"{tuple(map(str, block))}_room_{room.name}")
                #     for room in rooms
                # ]
                # task_rooms[interval_var] = room_vars

                # Ensure the correct number of rooms are assigned
                # model.Add(sum(room_vars) == room_count)

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
        # for room_index, room in enumerate(rooms):
        #     room_intervals = []
        #     for interval, room_vars in task_rooms.items():
        #         # Create a conditional interval for the room
        #         room_active = room_vars[room_index]
        #         room_start = task_starts[interval]
        #         room_end = task_ends[interval]
        #         room_duration = task_duration[interval]
        #         room_interval = model.NewOptionalIntervalVar(
        #             room_start,
        #             room_duration,
        #             room_end,
        #             room_active,
        #             f"{room.name}_interval",
        #         )
        #         room_intervals.append(room_interval)

        #     # Add no-overlap constraint for the room
        #     model.AddNoOverlap(room_intervals)

        # model.minimize(sum(minimization_vars))
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


def solve_schedule(req_set: RequirementSet, block_list, specimen):
    horizon = 12

    group_block_indexes = get_group_block_indexes(
        block_list, StudentGroup.objects.filter(pool=req_set.group_pool)
    )
    teacher_block_indexes = get_teacher_block_indexes(
        block_list, Teacher.objects.filter(pool=req_set.teacher_pool)
    )

    rooms = Room.objects.filter(pool=req_set.room_pool)

    all_intervals = []
    return_plan: list[tuple[tuple[Requirement], int, int, int]] = []

    for day_index, day in enumerate(specimen):
        model = cp_model.CpModel()
        minimization_vars = []

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
                interval_blocks[interval_var] = block

                # --- Determine number of rooms required per subject ---
                # Count how many distinct teachers teach each subject in this block.
                rooms_dict = defaultdict(set)
                for req in block:
                    rooms_dict[req.subject].add(req.teacher)
                rooms_dict = {
                    subject: len(teachers) for subject, teachers in rooms_dict.items()
                }

                # --- Create optional room intervals for this block ---
                block_room_assignments = []

                for subject, required_room_count in rooms_dict.items():
                    # Find compatible rooms
                    compatible_rooms = [
                        room
                        for room in rooms
                        if subject in room.compatible_subjects.all()
                    ]

                    if not compatible_rooms:
                        raise ValueError(
                            f"No compatible rooms found for subject {subject}"
                        )

                    for room_req_idx in range(required_room_count):
                        # Create one assignment among compatible rooms
                        room_assignment_vars = []
                        for room in compatible_rooms:
                            room_present_var = model.NewBoolVar(
                                f"room_present_{room.id}_{room_req_idx}_{subject}"
                            )
                            room_start_var = model.NewIntVar(
                                0,
                                horizon,
                                f"room_start_{room.id}_{room_req_idx}_{subject}",
                            )
                            room_end_var = model.NewIntVar(
                                0,
                                horizon,
                                f"room_end_{room.id}_{room_req_idx}_{subject}",
                            )

                            room_interval_var = model.NewOptionalIntervalVar(
                                room_start_var,
                                duration,
                                room_end_var,
                                room_present_var,
                                f"room_interval_{room.id}_{room_req_idx}_{subject}",
                            )

                            # Room time must match block time if used
                            model.Add(room_start_var == start_var).OnlyEnforceIf(
                                room_present_var
                            )
                            model.Add(room_end_var == end_var).OnlyEnforceIf(
                                room_present_var
                            )

                            room_assignment_vars.append(
                                (room.id, room_present_var, room_interval_var)
                            )
                            room_intervals[room.id].append(room_interval_var)

                        # Exactly one compatible room must be chosen for this required slot
                        model.AddExactlyOne([var[1] for var in room_assignment_vars])
                        block_room_assignments.extend(room_assignment_vars)

                room_assignments[interval_var] = block_room_assignments

                if any(req.subject.border for req in block):
                    task_border_vars[interval_var] = (start_var, end_var)

                task_intervals.append(interval_var)
                all_intervals.append(interval_var)

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
            model.AddMinEquality(day_start, [task_starts[i] for i in teacher_intervals])
            model.AddMaxEquality(day_end, [task_ends[i] for i in teacher_intervals])
            teacher_duration = model.NewIntVar(0, horizon, "teacher_total_time")
            model.Add(teacher_duration == day_end - day_start)
            minimization_vars.append(teacher_duration)

        for group_intervals in group_intervals_dict.values():
            model.AddNoOverlap(group_intervals)
            day_start = model.NewIntVar(0, horizon, "group_start")
            day_end = model.NewIntVar(0, horizon, "group_end")
            model.AddMinEquality(day_start, [task_starts[i] for i in group_intervals])
            model.AddMaxEquality(day_end, [task_ends[i] for i in group_intervals])
            model.Add(
                day_end - day_start == sum([task_duration[i] for i in group_intervals])
            )

            # for interval in group_intervals:
            #     if task_border_vars[interval]:
            #         start_bool = model.NewBoolVar("start_border")
            #         end_bool = model.NewBoolVar("end_border")
            #         model.Add(day_start == task_border_vars[interval][0]).OnlyEnforceIf(
            #             start_bool
            #         )
            #         model.Add(day_start != task_border_vars[interval][0]).OnlyEnforceIf(
            #             start_bool.Not()
            #         )
            #         model.Add(day_end == task_border_vars[interval][1]).OnlyEnforceIf(
            #             end_bool
            #         )
            #         model.Add(day_end != task_border_vars[interval][1]).OnlyEnforceIf(
            #             end_bool.Not()
            #         )
            #         model.AddBoolOr([start_bool, end_bool])

        # --- Optimization target ---
        model.Minimize(sum(minimization_vars))

        # --- Solve ---
        solver = cp_model.CpSolver()
        # solver.parameters.log_search_progress = True
        solver.parameters.relative_gap_limit = 0.1
        status = solver.Solve(model)

        if status in (cp_model.OPTIMAL, cp_model.FEASIBLE):
            print(f"constructed day {day}")

            for interval in task_intervals:
                if interval:
                    return_plan.append(
                        (
                            interval_blocks[interval],
                            solver.Value(interval.StartExpr()),
                            solver.Value(interval.EndExpr()),
                            day_index,
                        )
                    )
        else:
            print("Impossible")
            return

    return return_plan


def solve_schedule(req_set: RequirementSet, block_list, specimen):
    horizon = 12

    group_block_indexes = get_group_block_indexes(
        block_list, StudentGroup.objects.filter(pool=req_set.group_pool)
    )
    teacher_block_indexes = get_teacher_block_indexes(
        block_list, Teacher.objects.filter(pool=req_set.teacher_pool)
    )

    rooms = Room.objects.filter(pool=req_set.room_pool)
    room_compatibility = {
        subject: [room for room in rooms if subject in room.compatible_subjects.all()]
        for subject in Subject.objects.filter(pool=req_set.subject_pool)
    }

    all_intervals = []
    return_plan: list[tuple[tuple[Requirement], int, int, int]] = []

    for day_index, day in enumerate(specimen):
        model = cp_model.CpModel()
        minimization_vars = []

        task_intervals = []
        interval_blocks = {}
        task_starts = {}
        task_ends = {}
        task_duration = {}
        task_border_vars = defaultdict(tuple)

        # Room assignment variables
        room_assignments = defaultdict(list)  # interval -> list of room assignment vars
        room_intervals = defaultdict(list)  # room_id -> list of optional intervals

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
                interval_blocks[interval_var] = block

                rooms_dict = defaultdict(set)
                for req in block:
                    rooms_dict[req.subject].add(req.teacher)

                block_room_assignments = []
                for subject, teachers in rooms_dict.items():
                    room_present_vars = []
                    for room in room_compatibility[subject]:
                        room_present_var = model.NewBoolVar(
                            f"room_present_{room.id}_{tuple(map(str, block))}"
                        )
                        room_interval_var = model.NewOptionalIntervalVar(
                            start_var,
                            duration,
                            end_var,
                            room_present_var,
                            f"room_interval_{room.id}_{tuple(map(str, block))}",
                        )

                        room_present_vars.append(room_present_var)
                        room_intervals[room.id].append(room_interval_var)
                        block_room_assignments.append(
                            (room.id, room_present_var, room_interval_var)
                        )

                    model.Add(sum(room_present_vars) == len(teachers))

                room_assignments[interval_var] = block_room_assignments
                task_intervals.append(interval_var)
                all_intervals.append(interval_var)

        # Add no-overlap constraints for rooms
        for room_id, intervals in room_intervals.items():
            if intervals:
                model.AddNoOverlap(intervals)

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
            model.AddMinEquality(day_start, [task_starts[i] for i in teacher_intervals])
            model.AddMaxEquality(day_end, [task_ends[i] for i in teacher_intervals])
            teacher_duration = model.NewIntVar(0, horizon, "teacher_total_time")
            model.Add(teacher_duration == day_end - day_start)
            minimization_vars.append(teacher_duration)

        for group_intervals in group_intervals_dict.values():
            model.AddNoOverlap(group_intervals)
            day_start = model.NewIntVar(0, horizon, "group_start")
            day_end = model.NewIntVar(0, horizon, "group_end")
            model.AddMinEquality(day_start, [task_starts[i] for i in group_intervals])
            model.AddMaxEquality(day_end, [task_ends[i] for i in group_intervals])
            model.Add(
                day_end - day_start == sum([task_duration[i] for i in group_intervals])
            )

        # --- Optimization target ---
        # model.Minimize(sum(minimization_vars))

        # --- Solve ---
        solver = cp_model.CpSolver()
        # solver.parameters.log_search_progress = True
        # solver.parameters.relative_gap_limit = 0.3
        status = solver.Solve(model)

        if status in (cp_model.OPTIMAL, cp_model.FEASIBLE):
            print(f"constructed day {day}")

            for interval in task_intervals:
                if interval:
                    assigned_rooms = []
                    for room_id, present_var, room_interval in room_assignments[
                        interval
                    ]:
                        if solver.BooleanValue(present_var):
                            assigned_rooms.append(room_id)

                    return_plan.append(
                        (
                            interval_blocks[interval],
                            solver.Value(interval.StartExpr()),
                            solver.Value(interval.EndExpr()),
                            day_index,
                            assigned_rooms,
                        )
                    )
        else:
            print("Impossible")
            return

    return return_plan


# Print the sorted plan for each day
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
