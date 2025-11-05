import numpy as np
from backend.helpers import *
import matplotlib.pyplot as plt
from backend.linear_solver import solve_schedule

np.set_printoptions(precision=3, suppress=True)

def run_evolutionary_process(generations: int, req_set_id: int):
    # Fetch the specified requirement set
    REQ_SET = RequirementSet.objects.get(id=req_set_id)
    REQUIREMENTS = Requirement.objects.filter(req_set=REQ_SET)
    VALIDATION_HOURS = list(map(lambda req: req.hours, REQUIREMENTS))

    # Prefetch teachers and student groups
    TEACHERS = list(Teacher.objects.filter(pool=REQ_SET.teacher_pool))
    TEACHER_AVAILABILITY = np.array([
        next(list(avail.availability.values()) for avail in TeacherAvailability.objects.filter(req_set=REQ_SET, teacher=teacher))
        for teacher in TEACHERS
    ])
    STUDENT_GROUPS = list(StudentGroup.objects.filter(pool=REQ_SET.group_pool))
    
    # for teacher in TEACHERS:

    # Generate blocks and evaluate population
    BLOCK_LIST, BLOCK_VAL = generate_blocks(REQUIREMENTS, REQ_SET, VALIDATION_HOURS)
    TEACHER_AVAILABILITY = np.array([
        np.all(TEACHER_AVAILABILITY[[TEACHERS.index(b.teacher) for b in block]], axis=0)
        for block in BLOCK_LIST
    ])

    population = initialize_population(1000, BLOCK_VAL, TEACHER_AVAILABILITY)

    best_specimen = np.load("specimen.npy")
    print("Loaded best specimen")
    print(best_specimen)
    
    # best_specimen = evolutionary_loop(
    #     block_list=BLOCK_LIST,
    #     req_set=REQ_SET,
    #     population=population,
    #     teachers=TEACHERS,
    #     student_groups=STUDENT_GROUPS,
    #     block_val=BLOCK_VAL,
    #     availability=TEACHER_AVAILABILITY,
    #     generations=generations,
    #     alphas=np.array([1.0, 1.0, 1.0]),
    # )

    plan, _ = solve_schedule(REQ_SET, BLOCK_LIST, best_specimen)
    
    return plan
