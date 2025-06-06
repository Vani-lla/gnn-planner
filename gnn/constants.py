import numpy as np
import torch

FEATURE_DIM = 10
THRESHOLD = 0.5
REQUIRED_LESSONS = torch.tensor(list(zip(*np.nonzero(np.load("data/constraints.npy")))))
CLASSES = REQUIRED_LESSONS[:, 1]
CONSTRAINTS = torch.from_numpy(np.load("data/constraints.npy"))
T, C, S = CONSTRAINTS.shape

ARR_C, ARR_T = torch.arange(C), torch.arange(T)
TEACHER_LESSONS_IDS = REQUIRED_LESSONS[:, 0] == ARR_T[:, None]
CLASSES_LESSONS_IDS = REQUIRED_LESSONS[:, 0] == ARR_C[:, None]

GLOBAL_COMPLEMENTARY = [
    (11, 12, 14),  # Language groups
    (1, 8),  # English + IT
    (1, 1),  # Double English
    (10, 10, 4),  # Religion + Ethics
    (16, 16),  # PE
]
PER_CLASS_COMPLEMENTARY = {
    6: [(15, 3)],  # Bio + Social Studies
    7: [(11, 18)],  # German + Math
    8: [(6, 8), (15, 7)],
    9: [(6, 15)],
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

START_END_SUBJECTS = set((4, 10, 24, 23, 22, 21, 20, 14, 12, 11))
