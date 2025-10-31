import numpy as np
from backend.models import *


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


def initialize_population(n: int, validation_hours) -> np.ndarray:
    population = []
    for _ in range(n):
        specimen = []
        for h in validation_hours:
            if h == 3:
                day_distribution = np.random.permutation([1, 2, 0, 0, 0])
            else:
                day_distribution = np.random.multinomial(h, [1 / 5] * 5)
                while any(day_distribution > 2):
                    excess_indices = np.where(day_distribution > 2)[0]
                    for idx in excess_indices:
                        excess = day_distribution[idx] - 2
                        day_distribution[idx] = 2
                        redistribution = np.random.multinomial(excess, [1 / 4] * 4)
                        mask = np.ones(5, dtype=bool)
                        mask[idx] = False
                        day_distribution[mask] += redistribution
            specimen.append(day_distribution)
        population.append(np.array(specimen).T)
    return np.array(population)


def generate_blocks(requirements_querry, req_set, validation_hours):
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
    population: np.ndarray, block_val: np.ndarray, mutation_rate: float = 0.1
) -> np.ndarray:
    """
    Mutate a percentage of the population by redistributing values within columns (blocks).

    Args:
        population (np.ndarray): The population to mutate (shape: [n_population, 5, n_blocks]).
        block_val (np.ndarray): The target column sums for each block.
        mutation_rate (float): The percentage of the population to mutate (0.0 to 1.0).

    Returns:
        np.ndarray: The mutated population.
    """
    n_population, n_days, n_blocks = population.shape

    # Determine the number of specimens to mutate
    n_to_mutate = int(n_population * mutation_rate)
    if n_to_mutate == 0:
        return population

    # Randomly select specimens to mutate
    mutate_indices = np.random.choice(n_population, n_to_mutate, replace=False)

    # Create a copy of the population to mutate
    mutated_population = population.copy()

    # Generate random distributions for the selected specimens and blocks
    for specimen_idx in mutate_indices:
        # Redistribute values for each block
        for block_idx in range(n_blocks):
            total = block_val[block_idx]
            if total == 3:
                new_distribution = np.random.permutation([1, 2, 0, 0, 0])
            else:
                new_distribution = np.random.multinomial(total, [1 / n_days] * n_days)
                while np.any(new_distribution > 2):
                    new_distribution = np.random.multinomial(
                        total, [1 / n_days] * n_days
                    )
            mutated_population[specimen_idx, :, block_idx] = new_distribution

    return mutated_population


def evolutionary_loop(
    block_list: list[tuple[Requirement]],
    req_set: RequirementSet,
    population: np.ndarray,
    teachers: list[Teacher],
    student_groups: list[StudentGroup],
    block_val: np.ndarray,
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
        population = mutate_population(population, block_val, 0.2)
        # population = add_integer_noise_batch(population)

        population = np.concatenate(
            [population, best_specimen[np.newaxis, :, :]], axis=0
        )

    # Return the best specimen after all generations
    return best_specimen
