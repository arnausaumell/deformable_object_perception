"""
Correction of pixelwise annotations

The knots_info_pre.json file gives the pixelwise position of each annotated
point of the mesh (for each of the images). However, some point may be
occluded by the mesh itself.

For each of these annotated points with piel coordinates [x,y] for a given
image, correct_annotations() compares:
    * the depth value at pixel [x,y] (using the depth image)
    * the distance between the camera and the annotated point (using the
    knots_info_pre.json).
If this two values are different, the point seen from the image perspective at
position [x,y] does not coincide with the annotated one.

Moreover, this function also filters out all those points that are out of the
scope of the image (pixel coordinates exceeding the image frame).
"""

import cv2
import json
import os
import argparse

os.environ["OPENCV_IO_ENABLE_OPENEXR"] = "1"


def correct_annotations(old_knots_filename, new_knots_filename,
                        depth_val_filename, depth_threshold=0.15):
    """
    Correct the pixelwise coordinates for all the annotated points by
    filtering out all the occluded and out-of-image-frame points. To filter
    them out, its values in the new knots file are replaced by [-1, -1, -1].

    :param old_knots_filename: filename of the pixelwise annotations before
    correction
    :param new_knots_filename: filename of the pixelwise annotations after
    correction
    :param depth_val_filename: filename format of depth value images
    :param depth_threshold: threshold to compare image depth with annotated
    depth
    """
    with open(old_knots_filename) as f:
        knots = json.load(f)
    print("Knots file read.")

    depth_img = cv2.imread(depth_val_filename % [x for x in knots][0],
                           cv2.IMREAD_ANYCOLOR | cv2.IMREAD_ANYDEPTH).copy()
    img_height, img_width, _ = depth_img.shape
    new_knots = {}
    n_depth = 0
    n_out_of_bounds = 0
    n_points = 0
    for img_index in knots:
        depth_img = cv2.imread(depth_val_filename % img_index,
                               cv2.IMREAD_ANYCOLOR | cv2.IMREAD_ANYDEPTH).copy()
        pixels = []
        n_points += len(knots[img_index])
        for x, y, z in knots[img_index]:
            if x >= img_width or y >= img_height or x < 0 or y < 0:
                # filter pixels out of the image frame
                pixels.append([-1, -1, -1])
                n_out_of_bounds += 1
            elif abs(float(z) - depth_img[y, x][0]) > depth_threshold:
                # compare depths
                pixels.append([-1, -1, -1])
                n_depth += 1
            else:
                pixels.append([x, y, z])
        new_knots[img_index] = pixels

    print("Points deleted by depth mismatch:\t {} %".format(
        round(n_depth / n_points * 100, 2)))
    print("Points deleted by out of borders:\t {} %".format(
        round(n_out_of_bounds / n_points * 100, 2)))
    with open(new_knots_filename, 'w') as outfile:
        json.dump(new_knots, outfile, sort_keys=True, indent=2)
    print("Knots information corrected and saved at %s." % new_knots_filename)


if __name__ == '__main__':
    argParser = argparse.ArgumentParser()
    argParser.add_argument("-s", "--scene_name", help="name of the scene")
    args = argParser.parse_args()

    data_dir = 'pdc/logs_proto/%s/processed' % args.scene_name
    images_dir = os.path.join(data_dir, 'images')
    depth_val_dir = os.path.join(data_dir, 'depth_values')

    # Correct annotations
    correct_annotations(
        old_knots_filename=os.path.join(os.getcwd(), images_dir,
                                        "knots_info_pre.json"),
        new_knots_filename=os.path.join(os.getcwd(), images_dir,
                                        "knots_info.json"),
        depth_val_filename=os.path.join(os.getcwd(), depth_val_dir,
                                        "depth-%s.exr"),
        depth_threshold=0.12)
