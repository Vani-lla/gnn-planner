import numpy as np
from docplex.mp.model import Model
from docplex.mp.dvar import Var

CONSTRAINTS = np.load("data/constraints.npy")
T, C, S = CONSTRAINTS.shape
D = 5
H = 11
R = 50

REQUIRED_LESSONS = list(zip(*np.nonzero(CONSTRAINTS)))
REQUIRED_LESSONS_SET = set(REQUIRED_LESSONS)

GLOBAL_COMPLEMENTARY_SUBJECTS = [
    (11, 12, 14),  # Języki
    (1, 8),  # Angielski + inf
    (1, 1),  # Ang + Ang
    (10, 10, 4),  # Religia + etyka
    (16, 16),  # WF
]
GLOBAL_COMPLEMENTARY_SUBJECTS_SET = set(
    y for x in GLOBAL_COMPLEMENTARY_SUBJECTS for y in x
)
PER_CLASS_COMPLEMENTARY_SUBJECTS = {
    6: [
        (15, 3),
    ],  # Psych-prawna  # Biol + WOS
    7: [
        (11, 18),
    ],  # Niem + mat
    8: [(6, 8), (15, 7)],  # Chem + inf  # Biol + fiz
    9: [
        (6, 15),
    ],  # >30 osób  # Chem + biol
}

GLOBAL_GROUP_SUBJECTS = {
    11: [
        (40, 41, 42),
        (6, 7, 8, 9),
        (10, 11, 12, 13, 14, 15),
        (16, 17, 18, 19, 20, 21),
    ],
    12: [
        (43, 44, 45),
        (6, 7, 8, 9),
        (10, 11, 12, 13, 14, 15),
        (16, 17, 18, 19, 20, 21),
    ],
    14: [
        (46, 47, 48, 49),
        (6, 7, 8, 9),
        (10, 11, 12, 13, 14, 15),
        (16, 17, 18, 19, 20, 21),
    ],
    16: [
        (52, 53, 54, 55, 56, 57),
        (0, 1, 2, 3, 4, 5),
        (6, 7, 8, 9),
        (10, 11, 12, 13, 14, 15),
        (16, 17, 18, 19, 20, 21),
    ],
}

PER_CLASS_GROUP_SUBJECTS = {}


def create_variables(mdl: Model) -> dict[tuple[int], Var]:
    return mdl.binary_var_dict(
        (t, c, d, h, s, r)
        for t, c, s in REQUIRED_LESSONS
        for d in range(D)
        for h in range(H)
        for r in range(R)
    )


def class_double_booking(x: dict[tuple[int], Var], mdl: Model) -> None:
    for c in range(C):
        print(c, C)
        per_class_complementary: list[tuple[int]] = GLOBAL_COMPLEMENTARY_SUBJECTS.copy()
        if c in PER_CLASS_COMPLEMENTARY_SUBJECTS.keys():
            per_class_complementary.extend(PER_CLASS_COMPLEMENTARY_SUBJECTS[c])

        for d in range(D):
            for h in range(H):
                zs = mdl.binary_var_list(len(per_class_complementary) + 1)

                for ind, complementary in enumerate(per_class_complementary):
                    for s in set(complementary):
                        conflicts = []
                        for ind_2, complementary_2 in enumerate(
                            per_class_complementary
                        ):
                            if (
                                s in complementary_2
                                and complementary != complementary_2
                            ):
                                conflicts.append((zs[ind_2], complementary_2.count(s)))

                        if conflicts:
                            biggest_conflict = max(conflicts, key=lambda c: c[1])
                            mdl.add_indicator(
                                zs[ind],
                                mdl.sum(
                                    x[t, c, d, h, s, r]
                                    for r in range(R)
                                    for t in range(T)
                                    if (t, c, s) in REQUIRED_LESSONS_SET
                                )
                                <= complementary.count(s)
                                + biggest_conflict[0] * biggest_conflict[1],
                            )
                        else:
                            mdl.add_indicator(
                                zs[ind],
                                mdl.sum(
                                    x[t, c, d, h, s, r]
                                    for r in range(R)
                                    for t in range(T)
                                    if (t, c, s) in REQUIRED_LESSONS_SET
                                )
                                <= complementary.count(s),
                            )

                mdl.add_constraint(
                    mdl.sum(
                        x[t, c, d, h, s, r]
                        for r in range(R)
                        for s in range(S)
                        for t in range(T)
                        if (t, c, s) in REQUIRED_LESSONS_SET
                        if s not in set(y for x in per_class_complementary for y in x)
                    )
                    <= zs[-1]
                )
                mdl.add_constraint(mdl.sum(zs) == 1)


def required_plan(x: dict[tuple[int], Var], mdl: Model) -> None:
    mdl.add_constraints(
        mdl.sum(
            x[t, c, d, h, s, r] for d in range(D) for h in range(H) for r in range(R)
        )
        == CONSTRAINTS[t, c, s]
        for t, c, s in REQUIRED_LESSONS
    )


def teacher_double_booking(x: dict[tuple[int], Var], mdl: Model) -> None:
    group_teachers = set(
        [
            item
            for tup in [lst[0] for lst in GLOBAL_GROUP_SUBJECTS.values()]
            for item in tup
        ]
    )
    group_subjects = set(GLOBAL_GROUP_SUBJECTS.keys())
    for t in range(T):
        print(t, "/", T)
        for d in range(D):
            for h in range(H):
                if t not in group_teachers:
                    mdl.add_constraint(
                        mdl.sum(
                            x[t, c, d, h, s, r]
                            for c in range(C)
                            for s in range(S)
                            for r in range(R)
                            if (t, c, s) in REQUIRED_LESSONS_SET
                        )
                        <= 1
                    )
                else:
                    per_class_groups = list(GLOBAL_GROUP_SUBJECTS.items())
                    affected_classes = set()
                    zs = mdl.binary_var_list(len(per_class_groups) + 1)
                    for ind, (s, group_info) in enumerate(per_class_groups):
                        teacher_group, *class_groups = group_info
                        affected_classes.update(*class_groups)
                        if t in teacher_group:
                            mdl.add_constraint(
                                mdl.sum(
                                    x[t, c, d, h, s, r]
                                    for class_group in class_groups
                                    for c in class_group
                                    for r in range(R)
                                    if (t, c, s) in REQUIRED_LESSONS_SET
                                )
                                <= zs[ind]
                            )
                        else:
                            mdl.add_constraint(zs[ind] == 0)
                    non_group_subjects = [
                        s for s in range(S) if s not in group_subjects
                    ]
                    non_group_classes = [
                        c for c in range(C) if c not in affected_classes
                    ]
                    mdl.add_constraint(
                        mdl.sum(
                            x[t, c, d, h, s, r]
                            for c in non_group_classes
                            for s in non_group_subjects
                            for r in range(R)
                            if (t, c, s) in REQUIRED_LESSONS_SET
                        )
                        <= zs[-1]
                    )
                    mdl.add_constraint(mdl.sum(zs) == 1)


def room_double_booking(x: dict[tuple[int], Var], mdl: Model) -> None:
    for r in range(R):
        for d in range(D):
            for h in range(H):
                mdl.add_constraint(
                    mdl.sum(
                        x[t, c, d, h, s, r]
                        for t in range(T)
                        for c in range(C)
                        for s in range(S)
                        if (t, c, s) in REQUIRED_LESSONS_SET
                    )
                    <= 1
                )


def minimize_teacher_hours(x: dict[tuple[int], Var], mdl: Model) -> None:
    """
    Adds binary variables teach_time[t, d, h] and constraints so that
    we minimize the total number of hours teachers spend teaching.
    Group lessons are counted only once per time slot.
    """
    T = max(t for t, _, _, _, _, _ in x.keys()) + 1
    D = max(d for _, _, d, _, _, _ in x.keys()) + 1
    H = max(h for _, _, _, h, _, _ in x.keys()) + 1
    C = max(c for _, c, _, _, _, _ in x.keys()) + 1

    teach_time = {
        (t, d, h): mdl.binary_var(name=f"teach_time_{t}_{d}_{h}")
        for t in range(T)
        for d in range(D)
        for h in range(H)
    }

    for t, d, h in teach_time:
        mdl.add_constraint(
            mdl.sum(
                x[t, c, d, h, s, r]
                for c in range(C)
                for s in range(S)
                for r in range(R)
                if (t, c, s) in REQUIRED_LESSONS_SET
            )
            <= C * teach_time[t, d, h]
        )

    mdl.minimize(mdl.sum(teach_time.values()))


def double_subjects(x: dict[tuple[int], Var], mdl: Model) -> None:
    for d in range(D):
        for s in range(S):
            mdl.add_constraints(
                mdl.sum(
                    x[t, c, d, h, s, r]
                    for r in range(R)
                    for t in range(T)
                    for h in range(H)
                    if (t, c, s) in REQUIRED_LESSONS_SET
                )
                <= 2
                for c in range(C)
            )


if __name__ == "__main__":
    mdl = Model(name="SchoolSchedule", ignore_names=True, checker="off")
    mdl.parameters.threads = 8
    mdl.parameters.parallel = -1
    mdl.parameters.preprocessing.symmetry = 0
    mdl.parameters.mip.tolerances.mipgap = 0.10

    x = create_variables(mdl)
    print("Created variables")

    double_subjects(x, mdl)
    print("Max 2 hours of the same")
    required_plan(x, mdl)
    print("Loaded main constraints")
    class_double_booking(x, mdl)
    print("Class double booking")
    room_double_booking(x, mdl)
    print("Room double booking")
    teacher_double_booking(x, mdl)
    print("Teacher double booking")
    

    print("No. of variables", mdl.number_of_variables)
    print("No. of constraints", mdl.number_of_constraints)

    mdl.minimize(mdl.sum(x.values()))
    # minimize_teacher_hours(x, mdl)
    solution = mdl.solve(log_output=True)

    if solution:
        for (t, c, d, h, s, r), var in x.items():
            if var.solution_value > 0.5:
                print(f"{c} {r} {t} {s} {d} {h}")
    else:
        print("No feasible solution found!")
