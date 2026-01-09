"""
    Script for exporting armature to trskl file.
"""

import os
import sys

import bpy
from mathutils import Matrix
import flatbuffers

# pylint: disable=wrong-import-position, import-error, too-many-statements, too-many-branches
# pylint: disable=too-many-locals

from .Titan.Model import TRSKL, TransformNode, Transform, Bone, BoneMatrix, Vec3


def export_skeleton(armature_obj: bpy.types.Object) -> int | bytearray:
    """
    Exports Armature object to TRSKL format.
    :param armature_obj: Armature object.
    :return: TRSKL bytearray.
    """
    assert armature_obj and armature_obj.type == "ARMATURE", "Selected object is not Armature."
    transform_nodes = []
    bones = []
    trskl = TRSKL.TRSKLT()
    trskl.transformNodes = transform_nodes
    trskl.bones = bones
    trskl.iks = []
    # Assume the armature has only one pose for simplicity
    for bone in armature_obj.data.bones:
        parent = bone.parent
        matrix = bone.matrix_local.inverted()

        bone_obj = Bone.BoneT()
        if hasattr(bone, "inherit_scale"):
            if bone.inherit_scale not in ("FULL", "NONE", "NONE_LEGACY"):
                print(f"Bone {bone.name} has incompatible scale inheritance mode: "
                      f"{bone.inherit_scale}. Full scale inheritance will be used "
                      "instead.")
                bone_obj.inheritScale = False
            else:
                bone_obj.inheritScale = bone.inherit_scale != "FULL"
        else:
            bone_obj.inheritScale = not bone.use_inherit_scale
        bone_obj.influenceSkinning = True   # always included
        bone_obj.matrix = create_bone_matrix(matrix)
        bones.append(bone_obj)

        bone_index = armature_obj.data.bones.find(bone.name)
        # Get the parent index
        parent_index = -1  # Default value for bones without a parent
        if bone.parent:
            parent_index = armature_obj.data.bones.find(bone.parent.name)
        # Get the bone's Matrix from the current pose
        pose_matrix = bone.matrix_local
        if parent:
            parent_matrix = parent.matrix_local.inverted()
        else:
            parent_matrix = armature_obj.matrix_world
        pose_matrix = parent_matrix @ pose_matrix
        transform_node = TransformNode.TransformNodeT()
        transform_node.name = bone.name
        transform_node.transform = Transform.TransformT()
        transform_node.transform.vecScale = create_vec3(1.0, 1.0, 1.0)
        vec = pose_matrix.to_euler()
        transform_node.transform.vecRot = create_vec3(round(vec[0], 6) + 0.0,
                                                      round(vec[1], 6) + 0.0,
                                                      round(vec[2], 6) + 0.0)
        vec = pose_matrix.to_translation()
        transform_node.transform.vecTranslate = create_vec3(round(vec[0], 6) + 0.0,
                                                            round(vec[1], 6) + 0.0,
                                                            round(vec[2], 6) + 0.0)
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
    m.x = create_vec3(round(matrix[0][0], 6) + 0.0, round(matrix[0][1], 6) + 0.0,
                      round(matrix[0][2], 6) + 0.0)
    m.y = create_vec3(round(matrix[1][0], 6) + 0.0, round(matrix[1][1], 6) + 0.0,
                      round(matrix[1][2], 6) + 0.0)
    m.z = create_vec3(round(matrix[2][0], 6) + 0.0, round(matrix[2][1], 6) + 0.0,
                      round(matrix[2][2], 6) + 0.0)
    m.w = create_vec3(round(matrix[0][3], 6) + 0.0, round(matrix[1][3], 6) + 0.0,
                      round(matrix[2][3], 6) + 0.0)
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
    v.x, v.y, v.z = x, y, z
    return v
