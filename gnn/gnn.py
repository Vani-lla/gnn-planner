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
        x=torch.randn(REQUIRED_LESSONS.shape[0], FEATURE_DIM),
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
            nn.Linear(
                out_channels * num_of_lessons,
                num_of_lessons + self.unique_classes.shape[0],
            ),
            nn.Sigmoid(),
        )

    def forward(self, x, edge_index, edge_type):
        for layer in self.graph_layer_list:
            x = layer(x, edge_index=edge_index, edge_type=edge_type)
            x = F.relu(x)
        x = self.post_graph_layer(x.view(-1))

        class_ids = torch.bucketize(self.classes_dic, self.unique_classes)
        probs = torch.zeros(
            self.unique_classes.shape[0], self.classes_dic.shape[0], device=x.device
        )
        probs[class_ids, torch.arange(self.classes_dic.shape[0])] = x

        return probs


if __name__ == "__main__":
    data = get_data()
    device = torch.device("cuda:0")

    model = RGCNModel(10, 10)
    optimizer = torch.optim.Adam(model.parameters(), lr=0.001)
    model.to(device)
    data.to(device)

    start = time()
    for _ in range(1000):
        result = model(data.x, data.edge_index, data.edge_type)
        selected = result > THRESHOLD

        f_o: torch.Tensor = result * get_score(selected).detach()
        loss = -f_o.sum()

        loss.backward()
        optimizer.step()

        print(loss.item())

    print(time() - start)
