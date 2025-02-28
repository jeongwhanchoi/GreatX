import os.path as osp

import torch
import torch_geometric.transforms as T

from greatx.attack.untargeted import FGAttack
from greatx.datasets import GraphDataset
from greatx.nn.models import GCN, GNNGUARD
from greatx.training.callbacks import ModelCheckpoint
from greatx.training.trainer import Trainer
from greatx.utils import split_nodes

dataset = 'Cora'
root = osp.join(osp.dirname(osp.realpath(__file__)), '../..', 'data')
dataset = GraphDataset(root=root, name=dataset,
                       transform=T.LargestConnectedComponents())

data = dataset[0]
splits = split_nodes(data.y, random_state=15)

num_features = data.x.size(-1)
num_classes = data.y.max().item() + 1

device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')

# ================================================================== #
#                      Before Attack                                 #
# ================================================================== #
trainer_before = Trainer(GCN(num_features, num_classes), device=device)
ckp = ModelCheckpoint('model_before.pth', monitor='val_acc')
trainer_before.fit(data, mask=(splits.train_nodes, splits.val_nodes),
                   callbacks=[ckp])
logs = trainer_before.evaluate(data, splits.test_nodes)
print(f"Before attack\n {logs}")

# ================================================================== #
#                      Attacking                                     #
# ================================================================== #
attacker = FGAttack(data, device=device)
attacker.setup_surrogate(trainer_before.model, splits.train_nodes)
attacker.reset()
attacker.attack(0.2)

# ================================================================== #
#                      After evasion Attack                          #
# ================================================================== #
logs = trainer_before.evaluate(attacker.data(), splits.test_nodes)
print(f"After evasion attack\n {logs}")
# ================================================================== #
#                      After poisoning Attack                        #
# ================================================================== #
trainer_after_gcn = Trainer(GCN(num_features, num_classes), device=device)
trainer_after_gcn.fit(attacker.data(), mask=splits.train_nodes)
logs = trainer_after_gcn.evaluate(attacker.data(), splits.test_nodes)
print(f"After poisoning attack (GCN)\n {logs}")

trainer_after_defense = Trainer(GNNGUARD(num_features, num_classes),
                                device=device)
trainer_after_defense.fit(attacker.data(), mask=splits.train_nodes)
logs = trainer_after_defense.evaluate(attacker.data(), splits.test_nodes)
print(f"After poisoning attack (GNNGUARD)\n {logs}")
