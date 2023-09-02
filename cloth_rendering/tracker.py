"""
Helper functions to visualize annotated points over the images.
"""

import cv2
import numpy as np
import json
import os
import random

os.environ["OPENCV_IO_ENABLE_OPENEXR"] = "1"


def point_in_cam(x, y, img_width=640, img_height=480):
    """Check if a point is within the scope of the camera"""
    if x < 0 or x >= img_width or y < 0 or y >= img_height:
        return False
    return True


def show_all_annotations(rgb_filename, img_index, map, output_dir):
    """Draw all the annotated points over an image"""
    img = cv2.imread(rgb_filename % img_index).copy()
    for p in map[img_index]:
        if np.all(i == -1 for i in p):
            pass
        x, y, _ = p
        img = cv2.circle(img, (x, y), 1, (255, 0, 0), -1)

    output_dir = os.path.join(output_dir, 'annotated')
    output_filename = os.path.join(output_dir,
                                   'annotations-%s.png' % img_index)
    os.makedirs(output_dir, exist_ok=True)
    cv2.imwrite(output_filename, img)
    print('Annotations saved at {}'.format(output_filename))


def compare_depths(depth_filename, img_index, map, point_idx=50):
    """Compare the depth and the distance to camera of a given point"""
    depth = cv2.imread(depth_filename % img_index,
                       cv2.IMREAD_ANYCOLOR | cv2.IMREAD_ANYDEPTH).copy()
    x, y, z = map[img_index][point_idx]

    if not point_in_cam(x, y):
        print("Point out of camera scope. Cannot compare depths.")
        return

    print('Image %s' % img_index)
    print(" - real depth:  ", z)
    print(" - image depth: ", depth[y, x][0])
    print()


def track_a_point(rgb_filename, img_index, map, output_dir, point_idxs):
    """Given different perspectives of a same scene, paint a set of points
    across all of them"""
    rgb = cv2.imread(rgb_filename % img_index).copy()
    colors = [(255, 0, 0), (0, 255, 0), (0, 0, 255), (0, 0, 0)]
    for point_idx, color in zip(point_idxs, colors):
        x, y, _ = map[img_index][point_idx]
        rgb = cv2.circle(rgb, (x, y), 1, color, 2)
        # rgb = cv2.circle(rgb, (640-x,y), 1, (0,0,255), 2)

    output_dir = os.path.join(output_dir, 'tracking_tests')
    output_filename = os.path.join(output_dir,
                                   'track_point-%s.png' % img_index)
    os.makedirs(output_dir, exist_ok=True)
    cv2.imwrite(output_filename, rgb)
    print('Tracking point image saved at {}'.format(output_filename))


if __name__ == '__main__':

    for scene_name in ['shirt_canonical']:
        data_dir = 'pdc/logs_proto/%s/processed' % scene_name
        rgb_filename = os.path.join(os.getcwd(), data_dir, 'images/rgb-%s.png')
        depth_filename = os.path.join(os.getcwd(), data_dir,
                                      'depth_values/depth-%s.exr')

        with open(os.path.join(data_dir, 'images',
                               'knots_info.json')) as json_file:
            knots = json.load(json_file)
        point_nums = [500]

        for i in range(1):
            img_index_plain = 'cam%d-0-0' % i
            show_all_annotations(rgb_filename, img_index_plain, knots,
                                 data_dir)

        # counter = 0
        # for img_index in knots:
        #     track_a_point(rgb_filename, img_index, knots, data_dir, point_idxs=point_nums)
        #     # compare_depths(depth_filename, img_index, knots, point_idx=point_num)
        #     print()
        #     counter += 1
        #     if counter > 10:
        #         quit()
