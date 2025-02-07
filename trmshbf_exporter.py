import bpy
from mathutils import Vector
import json
import struct
import random
import sys
import os
from pathlib import Path
import glob
import shutil
from os import path
# import fake_bpy as bpy

TRMBF = ".trmbf"
TRMSH = ".trmsh"

vertFormat = struct.Struct("<fff")
normFormat = struct.Struct("<eeee")
uvFormat = struct.Struct("<ff")
colorFormat = struct.Struct("bbbb")
mtFormat = struct.Struct("<BBBB")
wtFormat = struct.Struct("<HHHH")
polyFormat = struct.Struct("<HHH")

def get_poly_count_for_mat(obj, material_name):
    polyCount = 0
    for poly in obj.data.polygons:
        if obj.data.materials[poly.material_index].name == material_name:
                polyCount += 1
    return polyCount

def write_mesh_data(context, obj, settings):
    if obj.type != "MESH":
        return -1

    bboxco = [Vector(co) for co in obj.bound_box]

    minbbox = min(bboxco)
    maxbbox = max(bboxco)

    bbox = {
        "min": {
            "x": round(minbbox.x, 6),
            "y": round(minbbox.y, 6),
            "z": round(minbbox.z, 6),
        },
        "max": {
            "x": round(maxbbox.x, 6),
            "y": round(maxbbox.y, 6),
            "z": round(maxbbox.z, 6),
        },
    }

    clip_sphere_pos = (minbbox + maxbbox) / 2
    clip_sphere_radius = (maxbbox - minbbox).length / 2

    clip_sphere = {
        "x": round(clip_sphere_pos.x, 6),
        "y": round(clip_sphere_pos.y, 6),
        "z": round(clip_sphere_pos.z, 6),
        "radius": round(clip_sphere_radius, 6),
    }

    vtx_size = vertFormat.size
    vtx_attrs = [
        {
            "attr_0" : 0,
            "attribute": "POSITION",
            "attribute_layer": 0,
            "type": "RGB_32_FLOAT",
            "position": 0,
        }
    ]

    if settings["normal"] == 1:
        vtx_attrs.append(
            {
                "attr_0" : 0,
                "attribute": "NORMAL",
                "attribute_layer": 0,
                "type": "RGBA_16_FLOAT",
                "position": vtx_size,
            }
        )
        vtx_size += normFormat.size

    if settings["tangent"] == 1:
        vtx_attrs.append(
            {
                "attr_0" : 0,
                "attribute": "TANGENT",
                "attribute_layer": 0,
                "type": "RGBA_16_FLOAT",
                "position": vtx_size,
            }
        )
        vtx_size += normFormat.size

    if settings["uv"] == 1:
        for i in range(settings["uv_count"]):
            vtx_attrs.append(
                {
                    "attr_0" : 0,
                    "attribute": "TEXCOORD",
                    "attribute_layer": i,
                    "type": "RG_32_FLOAT",
                    "position": vtx_size,
                },
            )
            vtx_size += uvFormat.size

    if settings["color"] == 1:
        for i in range(settings["color_count"]):
            vtx_attrs.append(
                {
                    "attr_0" : 0,
                    "attribute": "COLOR",
                    "attribute_layer": i,
                    "type": "RGBA_8_UNORM",
                    "position": vtx_size,
                },
            )
            vtx_size += uvFormat.size

    if settings["skinning"] == 1:
        vtx_attrs.append(
            {
                "attr_0" : 0,
                "attribute": "BLEND_INDICES",
                "attribute_layer": 0,
                "type": "RGBA_8_UNSIGNED",
                "position": vtx_size,
            }
        )
        vtx_size += mtFormat.size
        vtx_attrs.append(
            {
                "attr_0" : 0,
                "attribute": "BLEND_WEIGHTS",
                "attribute_layer": 0,
                "type": "RGBA_16_UNORM",
                "position": vtx_size,
            }
        )
        vtx_size += wtFormat.size

    attributes = [{
        "attrs": vtx_attrs,
        "size": [{"size": vtx_size}],
    }]
    materials = []
    for index, material in enumerate(obj.material_slots):
        if material.name != "":
            new_material = {
                "material_name": material.name,
                "poly_offset": 0,
                #"poly_count": len(obj.data.polygons) * 3,
                "poly_count": get_poly_count_for_mat(obj, material.name) * 3,
                "sh_unk3": 0,
                "sh_unk4": 0,
            }
            if len(materials) == 1:
                new_material['poly_offset'] = materials[len(materials) - 1]['poly_count']
            if len(materials) > 1:
                new_material['poly_offset'] = materials[len(materials) - 1]['poly_count'] + materials[len(materials) - 1]['poly_offset']
            materials.append(new_material)
        #materials = [
    #    {
    #        "material_name": obj.material_slots[0].name,
    #        "poly_offset": 0,
    #        "poly_count": len(obj.data.polygons) * 3,
    #        "sh_unk3": 0,
    #        "sh_unk4": 0,
    #    }
    #]

    mesh = {
        "mesh_shape_name": obj.data.name,
        "bounds": bbox,
        "polygon_type": "UINT16",
        "attributes": attributes,
        "materials": materials,
        "clip_sphere": clip_sphere,
        "res0": 0,
        "res1": 0,
        "res2": 0,
        "res3": 0,
        "influence": [
						{
							"index": 1,
							"scale": 36.0
                		}
            ],
        "vis_shapes": [],
        "mesh_name": obj.name,
        "unk13": 0
    }

    return mesh


def write_buffer_data(context, obj, settings, bone_dict):
    if obj.type != "MESH":
        return -1

    mesh = obj.data
    mesh.calc_tangents()

    vert_data = [None] * len(mesh.vertices)
    poly_data = []

    material_data = []

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
            vidx = loop.vertex_index
            pol.append(loop.vertex_index)

            vert = mesh.vertices[vidx]
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

            vert_data[vidx] = vert_d
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
            grps = list([x[0] for x in vert[cursor]])
            vert_bytes += mtFormat.pack(grps[0], grps[1], grps[2], grps[3])

            wgts = list([int(x[1] * 0xFFFF) for x in vert[cursor]])
            vert_bytes += wtFormat.pack(wgts[0], wgts[1], wgts[2], wgts[3])

    data = {
        "index_buffer": [{"buffer": list(poly_bytes)}],
        "vertex_buffer": [{"buffer": list(vert_bytes)}],
    }

    return data

def readbyte(file):
    return int.from_bytes(file.read(1), byteorder='little')

def readshort(file):
    return int.from_bytes(file.read(2), byteorder='little')

# SIGNED!!!!
def readlong(file):
    bytes_data = file.read(4)
    return int.from_bytes(bytes_data, byteorder='little', signed=True)

def readfloat(file):
    return struct.unpack('<f', file.read(4))[0]

def readhalffloat(file):
    return struct.unpack('<e', file.read(2))[0]

def readfixedstring(file, length):
    bytes_data = file.read(length)
    return bytes_data.decode('utf-8')

def fseek(file, offset):
    file.seek(offset)

def ftell(file):
    return file.tell()

def fclose(file):
    file.close()
    
def fopen(file):
    file.open()


def readtrskl(trsklfile):
    trskl = open(trsklfile, "rb")
    bone_array = []
    bone_id_map = {}
    bone_rig_array = []
    trskl_bone_adjust = 0
    print("Parsing TRSKL...")
    trskl_file_start = readlong(trskl)
    fseek(trskl, trskl_file_start)
    trskl_struct = ftell(trskl) - readlong(trskl); fseek(trskl, trskl_struct)
    trskl_struct_len = readshort(trskl)
    
    if trskl_struct_len == 0x000C:
        trskl_struct_section_len = readshort(trskl)
        trskl_struct_start = readshort(trskl)
        trskl_struct_bone = readshort(trskl)
        trskl_struct_b = readshort(trskl)
        trskl_struct_c = readshort(trskl)
        trskl_struct_bone_adjust = 0
    elif trskl_struct_len == 0x000E:
        trskl_struct_section_len = readshort(trskl)
        trskl_struct_start = readshort(trskl)
        trskl_struct_bone = readshort(trskl)
        trskl_struct_b = readshort(trskl)
        trskl_struct_c = readshort(trskl)
        trskl_struct_bone_adjust = readshort(trskl)
    else:
        raise AssertionError("Unexpected TRSKL header struct length!")
    
    if trskl_struct_bone_adjust != 0:
        fseek(trskl, trskl_file_start + trskl_struct_bone_adjust)
        trskl_bone_adjust = readlong(trskl)
        print(f"Mesh node IDs start at {trskl_bone_adjust}")
    
    if trskl_struct_bone != 0:
        fseek(trskl, trskl_file_start + trskl_struct_bone)
        trskl_bone_start = ftell(trskl) + readlong(trskl)
        fseek(trskl, trskl_bone_start)
        bone_count = readlong(trskl)
    
        for x in range(bone_count):
            bone_offset = ftell(trskl) + readlong(trskl)
            bone_ret = ftell(trskl)
            fseek(trskl, bone_offset)
            trskl_bone_struct = ftell(trskl) - readlong(trskl)
            fseek(trskl, trskl_bone_struct)
            trskl_bone_struct_len = readshort(trskl)
    
            if trskl_bone_struct_len == 0x0012:
                trskl_bone_struct_ptr_section_len = readshort(trskl)
                trskl_bone_struct_ptr_string = readshort(trskl)
                trskl_bone_struct_ptr_bone = readshort(trskl)
                trskl_bone_struct_ptr_c = readshort(trskl)
                trskl_bone_struct_ptr_d = readshort(trskl)
                trskl_bone_struct_ptr_parent = readshort(trskl)
                trskl_bone_struct_ptr_rig_id = readshort(trskl)
                trskl_bone_struct_ptr_bone_merge = readshort(trskl)
                trskl_bone_struct_ptr_h = 0
            elif trskl_bone_struct_len == 0x0014:
                trskl_bone_struct_ptr_section_len = readshort(trskl)
                trskl_bone_struct_ptr_string = readshort(trskl)
                trskl_bone_struct_ptr_bone = readshort(trskl)
                trskl_bone_struct_ptr_c = readshort(trskl)
                trskl_bone_struct_ptr_d = readshort(trskl)
                trskl_bone_struct_ptr_parent = readshort(trskl)
                trskl_bone_struct_ptr_rig_id = readshort(trskl)
                trskl_bone_struct_ptr_bone_merge = readshort(trskl)
                trskl_bone_struct_ptr_h = readshort(trskl)
            else:
                trskl_bone_struct_ptr_section_len = readshort(trskl)
                trskl_bone_struct_ptr_string = readshort(trskl)
                trskl_bone_struct_ptr_bone = readshort(trskl)
                trskl_bone_struct_ptr_c = readshort(trskl)
                trskl_bone_struct_ptr_d = readshort(trskl)
                trskl_bone_struct_ptr_parent = readshort(trskl)
                trskl_bone_struct_ptr_rig_id = readshort(trskl)
                trskl_bone_struct_ptr_bone_merge = readshort(trskl)
                trskl_bone_struct_ptr_h = readshort(trskl)
    
            if trskl_bone_struct_ptr_bone_merge != 0:
                fseek(trskl, bone_offset + trskl_bone_struct_ptr_bone_merge)
                bone_merge_start = ftell(trskl) + readlong(trskl)
                fseek(trskl, bone_merge_start)
                bone_merge_string_len = readlong(trskl)
                if bone_merge_string_len != 0:
                    bone_merge_string = readfixedstring(trskl, bone_merge_string_len)
                else:
                    bone_merge_string = ""
    
            if trskl_bone_struct_ptr_bone != 0:
                fseek(trskl, bone_offset + trskl_bone_struct_ptr_bone)
                bone_pos_start = ftell(trskl) + readlong(trskl)
                fseek(trskl, bone_pos_start)
                bone_pos_struct = ftell(trskl) - readlong(trskl)
                fseek(trskl, bone_pos_struct)
                bone_pos_struct_len = readshort(trskl)
    
                if bone_pos_struct_len != 0x000A:
                    raise AssertionError("Unexpected bone position struct length!")
    
                bone_pos_struct_section_len = readshort(trskl)
                bone_pos_struct_ptr_scl = readshort(trskl)
                bone_pos_struct_ptr_rot = readshort(trskl)
                bone_pos_struct_ptr_trs = readshort(trskl)
    
                fseek(trskl, bone_pos_start + bone_pos_struct_ptr_trs)
                bone_tx = readfloat(trskl)
                bone_ty = readfloat(trskl)
                bone_tz = readfloat(trskl)
    
                fseek(trskl, bone_pos_start + bone_pos_struct_ptr_rot)
                bone_rx = readfloat(trskl)
                bone_ry = readfloat(trskl)
                bone_rz = readfloat(trskl)
    
                fseek(trskl, bone_pos_start + bone_pos_struct_ptr_scl)
                bone_sx = readfloat(trskl)
                bone_sy = readfloat(trskl)
                bone_sz = readfloat(trskl)
    
                if trskl_bone_struct_ptr_string != 0:
                    fseek(trskl, bone_offset + trskl_bone_struct_ptr_string)
                    bone_string_start = ftell(trskl) + readlong(trskl)
                    fseek(trskl, bone_string_start)
                    bone_str_len = readlong(trskl)
                    bone_name = readfixedstring(trskl, bone_str_len)
    
                if trskl_bone_struct_ptr_parent != 0x00:
                    fseek(trskl, bone_offset + trskl_bone_struct_ptr_parent)
                    bone_parent = readlong(trskl)
                else:
                    bone_parent = 0
                
                if str(trskl_bone_struct_ptr_rig_id) == "-1":
                    trskl_bone_struct_ptr_rig_id = 99
                if trskl_bone_struct_ptr_rig_id != 0:
                    fseek(trskl, bone_offset + trskl_bone_struct_ptr_rig_id)
                    bone_rig_id = readlong(trskl) + trskl_bone_adjust
    
                    while len(bone_rig_array) <= bone_rig_id:
                        bone_rig_array.append("")
                    bone_rig_array[bone_rig_id] = bone_name
                    bone_id_map[bone_name] = bone_rig_id
    
            fseek(trskl, bone_ret)
    
    fclose(trskl)
    
    bone_dict = {}
    for bone_name, bone_rig_id in bone_id_map.items():
        bone_dict[bone_name] = bone_rig_id
   
    return bone_dict