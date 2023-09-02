import bpy
import pickle
import os


def rounded_tuple(tup):
    return tuple(round(value, 4) for value in tup)


def write_list(a_list, filename):
    with open(filename, 'wb') as fp:
        pickle.dump(a_list, fp)


def read_list(filename):
    with open(filename, 'rb') as fp:
        n_list = pickle.load(fp)
        return n_list


def load_mesh(data_dir, obj_name='Shirt', new_collection_name=None):
    """ Create a mesh from its data"""
    verts = read_list(os.path.join(data_dir, 'vertices.txt'))
    edges = read_list(os.path.join(data_dir, 'edges.txt'))
    faces = read_list(os.path.join(data_dir, 'faces.txt'))
    rotation = read_list(os.path.join(data_dir, 'rotation.txt'))

    new_mesh = bpy.data.meshes.new('new_mesh')
    new_mesh.from_pydata(verts, edges, faces)
    new_mesh.update()
    new_object = bpy.data.objects.new(obj_name, new_mesh)
    new_object.rotation_euler = rotation

    if new_collection_name:
        new_collection = bpy.data.collections.new(new_collection_name)
        bpy.context.scene.collection.children.link(new_collection)
        bpy.data.collections['Shirt'].objects.link(new_object)
    else:
        bpy.data.collections['Collection'].objects.link(new_object)
    return new_object


def save_mesh(obj, data_dir):
    """Capture data from a obj and save its vertices, edges and faces data"""
    mesh = obj.data

    verts = [rounded_tuple(vertex.co.to_tuple()) for vertex in mesh.vertices]
    faces = [[f for f in face.vertices] for face in mesh.polygons]
    edges = [[e for e in edge.vertices] for edge in mesh.edges]
    rotation = [r for r in obj.rotation_euler]

    write_list(verts, os.path.join(data_dir, 'vertices.txt'))
    write_list(edges, os.path.join(data_dir, 'edges.txt'))
    write_list(faces, os.path.join(data_dir, 'faces.txt'))
    write_list(rotation, os.path.join(data_dir, 'rotation.txt'))

    print('Data saved in {}'.format(data_dir))


if __name__ == '__main__':

    OBJS_DIR = os.path.join(os.getcwd(), 'generated_shirts/objects')
    DATA_DIR = os.path.join(os.getcwd(), 'generated_shirts/data')
    obj_name = 'Shirt'
    OBJ_DIR = os.path.join(DATA_DIR, obj_name)
    os.makedirs(OBJ_DIR, exist_ok=True)

    import_obj = False
    if import_obj:
        obj_file = os.path.join(OBJS_DIR, obj_name + '.obj')
        obj = bpy.ops.import_scene.obj(filepath=obj_file)
        bpy.context.selected_objects[0].name = obj_name
        bpy.ops.object.origin_set(type='GEOMETRY_ORIGIN', center='MEDIAN')

    save_mesh(bpy.data.objects[obj_name], OBJ_DIR)

#    load_mesh(OBJ_DIR, obj_name=obj_name)
