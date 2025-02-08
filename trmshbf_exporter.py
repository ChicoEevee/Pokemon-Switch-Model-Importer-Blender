"""
    Script for exporting meshes to trmbf and trmsh files.
"""
import struct
import sys
import os
from enum import IntEnum
from io import FileIO

import bpy
import flatbuffers
from mathutils import Vector

sys.path.append(os.path.join(os.path.dirname(__file__), "."))

# pylint: disable=wrong-import-position, import-error, too-many-statements, too-many-branches
# pylint: disable=too-many-locals

from Titan.Model.TRMBF import TRMBFT
from Titan.Model.Buffer import BufferT
from Titan.Model.Indexes import IndexesT
from Titan.Model.TRMSH import TRMSHT
from Titan.Model.Vertices import VerticesT
from Titan.Model.BoundingBox import BoundingBoxT
from Titan.Model.MeshShape import MeshShapeT
from Titan.Model.Vec3 import Vec3T
from Titan.Model.VertexAccessors import VertexAccessorsT
from Titan.Model.Influence import InfluenceT
from Titan.Model.MaterialInfo import MaterialInfoT
from Titan.Model.Sphere import SphereT
from Titan.Model.VertexAccessor import VertexAccessorT
from Titan.Model.VertexSize import VertexSizeT
from Titan.Model.VisShape import VisShapeT

vertFormat = struct.Struct("<fff")
normFormat = struct.Struct("<eeee")
uvFormat = struct.Struct("<ff")
colorFormat = struct.Struct("bbbb")
mtFormat = struct.Struct("<BBBB")
wtFormat = struct.Struct("<HHHH")
polyFormat = struct.Struct("<HHH")


def get_poly_count_for_mat(obj, material_name):
    """
    Returns polygon count for Mesh.
    :param obj: Mesh object.
    :param material_name: Material name.
    :returns: Polygon count.
    """
    poly_count = 0
    for poly in obj.data.polygons:
        if obj.data.materials[poly.material_index].name == material_name:
            poly_count += 1
    return poly_count


class VertexAttribute(IntEnum):
    """
    Enum for VertexAttribute.
    """
    NONE = 0
    POSITION = 1
    NORMAL = 2
    TANGENT = 3
    BINORMAL = 4
    COLOR = 5
    TEXCOORD = 6
    BLEND_INDICES = 7
    BLEND_WEIGHTS = 8
    USER = 9
    USER_ID = 10


class PolygonType(IntEnum):
    """
    Enum for PolygonType.
    """
    UINT8 = 0
    UINT16 = 1
    UINT32 = 2
    UINT64 = 3


class Type(IntEnum):
    """
    Enum for Type.
    """
    NONE = 0
    RGBA_8_UNORM = 20
    RGBA_8_UNSIGNED = 22
    R_32_UINT = 36
    R_32_INT = 37
    RGBA_16_UNORM = 39
    RGBA_16_FLOAT = 43
    RG_32_FLOAT = 48
    RGB_32_FLOAT = 51
    RGBA_32_FLOAT = 54


def get_trmsh_data(obj: bpy.types.Object, settings: dict) -> dict:
    """
    Returns data for TRMSH file from Mesh object.
    :param obj: Mesh object.
    :param settings: Dict of export settings.
    :returns: Dict of TRMSH file data.
    """
    assert obj.type == "MESH", "Selected object is not mesh."
    bbox_co = [Vector(co) for co in obj.bound_box]
    min_bbox = min(bbox_co)
    max_bbox = max(bbox_co)
    bbox = {
        "min": {
            "x": round(min_bbox.x, 6),
            "y": round(min_bbox.y, 6),
            "z": round(min_bbox.z, 6),
        },
        "max": {
            "x": round(max_bbox.x, 6),
            "y": round(max_bbox.y, 6),
            "z": round(max_bbox.z, 6),
        }
    }
    clip_sphere_pos = (min_bbox + max_bbox) / 2
    clip_sphere_radius = (max_bbox - min_bbox).length / 2
    clip_sphere = {
        "x": round(clip_sphere_pos.x, 6),
        "y": round(clip_sphere_pos.y, 6),
        "z": round(clip_sphere_pos.z, 6),
        "radius": round(clip_sphere_radius, 6)
    }
    vtx_size = vertFormat.size
    vtx_attrs = [
        {
            "attr_0": 0,
            "attribute": VertexAttribute.POSITION,
            "attribute_layer": 0,
            "type": Type.RGB_32_FLOAT,
            "position": 0
        }
    ]
    if settings["normal"] == 1:
        vtx_attrs.append(
            {
                "attr_0": 0,
                "attribute": VertexAttribute.NORMAL,
                "attribute_layer": 0,
                "type": Type.RGBA_16_FLOAT,
                "position": vtx_size
            }
        )
        vtx_size += normFormat.size
    if settings["tangent"] == 1:
        vtx_attrs.append(
            {
                "attr_0": 0,
                "attribute": VertexAttribute.TANGENT,
                "attribute_layer": 0,
                "type": Type.RGBA_16_FLOAT,
                "position": vtx_size
            }
        )
        vtx_size += normFormat.size
    if settings["uv"] == 1:
        for i in range(settings["uv_count"]):
            vtx_attrs.append(
                {
                    "attr_0": 0,
                    "attribute": VertexAttribute.TEXCOORD,
                    "attribute_layer": i,
                    "type": Type.RG_32_FLOAT,
                    "position": vtx_size
                },
            )
            vtx_size += uvFormat.size
    if settings["color"] == 1:
        for i in range(settings["color_count"]):
            vtx_attrs.append(
                {
                    "attr_0": 0,
                    "attribute": VertexAttribute.COLOR,
                    "attribute_layer": i,
                    "type": Type.RGBA_8_UNORM,
                    "position": vtx_size
                },
            )
            vtx_size += uvFormat.size
    if settings["skinning"] == 1:
        vtx_attrs.append(
            {
                "attr_0": 0,
                "attribute": VertexAttribute.BLEND_INDICES,
                "attribute_layer": 0,
                "type": Type.RGBA_8_UNSIGNED,
                "position": vtx_size
            }
        )
        vtx_size += mtFormat.size
        vtx_attrs.append(
            {
                "attr_0": 0,
                "attribute": VertexAttribute.BLEND_WEIGHTS,
                "attribute_layer": 0,
                "type": Type.RGBA_16_UNORM,
                "position": vtx_size
            }
        )
        vtx_size += wtFormat.size
    attributes = [{
        "attrs": vtx_attrs,
        "size": [{"size": vtx_size}]
    }]
    materials = []
    for _, material in enumerate(obj.material_slots):
        if material.name != "":
            new_material = {
                "material_name": material.name,
                "poly_offset": 0,
                # "poly_count": len(obj.data.polygons) * 3,
                "poly_count": get_poly_count_for_mat(obj, material.name) * 3,
                "sh_unk3": 0,
                "sh_unk4": 0
            }
            if len(materials) == 1:
                new_material["poly_offset"] = materials[len(materials) - 1]["poly_count"]
            if len(materials) > 1:
                new_material["poly_offset"] = materials[len(materials) - 1]["poly_count"] + \
                                              materials[len(materials) - 1]["poly_offset"]
            materials.append(new_material)
    # materials = [
    #    {
    #        "material_name": obj.material_slots[0].name,
    #        "poly_offset": 0,
    #        "poly_count": len(obj.data.polygons) * 3,
    #        "sh_unk3": 0,
    #        "sh_unk4": 0
    #    }
    # ]
    mesh = {
        "mesh_shape_name": obj.data.name,
        "bounds": bbox,
        "polygon_type": PolygonType.UINT16,
        "attributes": attributes,
        "materials": materials,
        "clip_sphere": clip_sphere,
        "res0": 0,
        "res1": 0,
        "res2": 0,
        "res3": 0,
        "influence": [{"index": 1, "scale": 36.0}],
        "vis_shapes": [],
        "mesh_name": obj.name,
        "unk13": 0
    }
    return mesh


def get_trmbf_data(obj: bpy.types.Object, settings: dict, bone_dict: dict) -> dict:
    """
    Returns data for TRMBF file from Mesh object.
    :param obj: Mesh object.
    :param settings: Dict of export settings.
    :param bone_dict: Dict of armature info from TRSKL file.
    :returns: Dict of TRSKL file data.
    """
    assert obj.type == "MESH", "Selected object is not mesh."
    mesh = obj.data
    mesh.calc_tangents()
    vert_data = [None] * len(mesh.vertices)
    poly_data = []
    # material_data = []
    ## Accumulate all the relevant data
    ## TODO: make it possible later for different presets
    ## for trainers, pokemon, buildings
    # uvs = []
    uv = mesh.uv_layers.active.data
    # if settings["uv"] == 1:
    # uv = mesh.uv_layers.active.data
    for poly in mesh.polygons:
        pol = []
        for loop_index in poly.loop_indices:
            vert_d = []
            loop = mesh.loops[loop_index]
            v_idx = loop.vertex_index
            pol.append(loop.vertex_index)
            vert = mesh.vertices[v_idx]
            pos = (vert.co[0], vert.co[1], vert.co[2])
            vert_d.append(pos)
            if settings["normal"] == 1:
                nor = (loop.normal[0], loop.normal[1], loop.normal[2])
                vert_d.append(nor)
            if settings["tangent"] == 1:
                tan = (loop.tangent[0], loop.tangent[1], loop.tangent[2])
                vert_d.append(tan)
            if settings["uv"] == 1:
                tex = (uv[loop_index].uv[0], uv[loop_index].uv[1])
                vert_d.append(tex)
            if settings["skinning"] == 1:
                grp = []
                for gp in vert.groups:
                    group_name = obj.vertex_groups[gp.group].name
                    if group_name in bone_dict:
                        bone_id = bone_dict[group_name]
                        print("Bone ID:", bone_id)
                        grp.append((bone_id, gp.weight))
                    else:
                        print("Bone not found.")
                while len(grp) < 4:
                    grp.append((0, 0.0))
                grp = grp[0:4]
                vert_d.append(grp)
            vert_data[v_idx] = vert_d
        poly_data.append(pol)
    ## Write poly bytes
    ## TODO: make it possible later for different polytypes
    poly_bytes = b""
    for poly in poly_data:
        poly_bytes += polyFormat.pack(poly[0], poly[1], poly[2])
    ## Write vert bytes
    ## TODO: make it possible later for using different presets
    ## Such as extra UVs for Buildings, extra vertex colors, etc.
    vert_bytes = b""
    for vert in vert_data:
        cursor = 0
        co = vert[cursor]
        vert_bytes += vertFormat.pack(co[0], co[1], co[2])
        cursor += 1
        if settings["normal"] == 1:
            norm = vert[cursor]
            vert_bytes += normFormat.pack(norm[0], norm[1], norm[2], 0.0)
            cursor += 1
        if settings["tangent"] == 1:
            tan = vert[cursor]
            vert_bytes += normFormat.pack(tan[0], tan[1], tan[2], 0.0)
            cursor += 1
        if settings["uv"] == 1:
            tex = vert[cursor]
            vert_bytes += uvFormat.pack(tex[0], tex[1])
            cursor += 1
        if settings["skinning"] == 1:
            groups = [x[0] for x in vert[cursor]]
            vert_bytes += mtFormat.pack(groups[0], groups[1], groups[2], groups[3])
            weights = [int(x[1] * 0xFFFF) for x in vert[cursor]]
            vert_bytes += wtFormat.pack(weights[0], weights[1], weights[2], weights[3])
    data = {
        "index_buffer": [{"buffer": list(poly_bytes)}],
        "vertex_buffer": [{"buffer": list(vert_bytes)}],
    }
    return data


def read_byte(file: FileIO):
    """
    Reads 1 byte of file as 8-bit integer in little endian order.
    """
    return int.from_bytes(file.read(1), byteorder="little")


def read_short(file: FileIO):
    """
    Reads 2 bytes of file as 16-bit integer in little endian order.
    :param file: Target file.
    """
    return int.from_bytes(file.read(2), byteorder="little")


# SIGNED!!!!
def read_long(file: FileIO):
    """
    Reads 4 bytes of file as signed 32-bit integer in little endian order.
    :param file: Target file.
    """
    bytes_data = file.read(4)
    return int.from_bytes(bytes_data, byteorder="little", signed=True)


def read_float(file: FileIO):
    """
    Unpacks 4 bytes of file to 32-bit float.
    :param file: Target file.
    """
    return struct.unpack("<f", file.read(4))[0]


def read_halffloat(file: FileIO):
    """
    Unpacks 2 bytes of file to 16-bit float.
    :param file: Target file.
    """
    return struct.unpack("<e", file.read(2))[0]


def read_fixedstring(file: FileIO, length: int):
    """
    Reads specified amount of file bytes as UTF-8 string.
    :param file: Target file.
    :param length: Bytes amount.
    """
    bytes_data = file.read(length)
    return bytes_data.decode("utf-8")


def f_seek(file: FileIO, offset: int):
    """
    Changes file offset.
    :param file: Target file.
    :param offset: New offset.
    """
    file.seek(offset)


def f_tell(file: FileIO):
    """
    Returns current file's offset.
    :param file: Target file.
    """
    return file.tell()


def f_close(file: FileIO):
    """
    Closes file.
    :param file: Target file.
    """
    file.close()


def f_open(file: FileIO):
    """
    Opens file.
    :param file: Target file.
    """
    file.open()


def trskl_to_dict(filepath: str) -> dict:
    """
    Reads TRSKL file as dictionary for TRMSH and TRMBF export.
    :param filepath: Path to TRSKL file.
    :returns: TRSKL dictionary.
    """
    with open(filepath, "rb") as trskl:
        bone_array = []
        bone_id_map = {}
        bone_rig_array = []
        trskl_bone_adjust = 0
        print("Parsing TRSKL...")
        trskl_file_start = read_long(trskl)
        f_seek(trskl, trskl_file_start)
        trskl_struct = f_tell(trskl) - read_long(trskl);
        f_seek(trskl, trskl_struct)
        trskl_struct_len = read_short(trskl)
        if trskl_struct_len == 0x000C:
            trskl_struct_section_len = read_short(trskl)
            trskl_struct_start = read_short(trskl)
            trskl_struct_bone = read_short(trskl)
            trskl_struct_b = read_short(trskl)
            trskl_struct_c = read_short(trskl)
            trskl_struct_bone_adjust = 0
        elif trskl_struct_len == 0x000E:
            trskl_struct_section_len = read_short(trskl)
            trskl_struct_start = read_short(trskl)
            trskl_struct_bone = read_short(trskl)
            trskl_struct_b = read_short(trskl)
            trskl_struct_c = read_short(trskl)
            trskl_struct_bone_adjust = read_short(trskl)
        else:
            raise AssertionError("Unexpected TRSKL header struct length!")
        if trskl_struct_bone_adjust != 0:
            f_seek(trskl, trskl_file_start + trskl_struct_bone_adjust)
            trskl_bone_adjust = read_long(trskl)
            print(f"Mesh node IDs start at {trskl_bone_adjust}")
        if trskl_struct_bone != 0:
            f_seek(trskl, trskl_file_start + trskl_struct_bone)
            trskl_bone_start = f_tell(trskl) + read_long(trskl)
            f_seek(trskl, trskl_bone_start)
            bone_count = read_long(trskl)
            for x in range(bone_count):
                bone_offset = f_tell(trskl) + read_long(trskl)
                bone_ret = f_tell(trskl)
                f_seek(trskl, bone_offset)
                trskl_bone_struct = f_tell(trskl) - read_long(trskl)
                f_seek(trskl, trskl_bone_struct)
                trskl_bone_struct_len = read_short(trskl)
                if trskl_bone_struct_len == 0x0012:
                    trskl_bone_struct_ptr_section_len = read_short(trskl)
                    trskl_bone_struct_ptr_string = read_short(trskl)
                    trskl_bone_struct_ptr_bone = read_short(trskl)
                    trskl_bone_struct_ptr_c = read_short(trskl)
                    trskl_bone_struct_ptr_d = read_short(trskl)
                    trskl_bone_struct_ptr_parent = read_short(trskl)
                    trskl_bone_struct_ptr_rig_id = read_short(trskl)
                    trskl_bone_struct_ptr_bone_merge = read_short(trskl)
                    trskl_bone_struct_ptr_h = 0
                elif trskl_bone_struct_len == 0x0014:
                    trskl_bone_struct_ptr_section_len = read_short(trskl)
                    trskl_bone_struct_ptr_string = read_short(trskl)
                    trskl_bone_struct_ptr_bone = read_short(trskl)
                    trskl_bone_struct_ptr_c = read_short(trskl)
                    trskl_bone_struct_ptr_d = read_short(trskl)
                    trskl_bone_struct_ptr_parent = read_short(trskl)
                    trskl_bone_struct_ptr_rig_id = read_short(trskl)
                    trskl_bone_struct_ptr_bone_merge = read_short(trskl)
                    trskl_bone_struct_ptr_h = read_short(trskl)
                else:
                    trskl_bone_struct_ptr_section_len = read_short(trskl)
                    trskl_bone_struct_ptr_string = read_short(trskl)
                    trskl_bone_struct_ptr_bone = read_short(trskl)
                    trskl_bone_struct_ptr_c = read_short(trskl)
                    trskl_bone_struct_ptr_d = read_short(trskl)
                    trskl_bone_struct_ptr_parent = read_short(trskl)
                    trskl_bone_struct_ptr_rig_id = read_short(trskl)
                    trskl_bone_struct_ptr_bone_merge = read_short(trskl)
                    trskl_bone_struct_ptr_h = read_short(trskl)
                if trskl_bone_struct_ptr_bone_merge != 0:
                    f_seek(trskl, bone_offset + trskl_bone_struct_ptr_bone_merge)
                    bone_merge_start = f_tell(trskl) + read_long(trskl)
                    f_seek(trskl, bone_merge_start)
                    bone_merge_string_len = read_long(trskl)
                    if bone_merge_string_len != 0:
                        bone_merge_string = read_fixedstring(trskl, bone_merge_string_len)
                    else:
                        bone_merge_string = ""
                if trskl_bone_struct_ptr_bone != 0:
                    f_seek(trskl, bone_offset + trskl_bone_struct_ptr_bone)
                    bone_pos_start = f_tell(trskl) + read_long(trskl)
                    f_seek(trskl, bone_pos_start)
                    bone_pos_struct = f_tell(trskl) - read_long(trskl)
                    f_seek(trskl, bone_pos_struct)
                    bone_pos_struct_len = read_short(trskl)
                    if bone_pos_struct_len != 0x000A:
                        raise AssertionError("Unexpected bone position struct length!")
                    bone_pos_struct_section_len = read_short(trskl)
                    bone_pos_struct_ptr_scl = read_short(trskl)
                    bone_pos_struct_ptr_rot = read_short(trskl)
                    bone_pos_struct_ptr_trs = read_short(trskl)
                    f_seek(trskl, bone_pos_start + bone_pos_struct_ptr_trs)
                    bone_tx = read_float(trskl)
                    bone_ty = read_float(trskl)
                    bone_tz = read_float(trskl)
                    f_seek(trskl, bone_pos_start + bone_pos_struct_ptr_rot)
                    bone_rx = read_float(trskl)
                    bone_ry = read_float(trskl)
                    bone_rz = read_float(trskl)
                    f_seek(trskl, bone_pos_start + bone_pos_struct_ptr_scl)
                    bone_sx = read_float(trskl)
                    bone_sy = read_float(trskl)
                    bone_sz = read_float(trskl)
                    if trskl_bone_struct_ptr_string != 0:
                        f_seek(trskl, bone_offset + trskl_bone_struct_ptr_string)
                        bone_string_start = f_tell(trskl) + read_long(trskl)
                        f_seek(trskl, bone_string_start)
                        bone_str_len = read_long(trskl)
                        bone_name = read_fixedstring(trskl, bone_str_len)
                    if trskl_bone_struct_ptr_parent != 0x00:
                        f_seek(trskl, bone_offset + trskl_bone_struct_ptr_parent)
                        bone_parent = read_long(trskl)
                    else:
                        bone_parent = 0
                    if str(trskl_bone_struct_ptr_rig_id) == "-1":
                        trskl_bone_struct_ptr_rig_id = 99
                    if trskl_bone_struct_ptr_rig_id != 0:
                        f_seek(trskl, bone_offset + trskl_bone_struct_ptr_rig_id)
                        bone_rig_id = read_long(trskl) + trskl_bone_adjust
                        while len(bone_rig_array) <= bone_rig_id:
                            bone_rig_array.append("")
                        bone_rig_array[bone_rig_id] = bone_name
                        bone_id_map[bone_name] = bone_rig_id
                f_seek(trskl, bone_ret)
        f_close(trskl)
        bone_dict = {}
        for bone_name, bone_rig_id in bone_id_map.items():
            bone_dict[bone_name] = bone_rig_id
        return bone_dict


def export_trmbf_trmsh(export_settings: dict, bone_dict: dict,
                       buffer_name: str) -> (int | bytearray | None, int | bytearray | None):
    """
    Exports selected meshes to TRMBF and TRMSH files.
    :param export_settings: Dict of export settings.
    :param bone_dict: Dict of armature information (TRSKL file).
    :param buffer_name: Base name of resulting TRMBF file.
    """
    buffers = []
    meshes = []
    b = False
    for obj in bpy.context.selected_objects:
        if not obj or obj.type != "MESH":
            continue
        buffers.append(create_mesh_buffer(obj, export_settings, bone_dict))
        meshes.append(create_mesh_shape(obj, export_settings))
        b = True
    if not b:
        return None, None
    trmbf = TRMBFT()
    trmbf.buffers = buffers
    builder = flatbuffers.Builder()
    trmbf = trmbf.Pack(builder)
    builder.Finish(trmbf)
    trmbf = builder.Output()
    trmsh = TRMSHT()
    trmsh.meshes = meshes
    trmsh.bufferName = buffer_name
    builder = flatbuffers.Builder()
    trmsh = trmsh.Pack(builder)
    builder.Finish(trmsh)
    trmsh = builder.Output()
    return trmbf, trmsh


def create_mesh_buffer(mesh_obj: bpy.types.Object, export_settings: dict,
                       bone_dict: dict) -> BufferT:
    """
    Creates Buffer object from Mesh and bones info dict.
    :param mesh_obj: Mesh object.
    :param export_settings: Dict of export settings.
    :param bone_dict: Dict of bone info.
    :returns: Buffer object.
    """
    buffer = BufferT()
    buffer_data = get_trmbf_data(mesh_obj, export_settings, bone_dict)
    buffer.morphs = []
    buffer.indexBuffer = []
    buffer.vertexBuffer = []
    for index_buffer_data in buffer_data["index_buffer"]:
        index_buffer = IndexesT()
        index_buffer.buffer = index_buffer_data["buffer"]
        buffer.indexBuffer.append(index_buffer)
    for vertex_buffer_data in buffer_data["vertex_buffer"]:
        vertex_buffer = VerticesT()
        vertex_buffer.buffer = vertex_buffer_data["buffer"]
        buffer.vertexBuffer.append(vertex_buffer)
    return buffer


def create_mesh_shape(mesh_obj: bpy.types.Object, export_settings: dict) -> MeshShapeT:
    """
    Creates MeshShape object from Mesh.
    :param mesh_obj: Mesh object.
    :param export_settings: Dict of export settings.
    :returns: MeshShape object.
    """
    mesh_shape = MeshShapeT()
    mesh_data = get_trmsh_data(mesh_obj, export_settings)
    mesh_shape.meshShapeName = mesh_data["mesh_shape_name"]
    mesh_shape.bounds = BoundingBoxT()
    mesh_shape.bounds.min = Vec3T()
    mesh_shape.bounds.min.x = mesh_data["bounds"]["min"]["x"]
    mesh_shape.bounds.min.x = mesh_data["bounds"]["min"]["y"]
    mesh_shape.bounds.min.x = mesh_data["bounds"]["min"]["z"]
    mesh_shape.bounds.max = Vec3T()
    mesh_shape.bounds.max.x = mesh_data["bounds"]["max"]["x"]
    mesh_shape.bounds.max.x = mesh_data["bounds"]["max"]["y"]
    mesh_shape.bounds.max.x = mesh_data["bounds"]["max"]["z"]
    mesh_shape.polygonType = mesh_data["polygon_type"]
    mesh_shape.attributes = []
    for mesh_data_attribute in mesh_data["attributes"]:
        attribute = VertexAccessorsT()
        attribute.attrs = []
        attribute.size = []
        for mesh_data_attr in mesh_data_attribute["attrs"]:
            attr = VertexAccessorT()
            attr.attr0 = mesh_data_attr["attr_0"]
            attr.attribute = mesh_data_attr["attribute"]
            attr.attributeLayer = mesh_data_attr["attribute_layer"]
            attr.type = mesh_data_attr["type"]
            attr.position = mesh_data_attr["position"]
            attribute.attrs.append(attr)
        for mesh_data_size in mesh_data_attribute["size"]:
            size = VertexSizeT()
            size.size = mesh_data_size["size"]
            attribute.size.append(size)
        mesh_shape.attributes.append(attribute)
    mesh_shape.materials = []
    for mesh_data_material in mesh_data["materials"]:
        material_info = MaterialInfoT()
        material_info.polyCount = mesh_data_material["poly_count"]
        material_info.polyOffset = mesh_data_material["poly_offset"]
        material_info.shUnk3 = mesh_data_material["sh_unk3"]
        material_info.materialName = mesh_data_material["material_name"]
        material_info.shUnk4 = mesh_data_material["sh_unk4"]
        mesh_shape.materials.append(material_info)
    mesh_shape.res0 = mesh_data["res0"]
    mesh_shape.res1 = mesh_data["res1"]
    mesh_shape.res2 = mesh_data["res2"]
    mesh_shape.res3 = mesh_data["res3"]
    mesh_shape.clipSphere = SphereT()
    mesh_shape.clipSphere.x = mesh_data["clip_sphere"]["x"]
    mesh_shape.clipSphere.y = mesh_data["clip_sphere"]["y"]
    mesh_shape.clipSphere.z = mesh_data["clip_sphere"]["z"]
    mesh_shape.clipSphere.radius = mesh_data["clip_sphere"]["radius"]
    mesh_shape.influence = []
    for mesh_data_influence in mesh_data["influence"]:
        influence = InfluenceT()
        influence.index = mesh_data_influence["index"]
        influence.scale = mesh_data_influence["scale"]
        mesh_shape.influence.append(influence)
    mesh_shape.visShapes = []
    for mesh_data_vis_shape in mesh_data["vis_shapes"]:
        vis_shape = VisShapeT()
        vis_shape.index = mesh_data_vis_shape["index"]
        vis_shape.name = mesh_data_vis_shape["name"]
        mesh_shape.visShapes.append(vis_shape)
    mesh_shape.meshName = mesh_data["mesh_name"]
    mesh_shape.unk13 = mesh_data["unk13"]
    return mesh_shape
