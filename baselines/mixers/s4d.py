"""Frozen s4d control with the public candidate signature."""
from torch import nn

from proxy_tasks.common_set.backbone import mixer_width
from proxy_tasks.common_set.mixers import make_mixer


class CandidateMixer(nn.Module):
    def __init__(self, d_model, num_heads, l_max):
        super().__init__()
        width = mixer_width('s4d', d_model, num_heads, l_max)
        self.mixer = make_mixer('s4d', d_model, num_heads, l_max, width)

    def forward(self, x):
        return self.mixer(x)
