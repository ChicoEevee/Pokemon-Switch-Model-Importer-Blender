import bpy
import json
import os
from bpy_extras.io_utils import ExportHelper
from mathutils import Matrix, Vector
from math import *

rx90 = Matrix.Rotation(radians(90),4,'X')
ry90 = Matrix.Rotation(radians(90),4,'Y')
rz90 = Matrix.Rotation(radians(90),4,'Z')
ryz90 = ry90 @ rz90

rx90n = Matrix.Rotation(radians(-90),4,'X')
ry90n = Matrix.Rotation(radians(-90),4,'Y')
rz90n = Matrix.Rotation(radians(-90),4,'Z')


def is_bone_weighted(armature, bone_name):
    a = False
    for obj in bpy.data.objects:
        if obj.type == 'MESH':
            for modifier in obj.modifiers:
                if modifier.type == 'ARMATURE' and modifier.object == armature:
                    bpy.context.view_layer.objects.active = obj
                    bpy.ops.object.mode_set(mode='OBJECT')

                    armature_data = modifier.object.data

                    try:

                        bpy.ops.object.mode_set(mode='OBJECT')  # Switch back to OBJECT mode

                        # Check if the bone is in the vertex groups
                        if bone_name in obj.vertex_groups:
                            a = True
                    except (KeyError, IndexError):
                        pass

    return a
    
def getEvaluatedPoseBones(armature_obj):
	depsgraph = bpy.context.evaluated_depsgraph_get()
	evaluated_armature = armature_obj.evaluated_get(depsgraph)

	return [evaluated_armature.pose.bones[bone.name] for bone in self.exportable_bones]


def getSmdFloat(fval):
	return "{:.6f}".format(float(fval))


def getSmdVec(iterable):
	return " ".join([getSmdFloat(val) for val in iterable])
    
    
def export_armature_matrix(armature_obj):
    transform_nodes = []
    bones = []
    data = {
        "res_0": 0,
        "transform_nodes": transform_nodes,
        "bones": bones,
                "iks": [
    
                ],
                "rig_offset": 0
            }


    # Assume the armature has only one pose for simplicity
    armature_obj.select_set(True)
    bpy.context.view_layer.objects.active = armature_obj
    bpy.ops.object.mode_set(mode='POSE')
    mat_BlenderToSMD = ry90 @ rz90
    for posebone in armature_obj.pose.bones:
        inherit_position = 1  # Set tow 1 for example, you can modify this based on your requirements
        result = is_bone_weighted(armature_obj, posebone.name)
        parent = posebone.parent
        matrix = posebone.matrix.inverted() @ (armature_obj.matrix_world.inverted()
                                                          @ armature_obj.matrix_world)

        if result == True:
            bones.append({
                    "inherit_position": inherit_position,
                    "unk_bool_2": 1,
                    "matrix": {
                        "x": {
                            "x": round(matrix[0][0], 6),
                            "y": round(matrix[0][1], 6),
                            "z": round(matrix[0][2], 6)
                        },
                        "y": {
                            "x": round(matrix[1][0], 6),
                            "y": round(matrix[1][1], 6),
                            "z": round(matrix[1][2], 6)
                        },
                        "z": {
                            "x": round(matrix[2][0], 6),
                            "y": round(matrix[2][1], 6),
                            "z": round(matrix[2][2], 6)
                        },
                        "w": {
                            "x": round(matrix[0][3], 6),
                            "y": round(matrix[1][3], 6),
                            "z": round(matrix[2][3], 6)
                        },
                        # THIS IS THE F - n trouble child
                    }})

        if result == True:
            bone_index = armature_obj.data.bones.find(posebone.name)
        else:
            bone_index = -1
        # Get the parent index
        parent_index = -1  # Default value for bones without a parent
        if posebone.parent:
            parent_index = armature_obj.data.bones.find(posebone.parent.name)
        # Get the bone's Matrix from the current pose
        PoseMatrix = posebone.matrix
        if armature_obj.data.vs.legacy_rotation:
            PoseMatrix @= mat_BlenderToSMD 
        if parent:
            parentMat = parent.matrix
            if armature_obj.data.vs.legacy_rotation: parentMat @= mat_BlenderToSMD 
            PoseMatrix = parentMat.inverted() @ PoseMatrix
        else:
            PoseMatrix = armature_obj.matrix_world @ PoseMatrix

        transform_nodes.append({
                "name": posebone.name,
                "transform": {
                    "VecScale": {
                        "x": 1.0,
                        "y": 1.0,
                        "z": 1.0
                    },
                    "VecRot": {
                        "x": float(getSmdVec(PoseMatrix.to_euler()).split()[0]),
                        "y": float(getSmdVec(PoseMatrix.to_euler()).split()[1]),
                        "z": float(getSmdVec(PoseMatrix.to_euler()).split()[2])
                    },
                    "VecTranslate": {
                        "x": float(getSmdVec(PoseMatrix.to_translation()).split()[0]),
                        "y": float(getSmdVec(PoseMatrix.to_translation()).split()[1]),
                        "z": float(getSmdVec(PoseMatrix.to_translation()).split()[2])
                    }
                },
                "scalePivot": {
                    "x": 0.0,
                    "y": 0.0,
                    "z": 0.0
                },
                "rotatePivot": {
                    "x": 0.0,
                    "y": 0.0,
                    "z": 0.0
                },
                "parent_idx": parent_index,
                "rig_idx": bone_index,
                "effect_node": "",
                "type": "Default"
                })
    return data