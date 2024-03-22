from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import torch
import torch.nn as nn
from torch import optim
import os
from microbleednet.microbleed_net import (microbleednet_loss_functions,
                              microbleednet_models, microbleednet_train)
from microbleednet.utils import microbleednet_utils

#=========================================================================================
# Microbleednet Candidate detection model fine_tuning function
# Vaanathi Sundaresan
# 10-01-2023
#=========================================================================================


def main(sub_name_dicts, ft_params, aug=True, save_cp=True, save_wei=True, save_case='best',
         verbose=True, model_dir=None, dir_cp=None):
    """
    The main function for fine-tuning the model
    :param sub_name_dicts: list of dictionaries containing subject filepaths for fine-tuning
    :param ft_params: dictionary of fine-tuning parameters
    :param aug: bool, whether to do data augmentation
    :param save_cp: bool, whether to save checkpoint
    :param save_wei: bool, whether to save weights alone or the full model
    :param save_case: str, condition for saving the CP
    :param verbose: bool, display debug messages
    :param model_dir: str, filepath containing pretrained model
    :param dir_cp: str, filepath for saving the model
    """
    assert len(sub_name_dicts) >= 5, "Number of distinct subjects for fine-tuning cannot be less than 5"

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model = microbleednet_models.CDetNet(n_channels=2, n_classes=2, init_channels=64)
    model.to(device=device)
    model = nn.DataParallel(model)

    model_name = ft_params['Modelname']
    try:
        model_path = os.path.join(model_dir, model_name + '_cdet_model.pth')
        model = microbleednet_utils.loading_model(model_path, model)
    except:
        try:
            model_path = os.path.join(model_dir, model_name + '_cdet_model.pth')
            model = microbleednet_utils.loading_model(model_path, model, mode='full_model')
        except ImportError:
            raise ImportError('In directory ' + model_dir + ', ' + model_name + '_cdet_model.pth or' +
                              model_name + '_cdisc_student_model.pth does not appear to be a valid model file')

    layers_to_ft = ft_params['Finetuning_layers']  # list of numbers [1,8]
    optim_type = ft_params['Optimizer']  # adam, sgd
    milestones = ft_params['LR_Milestones']  # list of integers [1, N]
    gamma = ft_params['LR_red_factor']  # scalar (0,1)
    ft_lrt = ft_params['Finetuning_learning_rate']  # scalar (0,1)
    train_prop = ft_params['Train_prop']  # scale (0,1)

    if type(milestones) != list:
        milestones = [milestones]

    if type(layers_to_ft) != list:
        layers_to_ft = [layers_to_ft]

    print('Total number of model parameters', flush=True)
    print('Cand detection model: ', str(sum([p.numel() for p in model.parameters()])), flush=True)

    model = microbleednet_utils.freeze_layer_for_finetuning(model, layers_to_ft, verbose=verbose)
    model.to(device=device)

    print('Total number of trainable parameters', flush=True)
    model_parameters = filter(lambda p: p.requires_grad, model.parameters())
    params = sum([p.numel() for p in model_parameters])
    print('Axial model: ', str(params), flush=True)

    if optim_type == 'adam':
        epsilon = ft_params['Epsilon']
        optimizer = optim.Adam(filter(lambda p: p.requires_grad,
                                            model.parameters()), lr=ft_lrt, eps=epsilon)
    elif optim_type == 'sgd':
        moment = ft_params['Momentum']
        optimizer = optim.SGD(filter(lambda p: p.requires_grad,
                                           model.parameters()), lr=ft_lrt, momentum=moment)
    else:
        raise ValueError("Invalid optimiser choice provided! Valid options: 'adam', 'sgd'")

    criterion = microbleednet_loss_functions.CombinedLoss()

    if verbose:
        print('Found' + str(len(sub_name_dicts)) + 'subjects', flush=True)

    num_val_subs = max(int(len(sub_name_dicts) * (1 - train_prop)), 1)
    train_name_dicts, val_name_dicts, val_ids = microbleednet_utils.select_train_val_names(sub_name_dicts,
                                                                                     num_val_subs)

    scheduler = optim.lr_scheduler.MultiStepLR(optimizer, milestones, gamma=gamma, last_epoch=-1)
    model = microbleednet_train.train_cdet(train_name_dicts, val_name_dicts, model, criterion,
                                           optimizer, scheduler, ft_params, device, augment=aug,
                                           save_checkpoint=save_cp, save_weights=save_wei,
                                           save_case=save_case, verbose=verbose, dir_checkpoint=dir_cp)

    print('Model Fine-tuning done!', flush=True)


