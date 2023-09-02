"""
Automated shirt generation using Blender Python API (only shirt creation, no motions).

When opening this file from Blender shirt_generation.blend file, one can create
randomized instances of shirts. These are generated as .fbx elements that can
then be exported to create motions. This is done in two steps:

    1. Creation of the skeleton for the basic shirt with generate_shirt() function.
    2. Creation of randomized instances of shirt models (saved as .fbx files).

Check the example below.
"""

import bpy
import math
import os
import sys
import random
import bmesh
import pickle


class Selector(object):
    """Handy class to enable easy selection and modification using Blender Python API"""
    
    def __init__(self, selector_type):
        """selector_type in ['VERT', 'EDGE', 'FACE']"""
        self.selector_type = selector_type

    def __enter__(self):
        obj = bpy.context.active_object
        bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.mesh.select_mode(type=self.selector_type)
        bpy.ops.mesh.select_all(action='DESELECT')
        bpy.ops.object.mode_set(mode='OBJECT')
        return obj

    def __exit__(self, exc_type, exc_value, exc_tb):
        bpy.ops.object.mode_set(mode='EDIT')


def context_override():
    """ Auxiliar function for Blender loopcut slide """
    area = next(a for a in bpy.context.window.screen.areas if a.type == 'VIEW_3D')
    region = next(r for r in area.regions if r.type == 'WINDOW')
    return {'area': area, 'region': region}


def are_close(x, y, thresh=0.05):
    return abs(x - y) < thresh


def clear_scene():
    """ Remove all objects in the scene except for the Body """
    try:
        bpy.ops.object.mode_set(mode='OBJECT')
    except:
        pass
    for obj in bpy.data.collections['Collection'].all_objects:
        if obj.name not in ['Body', 'Armature']:
            obj.select_set(True)
            bpy.ops.object.delete()


def generate_shirt(params, object_name=None):
    """ Generation of the shirt skeleton """
    # Initial cube generation
    params['cube_size'] = 1.5
    params['cube_loc'] = (0, 0, 0)
    params['cube_scale'] = (1, 1, 1.4)
    params['body_width'] = params['cube_size'] * params['cube_scale'][0] * 0.5
    params['body_height'] = params['cube_size'] * params['cube_scale'][2]
    bpy.ops.mesh.primitive_cube_add(size=params['cube_size'],
                                    location=params['cube_loc'],
                                    scale=params['cube_scale'])
    if object_name:
        bpy.data.objects['Cube'].name = object_name
    else:
        bpy.data.objects['Cube'].name = 'Shirt'
    bpy.ops.object.mode_set(mode='EDIT')

    # Body shape tunning
    loopcut_translation = 0.1
    waist_edge_translation = -0.1
    params['body_heights'] = [
        params['body_height'] / 3 - 2 * loopcut_translation / 3,
        params['body_height'] / 3 - waist_edge_translation,
        params[
            'body_height'] / 3 + 2 * loopcut_translation / 3 + waist_edge_translation,
    ]
    bpy.ops.mesh.loopcut_slide(context_override(),
                               MESH_OT_loopcut={"number_cuts": 2,
                                                "object_index": 0,
                                                "edge_index": 6},
                               TRANSFORM_OT_edge_slide={
                                   "value": -loopcut_translation})
    with Selector('EDGE') as obj:
        for i in [20, 22, 24, 26]:
            obj.data.edges[i].select = True
    bpy.ops.transform.translate(value=(0, 0, waist_edge_translation))

    # Remove left half
    bpy.ops.mesh.loopcut_slide(context_override(),
                               MESH_OT_loopcut={"number_cuts": 1,
                                                "object_index": 0,
                                                "edge_index": 21})
    with Selector('VERT') as obj:
        for v in obj.data.vertices:
            x, y, z = v.co.to_tuple()
            if x < 0:
                v.select = True
    bpy.ops.mesh.delete(type='VERT')

    # Sleeve creation
    with Selector('VERT') as obj:
        for v in obj.data.vertices:
            x, y, z = v.co.to_tuple()
            if are_close(x, params['body_width']) and z > 0:
                v.select = True
    bpy.ops.mesh.extrude_region_move(
        TRANSFORM_OT_translate={"value": (-1e-9, -0, -0)})
    bpy.ops.transform.rotate(value=-params['sleeve_angle'], orient_axis='Y')
    bpy.ops.transform.translate(value=params['sleeve_delta'])
    params['sleeve_max_length'] = 1.4
    bpy.ops.mesh.extrude_region_move(
        TRANSFORM_OT_translate={
            "value": (0, 0, params['sleeve_max_length']),
            "orient_matrix": ((math.sin(params['sleeve_angle']), 0,
                               math.cos(params['sleeve_angle'])),
                              (0, -1, 0),
                              (math.cos(params['sleeve_angle']), 0,
                               -math.sin(params['sleeve_angle'])))})

    # Helper loopcuts
    bpy.ops.mesh.loopcut_slide(context_override(),
                               MESH_OT_loopcut={"number_cuts": 1,
                                                "object_index": 0,
                                                "edge_index": 13})
    bpy.ops.mesh.loopcut_slide(context_override(),
                               MESH_OT_loopcut={"number_cuts": 1,
                                                "object_index": 0,
                                                "edge_index": 22})

    #    with selector('VERT') as obj:
    #        for v in obj.data.vertices:
    #            x, y, z = v.co.to_tuple()
    #            if are_close(z, params['body_height']*0.5) or are_close(z, -params['body_height']*0.5):
    #                v.select = True
    #    bpy.ops.mesh.delete(type='ONLY_FACE')
    #    with selector('VERT') as obj:
    #        for v in obj.data.vertices:
    #            x, y, z = v.co.to_tuple()
    #            if are_close(z, params['body_height']*0.2):
    #                v.select = True
    #    bpy.ops.mesh.delete(type='ONLY_FACE')
    #    with selector('VERT') as obj:
    #        for v in obj.data.vertices:
    #            x, y, z = v.co.to_tuple()
    #            if are_close(x, params['body_width']):
    #                v.select = True
    #    bpy.ops.mesh.delete(type='ONLY_FACE')

    # Delete sleeve and body holes
    with Selector('VERT') as obj:
        for v in obj.data.vertices:
            x, y, z = v.co.to_tuple()
            if are_close(z, -params['body_height'] * 0.5):
                v.select = True
            if are_close(z, params['body_height'] * 0.5) and x <= params[
                'body_width'] * 0.5:
                v.select = True
            sleeve_x = params['sleeve_max_length'] * math.cos(
                params['sleeve_angle'])
            sleeve_z = params['sleeve_max_length'] * math.sin(
                params['sleeve_angle'])
            delta_x = params['body_width'] + sleeve_x + params['sleeve_delta'][
                0]
            delta_z = params['body_height'] / 3 - 1 / 8 - sleeve_z
            if are_close(x - delta_x,
                         (z - delta_z) * math.tan(params['sleeve_angle'])):
                v.select = True
    bpy.ops.mesh.delete(type='ONLY_FACE')

    # Create sleeve end
    #    with selector('VERT') as obj:
    #        for v in obj.data.vertices:
    #            x, y, z = v.co.to_tuple()
    #            sleeve_x = params['sleeve_max_length'] * math.cos(params['sleeve_angle'])
    #            sleeve_z = params['sleeve_max_length'] * math.sin(params['sleeve_angle'])
    #            delta_x = params['body_width'] + sleeve_x + params['sleeve_delta'][0]
    #            delta_z = params['body_height'] / 3 - 1 / 8 - sleeve_z
    #            if are_close(x-delta_x, (z-delta_z) * math.tan(params['sleeve_angle'])):
    #                v.select = True
    #    bpy.ops.mesh.extrude_region_move(MESH_OT_extrude_region={"use_normal_flip":False, "use_dissolve_ortho_edges":False, "mirror":False}, TRANSFORM_OT_translate={"value":(params["handgrip_width"], 0, 0), "orient_axis_ortho":'X', "orient_type":'GLOBAL', "orient_matrix":((1, 0, 0), (0, 1, 0), (0, 0, 1)), "orient_matrix_type":'GLOBAL', "constraint_axis":(True, False, False), "mirror":False, "use_proportional_edit":False, "proportional_edit_falloff":'SMOOTH', "proportional_size":1, "use_proportional_connected":False, "use_proportional_projected":False, "snap":True, "snap_elements":{'INCREMENT'}, "use_snap_project":False, "snap_target":'CLOSEST', "use_snap_self":False, "use_snap_edit":False, "use_snap_nonedit":False, "use_snap_selectable":False, "snap_point":(0, 0, 0), "snap_align":False, "snap_normal":(0, 0, 0), "gpencil_strokes":False, "cursor_transform":False, "texture_space":False, "remove_on_cancel":False, "view2d_edge_pan":False, "release_confirm":False, "use_accurate":False, "use_automerge_and_split":False})
    #    bpy.ops.mesh.extrude_region_move(MESH_OT_extrude_region={"use_normal_flip":False, "use_dissolve_ortho_edges":False, "mirror":False}, TRANSFORM_OT_translate={"value":(-params["handgrip_width"], -0, -0), "orient_axis_ortho":'X', "orient_type":'GLOBAL', "orient_matrix":((1, 0, 0), (0, 1, 0), (0, 0, 1)), "orient_matrix_type":'GLOBAL', "constraint_axis":(True, False, False), "mirror":False, "use_proportional_edit":False, "proportional_edit_falloff":'SMOOTH', "proportional_size":1, "use_proportional_connected":False, "use_proportional_projected":False, "snap":True, "snap_elements":{'INCREMENT'}, "use_snap_project":False, "snap_target":'CLOSEST', "use_snap_self":False, "use_snap_edit":False, "use_snap_nonedit":False, "use_snap_selectable":False, "snap_point":(0, 0, 0), "snap_align":False, "snap_normal":(0, 0, 0), "gpencil_strokes":False, "cursor_transform":False, "texture_space":False, "remove_on_cancel":False, "view2d_edge_pan":False, "release_confirm":False, "use_accurate":False, "use_automerge_and_split":False})
    #    with selector('VERT') as obj:
    #        for v in obj.data.vertices:
    #            x, y, z = v.co.to_tuple()
    #            sleeve_x = params['sleeve_max_length'] * math.cos(params['sleeve_angle'])
    #            sleeve_z = params['sleeve_max_length'] * math.sin(params['sleeve_angle'])
    #            delta_x = params['body_width'] + sleeve_x + params['sleeve_delta'][0]
    #            delta_z = params['body_height'] / 3 - 1 / 8 - sleeve_z
    #            if are_close(x-delta_x, (z-delta_z) * math.tan(params['sleeve_angle'])) and are_close(y,0):
    #                v.select = True
    #            if are_close(x-delta_x, (z-delta_z) * math.tan(params['sleeve_angle']) +params['handgrip_width']) and are_close(y,0):
    #                v.select = True
    #    bpy.ops.mesh.delete(type='ONLY_FACE')

    # Create body end
    #    with selector('VERT') as obj:
    #        for v in obj.data.vertices:
    #            x, y, z = v.co.to_tuple()
    #            if are_close(z, -params['body_height'] * 0.5):
    #                v.select = True
    #    bpy.ops.mesh.extrude_region_move(MESH_OT_extrude_region={"use_normal_flip":False, "use_dissolve_ortho_edges":False, "mirror":False}, TRANSFORM_OT_translate={"value":(-0, -0, -params["handgrip_width"]*2), "orient_axis_ortho":'X', "orient_type":'GLOBAL', "orient_matrix":((1, 0, 0), (0, 1, 0), (0, 0, 1)), "orient_matrix_type":'GLOBAL', "constraint_axis":(False, False, True), "mirror":False, "use_proportional_edit":False, "proportional_edit_falloff":'SMOOTH', "proportional_size":1, "use_proportional_connected":False, "use_proportional_projected":False, "snap":True, "snap_elements":{'INCREMENT'}, "use_snap_project":False, "snap_target":'CLOSEST', "use_snap_self":False, "use_snap_edit":False, "use_snap_nonedit":False, "use_snap_selectable":False, "snap_point":(0, 0, 0), "snap_align":False, "snap_normal":(0, 0, 0), "gpencil_strokes":False, "cursor_transform":False, "texture_space":False, "remove_on_cancel":False, "view2d_edge_pan":False, "release_confirm":False, "use_accurate":False, "use_automerge_and_split":False})
    #    bpy.ops.mesh.extrude_region_move(MESH_OT_extrude_region={"use_normal_flip":False, "use_dissolve_ortho_edges":False, "mirror":False}, TRANSFORM_OT_translate={"value":(0, 0, params["handgrip_width"]*2), "orient_axis_ortho":'X', "orient_type":'GLOBAL', "orient_matrix":((1, 0, 0), (0, 1, 0), (0, 0, 1)), "orient_matrix_type":'GLOBAL', "constraint_axis":(False, False, True), "mirror":False, "use_proportional_edit":False, "proportional_edit_falloff":'SMOOTH', "proportional_size":1, "use_proportional_connected":False, "use_proportional_projected":False, "snap":True, "snap_elements":{'INCREMENT'}, "use_snap_project":False, "snap_target":'CLOSEST', "use_snap_self":False, "use_snap_edit":False, "use_snap_nonedit":False, "use_snap_selectable":False, "snap_point":(0, 0, 0), "snap_align":False, "snap_normal":(0, 0, 0), "gpencil_strokes":False, "cursor_transform":False, "texture_space":False, "remove_on_cancel":False, "view2d_edge_pan":False, "release_confirm":False, "use_accurate":False, "use_automerge_and_split":False})
    #    with selector('VERT') as obj:
    #        for v in obj.data.vertices:
    #            x, y, z = v.co.to_tuple()
    #            sleeve_x = params['sleeve_max_length'] * math.cos(params['sleeve_angle'])
    #            sleeve_z = params['sleeve_max_length'] * math.sin(params['sleeve_angle'])
    #            delta_x = params['body_width'] + sleeve_x + params['sleeve_delta'][0]
    #            delta_z = params['body_height'] / 3 - 1 / 8 - sleeve_z
    #            if are_close(z, -params['body_height'] * 0.5) and are_close(y, 0):
    #                v.select = True
    #            if are_close(z, -params['body_height'] * 0.5) and are_close(x, params['body_width']*0.5):
    #                v.select = True
    #            if are_close(z, -params['body_height'] * 0.5 -params['handgrip_width']) and are_close(y, 0):
    #                v.select = True
    #            if are_close(z, -params['body_height'] * 0.5 -params['handgrip_width']) and are_close(x, params['body_width']*0.5):
    #                v.select = True
    #    bpy.ops.mesh.delete(type='ONLY_FACE')
    #    with selector('VERT') as obj:
    #        for v in obj.data.vertices:
    #            x, y, z = v.co.to_tuple()
    #            if are_close(x, 0):
    #                v.select = True
    #    bpy.ops.mesh.delete(type='ONLY_FACE')

    # Adjust neck
    with Selector('VERT') as obj:
        for v in obj.data.vertices:
            x, y, z = v.co.to_tuple()
            if are_close(z, params['body_height'] * 0.5) and \
                    are_close(x, params['body_width'] * 0.5) and \
                    are_close(y, -params['cube_size'] * params['cube_scale'][
                        1] * 0.5):
                v.select = True
    bpy.ops.transform.translate(value=(-0.12, 0.18, -0.15))

#    with selector('VERT') as obj:
#        for v in obj.data.vertices:
#            x, y, z = v.co.to_tuple()
#            if z > params['body_height']*0.4 and x < params['body_width']*0.6:
#                v.select = True
#    bpy.ops.mesh.extrude_region_move(MESH_OT_extrude_region={"use_normal_flip":False, "use_dissolve_ortho_edges":False, "mirror":False}, TRANSFORM_OT_translate={"value":(0, 0, 0.001), "orient_axis_ortho":'X', "orient_type":'GLOBAL', "orient_matrix":((1, 0, 0), (0, 1, 0), (0, 0, 1)), "orient_matrix_type":'GLOBAL', "constraint_axis":(False, False, True), "mirror":False, "use_proportional_edit":False, "proportional_edit_falloff":'SMOOTH', "proportional_size":1, "use_proportional_connected":False, "use_proportional_projected":False, "snap":True, "snap_elements":{'INCREMENT'}, "use_snap_project":False, "snap_target":'CLOSEST', "use_snap_self":False, "use_snap_edit":False, "use_snap_nonedit":False, "use_snap_selectable":False, "snap_point":(0, 0, 0), "snap_align":False, "snap_normal":(0, 0, 0), "gpencil_strokes":False, "cursor_transform":False, "texture_space":False, "remove_on_cancel":False, "view2d_edge_pan":False, "release_confirm":False, "use_accurate":False, "use_automerge_and_split":False})
#    bpy.ops.transform.resize(value=(1.5, 1.5, 1), orient_type='GLOBAL', orient_matrix=((1, 0, 0), (0, 1, 0), (0, 0, 1)), orient_matrix_type='GLOBAL', mirror=True, use_proportional_edit=False, proportional_edit_falloff='SMOOTH', proportional_size=1, use_proportional_connected=False, use_proportional_projected=False, snap=False, snap_elements={'INCREMENT'}, use_snap_project=False, snap_target='CLOSEST', use_snap_self=False, use_snap_edit=False, use_snap_nonedit=False, use_snap_selectable=False)
#    with selector('VERT') as obj:
#        for v in obj.data.vertices:
#            x, y, z = v.co.to_tuple()
#            if z > params['body_height']*0.4 and are_close(x,0):
#                v.select = True
#    bpy.ops.mesh.delete(type='ONLY_FACE')
#    with selector('VERT') as obj:
#        for v in obj.data.vertices:
#            x, y, z = v.co.to_tuple()
#            if z > params['body_height']*0.4 and y < -params['body_width']*0.5 and x < params['body_width']:
#                v.select = True
#    bpy.ops.mesh.delete(type='ONLY_FACE')


def parametrize_shirt(params):
    """ Parametrize the shirt once the skeleton has been loaded using the
    params object. The parametrization will be applied to the selected object
    in the scene. """

    bpy.ops.object.mode_set(mode='EDIT')

    #    with selector('VERT') as obj:
    #        for v in obj.data.vertices:
    #            x, y, z = v.co.to_tuple()
    #            if are_close(x, params['body_width'] + params['sleeve_delta'][0]) and z > 0:
    #                v.select = True
    #            if are_close(x, params['body_width']) and z > 0:
    #                v.select = True
    #    bpy.ops.mesh.delete(type='ONLY_FACE')

    # Parametrize neck
    with Selector('VERT') as obj:
        for v in obj.data.vertices:
            x, y, z = v.co.to_tuple()
            if are_close(z, params['body_height'] / 2) and are_close(x,
                                                                     0) and are_close(
                    y, -params['cube_size'] * params['cube_scale'][1] * 0.5):
                v.select = True
    neck_low = 0.15 + params['neck_low'] * 0.65
    bpy.ops.transform.translate(value=(0, 0.18, -neck_low))

    # Parametrize body length
    with Selector('VERT') as obj:
        for v in obj.data.vertices:
            x, y, z = v.co.to_tuple()
            if are_close(-z,
                         params['body_height'] / 2 - params['body_heights'][
                             2] - -params['handgrip_width']) and x < params[
                'body_width'] + 0.01:
                v.select = True
    bpy.ops.transform.translate(value=(
    0, 0, (params['body_heights'][1]) * (0.4 - 0.6 * params['torso_length'])))

    with Selector('VERT') as obj:
        for v in obj.data.vertices:
            x, y, z = v.co.to_tuple()
            if are_close(z, -params['body_height'] / 2) and x < params[
                'body_width'] + 0.01:
                v.select = True
            if are_close(z, -params['body_height'] / 2 - params[
                'handgrip_width']) and x < params['body_width'] + 0.01:
                v.select = True
    bpy.ops.transform.translate(value=(0, 0, (
                params['body_heights'][1] + params['body_heights'][2]) * (
                                                   0.4 - 0.6 * params[
                                               'torso_length'])))

    # Parametrize sleeve length
    with Selector('VERT') as obj:
        for v in obj.data.vertices:
            x, y, z = v.co.to_tuple()
            if are_close(x, params['body_width'] + params['sleeve_delta'][0] +
                            params['sleeve_max_length'] + params[
                                'handgrip_width']):
                v.select = True
            if are_close(x, params['body_width'] + params['sleeve_delta'][0] +
                            params['sleeve_max_length']):
                v.select = True
    sleeve_length = 1 * (params['sleeve_length'] - 1.1)
    bpy.ops.transform.translate(value=(sleeve_length, 0, 0))

    # Collar creation
    if params['collar']:
        with Selector('VERT') as obj:
            for v in obj.data.vertices:
                x, y, z = v.co.to_tuple()
                if are_close(z, params['body_height'] * 0.5) and x < params[
                    'body_width'] * 0.6:
                    v.select = True
        bpy.ops.mesh.extrude_region_move(
            TRANSFORM_OT_translate={"value": (0, 0, 0.1)})

        with Selector('VERT') as obj:
            for v in obj.data.vertices:
                x, y, z = v.co.to_tuple()
                if z > params['body_height'] * 0.5 and y < -0.1 and are_close(
                        x, 0):
                    v.select = True
        bpy.ops.mesh.delete(type='VERT')

        with Selector('VERT') as obj:
            for v in obj.data.vertices:
                x, y, z = v.co.to_tuple()
                if z > params['body_height'] * 0.5 and 0.3 < x < 0.5:
                    v.select = True
        bpy.ops.mesh.extrude_region_move(
            TRANSFORM_OT_translate={"value": (0.055, 0, -0.035)})

        with Selector('VERT') as obj:
            for v in obj.data.vertices:
                x, y, z = v.co.to_tuple()
                if z > params['body_height'] * 0.5 and y > 0:
                    v.select = True
        bpy.ops.mesh.extrude_region_move(
            TRANSFORM_OT_translate={"value": (0, 0.055, -0.07)})

        with Selector('VERT') as obj:
            for v in obj.data.vertices:
                x, y, z = v.co.to_tuple()
                if z > params['body_height'] * 0.5 and y < -0.1:
                    v.select = True
        bpy.ops.transform.translate(value=(-0, 0.15, -0.1))

    # Add modifiers
    bpy.ops.object.modifier_add(type='MIRROR')
    bpy.ops.object.modifier_add(type='SHRINKWRAP')
    bpy.context.object.modifiers["Shrinkwrap"].target = bpy.data.objects[
        "Body"]
    bpy.context.object.modifiers["Shrinkwrap"].offset = 2  # tuneable parameter

    bpy.ops.object.modifier_add(type='COLLISION')
    bpy.ops.object.modifier_add(type='CLOTH')
    bpy.context.object.modifiers["Cloth"].settings.use_sewing_springs = True
    bpy.context.object.modifiers["Cloth"].settings.sewing_force_max = 14
    bpy.ops.object.modifier_add(type='SUBSURF')
    bpy.context.object.modifiers["Subdivision"].levels = params['subdivisions']
    bpy.ops.object.modifier_add(type='SOLIDIFY')
    bpy.context.object.modifiers["Solidify"].thickness = 0.01
    bpy.data.objects["Body"].hide_set(True)


def save_params(params, export_dir, obj_name='Cloth'):
    obj_filename = os.path.join(export_dir, obj_name + 'params.pkl')
    with open(obj_filename, 'wb') as f:
        pickle.dump(params, f)


def load_params(export_dir, obj_name='Cloth'):
    obj_filename = os.path.join(export_dir, obj_name + 'params.pkl')
    with open(obj_filename, 'rb') as f:
        params = pickle.load(f)
    return params


def export_object(export_dir, obj_name='Cloth'):
    """ Export .fbx object """
    obj_filename = os.path.join(export_dir, obj_name + '.fbx')
    bpy.data.objects[obj_name].select_set(True)
    bpy.ops.export_scene.fbx(filepath=obj_filename, use_selection=True)


def import_object(import_dir, obj_name, assigned_name=None):
    """ Import .fbx object """
    obj_file = os.path.join(import_dir, obj_name + '.fbx')
    bpy.ops.import_scene.fbx(filepath=obj_file)
    obj = bpy.context.selected_objects[0]
    if assigned_name is None:
        assigned_name = obj_name
    obj.name = assigned_name
    return obj


if __name__ == '__main__':

    # Create a skeleton model for the shirt
    clear_scene()

    model_name = 'Model_Shirt'
    OBJS_DIR = os.path.join(os.getcwd(), 'generated_shirts')
    os.makedirs(OBJS_DIR, exist_ok=True)
    shirt_params = {
        "sleeve_angle": 0,
        "sleeve_delta": (0.1, 0, 0),
        "subdivisions": 2,
        "handgrip_width": 0.2
    }
    generate_shirt(shirt_params, model_name)
    export_object(OBJS_DIR, model_name)

    # Load the model skeleton and render a basic shirt
    clear_scene()

    shirt_name = 'Basic_Shirt'
    shirt_params["collar"] = False
    shirt_params["sleeve_length"] = 1
    shirt_params["neck_low"] = 0
    shirt_params["torso_length"] = 0.8

    obj = import_object(OBJS_DIR, model_name, shirt_name)
    bpy.context.view_layer.objects.active = obj
    parametrize_shirt(shirt_params)
    export_object(OBJS_DIR, shirt_name)

    # Render random shirts
    for i in range(100):
        clear_scene()
        shirt_name = 'Random_shirt_%d' % i

        shirt_params["collar"] = False
        shirt_params["sleeve_length"] = random.random()
        shirt_params["neck_low"] = 0
        shirt_params["torso_length"] = 0.8

        obj = import_object(OBJS_DIR, model_name, shirt_name)
        bpy.context.view_layer.objects.active = obj
        parametrize_shirt(shirt_params)
        export_object(OBJS_DIR, shirt_name)
