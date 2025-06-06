import pandas as pd
from collections import defaultdict

D = 5
H = 10

with open("plan.txt", "r") as file:
    l = [tuple(map(int, line.rstrip().split(" "))) for line in file.readlines()]

plan = defaultdict(lambda: list([[] for _ in range(H)] for _ in range(D)))

for c, r, t, s, d, h in l:
    plan[c][d][h].append((s, t))

for i in range(22):
    tmp_plan = pd.DataFrame(plan[i]).T
    tmp_plan.columns = ["Pon", "Wt", "Śr", "Czw", "Pt"]
    print(i, "-------------------------------")
    print(tmp_plan)