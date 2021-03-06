# -*- coding:utf-8 -*-
import torch
import torch.nn.functional as F
import torch.utils.data as data
import numpy as np
import math
import skimage.io as io
import skimage.transform as transform
from skimage.filters import gaussian
from posenetopt import Options
import cv2

option = Options().parse()
# COCOkeypointloader用来读取原图和根据关键点生成heatmap
# 用来做第一阶段的关键点heatmap回归
class COCOkeypointloader(data.Dataset):
    def __init__(self,coco_train):
        self.coco_train = coco_train
        self.num_of_keypoints = option.num_of_keypoints
        self.images = self.getImage(self.coco_train)
        
    def __len__(self):
        return len(self.images)

    def __getitem__(self,item):
        ann_data = self.images[item]
        input,label = self.get_data(ann_data,self.coco_train)
        return input, label

    def get_data(self,ann_data,coco):
        img_id = ann_data['image_id']
        img_data = coco.loadImgs(img_id)[0]
        # img = io.imread('/path/to/coco'+img_data['filename'])
        img = cv2.imread(option.cocopath + '/' + img_data['file_name'])
        ori_size = img.shape
        img = transform.resize(img,(256,256))
        # resize to (256,256) => a scale of x and y coordinate
        x_scale = 256 / ori_size[0]
        y_scale = 256 / ori_size[1]
        size = img.shape

        # get a mask
        output = np.zeros((size[0],size[1],17))
        kpx = ann_data['keypoints'][0::3]
        kpy = ann_data['keypoints'][1::3]
        kpv = ann_data['keypoints'][2::3]

        for j in range(17):
            if kpv[j] > 0:
                x0 = int(kpx[j] * x_scale)
                y0 = int(kpy[j] * y_scale)

                if x0 >= size[1] and y0 >= size[0]:
                    output[size[0] - 1, size[1] - 1, j] = 1
                elif x0 >= size[1]:
                    output[y0, size[1] - 1, j] = 1
                elif y0 >= size[0]:
                    try:
                        output[size[0] - 1, x0, j] = 1
                    except:
                        output[size[0] - 1, 0, j] = 1
                elif x0 < 0 and y0 < 0:
                    output[0, 0, j] = 1
                elif x0 < 0:
                    output[y0, 0, j] = 1
                elif y0 < 0:
                    output[0, x0, j] = 1
                else:
                    output[y0, x0, j] = 1

        output = gaussian(output, sigma=2, mode='constant', multichannel=True)
        output = np.rollaxis(output,-1,0)
        # convert io.imread()=>(h,w,c) to (c,h,w)
        return np.rollaxis(img,-1,0),output
        
    def getImage(self,coco):
        ids = coco.getAnnIds()
        images = []
        for i in ids:
            image = coco.loadAnns(i)[0]
            if image['iscrowd'] == 0 and image['num_keypoints'] > self.num_of_keypoints:
                images.append(image)
        return images
