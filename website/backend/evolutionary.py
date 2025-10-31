import numpy as np
from backend.helpers import *
import matplotlib.pyplot as plt

np.set_printoptions(precision=3, suppress=True)

# Prefetch all necessary data
REQUIREMENTS = Requirement.objects.filter(req_set=14)
REQ_SET = REQUIREMENTS[0].req_set
VALIDATION_HOURS = list(map(lambda req: req.hours, REQUIREMENTS))

# Prefetch teachers and student groups
TEACHERS = list(Teacher.objects.filter(pool=REQ_SET.teacher_pool))
STUDENT_GROUPS = list(StudentGroup.objects.filter(pool=REQ_SET.group_pool))

# Generate blocks and evaluate population
BLOCK_LIST, BLOCK_VAL = generate_blocks(REQUIREMENTS, REQ_SET, VALIDATION_HOURS)
# for block in BLOCK_LIST:
#     print(block)
# print(len(BLOCK_LIST))

population = initialize_population(1000, BLOCK_VAL)

best_specimen = evolutionary_loop(
    block_list=BLOCK_LIST,
    req_set=REQ_SET,
    population=population,
    teachers=TEACHERS,
    student_groups=STUDENT_GROUPS,
    block_val=BLOCK_VAL,
    generations=10,
    alphas=np.array([1.0, 1.0, 1.0]),
)

a2 = group_day_lessons(BLOCK_LIST, REQ_SET, best_specimen)
a2 = np.array(list(a2.values()))

a1 = teacher_day_hours(BLOCK_LIST, REQ_SET, best_specimen)
a1 = np.array(list(a1.values()))

a3 = border_day_lessons(BLOCK_LIST, REQ_SET, best_specimen)
a3 = np.array(list(a3.values()))

np.save("specimen", best_specimen)
print(a1)
print(a1.sum(axis=0))
print(a1.sum(axis=1))
print(a2)
print((a2.sum(axis=1)/5).mean())
print(a3)