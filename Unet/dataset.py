# -*- coding:utf-8 -*-
# @author :adolf
import os
import random

import numpy as np
import torch
from PIL import Image

from torch.utils.data import Dataset
import math
from transforms import get_transforms
import cv2

from utils import pad_sample


class UNetSegmentationDataset(Dataset):
    in_channels = 3
    out_channels = 1

    def __init__(
            self,
            images_dir,
            image_size=256,
            transform=None,
            random_sampling=True,
            subset="train",
            is_resize=True,
            image_short_side=736,
            is_padding=False
    ):
        self.images_dir = images_dir
        self.transform = transform
        self.image_size = image_size
        self.random_sampling = random_sampling
        self.is_resize = is_resize
        self.image_short_side = image_short_side
        self.is_padding = is_padding

        assert subset in ["all", "train", "validation"]

        self.volumes = {}
        self.masks = {}

        print("begining")

        img_list = os.listdir(os.path.join(self.images_dir, "masks"))

        # img_list = img_list[:2]
        # print(img_list)

        self.patients = sorted(img_list)

        # validation_cases = 1
        validation_cases = int(0.02 * len(self.patients))

        if not subset == "all":
            validation_patients = random.sample(self.patients, k=validation_cases)
            if subset == "validation":
                self.patients = validation_patients
            else:
                self.patients = sorted(
                    list(set(self.patients).difference(validation_patients))
                )
        for img_name in self.patients:
            mask = Image.open(os.path.join(self.images_dir, "masks", img_name))

            img = cv2.imread(os.path.join(self.images_dir, "imgs", img_name))
            img = Image.fromarray(img).convert("RGB")

            if self.is_padding:
                img, mask = pad_sample(img, mask)

            assert img.size == mask.size
            img, mask = self.resize_img(img, mask)

            mask = np.array(mask)
            mask = mask[np.newaxis, ...]
            mask = torch.as_tensor(mask, dtype=torch.uint8)

            if self.transform is not None:
                img, mask = self.transform(img, mask)

            self.volumes[img_name] = img
            self.masks[img_name] = mask

        print('load image is end .....')

    def __len__(self):
        return len(self.patients)

    def __getitem__(self, idx):
        # print(self.volumes)
        img_name = self.patients[idx]

        # v, m = self.volumes[]
        image = self.volumes[img_name]
        mask = self.masks[img_name]
        # print(img_name, image.shape)
        # print('mask', mask.shape)
        return image, mask

    def resize_img(self, img, mask):
        '''输入PIL格式的图片'''
        width, height = img.size
        if self.is_resize:
            if height < width:
                new_height = self.image_short_side
                new_width = int(math.ceil(new_height / height * width / 32) * 32)
            else:
                new_width = self.image_short_side
                new_height = int(math.ceil(new_width / width * height / 32) * 32)
        else:
            if height < width:
                scale = int(height / 32)
                new_image_short_side = scale * 32
                new_height = new_image_short_side
                new_width = int(math.ceil(new_height / height * width / 32) * 32)
            else:
                scale = int(width / 32)
                new_image_short_side = scale * 32
                new_width = new_image_short_side
                new_height = int(math.ceil(new_width / width * height / 32) * 32)
        resized_img = img.resize((new_width, new_height), Image.ANTIALIAS)
        resized_mask = mask.resize((new_width, new_height), Image.ANTIALIAS)
        # print(new_height, new_width)
        return resized_img, resized_mask


if __name__ == '__main__':
    train_datasets = UNetSegmentationDataset(
        images_dir="/data3/adolf/ocr_hup/object_detection/data/gaoda/12_08",
        image_size=256,
        subset="train",
        transform=get_transforms(train=True),
    )
    train_datasets.__getitem__(2)
