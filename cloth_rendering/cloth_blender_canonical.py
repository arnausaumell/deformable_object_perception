"""
Generation of images of the canonical shirt in t-pose with a white texture.

To run this code from terminal:
    blender -b -P cloth_blender_canonical.py

This will generate files in pdc/logs_proto/shirt_canonical
"""

import bpy
import os
import sys
import json
import time
import bpy, bpy_extras
from math import *
from mathutils import *
import random
import numpy as np
from random import sample
import math
from contextlib import contextmanager

sys.path.append(os.getcwd())

import shirt_generation, cloth_blender


COLOR_BLACK = (0, 0, 0, 0)
COLOR_WHITE = (1, 1, 1, 1)
COLOR_GREEN = (0, 0.5, 0.5, 1)


def set_up_cameras_canonical():
    """ Configure cameras around the shirt """
    n_cameras = len(bpy.data.collections['Cameras'].all_objects)
    for i, cam in enumerate(bpy.data.collections['Cameras'].all_objects):
        pi = math.pi
        theta = 1.5 * pi
        phi = 0.5 * pi
        radius = 8
        x, y, z = radius * np.array([
            math.cos(theta) * math.sin(phi),
            math.sin(theta) * math.sin(phi),
            math.cos(phi)
        ])

        cam.location = (x, y, z)
        cam.rotation_euler = (math.pi / 2, i / n_cameras * math.pi, 0)


def annotate_canonical(cloth, episode, frame, mapping, num_annotations,
                       render_size):
    """ Gets num_annotations annotations of cloth image at provided frame #, adds to mapping

    :param cloth: cloth object
    :param episode: episode number
    :param frame: frame number within the episode
    :param mapping: empty dictionary with an entry for each camera-episode-frame view
    :param num_annotations: number of annotations taken over the cloth
    :param render_size: (width, height) of the images
    :return: dictionary with the pixelwise coordinates of the annotated points
    """
    scene = bpy.context.scene
    depsgraph = bpy.context.evaluated_depsgraph_get()
    cloth_deformed = cloth.evaluated_get(depsgraph)
    vertices = [cloth_deformed.matrix_world @ v.co for v in
                list(cloth_deformed.data.vertices)[::num_annotations]]

    for k, camera_obj in enumerate(
            bpy.data.collections['Cameras'].all_objects):
        pixels = []

        for i in range(len(vertices)):
            v = vertices[i]
            camera_coord = bpy_extras.object_utils.world_to_camera_view(scene,
                                                                        camera_obj,
                                                                        v)
            pixel = [
                round(camera_coord.x * render_size[0]),
                round(render_size[1] - camera_coord.y * render_size[1]),
                round(camera_coord.z, 4)
            ]
            pixels.append(pixel)
        mapping["cam%s-%d-%d" % (k, episode, max(frame - 1, 0))] = pixels
    return mapping


def render_canonical(filenames, engine, episode, cloth, render_size,
                     annotations=None, num_annotations=0):
    """ Render images for the given episode.

    :param filenames: filename format for images
    :param engine: Blender engine type ('BLENDER_WORKBENCH' or 'BLENDER_EEVEE')
    :param episode: episode number
    :param cloth: cloth object
    :param render_size: (width, height) of the images
    :param annotations: empty annotations dictionary for shirt images
    :param num_annotations: number of annotations over the mesh tracked
    """
    scene = bpy.context.scene
    scene.render.engine = engine
    scene.view_settings.exposure = 1.3
    if engine == 'BLENDER_WORKBENCH':
        scene.render.image_settings.color_mode = 'RGB'
        scene.display_settings.display_device = 'None'
        scene.sequencer_colorspace_settings.name = 'XYZ'
        scene.render.image_settings.file_format = 'PNG'
    elif engine == "BLENDER_EEVEE":
        scene.eevee.taa_samples = 1
        scene.view_settings.view_transform = 'Raw'
        scene.eevee.taa_render_samples = 1

    frame = 0
    bpy.context.scene.frame_end = 0
    cloth_blender.render_depth_rgb_multicamera(filenames, episode)
    if annotations is not None:
        annotations = annotate_canonical(cloth, episode, frame, annotations,
                                         num_annotations, render_size)
    scene.frame_set(frame)
    return annotations


def generate_dataset_canonical(num_episodes, filenames, num_annotations,
                               obj_file, obj_name='Cloth', texture_filepath='',
                               render_width=640, render_height=480, color=None,
                               n_cameras=1):
    """
    Generate the images of the canonical shirt in t-pose

    :param num_episodes: total number of episodes rendered
    :param filenames: filename format for the canonical images
    :param num_annotations: number of annotations over the mesh tracked
    :param obj_file: filename of the .fbx object for the canonical shirt
    :param obj_name: name of the Blender object
    :param texture_filepath: filepath to the canonical texture image
    select a randomized shirt at each episode or always load the canonical one)
    :param render_width: rendered image width in pixels
    :param render_height: rendered image height in pixels
    :param color: add a custom color to the mesh
    :param n_cameras: number of cameras in the scene
    """
    # Remove anything in scene 
    scene = bpy.context.scene
    scene.render.resolution_percentage = 150
    render_scale = scene.render.resolution_percentage / 100
    scene.render.resolution_x = render_width
    scene.render.resolution_y = render_height
    render_size = (
        int(scene.render.resolution_x * render_scale),
        int(scene.render.resolution_y * render_scale),
    )
    cloth_blender.clear_scene()

    # Make the camera, lights, table, and cloth only ONCE
    cloth_blender.add_camera_light(n_cameras=n_cameras)
    cloth = cloth_blender.make_cloth(obj_file, obj_name)
    engine = 'BLENDER_EEVEE'

    if texture_filepath != '':
        cloth_blender.pattern(cloth, texture_filepath)
    elif color:
        cloth_blender.colorize(cloth, color)

    annot = {}
    cloth_starting_loc = (0, 0, 0)
    for episode in range(num_episodes):
        # Restores cloth to initial state
        cloth_blender.reset_cloth(cloth, init_loc=cloth_starting_loc)
        # Creates a new deformed state
        cloth = cloth_blender.generate_cloth_state(cloth, rot=False, n_pined=0)
        set_up_cameras_canonical()
        with cloth_blender.stdout_redirected():
            # Render, save ground truth
            annot = render_canonical(filenames, engine, episode, cloth,
                                     render_size, annotations=annot,
                                     num_annotations=num_annotations)
        print("Rendered {}/{}".format(episode + 1, num_episodes))
    with open(filenames['knots'], 'w') as outfile:
        json.dump(annot, outfile, sort_keys=True, indent=2)


if __name__ == '__main__':
    scene_name = 'shirt_canonical'
    data_dir = 'pdc/logs_proto/%s/processed' % scene_name
    images_dir = os.path.join(data_dir, 'images')
    depth_val_dir = os.path.join(data_dir, 'depth_values')

    os.makedirs(images_dir, exist_ok=True)
    os.makedirs(depth_val_dir, exist_ok=True)

    obj_name = 'Basic_Shirt'
    objects_dir = 'generated_shirts'
    texture_choice = 'white.jpg'
    texture_filepath = 'textures/' + texture_choice
    texture_filepath = os.path.join(os.getcwd(), texture_filepath)

    # filename format data_type-cam_name-episode-frame
    filename_dict = {
        'rgb': os.path.join(os.getcwd(), images_dir, "rgb-cam%s-%d-#.png"),
        'depth': os.path.join(os.getcwd(), depth_val_dir,
                              "depth-cam%s-%d-#.exr"),
        'depth_img': os.path.join(os.getcwd(), images_dir,
                                  "depth-cam%s-%d-#.png"),
        'knots': os.path.join(os.getcwd(), images_dir, "knots_info_pre.json")
    }

    episodes = 1
    n_cameras = 1
    num_annotations = 50

    # Render dataset
    start = time.time()
    generate_dataset_canonical(episodes, filename_dict, num_annotations,
                               objects_dir, obj_name=obj_name,
                               texture_filepath=texture_filepath, color=None,
                               n_cameras=n_cameras)
    print("Render time with {} cameras: {} seconds".format(n_cameras,
                                                           time.time() - start))
