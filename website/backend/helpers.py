import numpy as np
from backend.models import StudentGroup

def is_array_valid(array: np.ndarray, validation_hours: np.ndarray):
    for i in range(validation_hours.shape[1]):
        if array[:, i].sum() != validation_hours[i]:
            return False

    return True


def initialize_population(n: int, validation_hours) -> np.ndarray:
    return np.array(
        [
            np.array(
                [np.random.multinomial(h, [1 / 5] * 5) for h in validation_hours]
            ).T
            for _ in range(n)
        ]
    )


def generate_blocks(requirements_querry, req_set, validation_hours):
    return_blocks = {}
    requirement_corrections = {}

    student_groups = list(StudentGroup.objects.filter(pool=req_set.group_pool))
    all_requirements = list(
        requirements_querry.select_related("subject").prefetch_related("subject__pairable")
    )

    requirements_by_group = {group.id: [] for group in student_groups}
    for req in all_requirements:
        requirements_by_group[req.group_id].append(req)

    for student_group in student_groups:
        tmp_requirements = requirements_by_group.get(student_group.id, [])
        blocks = {}

        for requirement in tmp_requirements:
            pairable_subjects = set(requirement.subject.pairable.all())
            pairable_subjects.add(requirement.subject)

            requirement_pairable = [
                req for req in tmp_requirements if req.subject in pairable_subjects
            ]

            if len(requirement_pairable) > 2:
                unique_subjects = {req.subject for req in requirement_pairable}
                if len(unique_subjects) != len(requirement_pairable):
                    blocks[(requirement_pairable[0], requirement_pairable[-1])] = 0
                    blocks[(requirement_pairable[1], requirement_pairable[-1])] = 0
                    for req in requirement_pairable:
                        requirement_corrections[req] = 0
                    continue

            if (
                len(requirement_pairable) > 1
                and tuple(requirement_pairable) not in blocks
            ):
                blocks[tuple(requirement_pairable)] = 0
                for req in requirement_pairable:
                    requirement_corrections[req] = 0

        while any(
            all(req.hours - requirement_corrections[req] > 0 for req in requirements)
            for requirements in blocks.keys()
        ):
            for requirements in blocks.keys():
                if all(
                    req.hours - requirement_corrections[req] > 0 for req in requirements
                ):
                    for req in requirements:
                        requirement_corrections[req] += 1
                    blocks[requirements] += 1

        if blocks:
            return_blocks.update(blocks)

    BLOCK_LIST = list((req,) for req in requirements_querry)
    BLOCK_VAL = list(validation_hours)

    for block, hours in blocks.items():
        for req in block:
            if requirement_corrections[req] == req.hours:
                if (req,) in BLOCK_LIST:
                    indx = BLOCK_LIST.index((req,))
                    BLOCK_LIST.pop(indx)
                    BLOCK_VAL.pop(indx)
            else:
                BLOCK_VAL[BLOCK_LIST.index((req,))] -= requirement_corrections[req]

            BLOCK_LIST.append(tuple(block))
            BLOCK_VAL.append(hours)

    # for block, hours in zip(BLOCK_LIST, BLOCK_VAL):
    #     print(f"{hours} | {tuple(str(req) for req in block)}")

    return BLOCK_LIST, BLOCK_VAL