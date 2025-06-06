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


def get_initial_lesson_ebeddings() -> torch.Tensor:
    embeddings = torch.zeros(REQUIRED_LESSONS.shape[0], 10)
    # 0 Remaining lessons
    # 1 Lessons in that day per class
    # 2 Lessons in that day per teacher
    # 3 Teacher windows
    # 4 Is starting
    # 5 No of lesson slot
    # 6 Is prievous the same
    # 7

    embeddings[:, 0] = CONSTRAINTS[*REQUIRED_LESSONS.T]
    # embeddings[:, 1] = 0
    # embeddings[:, 2] = 0
    # embeddings[:, 3] = 0
    embeddings[:, 4] = torch.ones(REQUIRED_LESSONS.shape[0])
    embeddings[:, 5] = 1

def step_on_selected(current_embeddings: torch.Tensor, selected: torch.Tensor) -> torch.Tensor:
    embeddings = current_embeddings.clone()
    
    embeddings[:, 0] -= selected.sum(dim=1)
    embeddings[CLASSES_LESSONS_IDS[ARR_C]:, 1] += selected.sum(dim=0).clip(0, 1)
    embeddings[TEACHER_LESSONS_IDS[ARR_T]:, 2] += selected.sum(dim=0).clip(0, 1)
    embeddings[:, 1] -= selected.sum(dim=0).clip(0, 1)
    embeddings[:, 1] -= selected.sum(dim=0).clip(0, 1)


def get_score(selected_: torch.Tensor) -> torch.Tensor:
    # T C S
    selected = selected_.to("cpu")
    final_score = torch.zeros_like(selected, dtype=torch.float32)
    for c, class_inds in enumerate(selected):
        lessons = REQUIRED_LESSONS[class_inds[: CLASSES.shape[0]]]
        skip_lesson = class_inds[REQUIRED_LESSONS.shape[0] + c]

        if skip_lesson and lessons.shape[0]:
            final_score[c, REQUIRED_LESSONS.shape[0] + c] = -5
        if lessons.shape[0] > 1:
            if are_subjects_complementary(lessons[:, 2], c):
                final_score[c, class_inds] = 4
            else:
                final_score[c, class_inds] = -100
        if lessons.shape[0] == 1:
            final_score[c, class_inds] = 2

    return final_score.to(selected_.device)
