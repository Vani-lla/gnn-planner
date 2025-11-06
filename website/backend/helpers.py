from collections import defaultdict
from itertools import combinations
import numpy as np
from django.db.models.query import QuerySet
from backend.models import *
from django.db.models import Count, Q


def is_array_valid(array: np.ndarray, validation_hours: np.ndarray):
    for i in range(validation_hours.size):
        if array[:, i].sum() != validation_hours[i]:
            return False

    return True


def get_teacher_block_indexes(
    block_list: list[tuple[Requirement]], teachers: list[Teacher]
) -> list[list[int]]:
    l = [[] for _ in range(len(block_list))]
    for t_ind, teacher in enumerate(teachers):
        for b_ind, block in enumerate(block_list):
            if any(req.teacher == teacher for req in block):
                l[b_ind].append(t_ind)
    return l


def get_group_block_indexes(
    block_list: list[tuple[Requirement]], groups: list[StudentGroup]
) -> list[list[int]]:
    l = [[] for _ in range(len(block_list))]
    for g_ind, group in enumerate(groups):
        for b_ind, block in enumerate(block_list):
            if any(req.group == group for req in block):
                l[b_ind].append(g_ind)
    return l


def initialize_population(n: int, validation_hours, availability) -> np.ndarray:
    population = []
    for _ in range(n):
        specimen = []
        for h, aval in zip(validation_hours, availability):
            day_distribution = np.zeros(5, dtype=int)
            if h > 0 and any(aval):
                valid_days = np.array(aval, dtype=bool)
                probabilities = valid_days / valid_days.sum()
                day_distribution = np.random.multinomial(h, probabilities)

                while any(day_distribution > 2):
                    excess_indices = np.where(day_distribution > 2)[0]
                    for idx in excess_indices:
                        excess = day_distribution[idx] - 2
                        day_distribution[idx] = 2
                        redistribution = np.random.multinomial(excess, probabilities)
                        day_distribution += redistribution * valid_days

            specimen.append(day_distribution)
        population.append(np.array(specimen).T)
    return np.array(population)


def generate_blocks(
    requirements_querry, req_set: RequirementSet, validation_hours: list[int]
):
    return_blocks = {}
    requirement_corrections = {}

    student_groups = list(StudentGroup.objects.filter(pool=req_set.group_pool))
    all_requirements = list(
        requirements_querry.select_related("subject").prefetch_related(
            "subject__pairable"
        )
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

            requirement_pairable = tuple(
                [req for req in tmp_requirements if req.subject in pairable_subjects]
            )

            if len(requirement_pairable) > 2:
                unique_subjects = {req.subject for req in requirement_pairable}
                if len(unique_subjects) != len(requirement_pairable):
                    blocks[(requirement_pairable[0], requirement_pairable[-1])] = 0
                    blocks[(requirement_pairable[1], requirement_pairable[-1])] = 0
                    for req in requirement_pairable:
                        requirement_corrections[req] = 0
                    continue

            if len(requirement_pairable) > 1:
                blocks[requirement_pairable] = 0
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

    for block, hours in return_blocks.items():
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

    return BLOCK_LIST, np.array(BLOCK_VAL)


def is_block_valid(reqs, block) -> bool:
    for subject in Subject.objects.filter(id__in=block.numbers.keys()):
        if len(reqs.filter(subject=subject)) != block.numbers[str(subject.id)]:
            return False
    return True


def generate_blocks(
    requirements_querry: QuerySet[Requirement],
    req_set: RequirementSet,
    validation_hours: list[int],
):
    return_blocks = defaultdict(lambda: 0)
    requirement_corrections = defaultdict(lambda: 0)

    block_reqset: dict[QuerySet[Requirement], SubjectBlock] = {}

    subject_blocks = SubjectBlock.objects.filter(req_set=req_set)
    student_groups = StudentGroup.objects.filter(pool=req_set.group_pool)
    singular_blocks = [
        block
        for block in subject_blocks
        if block.groups.count() == 1 or block.groups.count() > 14
    ]
    multi_blocks = [
        block
        for block in subject_blocks
        if block.groups.count() != 1
        and block.groups.count() <= 14
        and len([k for k, v in block.numbers.items() if v]) == 1
    ]
    combinatory_blocks = [
        block
        for block in subject_blocks
        if block not in singular_blocks and block not in multi_blocks
    ]

    multi_req_groups = []
    for block in multi_blocks:
        reqs = requirements_querry.filter(
            subject__in=[k for k, v in block.numbers.items() if v],
            group__in=block.groups.all(),
        )
        multi_req_groups.append(reqs)
        block_reqset[tuple(reqs)] = block

    power_blocks = []
    for block in combinatory_blocks:
        tmp = []
        used_teachers = set()
        subject_ids = set(map(int, block.numbers.keys()))
        for multi_block in multi_req_groups:
            if (
                len(multi_block)
                == len(multi_block.filter(group__in=block.groups.all()))
                and len(multi_block.filter(subject__in=subject_ids)) == len(multi_block)
                and multi_block[0].teacher not in used_teachers
                and all(req not in requirement_corrections for req in multi_block)
            ):
                tmp.extend(multi_block)
                used_teachers.add(multi_block[0].teacher)

        for req in requirements_querry.filter(
            ~Q(teacher__in=used_teachers),
            group__in=block.groups.all(),
            subject__id__in=subject_ids,
        ):
            if req.teacher not in used_teachers and req not in requirement_corrections:
                tmp.append(req)
                used_teachers.add(req.teacher)

        tmp = tuple(tmp)
        power_blocks.append(tmp)
        correction = min(req.hours for req in tmp)
        for req in tmp:
            requirement_corrections[req] = correction
            return_blocks[tmp] = correction
            block_reqset[tmp] = block

    for block in multi_req_groups:
        if all(req not in requirement_corrections for req in block):
            correction = min(req.hours for req in block)
            return_blocks[tuple(block)] = correction

            for req in block:
                requirement_corrections[req] = correction

    singular_req_groups = []
    for block in singular_blocks:
        for student_group in student_groups:
            if student_group in block.groups.all():
                reqs = requirements_querry.filter(
                    subject__in=[k for k, v in block.numbers.items() if v],
                    group=student_group,
                )
                if all(requirement_corrections[req] < req.hours for req in reqs):
                    if is_block_valid(reqs, block):
                        singular_req_groups.append(tuple(reqs))
                        block_reqset[tuple(reqs)] = block
                    else:
                        for combination in combinations(
                            reqs, sum(block.numbers.values())
                        ):
                            combination_querry = Requirement.objects.filter(
                                id__in=[req.id for req in combination]
                            )
                            if is_block_valid(combination_querry, block):
                                singular_req_groups.append(tuple(combination_querry))
                                block_reqset[tuple(combination_querry)] = block

    while any(
        all(req.hours - requirement_corrections[req] > 0 for req in requirements)
        or (
            block_reqset[requirements].max_number > 0
            and return_blocks[requirements] < block_reqset[requirements].max_number
        )
        for requirements in singular_req_groups
    ):
        for requirements in singular_req_groups:
            if all(
                req.hours - requirement_corrections[req] > 0 for req in requirements
            ) or (
                block_reqset[requirements].max_number > 0
                and return_blocks[requirements] < block_reqset[requirements].max_number
            ):
                # print(block_reqset[requirements].max_number)
                # print(block_reqset[requirements].max_number - return_blocks[requirements], requirements)
                # if block_reqset[requirements].max_number:
                # print(block_reqset[requirements])
                # print(block_reqset[requirements].max_number - return_blocks[requirements], requirements)
                for req in requirements:
                    requirement_corrections[req] += 1
                return_blocks[requirements] += 1

    # for k, v in return_blocks.items():
    #     # print(k)
    #     if k[0].group.name == "II_DF":
    #         print(v, end=" | ")
    #         for req in k:
    #             print(
    #                 req.subject,
    #                 req.group,
    #                 req.teacher,
    #                 requirement_corrections[req],
    #                 end=" | ",
    #             )
    #         print()

    for req in requirements_querry:
        diff = req.hours - requirement_corrections[req]
        if req.hours - requirement_corrections[req] > 0:
            return_blocks[(req,)] = diff

    return list(return_blocks.keys()), np.array(list(return_blocks.values()))


def teacher_day_hours(
    block_list: list[tuple[Requirement]], req_set: RequirementSet, specimen: np.ndarray
) -> dict[Teacher, np.ndarray]:
    return_hours = dict()

    for teacher in Teacher.objects.filter(pool=req_set.teacher_pool):
        return_hours[teacher] = np.zeros(5, dtype=np.uint8)
        for day in range(5):
            for ind, block in enumerate(block_list):
                for req in block:
                    if req.teacher == teacher:
                        return_hours[teacher][day] += specimen[day, ind]

    return return_hours


def border_day_lessons(
    block_list: list[tuple[Requirement]], req_set: RequirementSet, specimen: np.ndarray
) -> dict[StudentGroup, np.ndarray]:

    return_borders = dict()
    for student_group in StudentGroup.objects.filter(pool=req_set.group_pool):
        return_borders[student_group] = np.zeros(5, dtype=np.uint8)
        for day in range(5):
            for ind, block in enumerate(block_list):
                if (
                    block[0].group == student_group
                    and all(req.subject.border for req in block)
                    and specimen[day, ind]
                ):
                    return_borders[student_group][day] += 1

    return return_borders


def group_day_lessons(
    block_list: list[tuple[Requirement]], req_set: RequirementSet, specimen: np.ndarray
) -> dict[StudentGroup, np.ndarray]:
    return_borders = dict()
    for student_group in StudentGroup.objects.filter(pool=req_set.group_pool):
        return_borders[student_group] = np.zeros(5, dtype=np.uint8)
        for day in range(5):
            for ind, block in enumerate(block_list):
                if block[0].group == student_group:
                    return_borders[student_group][day] += specimen[day, ind]

    return return_borders


def teacher_day_hours_population(
    block_list: list[tuple[Requirement]],
    req_set: RequirementSet,
    population: np.ndarray,
    teachers: list[Teacher],
) -> np.ndarray:
    teacher_indices = {teacher: i for i, teacher in enumerate(teachers)}
    n_teachers = len(teachers)
    n_population, _, n_blocks = population.shape

    teacher_hours = np.zeros((n_population, n_teachers, 5))

    for block_idx, block in enumerate(block_list):
        for req in block:
            teacher_idx = teacher_indices[req.teacher]
            teacher_hours[:, teacher_idx, :] += population[:, :, block_idx]

    return teacher_hours


def border_day_lessons_population(
    block_list: list[tuple[Requirement]],
    req_set: RequirementSet,
    population: np.ndarray,
    student_groups: list[StudentGroup],
) -> np.ndarray:
    group_indices = {group: i for i, group in enumerate(student_groups)}
    n_groups = len(student_groups)
    n_population, _, n_blocks = population.shape

    border_lessons = np.zeros((n_population, n_groups, 5))

    for block_idx, block in enumerate(block_list):
        if all(req.subject.border for req in block):
            group_idx = group_indices[block[0].group]
            border_lessons[:, group_idx, :] += population[:, :, block_idx]

    return border_lessons


def group_day_lessons_population(
    block_list: list[tuple[Requirement]],
    req_set: RequirementSet,
    population: np.ndarray,
    student_groups: list[StudentGroup],
) -> np.ndarray:
    group_indices = {group: i for i, group in enumerate(student_groups)}
    n_groups = len(student_groups)
    n_population, _, n_blocks = population.shape

    group_lessons = np.zeros((n_population, n_groups, 5))

    for block_idx, block in enumerate(block_list):
        group_idx = group_indices[block[0].group]
        group_lessons[:, group_idx, :] += population[:, :, block_idx]

    return group_lessons


def normalized_normal_pdf(x, mean=0, std_dev=1) -> np.ndarray:
    variance = std_dev**2

    return np.exp(-((x - mean) ** 2) / (2 * variance))


def evaluate_specimen(
    block_list: list[tuple[Requirement]],
    req_set: RequirementSet,
    specimen: np.ndarray,
    alphas=np.ones(3, dtype=np.float64),
) -> np.ndarray:
    a1 = teacher_day_hours(block_list, req_set, specimen)
    a1 = np.array(list(a1.values()), dtype=np.float64)
    a1 = alphas[0] * normalized_normal_pdf(a1, mean=7).sum(axis=0)

    a2 = group_day_lessons(block_list, req_set, specimen)
    a2 = np.array(list(a2.values()), dtype=np.float64)
    a2 = alphas[1] * (normalized_normal_pdf(a2, mean=7) * 2 - 1).sum(axis=0)

    a3_ = border_day_lessons(block_list, req_set, specimen)
    a3_ = np.array(list(a3_.values()), dtype=np.float64)
    a3 = np.full(a3_.shape, -1, dtype=np.float64)
    a3[a3_ == 0] = 0
    a3[a3_ == 1] = 1
    a3[a3_ == 2] = 0.5
    a3 = alphas[2] * a3.sum(axis=0)

    return a1 + a2 + a3


def cross_breed_student_groups(specimen1, specimen2, eval1, eval2, group_block_indexes):
    child = np.zeros_like(specimen1)

    for ind, (e1, e2) in enumerate(zip(eval1, eval2)):
        if e1 > e2:
            child[:, group_block_indexes == ind] = specimen1[
                :, group_block_indexes == ind
            ]
        else:
            child[:, group_block_indexes == ind] = specimen2[
                :, group_block_indexes == ind
            ]

    return child


def cross_breed_teachers(specimen1, specimen2, eval1, eval2, teacher_block_indexes):
    child = np.zeros_like(specimen1)

    for ind, (e1, e2) in enumerate(zip(eval1, eval2)):
        if e1 > e2:
            child[:, teacher_block_indexes == ind] = specimen1[
                :, teacher_block_indexes == ind
            ]
        else:
            child[:, teacher_block_indexes == ind] = specimen2[
                :, teacher_block_indexes == ind
            ]

    return child


def evaluate_population(
    block_list: list[tuple[Requirement]],
    req_set: RequirementSet,
    population: np.ndarray,
    teachers: list[Teacher],
    student_groups: list[StudentGroup],
    alphas=np.ones(3, dtype=np.float64),
) -> np.ndarray:
    """
    Evaluate the entire population at once.

    Args:
        block_list: List of requirement blocks.
        req_set: The requirement set.
        population: A 3D numpy array representing the population (shape: [n_population, 5, n_blocks]).
        teachers: Preloaded list of Teacher objects.
        student_groups: Preloaded list of StudentGroup objects.
        alphas: Weights for the evaluation components.

    Returns:
        np.ndarray: A 1D array of evaluation scores for the population.
    """
    # Teacher day hours
    a1 = teacher_day_hours_population(block_list, req_set, population, teachers)
    # a1: np.ndarray = alphas[0] * (2 - np.abs(a1 - 7)) / len(teachers)
    a1: np.ndarray = alphas[0] * (-((7 - a1) ** 2) + 2) / len(teachers)

    a1_ = a1.sum(axis=2)
    a1 = a1.sum(axis=(1, 2))

    # Group day lessons
    a2 = group_day_lessons_population(block_list, req_set, population, student_groups)
    a2: np.ndarray = alphas[1] * (-((7 - a2) ** 2) + 2) / len(student_groups)

    a2_ = a2.sum(axis=2)
    a2 = a2.sum(axis=(1, 2))

    # print(a2_.shape)

    # Border day lessons
    # a3_ = border_day_lessons_population(block_list, req_set, population, student_groups)
    # a3 = np.full(a3_.shape, -1, dtype=np.float64)

    # a3[a3_ == 0] = 0
    # a3[a3_ == 1] = 1
    # a3[a3_ == 2] = 0.5
    # a3 = alphas[2] * a3.sum(axis=(1, 2))

    return a2 + a1, a2_, a1_


def cross_breed(
    subject1: np.ndarray,
    subject2: np.ndarray,
    eval1: np.ndarray,
    eval2: np.ndarray,
    block_val: np.ndarray,
) -> tuple[np.ndarray, np.ndarray]:
    best_day1 = np.argmax(eval1)
    best_day2 = np.argmax(eval2)

    worst_day1 = np.argmin(eval1)
    worst_day2 = np.argmin(eval2)

    child1 = subject1.copy()
    child1[worst_day1, :] = subject2[best_day2, :]

    child2 = subject2.copy()
    child2[worst_day2, :] = subject1[best_day1, :]

    for ind, difference in enumerate(
        child1[best_day1, :] + child1[worst_day1, :] - block_val
    ):
        if difference > 0:
            correction = np.random.multinomial(difference, [0.5, 0.5])
            child1[best_day1, ind] -= correction[0]
            child1[worst_day1, ind] -= correction[1]

            mask = np.ones(5, dtype=bool)
            mask[[best_day1, worst_day1]] = False
            child1[mask, ind] = 0

    for ind, difference in enumerate(
        child2[best_day2, :] + child2[worst_day2, :] - block_val
    ):
        if difference > 0:
            correction = np.random.multinomial(difference, [0.5, 0.5])
            child2[best_day2, ind] -= correction[0]
            child2[worst_day1, ind] -= correction[1]

            mask = np.ones(5, dtype=bool)
            mask[[best_day2, worst_day2]] = False
            child2[mask, ind] = 0

    return child1, child2


def cross_breed(
    subject1: np.ndarray,
    subject2: np.ndarray,
    eval1: np.ndarray,
    eval2: np.ndarray,
    block_val: np.ndarray,
) -> tuple[np.ndarray, np.ndarray]:
    best_day1 = np.argmax(eval1)
    best_day2 = np.argmax(eval2)

    worst_day1 = np.argmin(eval1)
    worst_day2 = np.argmin(eval2)

    child1 = subject1.copy()
    child1[worst_day1, :] = subject2[best_day2, :]

    child2 = subject2.copy()
    child2[worst_day2, :] = subject1[best_day1, :]

    # Adjust child1 to ensure no negative values and preserve column sums
    for ind, difference in enumerate(
        child1[best_day1, :] + child1[worst_day1, :] - block_val
    ):
        if difference > 0:
            correction = np.random.multinomial(difference, [0.5, 0.5])
            child1[best_day1, ind] -= correction[0]
            child1[worst_day1, ind] -= correction[1]

        # Ensure no negative values
        negatives = child1[:, ind] < 0
        if np.any(negatives):
            total_negative = -child1[negatives, ind].sum()
            child1[negatives, ind] = 0

            positives = child1[:, ind] > 0
            if np.any(positives):
                redistribution = np.random.multinomial(
                    total_negative,
                    child1[positives, ind] / child1[positives, ind].sum(),
                )
                child1[positives, ind] += redistribution

        # Final adjustment to ensure column sum matches block_val
        current_sum = child1[:, ind].sum()
        if current_sum != block_val[ind]:
            difference = block_val[ind] - current_sum
            redistribution = np.random.multinomial(
                abs(difference), [1 / 5] * 5
            )  # Distribute evenly across days
            if difference > 0:
                child1[:, ind] += redistribution
            else:
                child1[:, ind] -= redistribution

    # Adjust child2 to ensure no negative values and preserve column sums
    for ind, difference in enumerate(
        child2[best_day2, :] + child2[worst_day2, :] - block_val
    ):
        if difference > 0:
            correction = np.random.multinomial(difference, [0.5, 0.5])
            child2[best_day2, ind] -= correction[0]
            child2[worst_day2, ind] -= correction[1]

        # Ensure no negative values
        negatives = child2[:, ind] < 0
        if np.any(negatives):
            total_negative = -child2[negatives, ind].sum()
            child2[negatives, ind] = 0

            positives = child2[:, ind] > 0
            if np.any(positives):
                redistribution = np.random.multinomial(
                    total_negative,
                    child2[positives, ind] / child2[positives, ind].sum(),
                )
                child2[positives, ind] += redistribution

        # Final adjustment to ensure column sum matches block_val
        current_sum = child2[:, ind].sum()
        if current_sum != block_val[ind]:
            difference = block_val[ind] - current_sum
            redistribution = np.random.multinomial(
                abs(difference), [1 / 5] * 5
            )  # Distribute evenly across days
            if difference > 0:
                child2[:, ind] += redistribution
            else:
                child2[:, ind] -= redistribution

    return child1, child2


def mutate_population(
    population: np.ndarray,
    block_val: np.ndarray,
    availability: np.ndarray,
    mutation_rate: float = 0.1,
) -> np.ndarray:
    """
    Mutate a percentage of the population by redistributing values within columns (blocks),
    respecting availability constraints.

    Args:
        population (np.ndarray): The population to mutate (shape: [n_population, 5, n_blocks]).
        block_val (np.ndarray): The target column sums for each block.
        availability (np.ndarray): Availability matrix (shape: [n_blocks, 5]).
        mutation_rate (float): The percentage of the population to mutate (0.0 to 1.0).

    Returns:
        np.ndarray: The mutated population.
    """
    n_population, n_days, n_blocks = population.shape
    n_to_mutate = int(n_population * mutation_rate)
    if n_to_mutate == 0:
        return population

    mutate_indices = np.random.choice(n_population, n_to_mutate, replace=False)
    mutated_population = population.copy()

    for specimen_idx in mutate_indices:
        for block_idx in range(n_blocks):
            total = block_val[block_idx]
            valid_days = availability[block_idx]
            if total > 0 and valid_days.any():
                probabilities = valid_days / valid_days.sum()
                new_distribution = np.random.multinomial(total, probabilities)
                while np.any(new_distribution > 2):
                    excess = new_distribution - np.clip(new_distribution, 0, 2)
                    new_distribution = np.clip(new_distribution, 0, 2)
                    redistribution = np.random.multinomial(excess.sum(), probabilities)
                    new_distribution += redistribution * valid_days
                mutated_population[specimen_idx, :, block_idx] = new_distribution
            else:
                mutated_population[specimen_idx, :, block_idx] = 0

    return mutated_population


def evolutionary_loop(
    block_list: list[tuple[Requirement]],
    req_set: RequirementSet,
    population: np.ndarray,
    teachers: list[Teacher],
    student_groups: list[StudentGroup],
    block_val: np.ndarray,
    availability: np.ndarray,
    generations: int = 100,
    alphas=np.ones(3, dtype=np.float64),
):
    """
    Run the evolutionary algorithm.

    Args:
        block_list: List of requirement blocks.
        req_set: The requirement set.
        population: A 3D numpy array representing the population (shape: [n_population, 5, n_blocks]).
        teachers: Preloaded list of Teacher objects.
        student_groups: Preloaded list of StudentGroup objects.
        block_val: Array of block values.
        generations: Number of generations to run.
        alphas: Weights for the evaluation components.

    Returns:
        np.ndarray: The best specimen after all generations.
    """

    group_block_indexes = np.array(
        [student_groups.index(block[0].group) for block in block_list]
    )
    teacher_block_indexes = np.array(
        [teachers.index(block[0].teacher) for block in block_list]
    )
    population_size = population.shape[0]

    for generation in range(generations):
        # Evaluate the population
        evaluations, group_evaluations, teacher_evaluations = evaluate_population(
            block_list, req_set, population, teachers, student_groups, alphas
        )

        for specimen in population:
            assert is_array_valid(specimen, block_val)

        # Sort population by evaluation scores (descending)
        sorted_indices = np.argsort(evaluations)[::-1]
        population = population[sorted_indices]
        evaluations = evaluations[sorted_indices]
        group_evaluations = group_evaluations[sorted_indices]
        teacher_evaluations = teacher_evaluations[sorted_indices]

        # Print the best score of the current generation
        print(f"Generation {generation + 1}: Best Score = {evaluations[0]}")

        # Keep the best specimen unchanged
        best_specimen = population[0]

        # Select the top 50% of the population
        top_half = population[: population_size // 2]

        # Breed the top 50% to create the next generation
        new_population = []  # Start with the best specimen
        while len(new_population) < population_size - 1:
            # Randomly select two parents from the top half
            parent_indices = np.random.choice(len(top_half), 2, replace=False)

            parent1, parent2 = top_half[parent_indices]
            eval1, eval2 = evaluations[parent_indices]
            g_eval1, g_eval2 = group_evaluations[parent_indices]
            t_eval1, t_eval2 = teacher_evaluations[parent_indices]

            # Crossbreed the parents to produce two children
            # child1, child2 = cross_breed(parent1, parent2, eval1, eval2, block_val)
            child1 = cross_breed_student_groups(
                parent1, parent2, g_eval1, g_eval2, group_block_indexes
            )
            child2 = cross_breed_teachers(
                parent1, parent2, t_eval1, t_eval2, teacher_block_indexes
            )
            new_population.append(child1)
            new_population.append(child2)

            # Add the children to the new population
            # new_population.append(child1)
            # if len(new_population) < population_size - 1:
            #     new_population.append(child2)

        # Convert the new population back to a NumPy array
        population = np.array(new_population)
        population = mutate_population(population, block_val, availability, 0.2)
        # population = add_integer_noise_batch(population)

        population = np.concatenate(
            [population, best_specimen[np.newaxis, :, :]], axis=0
        )

    # Return the best specimen after all generations
    np.save("specimen", best_specimen)
    return best_specimen
