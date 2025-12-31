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
from Titan.Model.TRSKL import TRSKL

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
    bboxco_x = [Vector(co).x for co in obj.bound_box]
    bboxco_y = [Vector(co).y for co in obj.bound_box]
    bboxco_z = [Vector(co).z for co in obj.bound_box]

    minbbox = Vector((
        min(bboxco_x),
        min(bboxco_y),
        min(bboxco_z)
    ))
    maxbbox = Vector((
        max(bboxco_x),
        max(bboxco_y),
        max(bboxco_z)
    ))

    bbox = {
        "min": {
            "x": round(minbbox.x, 6),
            "y": round(minbbox.y, 6),
            "z": round(minbbox.z, 6)
        },
        "max": {
            "x": round(maxbbox.x, 6),
            "y": round(maxbbox.y, 6),
            "z": round(maxbbox.z, 6)
        }
    }
    clip_sphere_pos = (minbbox + maxbbox) / 2
    clip_sphere_radius = (maxbbox - minbbox).length / 2
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
                "material_name": material.name.split('.')[0],
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
    vert_data = []
    poly_data = []

    for poly in mesh.polygons:
        poly_indices = []

        for loop_index in poly.loop_indices:
            loop = mesh.loops[loop_index]
            vert = mesh.vertices[loop.vertex_index]
            export_index = len(vert_data)
            poly_indices.append(export_index)
            vert_d = []
            co = vert.co
            vert_d.append((co.x, co.y, co.z))
            # Normal (loop)
            if settings.get("normal") == 1:
                n = loop.normal
                vert_d.append((n.x, n.y, n.z))
            # Tangent (loop)
            if settings.get("tangent") == 1:
                t = loop.tangent
                vert_d.append((t.x, t.y, t.z))
            # UV (loop)
            if settings.get("uv") == 1:
                uv = uv_layer[loop_index].uv
                vert_d.append((uv.x, uv.y))
            # Skinning (vertex)
            if settings.get("skinning") == 1:
                groups = []
                for gp in vert.groups:
                    group_name = obj.vertex_groups[gp.group].name
                    if group_name in bone_dict:
                        groups.append((bone_dict[group_name], gp.weight))

                while len(groups) < 4:
                    groups.append((0, 0.0))

                vert_d.append(groups[:4])

            vert_data.append(vert_d)

        poly_data.append(poly_indices)
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


def trskl_to_dict(filepath: str, use_base_trskl: bool = False, base_trskl_path: str = None) -> dict:
    """
    Reads a TRSKL file (optionally using a base TRSKL) and returns a dictionary of bone names to rig IDs.
    
    :param filepath: Path to the main TRSKL file.
    :param use_base_trskl: Whether to use a base TRSKL for merging.
    :param base_trskl_path: Path to the base TRSKL file (required if use_base_trskl is True).
    :return: Dictionary mapping bone names to rig IDs.
    """
    transform_nodes = []
    bones = []

    if use_base_trskl:
        if base_trskl_path is None:
            raise ValueError("base_trskl_path must be provided when use_base_trskl is True.")

        # --- Load base TRSKL ---
        with open(base_trskl_path, "rb") as f:
            buf = bytearray(f.read())
        base_trskl = TRSKL.GetRootAsTRSKL(buf, 0)
        base_transform_nodes = []
        base_name_to_idx = {}
        
        for i in range(base_trskl.TransformNodesLength()):
            node = base_trskl.TransformNodes(i)
            name = node.Name().decode('utf-8')
            base_name_to_idx[name] = len(base_transform_nodes)
            base_transform_nodes.append({
                "name": name,
                "VecTranslateX": node.Transform().VecTranslate().X(),
                "VecTranslateY": node.Transform().VecTranslate().Y(),
                "VecTranslateZ": node.Transform().VecTranslate().Z(),
                "VecScaleX": node.Transform().VecScale().X(),
                "VecScaleY": node.Transform().VecScale().Y(),
                "VecScaleZ": node.Transform().VecScale().Z(),
                "VecRotX": node.Transform().VecRot().X(),
                "VecRotY": node.Transform().VecRot().Y(),
                "VecRotZ": node.Transform().VecRot().Z(),
                "parent_idx": node.ParentIdx(),
                "rig_idx": node.RigIdx(),
                "effect_node": node.EffectNode()
            })

        base_bones = [
            {
                "inherit_scale": bone.InheritScale(),
                "influence_skinning": bone.InfluenceSkinning()
            }
            for bone in (base_trskl.Bones(i) for i in range(base_trskl.BonesLength()))
        ]

        transform_nodes = base_transform_nodes
        bones = base_bones

        # --- Load extra TRSKL ---
        with open(filepath, "rb") as f:
            buf = bytearray(f.read())
        extra_trskl = TRSKL.GetRootAsTRSKL(buf, 0)
        rig_offset = extra_trskl.RigOffset()
        extra_transform_nodes = []

        for i in range(extra_trskl.TransformNodesLength()):
            node = extra_trskl.TransformNodes(i)
            name = node.Name().decode('utf-8')
            rig_idx = node.RigIdx() + rig_offset
            parent_idx = node.ParentIdx()
            effect_node_name = node.EffectNode()

            if effect_node_name:
                effect_node_name = effect_node_name.decode('utf-8')
                if effect_node_name in base_name_to_idx:
                    parent_idx = base_name_to_idx[effect_node_name]
                else:
                    raise ValueError(f"Effect node '{effect_node_name}' not found in base skeleton.")
            else:
                parent_idx += rig_offset

            extra_transform_nodes.append({
                "name": name,
                "VecTranslateX": node.Transform().VecTranslate().X(),
                "VecTranslateY": node.Transform().VecTranslate().Y(),
                "VecTranslateZ": node.Transform().VecTranslate().Z(),
                "VecScaleX": node.Transform().VecScale().X(),
                "VecScaleY": node.Transform().VecScale().Y(),
                "VecScaleZ": node.Transform().VecScale().Z(),
                "VecRotX": node.Transform().VecRot().X(),
                "VecRotY": node.Transform().VecRot().Y(),
                "VecRotZ": node.Transform().VecRot().Z(),
                "parent_idx": parent_idx,
                "rig_idx": rig_idx,
                "effect_node": effect_node_name
            })

        extra_bones = [
            {
                "inherit_scale": bone.InheritScale(),
                "influence_skinning": bone.InfluenceSkinning()
            }
            for bone in (extra_trskl.Bones(i) for i in range(extra_trskl.BonesLength()))
        ]

        transform_nodes += extra_transform_nodes
        bones += extra_bones

    else:
        # --- Load single TRSKL file ---
        with open(filepath, "rb") as f:
            buf = bytearray(f.read())
        trskl_data = TRSKL.GetRootAsTRSKL(buf, 0)

        for i in range(trskl_data.TransformNodesLength()):
            node = trskl_data.TransformNodes(i)
            transform_nodes.append({
                "name": node.Name().decode('utf-8'),
                "VecTranslateX": node.Transform().VecTranslate().X(),
                "VecTranslateY": node.Transform().VecTranslate().Y(),
                "VecTranslateZ": node.Transform().VecTranslate().Z(),
                "VecScaleX": node.Transform().VecScale().X(),
                "VecScaleY": node.Transform().VecScale().Y(),
                "VecScaleZ": node.Transform().VecScale().Z(),
                "VecRotX": node.Transform().VecRot().X(),
                "VecRotY": node.Transform().VecRot().Y(),
                "VecRotZ": node.Transform().VecRot().Z(),
                "parent_idx": node.ParentIdx() + 1,
                "rig_idx": node.RigIdx(),
            })
        for i in range(trskl_data.BonesLength()):
            bone = trskl_data.Bones(i)
            bones.append({
                "inherit_scale": bone.InheritScale(),
                "influence_skinning": bone.InfluenceSkinning(),
            })

    bone_id_map = {node["name"]: node["rig_idx"] for node in transform_nodes}
	
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
    trmsh.bufferName = buffer_name.replace("trskl","trmbf")
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
    mesh_shape.bounds.min.y = mesh_data["bounds"]["min"]["y"]
    mesh_shape.bounds.min.z = mesh_data["bounds"]["min"]["z"]
    mesh_shape.bounds.max = Vec3T()
    mesh_shape.bounds.max.x = mesh_data["bounds"]["max"]["x"]
    mesh_shape.bounds.max.y = mesh_data["bounds"]["max"]["y"]
    mesh_shape.bounds.max.z = mesh_data["bounds"]["max"]["z"]
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
