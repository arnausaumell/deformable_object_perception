"""
Create masks using depth images
"""

import cv2
import numpy as np
import os
import argparse
import itertools


def create_masks(image_filename, read_dir, save_dir):
    """ Produces a mask of a depth image by thresholding """
    img_depth = cv2.imread(os.path.join(read_dir, image_filename)).copy()

    mask = np.ceil(img_depth / 255.)
    mask_filename = os.path.join(save_dir, 'mask-%s' % image_filename[6:])
    cv2.imwrite(mask_filename, mask)

    visible_mask = mask * 255
    visible_mask_filename = os.path.join(save_dir, 'visible_mask-%s' % image_filename[6:])
    cv2.imwrite(visible_mask_filename, visible_mask)

    img_rgb_filename = os.path.join(read_dir, 'rgb-%s' % image_filename[6:])
    img_rgb = cv2.imread(img_rgb_filename).copy()

    img_masked = img_rgb * mask

    cv2.imwrite(img_rgb_filename, img_masked)


if __name__ == '__main__':

    argParser = argparse.ArgumentParser()
    argParser.add_argument("-s", "--scene_name", help="name of the scene")
    args = argParser.parse_args()

    data_dir = 'pdc/logs_proto/%s/processed' % args.scene_name
    images_dir = os.path.join(os.getcwd(), data_dir, 'images')
    depth_val_dir = os.path.join(os.getcwd(), data_dir, 'depth_values')

    # Masking using depth images
    masks_dir = os.path.join(os.getcwd(), data_dir, 'image_masks')
    os.makedirs(masks_dir, exist_ok=True)
    for filename in os.listdir(images_dir):
        if 'depth' in filename:
            create_masks(filename, images_dir, masks_dir)
            print("Creating mask from %s" % filename)
