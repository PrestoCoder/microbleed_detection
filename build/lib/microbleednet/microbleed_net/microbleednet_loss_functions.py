from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.nn.modules.loss import _Loss, _WeightedLoss
import numpy as np
from torch.autograd import Variable

#=========================================================================================
# Microbleednet loss functions
# Vaanathi Sundaresan
# 09-01-2023
#=========================================================================================

class DiceLoss(_WeightedLoss):
    def __init__(self, weight=None):
        super(DiceLoss, self).__init__(weight)

    def forward(self, pred_binary, target_binary):
        """
        Forward pass
        :param pred_binary: torch.tensor (NxCxHxW)
        :param target_binary: torch.tensor (NxHxW)
        :return: scalar
        """
        smooth = 1.
        pred_vect = pred_binary.contiguous().view(-1)
        target_vect = target_binary.contiguous().view(-1)
        intersection = (pred_vect * target_vect).sum()
        dice = (2. * intersection + smooth) / (torch.sum(pred_vect) + torch.sum(target_vect) + smooth)
        device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        dice = dice.to(device=device, dtype=torch.float)
        return -dice


class CrossEntropyLoss2d(_WeightedLoss):
    """
    Standard pytorch weighted nn.CrossEntropyLoss
    """

    def __init__(self, weight=None):
        super(CrossEntropyLoss2d, self).__init__()
        self.nll_loss = nn.CrossEntropyLoss(weight)

    def forward(self, inputs, targets):
        """
        Forward pass
        :param inputs: torch.tensor (NxC)
        :param targets: torch.tensor (N)
        :return: scalar
        """
        device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        targets = targets.to(device=device, dtype=torch.long)
        return self.nll_loss(inputs, targets)


class CombinedLoss(_Loss):
    """
    A combination of dice  and cross entropy loss
    """

    def __init__(self):
        super(CombinedLoss, self).__init__()
        self.cross_entropy_loss = CrossEntropyLoss2d()
        self.dice_loss = DiceLoss()

    def forward(self, input, target, weight=None):
        """
        Forward pass
        :param input: torch.tensor (NxCxHxW)
        :param target: torch.tensor (NxHxW)
        :param weight: torch.tensor (NxHxW)
        :return: scalar
        """
        input_soft = F.softmax(input, dim=1)
        probs_vector = input_soft.contiguous().view(-1, 2)
        mask_vector = (probs_vector[:, 1] > 0.5).double()
        l2 = torch.mean(self.dice_loss(mask_vector, target))
        if weight is None:
            l1 = torch.mean(self.cross_entropy_loss.forward(input, target))
        else:
            l1 = torch.mean(
                torch.mul(self.cross_entropy_loss.forward(input, target), weight.cuda()))
        return l1 + l2


class DistillationLoss(_Loss):
    """
    A combination of dice  and cross entropy loss
    """
    def __init__(self):
        super(DistillationLoss, self).__init__()
        self.cross_entropy_loss = CrossEntropyLoss2d()
        self.dice_loss = DiceLoss()

    def forward(self, input, target, temperature, alpha, teacher_scores=None):
        """
        Forward pass
        :param input: torch.tensor (NxCxHxW)
        :param target: torch.tensor (NxHxW)
        :param temperature: scalar
        :param alpha: scalar
        :param teacher_scores: torch.array
        :return: scalar
        """
        p = F.log_softmax(input / temperature, dim=1)
        q = F.softmax(teacher_scores / temperature, dim=1)
        l_kl = F.kl_div(p, q, size_average=False) * (temperature ** 2) / input.shape[0]
        l_ce = F.cross_entropy(input, target)
        return l_kl * alpha + l_ce * (1. - alpha)




