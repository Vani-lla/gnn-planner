from constants import *
import torch


def are_complementary(s_1: int, s_2: int, c_1: int, c_2: int) -> bool:
    g = PER_CLASS_COMPLEMENTARY.get(c_1)
    return (c_1 == c_2) and (
        any(s_1 in grp and s_2 in grp for grp in GLOBAL_COMPLEMENTARY)
        or (g and any(s_1 in grp and s_2 in grp for grp in g))
    )


def are_compatible(s_1: int, s_2: int, c_1: int, c_2: int, t_1: int, t_2: int) -> bool:
    g = GLOBAL_GROUP_SUBJECTS.get(s_1.item())
    return (
        s_1 == s_2
        and g
        and t_1 == t_2
        and t_1 in g[0]
        and any(c_1 in grp and c_2 in grp for grp in g[1:])
    )


def are_subjects_complementary(subjects: torch.Tensor, c: int) -> bool:
    for group in GLOBAL_COMPLEMENTARY + PER_CLASS_COMPLEMENTARY.get(c, []):
        if len(subjects) == len(group) and all(s in group for s in subjects):
            return True
    return False


def are_lessons_grouped(subjects: torch.Tensor) -> bool:
    if tmp := GLOBAL_GROUP_SUBJECTS.get(subjects[0, 2].item()):
        if subjects[0, 0].item() in tmp[0]:
            if any(all(c in g for c in subjects[:, 1]) for g in tmp[1:]):
                return True
    return False


def get_initial_lesson_ebeddings() -> torch.Tensor:
    embeddings = torch.zeros(REQUIRED_LESSONS.shape[0], FEATURE_DIM)
    # 0 Remaining lessons
    # 1 Lessons in that day per class
    # 2 Lessons in that day per teacher
    # 3 Teacher windows
    # 4 No of lesson slot
    # 5 Is prievous the same
    # 6 No of the same lessons in that day

    embeddings[:, 0] = CONSTRAINTS[*REQUIRED_LESSONS.T]

    return embeddings


def step_on_selected(
    current_embeddings: torch.Tensor, selected: torch.Tensor, old_selected: torch.Tensor
) -> torch.Tensor:
    embeddings = current_embeddings.clone()

    embeddings[:, 0] -= selected.type_as(embeddings)

    selected_ = selected.to("cpu")
    for c in CLASSES.unique():
        inds = torch.logical_and(CLASSES == c, selected_)
        embeddings[CLASSES == c, 1] += selected_[inds].sum().clip(0, 1)

    for t in TEACHERS.unique():
        teacher_inds = TEACHERS == t
        inds = torch.logical_and(teacher_inds, selected_)
        is_selected = selected_[inds].sum().clip(0, 1)
        embeddings[teacher_inds, 2] += is_selected

        if current_embeddings[teacher_inds, 2][0] > 0 and is_selected == 0:
            embeddings[teacher_inds, 3] += 1

    embeddings[:, 4] += 1
    embeddings[:, 5] = torch.logical_and(selected, old_selected)
    embeddings[:, 6] += selected.type_as(embeddings)

    return embeddings


def get_score(
    selected_: torch.Tensor, current_embeddings: torch.Tensor
) -> tuple[torch.Tensor, bool]:
    # T C S
    valid = True
    with torch.no_grad():
        selected = selected_.to("cpu")
        final_score = torch.zeros_like(selected, dtype=torch.float32)

        requirement_mask = torch.logical_and(current_embeddings[:, 0] <= 0.1, selected)
        final_score[requirement_mask] += -20
        if requirement_mask.any():
            valid = False
        final_score[~requirement_mask] += 0.5

        for c in CLASSES.unique():
            inds = torch.logical_and(CLASSES == c, selected)
            lessons = REQUIRED_LESSONS[inds]

            if lessons.shape[0] == 0:
                if current_embeddings[:, 1].any():
                    final_score[CLASSES == c] += 1
                    valid = False
                final_score[CLASSES == c] += 0.5
                pass
            else:
                if lessons.shape[0] == 1:
                    final_score[inds] += 2
                else:
                    if are_subjects_complementary(lessons[:, 2], c):
                        final_score[inds] += 4
                    else:
                        valid = False
                        final_score[inds] += -20

        for t in TEACHERS.unique():
            inds = torch.logical_and(TEACHERS == t, selected)
            lessons = REQUIRED_LESSONS[inds]

            if lessons.shape[0] == 0:
                final_score[TEACHERS == t] += 0
            elif not are_lessons_grouped(lessons):
                if lessons.shape[0] == 1:
                    final_score[inds] += 2
                else:
                    valid = False
                    final_score[inds] += -20
            else:
                final_score[inds] += 4

        invalid_mask = torch.logical_and(current_embeddings[:, 6] >= 1.9, selected)
        if invalid_mask.any():
            final_score[invalid_mask] += -20
            final_score[~invalid_mask] += 0.5
            valid = False

        return final_score.to(selected_.device), valid
