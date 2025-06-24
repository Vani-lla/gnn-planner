from itertools import combinations
from time import time

import torch
import torch.nn as nn
import torch.nn.functional as F
from constants import *
from helpers import *
from torch_geometric.data import Data
from torch_geometric.nn import FastRGCNConv


def get_data() -> Data:
    edges, types = [], []
    for (i1, (t1, c1, s1)), (i2, (t2, c2, s2)) in combinations(
        enumerate(REQUIRED_LESSONS), 2
    ):
        edge_type = 0  # Neutral
        if are_complementary(s1, s2, c1, c2):
            edge_type = 4
        elif are_compatible(s1, s2, c1, c2, t1, t2):
            edge_type = 3
        elif t1 == t2:
            edge_type = 2
        elif c1 == c2:
            edge_type = 1

        if edge_type:
            types.extend([edge_type, edge_type])
            edges.extend([(i1, i2), (i2, i1)])

    edge_index = torch.tensor(edges).T
    edge_type = torch.tensor(types) - 1

    return Data(
        x=get_initial_lesson_ebeddings(),
        edge_index=edge_index,
        edge_type=edge_type,
    )


class RGCNModel(nn.Module):
    def __init__(
        self,
        in_channels,
        hidden_channels,
        out_channels=3,
        num_relations=4,
        num_of_lessons=REQUIRED_LESSONS.shape[0],
    ):
        super(RGCNModel, self).__init__()
        self.num_of_lessons = num_of_lessons
        self.unique_classes: torch.Tensor = CLASSES.unique()
        self.classes_dic = torch.cat(
            (CLASSES, torch.arange(0, self.unique_classes.shape[0]))
        )

        self.graph_layer_list = nn.ModuleList(
            [
                FastRGCNConv(in_channels, hidden_channels, num_relations),
                FastRGCNConv(hidden_channels, hidden_channels, num_relations),
                FastRGCNConv(hidden_channels, hidden_channels, num_relations),
                FastRGCNConv(hidden_channels, out_channels, num_relations),
                FastRGCNConv(out_channels, out_channels, num_relations),
            ]
        )

        self.post_graph_layer = nn.Sequential(
            nn.Linear(out_channels * num_of_lessons, out_channels * num_of_lessons),
            nn.Tanh(),
            nn.Linear(out_channels * num_of_lessons, out_channels * num_of_lessons),
            nn.Tanh(),
            nn.Linear(out_channels * num_of_lessons, num_of_lessons),
            nn.Sigmoid(),
        )

    def forward(self, x, edge_index, edge_type):
        for layer in self.graph_layer_list:
            x = layer(x, edge_index=edge_index, edge_type=edge_type)
            x = F.relu(x)
        x = self.post_graph_layer(x.view(-1))

        return x


if __name__ == "__main__":
    data = get_data()
    device = torch.device("cuda:0")

    model = RGCNModel(FEATURE_DIM, 10)
    optimizer = torch.optim.Adam(model.parameters(), lr=0.001)
    model.to(device)
    data.to(device)

    valid = False
    embeddings = data.x
    old_selected = torch.zeros_like(CLASSES, device=device)
    i = 0
    for _ in range(2):
        print("asdfgykgjnkasdjnkasgghjnkasjksdcfakmghjasdgjkmasdfk")
        for _ in range(8):
            j = 0
            while not valid and j < 1000:
                optimizer.zero_grad()
                result = model(
                    embeddings + torch.rand_like(embeddings) * 0.01,
                    data.edge_index,
                    data.edge_type,
                )
                selected = result > THRESHOLD

                score, valid = get_score(selected, embeddings.to("cpu"))

                f_o: torch.Tensor = result * score
                loss = -f_o.sum()

                loss.backward()
                optimizer.step()

                j += 1
            i += 1
            
            embeddings = step_on_selected(embeddings, selected, old_selected)

            # print(-loss.item())
            # print(selected.sum().item(), valid)
            # print(valid)
            for c in range(6):
                lesson_name = ""
                for s in REQUIRED_LESSONS[
                    torch.logical_and(CLASSES == c, selected.to("cpu"))
                ][:, 2]:
                    lesson_name = "/".join([lesson_name, SUBJECTS_LOOKUP_DICT[s.item()]])
                print(f"{lesson_name[1:]:^30}", end=" | ")
            print()
            valid = False
