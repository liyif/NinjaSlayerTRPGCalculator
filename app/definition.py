
from .types import Difficulty

DIFFICULTY_KIDS = Difficulty.create([(2, 1)])       # 最简单
DIFFICULTY_EASY = Difficulty.create([(3, 1)])
DIFFICULTY_NORMAL = Difficulty.create([(4, 1)])
DIFFICULTY_HARD = Difficulty.create([(5, 1)])
DIFFICULTY_UHARD = Difficulty.create([(6, 1)])
DIFFICULTY_UHARD2 = Difficulty.create([(6, 2)])
DIFFICULTY_UHARD3 = Difficulty.create([(6, 3)])

DIFFICULTY_55 = Difficulty.create([(5, 2)])        # 5x2
DIFFICULTY_555 = Difficulty.create([(5, 3)])
DIFFICULTY_65 = Difficulty.create([(6, 1),(5, 2)])        # 6x1 + 5x2
DIFFICULTY_665 = Difficulty.create([(6, 2), (5, 3)])      # 6x2 + 5x3
DIFFICULTY_6665 = Difficulty.create([(6, 3), (5, 4)])     # 6x3 + 5x4


DIFFICULTIES = [
    ("KIDS", DIFFICULTY_KIDS),
    ("EASY", DIFFICULTY_EASY),
    ("NORMAL", DIFFICULTY_NORMAL),
    ("HARD", DIFFICULTY_HARD),
    ("UHARD", DIFFICULTY_UHARD),
    ("UHARD2", DIFFICULTY_UHARD2),
    ("UHARD3", DIFFICULTY_UHARD3),
    ("55", DIFFICULTY_55),
    ("555", DIFFICULTY_555),
    ("65", DIFFICULTY_65),
    ("665", DIFFICULTY_665),
    ("6665", DIFFICULTY_6665),
    ("66665", DIFFICULTY_6665),
]

LABEL_TO_DIFFICULTY = dict(DIFFICULTIES)
DIFFICULTY_TO_LABEL = dict(map(lambda x: (x[1], x[0]), DIFFICULTIES))