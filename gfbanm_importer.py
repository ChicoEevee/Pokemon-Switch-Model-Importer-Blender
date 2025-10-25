"""
    Script for importing animation from deserialized gfbanm file.
"""

import os
import sys
import math

import bpy
from mathutils import Vector, Quaternion, Matrix

sys.path.append(os.path.join(os.path.dirname(__file__), "."))

# pylint: disable=wrong-import-position, import-error, too-many-arguments, too-many-branches
# pylint: disable=too-many-positional-arguments

from GFLib.Anim.DynamicRotationTrack import DynamicRotationTrackT
from GFLib.Anim.DynamicVectorTrack import DynamicVectorTrackT
from GFLib.Anim.FixedRotationTrack import FixedRotationTrackT
from GFLib.Anim.FixedVectorTrack import FixedVectorTrackT
from GFLib.Anim.Framed16RotationTrack import Framed16RotationTrackT
from GFLib.Anim.Framed16VectorTrack import Framed16VectorTrackT
from GFLib.Anim.Framed8RotationTrack import Framed8RotationTrackT
from GFLib.Anim.Framed8VectorTrack import Framed8VectorTrackT
from GFLib.Anim.Animation import AnimationT
from GFLib.Anim.BoneTrack import BoneTrackT
from GFLib.Anim.Vec3 import Vec3T
from GFLib.Anim.sVec3 import sVec3T

TransformType = Vector | Quaternion | None
VectorTrackType = (FixedVectorTrackT | DynamicVectorTrackT | Framed16VectorTrackT |
                   Framed8VectorTrackT)
RotationTrackType = (FixedRotationTrackT | DynamicRotationTrackT | Framed16RotationTrackT |
                     Framed8RotationTrackT)


def import_animation(
        context: bpy.types.Context,
        file_path: str,
        ignore_origin_location: bool,
        frame_start: int,
        frame_end: bool,
        nla_import: bool
):
    """
    Imports animation from processing gfbanm file.
    :param context: Blender's Context.
    :param file_path: Path to gfbanm file.
    :param ignore_origin_location: Whether to ignore location transforms from Origin track.
    :param frame_start: Start frame.
    :param frame_end: True if set scene's end frame at last frame of animation.
    :param nla_import: If True, the imported animation action will be pushed into the object's NLA as a strip.
    """
    if context.object is None or context.object.type != "ARMATURE":
        raise OSError("Target Armature not selected.")
    print(f"Armature name: {context.object.name}.")
    anim_name = os.path.splitext(os.path.basename(file_path))[0]
    print(f"Animation name: {anim_name}.")
    with open(file_path, "rb") as file:
        anm = AnimationT.InitFromPackedBuf(bytearray(file.read()), 0)
        if anm.info is None:
            raise OSError(f"{file_path} contains invalid info chunk.")
        if anm.info.keyFrames < 1:
            raise OSError(f"{file_path} contains invalid info.keyFrames chunk.")
        if frame_end:
            bpy.context.scene.frame_end = frame_start+anm.info.keyFrames-1
        print(f"Keyframes amount: {anm.info.keyFrames}.")
        if anm.info.frameRate < 1:
            raise OSError(f"{file_path} contains invalid info.frameRate chunk.")
        print(f"Framerate: {anm.info.frameRate} FPS.")
        if anm.skeleton is None:
            raise OSError(f"{file_path} contains invalid skeleton chunk.")
        if anm.skeleton.tracks is None:
            raise OSError(f"{file_path} contains invalid skeleton.tracks chunk.")
        print(f"Tracks amount: {len(anm.skeleton.tracks)}.")
        apply_animation_to_tracks(
            context,
            anim_name,
            anm.info.frameRate,
            anm.info.keyFrames,
            anm.skeleton.tracks,
            ignore_origin_location,
            frame_start,
            nla_import
        )


def apply_animation_to_tracks(
        context: bpy.types.Context,
        anim_name: str,
        frame_rate: int,
        key_frames: int,
        tracks: list[BoneTrackT | None],
        ignore_origin_location: bool,
        frame_start: int,
        nla_import: bool = False
):
    """
    Applies animation to bones of selected Armature.
    :param context: Blender's Context.
    :param anim_name: Action name.
    :param frame_rate: Framerate.
    :param key_frames: Keyframes amount.
    :param tracks: List of BoneTrack objects.
    :param ignore_origin_location: Whether to ignore location transforms from Origin track.
    :param frame_start: Start frame.
    :param nla_import: If True, the created action will be pushed into the object's NLA as a strip.
    """
    assert (context.object is not None and context.object.type == "ARMATURE"), \
        "Selected object is not Armature."
    for pose_bone in context.object.pose.bones:
        print(f"Clearing pose for {pose_bone.name} bone.")
        pose_bone.matrix_basis = Matrix.Identity(4)
    context.view_layer.update()
    action = None
    context.window_manager.progress_begin(0, len(tracks))
    for i, track in enumerate(tracks):
        if track is None or track.name is None or track.name == "":
            context.window_manager.progress_update(i + 1)
            continue
        print(f"Creating keyframes for {track.name} track.")
        if track.name not in context.object.pose.bones.keys():
            context.window_manager.progress_update(i + 1)
            continue
        pose_bone = context.object.pose.bones[track.name]
        t_list = get_track_transforms(track.translate, key_frames)
        s_list = get_track_transforms(track.scale, key_frames)
        r_list = get_track_transforms(track.rotate, key_frames)
        if context.object.animation_data is None:
            context.object.animation_data_create()
        if action is None:
            action = bpy.data.actions.new(anim_name)
            action.use_fake_user = True
            # While building keyframes we set the object's active action so keyframe_insert targets it.
            context.object.animation_data.action = action
            context.scene.render.fps = frame_rate
            context.scene.render.fps_base = 1.0
        apply_track_transforms_to_posebone(pose_bone, list(zip(t_list, r_list, s_list)),
                                           ignore_origin_location, frame_start)
        context.window_manager.progress_update(i + 1)
    context.window_manager.progress_end()
    context.view_layer.update()

    # If requested, push the newly-created action into NLA as a new track/strip.
    if nla_import and action is not None:
        print(f"Pushing action '{anim_name}' into NLA starting at frame {frame_start}.")
        # Ensure animation_data exists (should already exist) and create an NLA track.
        if context.object.animation_data is None:
            context.object.animation_data_create()
        nla_track = context.object.animation_data.nla_tracks.new()
        nla_track.name = anim_name
        # Create strip and set its frames to match imported keyframes length.
        strip = nla_track.strips.new(anim_name, frame_start, action)
        strip.frame_end = frame_start + key_frames - 1
        # Map the action frames to the strip.
        strip.action_frame_start = 0.0
        strip.action_frame_end = float(key_frames)
        # Clear the active action so the object is not left with the action assigned.
        context.object.animation_data.action = None
        context.view_layer.update()
    elif action is not None:
        # Leave the action assigned as the active action (default behavior).
        print(f"Action '{anim_name}' created and set as active action.")


def apply_track_transforms_to_posebone(
        pose_bone: bpy.types.PoseBone,
        transforms: list[(Vector | None, Quaternion | None, Vector | None)],
        ignore_origin_location: bool,
        frame_start: int
):
    """
    Applies track transforms to PoseBone for every keyframe of animation.
    :param pose_bone: Target PoseBone.
    :param transforms: List of (Location, Rotation, Scaling) track transform tuples.
    :param ignore_origin_location: Whether to ignore location transforms from Origin track.
    :param frame_start: Start frame.
    """
    matrix_local = pose_bone.bone.matrix_local
    if pose_bone.parent:
        matrix_local = pose_bone.parent.bone.matrix_local.inverted() @ matrix_local
    previous_rot = None
    for i, transform in enumerate(transforms):
        loc, rot, scale = matrix_local.decompose()
        if transform[0] is not None:
            if not ignore_origin_location or pose_bone.bone.name.casefold() != "Origin".casefold():
                loc = transform[0]
        if transform[1] is not None:
            rot = transform[1]
        matrix = Matrix.LocRotScale(loc, rot, scale)
        if pose_bone.parent:
            matrix = pose_bone.parent.matrix @ matrix
        loc, rot, scale = Matrix.Identity(4).decompose()
        if transform[2] is not None:
            scale = transform[2]
        matrix = matrix @ Matrix.LocRotScale(loc, rot, scale)
        loc, rot, scale = matrix.decompose()
        if previous_rot is not None:
            rot.make_compatible(previous_rot)
        previous_rot = rot
        matrix = Matrix.LocRotScale(loc, rot, scale)
        pose_bone.matrix = matrix
        current_frame = frame_start + i
        if transform[0] is not None:
            pose_bone.keyframe_insert(data_path="location", frame=current_frame)
        if transform[1] is not None:
            pose_bone.keyframe_insert(data_path="rotation_quaternion", frame=current_frame)
        if transform[2] is not None:
            pose_bone.keyframe_insert(data_path="scale", frame=current_frame)


def get_track_transforms(track: VectorTrackType | RotationTrackType | None, key_frames: int) -> \
        list[TransformType]:
    """
    Generalized function to extract track transforms (Vector or Rotation).
    :param track: The track object containing keyframe data.
    :param key_frames: Total number of keyframes in the animation.
    :return: List of transforms as tuples (x, y, z) for Vectors or Quaternions for Rotations.
    """
    assert key_frames > 0, "Keyframes amount is less than 1."
    if track is None or getattr(track, "co", None) is None:
        return [None] * key_frames
    if isinstance(track, FixedVectorTrackT):
        return [Vector((track.co.x, track.co.y, track.co.z)) if i == 0 else None for i in range(key_frames)]
    if isinstance(track, DynamicVectorTrackT):
        return [Vector((track.co[i].x, track.co[i].y, track.co[i].z)) if i < len(track.co) else None for i in
                range(key_frames)]
    if isinstance(track, (Framed16VectorTrackT, Framed8VectorTrackT)):
        return [Vector((track.co[j].x, track.co[j].y, track.co[j].z)) if (j := list(track.frames).index(
            i) if i in track.frames else -1) > -1 else None for i in range(key_frames)]
    if isinstance(track, FixedRotationTrackT):
        return [get_quaternion_from_packed(track.co) if i == 0 else None for i in range(key_frames)]
    if isinstance(track, DynamicRotationTrackT):
        return [get_quaternion_from_packed(track.co[i]) if i < len(track.co) else None for i in range(key_frames)]
    if isinstance(track, (Framed16RotationTrackT, Framed8RotationTrackT)):
        return [get_quaternion_from_packed(track.co[j]) if (j := list(track.frames).index(
            i) if i in track.frames else -1) > -1 else None for i in range(key_frames)]
    return [None] * key_frames


SCALE = 0x7FFF
PI_QUARTER = math.pi / 4.0
PI_HALF = math.pi / 2.0


def expand_float(i: int) -> float:
    """
    Expands packed integer into float.
    :param i: Packed integer.
    :return: Expanded float.
    """
    return i * (PI_HALF / SCALE) - PI_QUARTER


def unpack_48bit_quaternion(x: int, y: int, z: int) -> Quaternion:
    """
    Unpacks 48-bit integer Vector into Blender Quaternion.
    :param x: X value.
    :param y: Y value.
    :param z: Z value.
    :return: Blender Quaternion.
    """
    pack = (z << 32) | (y << 16) | x
    q1 = expand_float((pack >> 3) & 0x7FFF)
    q2 = expand_float((pack >> 18) & 0x7FFF)
    q3 = expand_float((pack >> 33) & 0x7FFF)
    values = [q1, q2, q3]
    max_component = max(1.0 - (q1 * q1 + q2 * q2 + q3 * q3), 0.0)
    max_component = math.sqrt(max_component)
    missing_component = pack & 0B0011
    values.insert(missing_component, max_component)
    is_negative = (pack & 0B0100) != 0
    return (
        Quaternion((values[3], values[0], values[1], values[2]))
        if not is_negative
        else Quaternion((-values[3], -values[0], -values[1], -values[2]))
    )


def get_quaternion_from_packed(vec: Vec3T | sVec3T | None) -> Quaternion | None:
    """
    Converts packed quaternion components into a Quaternion object.
    :param vec: Packed Vector object.
    :return: Quaternion object.
    """
    if vec is None:
        return None
    quat = unpack_48bit_quaternion(vec.x, vec.y, vec.z)
    return quat
