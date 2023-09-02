"""
Generation of a dataset of images of shirts hanging from a single grasping
point and of shirts over a table.

The steps to creating this image:

1. Load a Blender shirt object and set it to an initial state.
2. Pin a selected random point over the shirt and let the rest of the cloth
fall during some frames.
3. The whole cloth is brought to the horizontal surface and the images for
shirt on the table are rendered (frame 60).
4. The pined point is brought upwards and the image of the shirt hanging is
captured (frame 120).

To run this code from terminal:
    blender -b -P cloth_blender.py

This will generate files in:
    - pdc/logs_proto/shirt_hanging
    - pdc/logs_proto/shirt_table
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

import shirt_generation

COLOR_BLACK = (0, 0, 0, 0)
COLOR_WHITE = (1, 1, 1, 1)
COLOR_GREEN = (0, 1, 0, 1)


@contextmanager
def stdout_redirected(to=os.devnull):
    """ Disable stdout outputs """
    fd = sys.stdout.fileno()

    def _redirect_stdout(to):
        sys.stdout.close()
        os.dup2(to.fileno(), fd)
        sys.stdout = os.fdopen(fd, 'w')

    with os.fdopen(os.dup(fd), 'w') as old_stdout:
        with open(to, 'w') as file:
            _redirect_stdout(to=file)
        try:
            yield
        finally:
            _redirect_stdout(to=old_stdout)


def clear_scene():
    """ Clear existing objects in scene """
    for block in bpy.data.meshes:
        if block.users == 0:
            bpy.data.meshes.remove(block)
    for block in bpy.data.materials:
        if block.users == 0:
            bpy.data.materials.remove(block)
    for block in bpy.data.textures:
        if block.users == 0:
            bpy.data.textures.remove(block)
    for block in bpy.data.images:
        if block.users == 0:
            bpy.data.images.remove(block)
    bpy.ops.object.mode_set(mode='OBJECT')
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()


def make_table():
    """ Create a plain horizontal surface in the scene """
    # Generate table surface
    bpy.ops.mesh.primitive_plane_add(size=7, location=(0, 0, -2.5))
    bpy.ops.object.modifier_add(type='COLLISION')
    bpy.context.object.name = 'Table'
    colorize(bpy.context.object, COLOR_GREEN)
    bpy.context.object.hide_render = True
    return bpy.context.object


def make_cloth(objs_dir=None, obj_name='Cloth'):
    """ Load cloth object and custom the mesh """
    if objs_dir is None:
        bpy.ops.mesh.primitive_plane_add(size=2, location=(0, 0, 0))
        bpy.context.object.name = 'Cloth'
        bpy.ops.object.editmode_toggle()
        bpy.ops.mesh.subdivide(number_cuts=25)  # Tune this number for cloth detail
        bpy.ops.object.editmode_toggle()
    else:
        with stdout_redirected():
            shirt_generation.import_object(objs_dir, obj_name)
    bpy.context.view_layer.objects.active = bpy.data.objects[obj_name]
    bpy.ops.object.modifier_add(type='COLLISION')
    bpy.ops.object.modifier_add(type='CLOTH')
    bpy.context.object.modifiers[
        "Cloth"].collision_settings.use_self_collision = True
    bpy.context.object.modifiers[
        "Cloth"].collision_settings.self_distance_min = 0.002
    bpy.context.object.modifiers["Cloth"].settings.mass = 0.7
    # bpy.context.object.modifiers["Cloth"].settings.quality = 4
    # bpy.context.object.modifiers["Cloth"].settings.bending_model = 'LINEAR'
    bpy.context.object.modifiers["Cloth"].collision_settings.collision_quality = 4
    # bpy.context.object.modifiers["Cloth"].settings.tension_stiffness = 20
    # bpy.context.object.modifiers["Cloth"].settings.shear_stiffness = 15
    # bpy.context.object.modifiers["Cloth"].settings.bending_stiffness = 0.2
    # bpy.context.object.modifiers["Cloth"].settings.tension_damping = 0.1
    # bpy.context.object.modifiers["Cloth"].settings.air_damping = 0.25
    bpy.ops.object.modifier_add(type='SUBSURF')
    bpy.context.object.modifiers["Subdivision"].levels = 2
    bpy.ops.object.modifier_add(type='SOLIDIFY')
    bpy.context.object.modifiers["Solidify"].thickness = 0.005
    return bpy.context.object


def generate_cloth_state(cloth, rot=True, n_pined=1):
    """ Given a cloth object generate a random initial state
    :param cloth: cloth object as a bpy.context.object
    :param rot: whether the shirt's initial orientation should be parallel to
    the table (True) or perpendicular to it (False)
    :param n_pined: number of pined points over the shirt
    """
    if rot:
        cloth.rotation_euler = (pi / 2 * random.choice([-1, 1]), random.randrange(0, 2) * pi, 0)
    depsgraph = bpy.context.evaluated_depsgraph_get()
    cloth_rotated = cloth.evaluated_get(depsgraph)
    if 'Pinned' in cloth.vertex_groups:
        cloth.vertex_groups.remove(cloth.vertex_groups['Pinned'])
    pinned_group = cloth.vertex_groups.new(name='Pinned')
    n_points = 0
    while n_points < n_pined:
        idx = random.randrange(len(cloth.data.vertices))
        x, y, z = cloth_rotated.matrix_world @ cloth_rotated.data.vertices[
            idx].co
        if z > 0.15:
            pinned_group.add([idx], 1.0, 'ADD')
            n_points += 1
            cloth.location.x -= x
            cloth.location.y -= y
            cloth.location.z -= z
    cloth.modifiers["Cloth"].settings.vertex_group_mass = 'Pinned'

    cloth.keyframe_insert(data_path="location", frame=35)
    cloth.location[2] = -2.5
    cloth.keyframe_insert(data_path="location", frame=55)
    cloth.keyframe_insert(data_path="location", frame=70)
    cloth.location[2] += 2.3
    cloth.keyframe_insert(data_path="location", frame=125)

    # Episode length = 120 frames
    bpy.context.scene.frame_start = 0
    bpy.context.scene.frame_end = 121
    return cloth


def reset_cloth(cloth, init_loc=(0, 0, 0)):
    """ Reset cloth to initial state """
    cloth.modifiers["Cloth"].settings.vertex_group_mass = ''
    cloth.location = init_loc
    bpy.context.scene.frame_set(0)


def set_viewport_shading(mode):
    """ Makes color/texture viewable in viewport """
    areas = bpy.context.workspace.screens[0].areas
    for area in areas:
        for space in area.spaces:
            if space.type == 'VIEW_3D':
                space.shading.type = mode


def pattern(obj, texture_filename):
    """ Add image texture to object """
    mat = bpy.data.materials.new(name="ImageTexture")
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes["Principled BSDF"]
    texImage = mat.node_tree.nodes.new('ShaderNodeTexImage')
    texImage.image = bpy.data.images.load(texture_filename)
    mat.node_tree.links.new(bsdf.inputs['Base Color'],
                            texImage.outputs['Color'])
    obj.data.materials.clear()
    obj.data.materials.append(mat)


def colorize(obj, color):
    """ Add color to object """
    mat = bpy.data.materials.new(name="Color")
    mat.use_nodes = False
    mat.diffuse_color = color
    obj.data.materials.append(mat)
    set_viewport_shading('MATERIAL')


def add_camera_light(n_cameras=1):
    """ Define the lighting conditions and create the camera(s) object(s) """
    # Create light scene
    bpy.ops.object.light_add(type='SUN', radius=1, location=(0, 0, 3.5),
                             rotation=(0, 0, 0))
    bpy.context.object.data.energy = 0.6
    bpy.ops.object.light_add(type='SUN', radius=1, location=(0, 0, -3.5),
                             rotation=(0, math.pi, 0))
    bpy.context.object.data.energy = 0.6
    bpy.ops.object.light_add(type='SUN', radius=1, location=(3.5, 3.5, 0),
                             rotation=(-0.25 * math.pi, 0.5 * math.pi, 0))
    bpy.context.object.data.energy = 0.6
    bpy.ops.object.light_add(type='SUN', radius=1, location=(-3.5, -3.5, 0),
                             rotation=(0.75 * math.pi, 0.5 * math.pi, 0))
    bpy.context.object.data.energy = 0.6
    bpy.ops.object.light_add(type='SUN', radius=1, location=(3.5, -3.5, 0),
                             rotation=(0.25 * math.pi, 0.5 * math.pi, 0))
    bpy.context.object.data.energy = 0.6
    bpy.ops.object.light_add(type='SUN', radius=1, location=(-3.5, 3.5, 0),
                             rotation=(-0.25 * math.pi, -0.5 * math.pi, 0))
    bpy.context.object.data.energy = 0.6

    # Create collection of cameras
    cameras = bpy.data.collections.new("Cameras")
    bpy.context.scene.collection.children.link(cameras)
    for _ in range(n_cameras):
        bpy.ops.object.camera_add()
        cameras.objects.link(bpy.context.object)


def set_up_cameras():
    """ Configure cameras so that they point to a target point at (0, 0, -1.45) """
    target = bpy.data.objects.new("Empty", None)
    target.location = (0, 0, -1.45)

    for _, cam in enumerate(bpy.data.collections['Cameras'].all_objects):
        pi = math.pi
        theta = random.random() * 2 * pi
        # phi = (random.random()*0.15 + 0.35) * pi
        phi = 0.45 * pi
        radius = 5.1
        x, y, z = radius * np.array([
            math.cos(theta) * math.sin(phi),
            math.sin(theta) * math.sin(phi),
            math.cos(phi)
        ])
        cam.location = (x, y, z)
        cam_constraint = cam.constraints.new(type='TRACK_TO')
        cam_constraint.target = target
        cam_constraint.track_axis = 'TRACK_NEGATIVE_Z'
        cam_constraint.up_axis = 'UP_Y'


def render_depth_rgb_multicamera(filenames, episode):
    """ Renders depth and rgb images using all cameras in the scene """
    scene = bpy.context.scene
    scene.use_nodes = True
    scene.view_layers["ViewLayer"].use_pass_z = True
    scene.view_layers["ViewLayer"].use_pass_normal = True
    scene.view_layers["ViewLayer"].use_pass_diffuse_color = True
    scene.view_layers["ViewLayer"].use_pass_object_index = True

    nodes = bpy.context.scene.node_tree.nodes
    links = bpy.context.scene.node_tree.links

    # Clear default nodes
    for n in nodes:
        nodes.remove(n)

    # RGB IMAGE VALUES
    # Create input render layer node
    render_layers = nodes.new('CompositorNodeRLayers')
    # Create depth output nodes
    rgb_file_output = nodes.new(type="CompositorNodeOutputFile")
    rgb_file_output.label = 'Image Output'
    rgb_file_output.base_path = ''
    rgb_file_output.file_slots[0].use_node_format = True
    rgb_file_output.format.file_format = 'PNG'
    rgb_file_output.format.color_mode = 'RGB'
    rgb_file_output.format.color_depth = '16'
    links.new(render_layers.outputs['Image'], rgb_file_output.inputs[0])

    # REAL DEPTH VALUES
    # Create depth output nodes
    depth_file_output = nodes.new(type="CompositorNodeOutputFile")
    depth_file_output.label = 'Depth Output'
    depth_file_output.base_path = ''
    depth_file_output.file_slots[0].use_node_format = True
    depth_file_output.format.file_format = 'OPEN_EXR'
    depth_file_output.format.color_mode = 'RGB'
    depth_file_output.format.color_depth = '16'
    # Create node map
    links.new(render_layers.outputs['Depth'], depth_file_output.inputs[0])

    # DEPTH VISUALIZATION
    # Create depth output nodes
    depth_img_file_output = nodes.new(type="CompositorNodeOutputFile")
    depth_img_file_output.label = 'Depth Image Output'
    depth_img_file_output.base_path = ''
    depth_img_file_output.file_slots[0].use_node_format = True
    depth_img_file_output.format.file_format = 'PNG'
    depth_img_file_output.format.color_mode = 'RGB'
    depth_img_file_output.format.color_depth = '16'
    # Create node map
    normalize = nodes.new(type="CompositorNodeNormalize")
    inversion = nodes.new(type="CompositorNodeInvert")
    links.new(render_layers.outputs['Depth'], normalize.inputs[0])
    links.new(normalize.outputs[0], inversion.inputs[1])
    links.new(inversion.outputs[0], depth_img_file_output.inputs[0])

    for cam_idx, cam in enumerate(bpy.data.collections['Cameras'].all_objects):
        scene.camera = cam
        scene.render.filepath = ''
        rgb_file_output.file_slots[0].path = filenames['rgb'] % (
        cam_idx, episode)
        depth_file_output.file_slots[0].path = filenames['depth'] % (
        cam_idx, episode)
        depth_img_file_output.file_slots[0].path = filenames['depth_img'] % (
        cam_idx, episode)
        bpy.ops.render.render(write_still=True)


def annotate(cloth, episode, frame, mapping, num_annotations, render_size):
    """Gets num_annotations annotations of cloth image at provided frame #, adds to mapping
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
                round(camera_coord.x * render_size[0]),                     # horizontal pixelwise coordinate
                round(render_size[1] - camera_coord.y * render_size[1]),    # vertical pixelwise coordinate
                round(camera_coord.z, 4)                                    # distance point-camera
            ]
            pixels.append(pixel)
        mapping["cam%s-%d-%d" % (k, episode, max(frame - 1, 0))] = pixels
    return mapping


def render(filenames_table, filenames_hanging, engine, episode, cloth,
           render_size, annotations_table=None, annotations_hanging=None,
           num_annotations=0):
    """ Render images for all frames of the given episode. Images for shirt on
    the table are rendered on frame 60 and images for shirt hanging are
    rendered on frame 120.

    :param filenames_table: filename format for images for shirt on the table
    :param filenames_hanging: filename format for images for shirt hanging
    :param engine: Blender engine type ('BLENDER_WORKBENCH' or 'BLENDER_EEVEE')
    :param episode: episode number
    :param cloth: cloth object
    :param render_size: (width, height) of the images
    :param annotations_table: empty annotations dictionary for shirt on the table images
    :param annotations_hanging: empty annotations dictionary for shirt hanging images
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

    for frame in range(1, scene.frame_end + 1):
        if annotations_table is not None:
            if frame == 60:
                render_depth_rgb_multicamera(filenames_table, episode)
                annotations_table = annotate(cloth, episode, frame,
                                             annotations_table,
                                             num_annotations, render_size)
        if annotations_hanging is not None:
            if frame == 120:
                render_depth_rgb_multicamera(filenames_hanging, episode)
                annotations_hanging = annotate(cloth, episode, frame,
                                               annotations_hanging,
                                               num_annotations, render_size)
        scene.frame_set(frame)
    return annotations_table, annotations_hanging


def generate_dataset(num_episodes, filenames_table, filenames_hanging,
                     num_annotations, obj_dir, canonical_shirt_name,
                     random_sized_shirt_name, textures_dir, canonical_texture,
                     random_sizes=False, random_textures=False,
                     render_width=640, render_height=480, n_cameras=1):
    """
    Generate the whole dataset of images of shirts over a table and shirts hanging

    :param num_episodes: total number of episodes rendered
    :param filenames_table: filename format for images for shirt on the table
    :param filenames_hanging: filename format for images for shirt hanging
    :param num_annotations: number of annotations over the mesh tracked
    :param obj_dir: directory of all the .fbx objects generated
    :param canonical_shirt_name: name of the canonical shirt as it appears in obj_dir
    :param random_sized_shirt_name: format of the name of the random shirts
    :param textures_dir: directory of the texture images
    :param canonical_texture: name of the canonical texture image
    :param random_sizes: whether to randomize the shirt sizes or not (randomly
    select a randomized shirt at each episode or always load the canonical one)
    :param random_textures: whether to randomize the shirt texture or not
    (randomly select a texture at each episode or always load the canonical one)
    :param render_width: rendered image width in pixels
    :param render_height: rendered image height in pixels
    :param n_cameras: number of cameras in the scene
    """
    # Remove anything in scene
    scene = bpy.context.scene
    scene.render.resolution_percentage = 100
    render_scale = scene.render.resolution_percentage / 100
    scene.render.resolution_x = render_width
    scene.render.resolution_y = render_height
    render_size = (
        int(scene.render.resolution_x * render_scale),
        int(scene.render.resolution_y * render_scale),
    )
    clear_scene()
    add_camera_light(n_cameras=n_cameras)
    _ = make_table()
    engine = 'BLENDER_EEVEE'

    annot_table = {}
    annot_hanging = {}
    for episode in range(num_episodes):

        obj_name = random_sized_shirt_name % random.randrange(0, 3) if random_sizes else canonical_shirt_name
        cloth = make_cloth(obj_dir, obj_name)

        texture_choice = random.choice(
            os.listdir(textures_dir)) if random_textures else canonical_texture
        pattern(cloth, os.path.join(textures_dir, texture_choice))

        reset_cloth(cloth)
        cloth = generate_cloth_state(cloth, n_pined=1)
        set_up_cameras()
        with stdout_redirected():
            annot_table, annot_hanging = render(filenames_table,
                                                filenames_hanging, engine,
                                                episode, cloth, render_size,
                                                annotations_table=annot_table,
                                                annotations_hanging=annot_hanging,
                                                num_annotations=num_annotations)

        print("Rendered {}/{}".format(episode + 1, num_episodes))
        if num_episodes > 1:
            bpy.ops.object.delete()
    with open(filenames_table['knots'], 'w') as outfile:
        json.dump(annot_table, outfile, sort_keys=True, indent=2)
    with open(filenames_hanging['knots'], 'w') as outfile:
        json.dump(annot_hanging, outfile, sort_keys=True, indent=2)


if __name__ == '__main__':

    scene_table = 'shirt_table'
    scene_hanging = 'shirt_hanging'
    filename_dict = {}
    for scene_name in [scene_table, scene_hanging]:
        data_dir = 'pdc/logs_proto/%s/processed' % scene_name
        images_dir = os.path.join(data_dir, 'images')
        depth_val_dir = os.path.join(data_dir, 'depth_values')

        os.makedirs(images_dir, exist_ok=True)
        os.makedirs(depth_val_dir, exist_ok=True)

        objects_dir = 'generated_shirts'
        textures_dir = os.path.join(os.getcwd(), 'textures')

        # filename format data_type-cam_name-episode-frame
        filename_dict[scene_name] = {
            'rgb': os.path.join(os.getcwd(), images_dir, "rgb-cam%s-%d-#.png"),
            'depth': os.path.join(os.getcwd(), depth_val_dir, "depth-cam%s-%d-#.exr"),
            'depth_img': os.path.join(os.getcwd(), images_dir, "depth-cam%s-%d-#.png"),
            'knots': os.path.join(os.getcwd(), images_dir, "knots_info_pre.json")
        }

    episodes = 1
    n_cameras = 3
    num_annotations = 50

    # Render dataset
    start = time.time()
    generate_dataset(
        num_episodes=episodes,
        filenames_table=filename_dict[scene_table],
        filenames_hanging=filename_dict[scene_hanging],
        num_annotations=num_annotations,
        obj_dir=objects_dir,
        canonical_shirt_name='Basic_shirt',
        random_sized_shirt_name='Random_shirt_%d',
        textures_dir=textures_dir,
        canonical_texture='white.jpg',
        random_sizes=True, random_textures=True,
        render_width=960, render_height=720, n_cameras=n_cameras
    )

    print("Render time with {} cameras: {} seconds".format(n_cameras, time.time() - start))
