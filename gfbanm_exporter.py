"""
    Script for exporting armature animation to gfbanm/tranm format.
"""
import os
import sys
import math

import bpy
from mathutils import Vector, Quaternion, Matrix
import flatbuffers

sys.path.append(os.path.join(os.path.dirname(__file__), "."))

# pylint: disable=wrong-import-position, import-error, too-many-branches

from GFLib.Anim.Animation import AnimationT
from GFLib.Anim.BoneAnimation import BoneAnimationT
from GFLib.Anim.BoneTrack import BoneTrackT
from GFLib.Anim.FixedVectorTrack import FixedVectorTrackT
from GFLib.Anim.DynamicVectorTrack import DynamicVectorTrackT
from GFLib.Anim.Framed16VectorTrack import Framed16VectorTrackT
from GFLib.Anim.Framed8VectorTrack import Framed8VectorTrackT
from GFLib.Anim.FixedRotationTrack import FixedRotationTrackT
from GFLib.Anim.DynamicRotationTrack import DynamicRotationTrackT
from GFLib.Anim.Framed16RotationTrack import Framed16RotationTrackT
from GFLib.Anim.Framed8RotationTrack import Framed8RotationTrackT
from GFLib.Anim.Info import InfoT
from GFLib.Anim.Vec3 import Vec3T
from GFLib.Anim.sVec3 import sVec3T

VectorTrackType = (FixedVectorTrackT | DynamicVectorTrackT | Framed16VectorTrackT |
                   Framed8VectorTrackT)
RotationTrackType = (FixedRotationTrackT | DynamicRotationTrackT | Framed16RotationTrackT |
                     Framed8RotationTrackT)


def export_animation(context: bpy.types.Context, does_loop: bool) -> int | bytearray:
    """
    Exports armature animation to GFBANM/TRANM format.
    :param context: Blender's Context.
    :param does_loop: True if animation is looping.
    :return: GFBANM/TRANM bytearray.
    """
    assert context.object is not None and context.object.type == "ARMATURE", \
        "Target Armature not selected."
    animation = AnimationT()
    animation.info = InfoT()
    animation.info.keyFrames = context.scene.frame_end - context.scene.frame_start + 1
    animation.info.frameRate = int(context.scene.render.fps / context.scene.render.fps_base)
    animation.info.doesLoop = int(does_loop)
    animation.skeleton = BoneAnimationT()
    animation.skeleton.tracks = []
    current_frame = context.scene.frame_current
    for pose_bone in context.object.pose.bones:
        print(f"Exporting keyframes for {pose_bone.name} track.")
        transforms = get_track_transforms_from_posebone(context, pose_bone)
        t_list = []
        r_list = []
        s_list = []
        for transform in transforms:
            t_list.append(transform[0])
            r_list.append(transform[1])
            s_list.append(transform[2])
        track = BoneTrackT()
        track.name = pose_bone.name
        track.translate = vector_list_to_vector_track(t_list)
        track.translateType = vector_track_to_type(track.translate)
        track.rotate = quaternion_list_to_rotation_track(r_list)
        track.rotateType = rotation_track_to_type(track.rotate)
        track.scale = vector_list_to_vector_track(s_list)
        track.scaleType = vector_track_to_type(track.scale)
        animation.skeleton.tracks.append(track)
    context.scene.frame_set(current_frame)
    builder = flatbuffers.Builder()
    animation = animation.Pack(builder)
    builder.Finish(animation)
    return builder.Output()


PI_DIVISOR = math.pi / 65536
PI_ADDEND = math.pi / 4.0


def quantize_float(f: float) -> int:
    """
    Packs expanded float into integer.
    :param f: Expanded float.
    :return: Packed integer.
    """
    result = int((f + PI_ADDEND) / PI_DIVISOR)
    return result & 0x7FFF


def pack_quaternion_to_48bit(q: Quaternion) -> (int, int, int):
    """
    Packs Blender Quaternion into 48-bit integer Vector.
    To-do: fix return values. There may be something wrong with index-based swizzling.
    :param q: Blender Quaternion.
    :return: X, Y, Z values of integer Vector.
    """
    q_list = [q.w, q.x, q.y, q.z]
    max_val = max(q_list)
    min_val = min(q_list)
    is_negative = 0
    if abs(min_val) > max_val:
        max_val = min_val
        is_negative = 1
    max_index = q_list.index(max_val)
    if is_negative == 1:
        q_list = [-x for x in q_list]
    if max_index == 0:
        tx = quantize_float(q_list[3])
        ty = quantize_float(q_list[1])
        tz = quantize_float(q_list[2])
    elif max_index == 1:
        tx = quantize_float(q_list[0])
        ty = quantize_float(q_list[3])
        tz = quantize_float(q_list[2])
    elif max_index == 2:
        tx = quantize_float(q_list[0])
        ty = quantize_float(q_list[1])
        tz = quantize_float(q_list[3])
    else:
        tx = quantize_float(q_list[0])
        ty = quantize_float(q_list[1])
        tz = quantize_float(q_list[2])
    pack = (tz << 30) | (ty << 15) | tx
    pack = (pack << 3) | ((is_negative << 2) | max_index)
    return pack & 0xFFFF, (pack >> 16) & 0xFFFF, (pack >> 32) & 0xFFFF


def vector_list_to_vector_track(vector_list: list[Vector | None]) -> None | VectorTrackType | None:
    """
    Converts list of Vectors to appropriate VectorTrack.
    :param vector_list: List of Vectors
    :return: VectorTrack.
    """
    val = None
    for i, _ in enumerate(vector_list):
        if vector_list[i] is not None:
            vector_list[i][0] = round(vector_list[i][0], 6)
            vector_list[i][1] = round(vector_list[i][1], 6)
            vector_list[i][2] = round(vector_list[i][2], 6)
            # Fix for negative zero appearing sometimes.
            vector_list[i][0] += 0.0
            vector_list[i][1] += 0.0
            vector_list[i][2] += 0.0
        if val is None:
            val = vector_list[i]
            continue
        if vector_list[i] == val:
            vector_list[i] = None
        else:
            val = vector_list[i]
    indexes = [i for i, vector in enumerate(vector_list) if vector is not None]
    if len(indexes) < 1:
        return None
    if len(indexes) == 1:
        track = FixedVectorTrackT()
        vector = vector_list[indexes[0]]
        val = vector[0], vector[1], vector[2]
        track.co = Vec3T()
        track.co.x, track.co.y, track.co.z = val
        return track
    if len(indexes) > 65535 or len(indexes) == len(vector_list):
        track = DynamicVectorTrackT()
        track.co = []
        vector = vector_list[indexes[0]]
        val = vector[0], vector[1], vector[2]
        for vector in vector_list:
            if vector is not None:
                val = vector[0], vector[1], vector[2]
            vec = Vec3T()
            vec.x, vec.y, vec.z = val
            track.co.append(vec)
        return track
    if len(indexes) < 256:
        track = Framed8VectorTrackT()
    else:
        track = Framed16VectorTrackT()
    track.frames = []
    track.co = []
    for i in indexes:
        vector = vector_list[i]
        val = vector[0], vector[1], vector[2]
        track.frames.append(i)
        vec = Vec3T()
        vec.x, vec.y, vec.z = val
        track.co.append(vec)
    return track


def quaternion_list_to_rotation_track(
        quat_list: list[Quaternion | None]) -> RotationTrackType | None:
    """
    Converts list of Quaternions to appropriate RotationTrack.
    :param quat_list: List of Quaternions
    :return: RotationTrack.
    """
    val = None
    for i, _ in enumerate(quat_list):
        if val is None:
            val = quat_list[i]
            continue
        if quat_list[i] == val:
            quat_list[i] = None
        else:
            val = quat_list[i]
    indexes = [i for i, quat in enumerate(quat_list) if quat is not None]
    if len(indexes) < 1:
        return None
    if len(indexes) == 1:
        track = FixedRotationTrackT()
        quat = quat_list[indexes[0]]
        val = pack_quaternion_to_48bit(quat)
        track.co = sVec3T()
        track.co.x, track.co.y, track.co.z = val
        return track
    if len(indexes) > 65535 or len(indexes) == len(quat_list):
        track = DynamicRotationTrackT()
        track.co = []
        quat = quat_list[indexes[0]]
        val = pack_quaternion_to_48bit(quat)
        for quat in quat_list:
            if quat is not None:
                val = pack_quaternion_to_48bit(quat)
            vec = sVec3T()
            vec.x, vec.y, vec.z = val
            track.co.append(vec)
        return track
    if len(indexes) < 256:
        track = Framed8RotationTrackT()
    else:
        track = Framed16RotationTrackT()
    track.frames = []
    track.co = []
    for i in indexes:
        quat = quat_list[i]
        val = pack_quaternion_to_48bit(quat)
        track.frames.append(i)
        vec = sVec3T()
        vec.x, vec.y, vec.z = val
        track.co.append(vec)
    return track


def vector_track_to_type(track: VectorTrackType) -> int:
    """
    Returns integer based on VectorTrack type.
    :param track: VectorTrack.
    :return: Integer.
    """
    if isinstance(track, FixedVectorTrackT):
        return 1
    if isinstance(track, DynamicVectorTrackT):
        return 2
    if isinstance(track, Framed16VectorTrackT):
        return 3
    if isinstance(track, Framed8VectorTrackT):
        return 4
    return 0


def rotation_track_to_type(track: RotationTrackType) -> int:
    """
    Returns integer based on RotationTrack type.
    :param track: RotationTrack.
    :return: Integer.
    """
    if isinstance(track, FixedRotationTrackT):
        return 1
    if isinstance(track, DynamicRotationTrackT):
        return 2
    if isinstance(track, Framed16RotationTrackT):
        return 3
    if isinstance(track, Framed8RotationTrackT):
        return 4
    return 0


def get_track_transforms_from_posebone(context: bpy.types.Context, pose_bone: bpy.types.PoseBone) \
        -> list[(Vector, Quaternion, Vector)]:
    """
    Returns list of track transforms for every keyframe of animation.
    To-do: The resulting location and rotation are currently incorrect, needs a fix.
    :param context: Blender's Context.
    :param pose_bone: Target PoseBone.
    :return: List of (Location, Rotation, Scaling) track transform tuples.
    """
    transforms = []
    matrix = pose_bone.bone.matrix_local
    if pose_bone.parent:
        matrix = pose_bone.parent.bone.matrix_local.inverted() @ matrix
    rot = matrix.to_quaternion()
    for i in range(context.scene.frame_start, context.scene.frame_end + 1):
        context.scene.frame_set(i)
        matrix_initial = Matrix.Identity(4)
        if pose_bone.parent:
            matrix_initial = (pose_bone.parent.matrix @
                              pose_bone.parent.bone.matrix_local.inverted() @
                              pose_bone.bone.matrix_local @ matrix_initial)
        translation = (matrix + pose_bone.matrix - matrix_initial).to_translation()
        rotation = rot.conjugated().rotation_difference(pose_bone.matrix_basis.to_quaternion())
        scale = pose_bone.matrix_basis.to_scale()
        transforms.append((translation, rotation, scale))
    return transforms
