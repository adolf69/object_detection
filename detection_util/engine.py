import math
import sys
import time
import torch

import torchvision.models.detection.mask_rcnn

# from detection_util.coco_utils import get_coco_api_from_dataset
# from detection_util.coco_eval import CocoEvaluator
import detection_util.utils as utils


def train_one_epoch(model, optimizer, data_loader, device, epoch, print_freq):
    model.train()
    metric_logger = utils.MetricLogger(delimiter="  ")
    metric_logger.add_meter('lr', utils.SmoothedValue(window_size=1, fmt='{value:.6f}'))
    header = 'Epoch: [{}]'.format(epoch)

    lr_scheduler = None
    if epoch == 0:
        warmup_factor = 1. / 1000
        warmup_iters = min(1000, len(data_loader) - 1)

        lr_scheduler = utils.warmup_lr_scheduler(optimizer, warmup_iters, warmup_factor)

    # for images, targets, img_name in metric_logger.log_every(data_loader, print_freq, header):
    for images, targets in metric_logger.log_every(data_loader, print_freq, header):
        print(images)
        print('========')
        print(type(images))
        print(len(images))
        print(targets)
        print('-------')
        print(type(targets))
        print(len(targets))
        sys.exit(1)
        images = list(image.to(device) for image in images)
        targets = [{k: v.to(device) for k, v in t.items()} for t in targets]
        try:
            # output = ctpn_model(input)
            loss_dict_tmp = model(images, targets)
        except RuntimeError as exception:
            if "out of memory" in str(exception):
                print("WARNING: out of memory")

                targets_ = targets[0]
                img_id = targets_['image_id'].item()
                print('11111', img_id)

                img_data_dict = data_loader.dataset.__dict__
                img_data_dataset = img_data_dict['dataset']
                img_data_dataset_dict = img_data_dataset.__dict__

                img_list = img_data_dataset_dict['imgs']
                print('222222', img_list[img_id])

                if hasattr(torch.cuda, 'empty_cache'):
                    torch.cuda.empty_cache()
                    loss_dict_tmp = model(images, targets)
            else:
                raise exception
        # loss_dict = ctpn_model(images, targets)
        # print('1111', loss_dict)
        # print('images', images)
        # print('targets', targets)

        losses_tmp = sum(loss for loss in loss_dict_tmp.values())

        # reduce losses over all GPUs for logging purposes
        loss_dict_reduced_tmp = utils.reduce_dict(loss_dict_tmp)
        losses_reduced_tmp = sum(loss for loss in loss_dict_reduced_tmp.values())

        loss_value_tmp = losses_reduced_tmp.item()
        # print('targets', targets)

        if not math.isfinite(loss_value_tmp):
            targets_ = targets[0]
            img_id = targets_['image_id'].item()
            # print('11111', img_id)
            img_data_dict = data_loader.dataset.__dict__
            img_data_dataset = img_data_dict['dataset']
            img_data_dataset_dict = img_data_dataset.__dict__

            img_list = img_data_dataset_dict['imgs']
            print('222222', img_list[img_id])

            print("Loss is {}, stopping training".format(loss_value_tmp))
            print(loss_dict_reduced_tmp)
            # sys.exit(1)
            continue
        else:
            losses = losses_tmp
            losses_reduced = losses_reduced_tmp
            loss_dict_reduced = loss_dict_reduced_tmp
            loss_value = loss_value_tmp

        optimizer.zero_grad()
        losses.backward()
        optimizer.step()

        if lr_scheduler is not None:
            lr_scheduler.step()

        metric_logger.update(loss=losses_reduced, **loss_dict_reduced)
        metric_logger.update(lr=optimizer.param_groups[0]["lr"])


def _get_iou_types(model):
    model_without_ddp = model
    if isinstance(model, torch.nn.parallel.DistributedDataParallel):
        model_without_ddp = model.module
    iou_types = ["bbox"]
    if isinstance(model_without_ddp, torchvision.models.detection.MaskRCNN):
        iou_types.append("segm")
    if isinstance(model_without_ddp, torchvision.models.detection.KeypointRCNN):
        iou_types.append("keypoints")
    return iou_types

# @torch.no_grad()
# def evaluate(model, data_loader, device):
#     n_threads = torch.get_num_threads()
#     # FIXME remove this and make paste_masks_in_image run on the GPU
#     torch.set_num_threads(1)
#     cpu_device = torch.device("cpu")
#     model.eval()
#     metric_logger = utils.MetricLogger(delimiter="  ")
#     header = 'Test:'
#
#     coco = get_coco_api_from_dataset(data_loader.dataset)
#     iou_types = _get_iou_types(model)
#     coco_evaluator = CocoEvaluator(coco, iou_types)
#
#     for image, targets in metric_logger.log_every(data_loader, 100, header):
#         image = list(img.to(device) for img in image)
#         targets = [{k: v.to(device) for k, v in t.items()} for t in targets]
#
#         # torch.cuda.synchronize()
#         model_time = time.time()
#         outputs = model(image)
#
#         outputs = [{k: v.to(cpu_device) for k, v in t.items()} for t in outputs]
#         model_time = time.time() - model_time
#
#         res = {target["image_id"].item(): output for target, output in zip(targets, outputs)}
#         evaluator_time = time.time()
#         coco_evaluator.update(res)
#         evaluator_time = time.time() - evaluator_time
#         metric_logger.update(model_time=model_time, evaluator_time=evaluator_time)
#
#     # gather the stats from all processes
#     metric_logger.synchronize_between_processes()
#     print("Averaged stats:", metric_logger)
#     coco_evaluator.synchronize_between_processes()
#
#     # accumulate predictions from all images
#     coco_evaluator.accumulate()
#     coco_evaluator.summarize()
#     torch.set_num_threads(n_threads)
#     return coco_evaluator
