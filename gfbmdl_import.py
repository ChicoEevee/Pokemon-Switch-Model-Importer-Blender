# Copyright (c) 2019 Reisyukaku
#
# This program is free software; you can redistribute it and/or modify it
# under the terms and conditions of the GNU General Public License,
# version 2, as published by the Free Software Foundation.
#
# This program is distributed in the hope it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or
# FITNESS FOR A PARTICULAR PURPOSE.  See the GNU General Public License for
# more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import bpy
import mathutils
from mathutils import Matrix
from math import radians

import os.path
import sys
import struct
from enum import IntEnum

from .GFLib.Model.Model import Model

blender_version = bpy.app.version
class BufferFormat(IntEnum):
    Float = 0
    HalfFloat = 1
    Byte = 3
    Short = 5
    BytesAsFloat = 8
    
class WrapMode(IntEnum):
    Repeat = 0
    Clamp = 1
    Mirror = 2
    
class BoneType(IntEnum):
    NoSkinning = 0
    HasSkinning = 1

# #####################################################
# Utils
# #####################################################
def CalcStride(type, cnt):
    ret = 0
    if type == BufferFormat.Float:
        ret = 4 * cnt
    if type == BufferFormat.HalfFloat:
        ret = 2 * cnt
    if type == BufferFormat.Byte:
        ret = cnt
    if type == BufferFormat.Short:
        ret = 2 * cnt
    if type == BufferFormat.BytesAsFloat:
        ret = 1 * cnt
    return ret
    
def GetMatValue(mat, param):
    for v in range(mat.ValuesLength()):
        if mat.Values(v).Name().decode('utf-8') == param:
            return mat.Values(v).Value()
    return None
    
def RotateObj(obj, angle, axis):
    rot_mat = Matrix.Rotation(radians(angle), 4, axis)

    orig_loc, orig_rot, orig_scale = obj.matrix_world.decompose()
    orig_loc_mat = Matrix.Translation(orig_loc)
    orig_rot_mat = orig_rot.to_matrix().to_4x4()
    orig_scale_mat = Matrix.Scale(orig_scale[0],4,(1,0,0)) @ Matrix.Scale(orig_scale[1],4,(0,1,0)) @ Matrix.Scale(orig_scale[2],4,(0,0,1))

    obj.matrix_world = orig_loc_mat @ rot_mat @ orig_rot_mat @ orig_scale_mat 
    
# #####################################################
# Model
# #####################################################
def BuildArmature(mon, filename):
    armature = bpy.data.armatures.new(filename)
    armature_obj = bpy.data.objects.new(armature.name, armature)            
    bpy.context.collection.objects.link(armature_obj)
    armature_obj.select_set(True)
    bpy.context.view_layer.objects.active = armature_obj
    bone_id_map = []
    boneLen = mon.BonesLength()
    print("Total bones: %d" % boneLen)
    bpy.ops.object.mode_set(mode='EDIT')
    global_matrix = (Matrix.Scale(1, 4))
    for i in range(boneLen):
        bone = mon.Bones(i)
        bname = bone.Name().decode("utf-8")
        if bone.RigidCheck():
            print(bone.RigidCheck().Unknown1())
        else:
            bone_id_map.append(bname)
        btype = bone.BoneType()
        transVec = bone.Translation()
        rotVec = bone.Rotation()
        scaleVec = bone.Scale()
        parent = bone.Parent()
        vis = bone.Visible()
        bone_matrix = mathutils.Matrix.LocRotScale(
            (transVec.X(), transVec.Y(), transVec.Z()),
            mathutils.Euler((rotVec.X(), rotVec.Y(), rotVec.Z())),
            (scaleVec.X(), scaleVec.Y(), scaleVec.Z()))
        eb = armature.edit_bones.new(bname)
        eb.head = (0,0,0)
        eb.tail = (0,0,10.)
        eb.matrix = bone_matrix
        eb.use_inherit_rotation = True
        if blender_version[0] == 4:
            eb.inherit_scale = 'NONE'
        else:
            eb.use_inherit_scale = False
        if btype == BoneType.HasSkinning:
            eb.use_deform = True
        if parent >= 0:
            eb.parent = bpy.data.armatures[armature.name].edit_bones[parent]
            eb.matrix = eb.parent.matrix @ bone_matrix
        
    bpy.ops.object.mode_set(mode='OBJECT')
    bpy.ops.object.select_all(action='DESELECT')
    return bone_id_map, armature_obj

def CreateMaterial(material):
    mat = bpy.data.materials.new(name=material.Name().decode("utf-8"))
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    shdr = nodes.get('Principled BSDF')
    out = nodes.get('Material Output')
    img = nodes.new('ShaderNodeTexImage')
    att = nodes.new('ShaderNodeAttribute')
    mix = nodes.new('ShaderNodeMixRGB')
    img.location = (-450, 350)
    att.location = (-450, 165)
    mix.location = (-160, 160)
    att.attribute_name = "Colors"
    links.new(att.outputs[0], mix.inputs[1]) # vert cols -> mix
    links.new(img.outputs[0], mix.inputs[2]) # img cols -> mix
    links.new(mix.outputs[0], shdr.inputs[0]) # mix -> shader
    return mat

def CreateMesh(name, mon, ind, mats, bone_id_map, armature_obj):
    print(bone_id_map)
    attribType = []
    alignStride = []
    totalStride = 0
    mesh = mon.Meshes(ind)

    # Attribute/format lookup
    ATTRIB_TYPES = {
        0: "POSITION",
        1: "NORMAL",
        2: "TANGENT",
        3: "UV1",
        4: "UV2",
        5: "UV3",
        6: "UV4",
        7: "COLOR1",
        8: "COLOR2",
        11: "BONE_IDS",
        12: "WEIGHTS",
        13: "BITANGENT",
    }
    BUFFER_FORMATS = {
        0: ("f", 4, False),   # Float (4 bytes)
        1: ("e", 2, False),   # Half-float (2 bytes)
        3: ("B", 1, False),   # Unsigned byte (raw)
        5: ("H", 2, False),   # Unsigned short
        8: ("B", 1, True),    # Unsigned byte normalized (0–1)
    }

    # Calculate strides
    for t in range(mesh.AttributesLength()):
        attrib = mesh.Attributes(t)
        attribType.append(attrib)
        stride = int(CalcStride(attrib.BufferFormat(), attrib.ElementCount()))
        alignStride.append(stride)
        totalStride += stride
        print("VertexType:", attrib.VertexType(), ATTRIB_TYPES.get(attrib.VertexType(), "UNKNOWN"))
        print("BufferFormat:", attrib.BufferFormat())
        print("ElementCount:", attrib.ElementCount())

    rawData = mesh.DataAsNumpy()
    print("Total bytes (%s): %d" % (name, len(rawData)))
    print("Total stride (%s): %d" % (name, totalStride))

    nmesh = bpy.data.meshes.new(name)

    vert_array = []
    normal_array = []
    cols = []
    b1_array = []
    w1_array = []
    face_array = []
    face_mat_id_array = []
    alpha_array = []
    uv_sets = {3: [], 4: [], 5: [], 6: []}   # UV1–UV4
    color_sets = {7: [], 8: []} 
    weight_array = []
    tangent_array = []

    for v in range(int(len(rawData) / totalStride)):
        baseOff = int(v * totalStride)
        offset = 0

        for i, attrib in enumerate(attribType):
            vtype = attrib.VertexType()
            fmt, size, normalize = BUFFER_FORMATS[attrib.BufferFormat()]
            count = attrib.ElementCount()
            length = size * count
            data = struct.unpack_from(f"<{count}{fmt}", rawData, baseOff + offset)

            if normalize:
                data = tuple(x / 255.0 for x in data)

            if vtype == 0:
                vert_array.append(tuple(data[:3]))
            elif vtype == 1:
                normal_array.append(tuple(data[:3]))
            elif vtype == 2:
                tangent_array.append(tuple(data[:3]))
            elif vtype in (3, 4, 5, 6):  # UV sets
                uv_sets[vtype].append(tuple(data[:2]))
            elif vtype in (7, 8):  # Colors
                color_sets[vtype].append(tuple(data))
                if len(data) > 3:
                    alpha_array.append(data[3])
                else:
                    alpha_array.append(1.0)
            elif vtype == 11:
                b1_array.append({
                    "bone1": data[0], "bone2": data[1], "bone3": data[2], "bone4": data[3]
                })
            elif vtype == 12:
                w1_array.append({
                    "weight1": data[0], "weight2": data[1], "weight3": data[2], "weight4": data[3]
                })
            elif vtype == 13:
                pass

            offset += length

    for b in range(len(w1_array)):
        w = {"boneids": [], "weights": []}
        maxweight = w1_array[b]["weight1"] +\
                    w1_array[b]["weight2"] +\
                    w1_array[b]["weight3"] +\
                    w1_array[b]["weight4"]

        if maxweight > 0:
            if (w1_array[b]["weight1"] > 0):
                w["boneids"].append(b1_array[b]["bone1"])
                w["weights"].append(w1_array[b]["weight1"])
            if (w1_array[b]["weight2"] > 0):
                w["boneids"].append(b1_array[b]["bone2"])
                w["weights"].append(w1_array[b]["weight2"])
            if (w1_array[b]["weight3"] > 0):
                w["boneids"].append(b1_array[b]["bone3"])
                w["weights"].append(w1_array[b]["weight3"])
            if (w1_array[b]["weight4"] > 0):
                w["boneids"].append(b1_array[b]["bone4"])
                w["weights"].append(w1_array[b]["weight4"])
        weight_array.append(w)

    print(weight_array)


    for poly in range(mesh.PolygonsLength()):
        polygon = mesh.Polygons(poly)
        matIdx = polygon.MaterialIndex()
        length = int(polygon.FacesLength())
        for i in range(0, length, 3):
            face_mat_id_array.append(matIdx)
            face_array.append((polygon.Faces(i), polygon.Faces(i + 1), polygon.Faces(i + 2)))


    nmesh.from_pydata(vert_array, [], face_array)
    nmesh.update()
    for p in nmesh.polygons:
        p.use_smooth = True

    new_object = bpy.data.objects.new(name, nmesh)
    bpy.context.collection.objects.link(new_object)

    for uv_type, uvs in uv_sets.items():
        if not uvs:
            continue
        layer_name = f"UVMap{uv_type - 2}"
        uv_layer = nmesh.uv_layers.new(name=layer_name)
        for face in nmesh.polygons:
            for vert_idx, loop_idx in zip(face.vertices, face.loop_indices):
                uv_layer.data[loop_idx].uv = uvs[vert_idx]

    for col_type, cols in color_sets.items():
        if not cols:
            continue
        layer_name = "Color" if col_type == 7 else "Color2"
        color_layer = new_object.data.vertex_colors.new(name=layer_name)
        new_object.data.vertex_colors.active = color_layer

        for poly in new_object.data.polygons:
            for v, vert in enumerate(poly.vertices):
                loop_index = poly.loop_indices[v]

                rgba = cols[vert]
                if len(rgba) == 4:
                    r, g, b, a = rgba
                else:
                    r, g, b, a = rgba[0], rgba[1], rgba[2], 1.0

                if a == 0:
                    a = 1.0

                color_layer.data[loop_index].color = (r / a, g / a, b / a, a)

    for i, vertex_weights in enumerate(weight_array):
        bi = []
        wv = []
        for bone_id, weight in zip(vertex_weights["boneids"], vertex_weights["weights"]):
            try:
                group_name = bone_id_map[bone_id]
                bi.append(group_name)
                wv.append(weight)
            except:
                continue
        for group_name, weight in zip(bi, wv):
            if group_name not in new_object.vertex_groups:
                new_object.vertex_groups.new(name=group_name)
            group = new_object.vertex_groups[group_name]
            group.add([i], weight, 'REPLACE')

    for mat in mats:
        new_object.data.materials.append(mat)
    for i, poly in enumerate(new_object.data.polygons):
        poly.material_index = face_mat_id_array[i]

    new_object.parent = armature_obj
    arm_mod = new_object.modifiers.new(name='Skeleton', type='ARMATURE')
    arm_mod.object = armature_obj

    if blender_version[0] < 3:
        new_object.data.use_auto_smooth = True

    if normal_array:
        new_object.data.normals_split_custom_set_from_vertices(normal_array)

    new_object.data.update()
            
def LoadModel(buf, filename):
    mon = Model.GetRootAsModel(buf, 0)
    
    # Create armature
    a, armature_obj = BuildArmature(mon, filename)
    
    # Create materials
    mats = []
    matLen = mon.MaterialsLength()
    for i in range(matLen):
        mats.append(CreateMaterial(mon.Materials(i)))
    
    # Create meshes
    for i in range(mon.MeshesLength()):
        CreateMesh(bpy.data.armatures[0].bones[mon.Groups(i).BoneIndex() - 1].name, mon, i, mats, a, armature_obj) #TODO: dont assume groups are in order by matIndex

    # Orient properly
    RotateObj(armature_obj, 90, 'X')
    
# #####################################################
# Main
# #####################################################
class ImportModel():
    def load( operator, context ):
        for f in enumerate(operator.files):
            fpath = operator.directory + f[1].name
            print("Loading " + fpath)
            
            buf = open(fpath, 'rb').read()
            buf = bytearray(buf)
            LoadModel(buf, f[1].name)
            bpy.ops.object.delete()
            
            return {"FINISHED"}