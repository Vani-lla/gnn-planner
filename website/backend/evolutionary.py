import numpy as np
from backend.helpers import *
from backend.linear_solver import solve_schedule
from time import time

np.set_printoptions(precision=3, suppress=True)


def run_evolutionary_process(generations: int, req_set_id: int):
    REQ_SET = RequirementSet.objects.get(id=req_set_id)
    REQUIREMENTS = Requirement.objects.filter(req_set=REQ_SET)
    VALIDATION_HOURS = list(map(lambda req: req.hours, REQUIREMENTS))

    TEACHERS = list(Teacher.objects.filter(pool=REQ_SET.teacher_pool))
    TEACHER_AVAILABILITY = np.array(
        [
            next(
                list(avail.availability.values())
                for avail in TeacherAvailability.objects.filter(
                    req_set=REQ_SET, teacher=teacher
                )
            )
            for teacher in TEACHERS
        ]
    )
    STUDENT_GROUPS = list(StudentGroup.objects.filter(pool=REQ_SET.group_pool))

    print(len(REQUIREMENTS))

    start = time()
    BLOCK_LIST, BLOCK_VAL = generate_blocks(REQUIREMENTS, REQ_SET, VALIDATION_HOURS)
    print(time()-start)
    print(len(BLOCK_LIST))
    print(BLOCK_LIST)
    print(BLOCK_VAL)
    TEACHER_AVAILABILITY = np.array(
        [
            np.all(
                TEACHER_AVAILABILITY[[TEACHERS.index(b.teacher) for b in block]], axis=0
            )
            for block in BLOCK_LIST
        ]
    )

    # population = initialize_population(1000, BLOCK_VAL, TEACHER_AVAILABILITY)

    best_specimen = np.load("specimen.npy")
    print("Loaded best specimen")
    print(best_specimen)

    # start = time()
    # best_specimen = evolutionary_loop(
    #     block_list=BLOCK_LIST,
    #     req_set=REQ_SET,
    #     population=population,
    #     teachers=TEACHERS,
    #     student_groups=STUDENT_GROUPS,
    #     block_val=BLOCK_VAL,
    #     availability=TEACHER_AVAILABILITY,
    #     generations=generations,
    #     alphas=np.array([1.0, 2.0, 1.0]),
    # )
    # print(time() - start)

    ll = []
    for k, v in teacher_day_hours(BLOCK_LIST, REQ_SET, best_specimen).items():
        # print(sum(v))
        # ll.append(sum(v))
        zeros = np.where(v == 0)
        v = np.array(v, dtype=np.int64)
        # a1: np.ndarray = alphas[0] * (2 - np.abs(a1 - 7)) / len(teachers)
        a1 = (-((7 - v) ** 2) + 2)
        print(a1, v)
        a1[zeros] = 0.0
        if sum(v) > 0:
            ll.append(a1.sum())
    # print(list(int(x) for x in ll))
    # return
    # l = np.array(list(teacher_day_hours(BLOCK_LIST, REQ_SET, best_specimen).values())).flatten()
    # for x in np.unique(l):
    #     print(x, np.sum(l==x))
    # print("--")
    # for x in range(max(ll) + 1):
    #     print(f"({x}, {ll.count(x)})")
        
    print("------ xd")
    l = []
    ll = []
    for k, v in group_day_lessons(BLOCK_LIST, REQ_SET, best_specimen).items():
        # print(sum(v))
        # ll.append(sum(v))
        v = np.array(v, dtype=np.int64)
        # a1: np.ndarray = alphas[0] * (2 - np.abs(a1 - 7)) / len(teachers)
        a1 = (-((7 - v) ** 2) + 2)
        print(a1, v)
        if sum(v) > 0:
            ll.append(a1.sum())
    print(list(int(x) for x in ll))
    print(ll)
        
    # print("--")
    # for x in range(max(ll)):
    #     print(f"({x}, {ll.count(x)})")
        
    print("--")
    l = np.array(l)
    # l = np.array(list(group_day_lessons(BLOCK_LIST, REQ_SET, best_specimen).values())).flatten()
    # print(np.unique(l))
    for x in range(0, 14):
        print(x, np.sum(l==x))

    start = time()
    return
    plan = solve_schedule(REQ_SET, BLOCK_LIST, best_specimen)
    print(time() - start)

    return plan
