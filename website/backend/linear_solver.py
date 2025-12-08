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

        room_assignments = defaultdict(list)
        room_intervals = defaultdict(list)

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
        model.Minimize(sum(minimization_vars))

        # --- Solve ---
        solver = cp_model.CpSolver()
        solver.parameters.log_search_progress = True
        solver.parameters.relative_gap_limit = 0.3
        status = solver.Solve(model)

        if status in (cp_model.OPTIMAL, cp_model.FEASIBLE):
            print(np.sum(day))
            print(solver.objective_value)
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
