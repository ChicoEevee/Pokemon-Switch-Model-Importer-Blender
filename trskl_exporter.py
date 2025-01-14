"""
    Script for exporting armature to trskl file.
"""

import os
import sys
from math import radians
from collections.abc import Iterable

import bpy
from mathutils import Matrix
import flatbuffers

sys.path.append(os.path.join(os.path.dirname(__file__), "."))

from Titan.Model import TRSKL, TransformNode, Transform, Bone, BoneMatrix, Vec3

rx90 = Matrix.Rotation(radians(90), 4, 'X')
ry90 = Matrix.Rotation(radians(90), 4, 'Y')
rz90 = Matrix.Rotation(radians(90), 4, 'Z')
ryz90 = ry90 @ rz90

rx90n = Matrix.Rotation(radians(-90), 4, 'X')
ry90n = Matrix.Rotation(radians(-90), 4, 'Y')
rz90n = Matrix.Rotation(radians(-90), 4, 'Z')


def is_bone_weighted(armature_obj: bpy.types.Object, bone_name: str):
    """
    Checks if bone is weighted to any mesh.
    :param armature_obj: Armature object.
    :param bone_name: Bone's name.
    :returns: True if weighted, False otherwise.
    """
    for obj in bpy.data.objects:
        if obj.type != "MESH":
            continue
        for modifier in obj.modifiers:
            if modifier.type != "ARMATURE" or modifier.object != armature_obj:
                continue
            if bone_name in obj.vertex_groups:
                return True
    return False


def get_evaluated_pose_bones(armature_obj: bpy.types.Object):
    """
    Re-evaluating bones, I guess?
    What's even exportable_bones? Can I use getattr so that PyCharm does not complain?
    """
    depsgraph = bpy.context.evaluated_depsgraph_get()
    evaluated_armature = armature_obj.evaluated_get(depsgraph)
    return [evaluated_armature.pose.bones[bone.name] for bone in self.exportable_bones]


def get_smd_float(f: any) -> float:
    """
    Converts value to float and rounds it to 6 digits precision.
    :param f: Value to convert.
    :returns: Float.
    """
    return f"{float(f):.2f}"


def get_smd_vec(iterable: Iterable) -> str:
    """
    Converts values of iterable to float and concatenates them to evenly space string.
    :param iterable: Iterable.
    :returns: Evenly spaced string.
    """
    return " ".join([get_smd_float(val) for val in iterable])


def export_skeleton(armature_obj: bpy.types.Object) -> int | bytearray:
    """
    Exports Armature object to trskl file.
    :param armature_obj: Armature object.
    """
    transform_nodes = []
    bones = []
    trskl = TRSKL.TRSKLT()
    trskl.transformNodes = transform_nodes
    trskl.bones = bones
    trskl.iks = []
    # Assume the armature has only one pose for simplicity
    armature_obj.select_set(True)
    bpy.context.view_layer.objects.active = armature_obj
    bpy.ops.object.mode_set(mode="POSE")
    mat_blender_to_smd = ry90 @ rz90
    for posebone in armature_obj.pose.bones:
        result = is_bone_weighted(armature_obj, posebone.name)
        parent = posebone.parent
        matrix = posebone.matrix.inverted() @ (armature_obj.matrix_world.inverted()
                                               @ armature_obj.matrix_world)
        if result:
            bone = Bone.BoneT()
            if hasattr(posebone.bone, "inherit_scale"):
                if posebone.bone.inherit_scale not in ("FULL", "NONE", "NONE_LEGACY"):
                    print("Bone " + posebone.bone.name + " has incompatible scale inheritance mode:"
                        " "+ posebone.bone.inherit_scale + ". Full scale inheritance will be used"
                        " instead.")
                    bone.inheritScale = True
                else:
                    bone.inheritScale = posebone.bone.inherit_scale == "FULL"
            else:
                bone.inheritScale = posebone.bone.use_inherit_scale
            bone.influenceSkinning = True
            bone.matrix = create_bone_matrix(matrix)
            bones.append(bone)
        if result:
            bone_index = armature_obj.data.bones.find(posebone.name)
        else:
            bone_index = -1
        # Get the parent index
        parent_index = -1  # Default value for bones without a parent
        if posebone.parent:
            parent_index = armature_obj.data.bones.find(posebone.parent.name)
        # Get the bone's Matrix from the current pose
        pose_matrix = posebone.matrix
        if armature_obj.data.vs.legacy_rotation:
            pose_matrix @= mat_blender_to_smd
        if parent:
            parent_matrix = parent.matrix
            if armature_obj.data.vs.legacy_rotation:
                parent_matrix @= mat_blender_to_smd
            pose_matrix = parent_matrix.inverted() @ pose_matrix
        else:
            pose_matrix = armature_obj.matrix_world @ pose_matrix
        transform_node = TransformNode.TransformNodeT()
        transform_node.name = posebone.name
        transform_node.transform = Transform.TransformT()
        transform_node.transform.vecScale = create_vec3(1.0, 1.0, 1.0)
        vals = get_smd_vec(pose_matrix.to_euler()).split()
        transform_node.transform.vecRot = create_vec3(float(vals[0]), float(vals[1]),
                                                      float(vals[2]))
        vals = get_smd_vec(pose_matrix.to_translation()).split()
        transform_node.transform.vecTranslate = create_vec3(float(vals[0]), float(vals[1]),
                                                            float(vals[2]))
        transform_node.scalePivot = create_vec3(0.0, 0.0, 0.0)
        transform_node.rotatePivot = create_vec3(0.0, 0.0, 0.0)
        transform_node.parentIdx = parent_index
        transform_node.rigIdx = bone_index
        transform_node.effectNode = ""
        transform_node.priority = 0
        transform_nodes.append(transform_node)
    builder = flatbuffers.Builder()
    trskl = trskl.Pack(builder)
    builder.Finish(trskl)
    return builder.Output()


def create_bone_matrix(matrix: Matrix) -> BoneMatrix.BoneMatrixT:
    """
    Creates BoneMatrixT object from mathutils Matrix.
    :param matrix: Matrix.
    :returns: BoneMatrixT object.
    """
    m = BoneMatrix.BoneMatrixT()
    m.x = create_vec3(round(matrix[0][0], 6), round(matrix[0][1], 6), round(matrix[0][2], 6))
    m.y = create_vec3(round(matrix[1][0], 6), round(matrix[1][1], 6), round(matrix[1][2], 6))
    m.z = create_vec3(round(matrix[2][0], 6), round(matrix[2][1], 6), round(matrix[2][2], 6))
    m.w = create_vec3(round(matrix[0][3], 6), round(matrix[1][3], 6), round(matrix[2][3], 6))
    return m


def create_vec3(x: float, y: float, z: float) -> Vec3.Vec3T:
    """
    Creates Vec3T object from 3 floats.
    :param x: x value.
    :param y: y value.
    :param z: z value.
    :returns: Vec3T object.
    """
    v = Vec3.Vec3T()
    v.x = x
    v.y = y
    v.z = z
    return v
