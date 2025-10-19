"""
    Script for importing t animation from deserialized trcma file.
"""

import os
import sys
import math

import bpy
from mathutils import Vector, Quaternion, Matrix

sys.path.append(os.path.join(os.path.dirname(__file__), "."))

from Titan.Animation import TRCMA, Vec3, sVec3
from Titan.Animation import RotationTrack, FixedRotationTrack, DynamicRotationTrack, Framed16RotationTrack, Framed8RotationTrack
from Titan.Animation import VectorTrack, FixedVectorTrack, DynamicVectorTrack, Framed16VectorTrack, Framed8VectorTrack
from Titan.Animation import FloatTrack, FixedFloatTrack, DynamicFloatTrack, Framed16FloatTrack, Framed8FloatTrack



def import_trcma(context, file_path: str):
    with open(file_path, "rb") as f:
        buf = f.read()
    base_name = os.path.splitext(os.path.basename(file_path))[0]
    trcma = TRCMA.TRCMA.GetRootAs(buf, 0)
    info = trcma.Info()
    duration = info.Duration()
    fps = info.Framerate()

    cam_anim = trcma.Anim()
    cam_name = cam_anim.CamName().decode("utf-8")

    cam_obj = get_or_create_camera(cam_name)
    empty = bpy.data.objects.new(f"{base_name}_Rig", None)
    add_fov_driver(cam_obj, empty)
    context.collection.objects.link(empty)
    cam_obj.parent = empty
    empty.animation_data_create()
    empty.animation_data.action = bpy.data.actions.new(name=base_name)
    if "fieldofview" not in empty:
        empty["fieldofview"] = 0.0
    anim1 = cam_anim.AnimInfo1()
    for i in range(duration):
        val = get_float_value(anim1.FovType(), anim1.Fov(), i)
        if val is not None:
            empty["fieldofview"] = val
            empty.keyframe_insert(data_path='["fieldofview"]', frame=i)

    anim2 = cam_anim.AnimInfo2()
    for i in range(duration):
        loc = get_vector_value(anim2.TranslationType(), anim2.Translation(), i)
        rot = get_rotation_value(anim2.RotationType(), anim2.Rotation(), i)

        if loc is not None:
            cam_obj.location = loc
            cam_obj.keyframe_insert(data_path="location", frame=i)

        if rot is not None:
            cam_obj.rotation_mode = 'QUATERNION'
            cam_obj.rotation_quaternion = rot
            cam_obj.keyframe_insert(data_path="rotation_quaternion", frame=i)
    if empty.rotation_euler.x != math.radians(90):
        empty.rotation_euler.x += math.radians(90)
def add_fov_driver(cam_obj, empty):
    if "fieldofview" not in empty:
        empty["fieldofview"] = 0.0

    fcurve = cam_obj.data.driver_add("lens")
    driver = fcurve.driver
    driver.type = 'SCRIPTED'

    var = driver.variables.new()
    var.name = "fov"
    var.type = 'SINGLE_PROP'
    targ = var.targets[0]
    targ.id = empty
    targ.data_path = '["fieldofview"]'

    sensor_height = cam_obj.data.sensor_height
    driver.expression = f"{sensor_height}/(2*tan(fov/2))"
    
def get_or_create_camera(cam_name: str) -> bpy.types.Object:
    cam_obj = bpy.data.objects.get(cam_name)
    if cam_obj and cam_obj.type == "CAMERA":
        return cam_obj

    cam_data = bpy.data.cameras.new(name=cam_name)
    cam_obj = bpy.data.objects.new(cam_name, cam_data)
    bpy.context.collection.objects.link(cam_obj)

    return cam_obj

def get_float_value(track_type, track_table, index):
    if track_table is None:
        return None

    if track_type == FloatTrack.FloatTrack().FixedFloatTrack:
        obj = FixedFloatTrack.FixedFloatTrack()
        obj.Init(track_table.Bytes, track_table.Pos)
        return obj.Value()

    if track_type == FloatTrack.FloatTrack().DynamicFloatTrack:
        obj = DynamicFloatTrack.DynamicFloatTrack()
        obj.Init(track_table.Bytes, track_table.Pos)
        if index < obj.ValueLength():
            return obj.Value(index)

    if track_type == FloatTrack.FloatTrack().Framed16FloatTrack:
        obj = Framed16FloatTrack.Framed16FloatTrack()
        obj.Init(track_table.Bytes, track_table.Pos)
        frames = [obj.Frames(i) for i in range(obj.FramesLength())]
        if index in frames:
            j = frames.index(index)
            return obj.Value(j)

    if track_type == FloatTrack.FloatTrack().Framed8FloatTrack:
        obj = Framed8FloatTrack.Framed8FloatTrack()
        obj.Init(track_table.Bytes, track_table.Pos)
        frames = [obj.Frames(i) for i in range(obj.FramesLength())]
        if index in frames:
            j = frames.index(index)
            return obj.Value(j)

    return None


def get_vector_value(track_type, track_table, index):
    if track_table is None:
        return None

    if track_type == VectorTrack.VectorTrack().FixedVectorTrack:
        obj = FixedVectorTrack.FixedVectorTrack()
        obj.Init(track_table.Bytes, track_table.Pos)
        v = obj.Co()
        return Vector((v.X(), v.Y(), v.Z()))

    if track_type == VectorTrack.VectorTrack().DynamicVectorTrack:
        obj = DynamicVectorTrack.DynamicVectorTrack()
        obj.Init(track_table.Bytes, track_table.Pos)
        if index < obj.CoLength():
            v = obj.Co(index)
            return Vector((v.X(), v.Y(), v.Z()))

    if track_type == VectorTrack.VectorTrack().Framed16VectorTrack:
        obj = Framed16VectorTrack.Framed16VectorTrack()
        obj.Init(track_table.Bytes, track_table.Pos)
        frames = [obj.Frames(i) for i in range(obj.FramesLength())]
        if index in frames:
            j = frames.index(index)
            v = obj.Co(j)
            return Vector((v.X(), v.Y(), v.Z()))

    if track_type == VectorTrack.VectorTrack().Framed8VectorTrack:
        obj = Framed8VectorTrack.Framed8VectorTrack()
        obj.Init(track_table.Bytes, track_table.Pos)
        frames = [obj.Frames(i) for i in range(obj.FramesLength())]
        if index in frames:
            j = frames.index(index)
            v = obj.Co(j)
            return Vector((v.X(), v.Y(), v.Z()))

    return None

def get_rotation_value(track_type, track_table, index):
    if track_table is None:
        return None

    if track_type == RotationTrack.RotationTrack().FixedRotationTrack:
        obj = FixedRotationTrack.FixedRotationTrack()
        obj.Init(track_table.Bytes, track_table.Pos)
        return get_quaternion_from_packed(obj.Co())

    if track_type == RotationTrack.RotationTrack().DynamicRotationTrack:
        obj = DynamicRotationTrack.DynamicRotationTrack()
        obj.Init(track_table.Bytes, track_table.Pos)
        if index < obj.CoLength():
            return get_quaternion_from_packed(obj.Co(index))

    if track_type == RotationTrack.RotationTrack().Framed16RotationTrack:
        obj = Framed16RotationTrack.Framed16RotationTrack()
        obj.Init(track_table.Bytes, track_table.Pos)
        frames = [obj.Frames(i) for i in range(obj.FramesLength())]
        if index in frames:
            j = frames.index(index)
            return get_quaternion_from_packed(obj.Co(j))

    if track_type == RotationTrack.RotationTrack().Framed8RotationTrack:
        obj = Framed8RotationTrack.Framed8RotationTrack()
        obj.Init(track_table.Bytes, track_table.Pos)
        frames = [obj.Frames(i) for i in range(obj.FramesLength())]
        if index in frames:
            j = frames.index(index)
            return get_quaternion_from_packed(obj.Co(j))

    return None
    
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
    max_component = max(1.0 - (q1*q1 + q2*q2 + q3*q3), 0.0)
    max_component = math.sqrt(max_component)
    missing_component = pack & 0b0011
    values.insert(missing_component, max_component)
    is_negative = (pack & 0b0100) != 0
    return (
        Quaternion((values[3], values[0], values[1], values[2]))
        if not is_negative
        else Quaternion((-values[3], -values[0], -values[1], -values[2]))
    )

def get_quaternion_from_packed(vec) -> Quaternion | None:
    """
    Converts packed quaternion components into a Quaternion object.
    :param vec: Packed Vector object.
    :return: Quaternion object.
    """
    if vec is None:
        return None
    return unpack_48bit_quaternion(vec.X(), vec.Y(), vec.Z())