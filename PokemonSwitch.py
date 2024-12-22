import os
from os import path
import os.path
import random
import struct
from pathlib import Path
from bpy.props import (BoolProperty,
                       FloatProperty,
                       StringProperty,
                       EnumProperty,
                       CollectionProperty
                       )
from bpy_extras.io_utils import ImportHelper
from bpy.types import (
        Operator,
        OperatorFileListElement,
        )
import bpy
import mathutils
import math
import glob
import shutil
import sys
import numpy as np
import requests
sys.path.append(os.path.join(os.path.dirname(__file__), "."))
from Titan.Model.TRMDL import TRMDL
from Titan.Model.TRSKL import TRSKL

import flatbuffers
IN_BLENDER_ENV = True
blender_version = bpy.app.version

def from_trmdlsv(filep, trmdlname, rare, loadlods, bonestructh = False):
    # make collection
    if IN_BLENDER_ENV:
        new_collection = bpy.data.collections.new(os.path.basename(trmdlname[:-6]))
        bpy.context.scene.collection.children.link(new_collection)


    textureextension = ".png"

    trsklmapped = []
    materials = []
    bone_structure = None
    trskl = None
    trmsh = None
    trmtr = None
    
    trmsh_lods_array = []
    bone_array = []
    bone_id_map = [None] * 1000
    bone_rig_array = []
    trskl_bone_adjust = 0
    chara_check = "None"
    with open(os.path.join(filep, trmdlname), "rb") as f:
        trmdl_content = f.read()
        buf = bytearray(trmdl_content)
    trmdl = TRMDL.GetRootAsTRMDL(buf, 0)
    trmsh_count = trmdl.MeshesLength()
    trmtr_name = trmdl.Materials(0).decode('utf-8')
    if rare == True:
        trmtr = open(os.path.join(filep, Path(trmtr_name).stem + "_rare.trmtr"), "rb")
    else:
        trmtr = open(os.path.join(filep, trmtr_name), "rb") 
    trmsh = trmdl.Meshes(0).Filename().decode('utf-8')
    trmsh_lod1 = trmdl.Meshes(1).Filename().decode('utf-8')
    trmsh_lod2 = trmdl.Meshes(2).Filename().decode('utf-8')
    trmsh_lods_array = [trmsh, trmsh_lod1, trmsh_lod2]
    trskl = trmdl.Skeleton().Filename().decode('utf-8')
    if trmsh.startswith(('au_')): chara_check = "CommonNPC"
    elif trmsh.startswith(('bu_')): chara_check = "CommonNPC"
    elif trmsh.startswith(('cf_')): chara_check = "CommonNPC"
    elif trmsh.startswith(('cm_')): chara_check = "CommonNPC"
    elif trmsh.startswith(('df_')): chara_check = "CommonNPC"
    elif trmsh.startswith(('dm_')): chara_check = "CommonNPC"
    elif trmsh.startswith(('p1_drs')): chara_check = "SVProtag"
    elif trmsh.startswith(('p2_drs')): chara_check = "SVProtag"
    elif trmsh.startswith(('pm')): chara_check = "Pokemon"
    elif trmsh.startswith(('p0')): chara_check = "SVProtag"
    else: chara_check = "None"
    print("Parsing TRMDL...")
    if chara_check == "SVProtag":
        trskl = "../../model_pc_base/model/p0_base.trskl"
    
    if trskl is not None:
        print("Parsing TRSKL...")
        with open(os.path.join(filep, trskl), "rb") as f:
            trskl_content = f.read()
            buf = bytearray(trskl_content)
        trskl = TRSKL.GetRootAsTRSKL(buf, 0)
    
        # Retrieve transform nodes and bones
        transform_nodes = []
        for i in range(trskl.TransformNodesLength()):
            node = trskl.TransformNodes(i)
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
    
        bones = []
        for i in range(trskl.BonesLength()):
            bone = trskl.Bones(i)
            bones.append({
                "inherit_scale": bone.InheritScale(),
                "influence_skinning": bone.InfluenceSkinning(),
            })
        

            
        if IN_BLENDER_ENV:
            new_armature = bpy.data.armatures.new(trmdlname[:-6])
            bone_structure = bpy.data.objects.new(trmdlname[:-6], new_armature)
            new_collection.objects.link(bone_structure)
            bpy.context.view_layer.objects.active = bone_structure
            bpy.ops.object.editmode_toggle()
        for node in transform_nodes:
            rig_idx = node["rig_idx"]
            bone = bones[rig_idx] if rig_idx >= 0 and rig_idx < len(bones) else None
            trsklmapped.append({
                "transform_node": node,
                "bone": bone
            })
        for entry in trsklmapped:
            bone_matrix = mathutils.Matrix.LocRotScale(
                (entry["transform_node"]["VecTranslateX"], entry["transform_node"]["VecTranslateY"], entry["transform_node"]["VecTranslateZ"]),
                mathutils.Euler((entry["transform_node"]["VecRotX"], entry["transform_node"]["VecRotY"], entry["transform_node"]["VecRotZ"])),
                (entry["transform_node"]["VecScaleX"], entry["transform_node"]["VecScaleY"], entry["transform_node"]["VecScaleZ"]))
            
            if IN_BLENDER_ENV:
                new_bone = new_armature.edit_bones.new(entry["transform_node"]["name"])
                new_bone.use_connect = False
                new_bone.use_inherit_rotation = True
                if entry["bone"] != None:
                    if entry["bone"]["inherit_scale"] == False:
                        if blender_version[0] == 4:
                            new_bone.inherit_scale = 'FULL'
                        else:
                            new_bone.use_inherit_scale = True
                
                new_bone.head = (0,0,0)
                new_bone.tail = (0, 0, 0.1)
                new_bone.matrix = bone_matrix
                
                if entry["transform_node"]["parent_idx"] != 0:
                    new_bone.parent = bone_array[entry["transform_node"]["parent_idx"] - 1]
                    new_bone.matrix = bone_array[entry["transform_node"]["parent_idx"] - 1].matrix @ bone_matrix
                if entry["transform_node"]["rig_idx"] >= 0:
                    bone_id_map[entry["transform_node"]["rig_idx"]] = entry["transform_node"]["name"]
                
            bone_array.append(new_bone)
        if IN_BLENDER_ENV:
            bpy.ops.object.editmode_toggle()
    if trmtr is not None:
        print("Parsing TRMTR...")
        trmtr_file_start = readlong(trmtr)
        mat_data_array = []
        fseek(trmtr, trmtr_file_start)
        trmtr_struct = ftell(trmtr) - readlong(trmtr); fseek(trmtr, trmtr_struct)
        trmtr_struct_len = readshort(trmtr)

        if trmtr_struct_len != 0x0008:
            raise AssertionError("Unexpected TRMTR header struct length!")
        trmtr_struct_section_len = readshort(trmtr)
        trmtr_struct_start = readshort(trmtr)
        trmtr_struct_material = readshort(trmtr)

        if trmtr_struct_material != 0:
            fseek(trmtr, trmtr_file_start + trmtr_struct_material)
            mat_start = ftell(trmtr) + readlong(trmtr); fseek(trmtr, mat_start)
            mat_count = readlong(trmtr)
            for x in range(mat_count):
                mat_shader = ""; mat_col0 = ""; mat_lym0 = ""; mat_nrm0 = ""; mat_ao0 = ""; mat_emi0 = ""; mat_rgh0 = ""; mat_mtl0 = ""; mat_msk0 = ""; mat_highmsk0 = ""; mat_sssmask0 = ""
                mat_uv_scale_u = 1.0; mat_uv_scale_v = 1.0; mat_uv_trs_u = 0; mat_uv_trs_v = 0
                mat_uv_scale2_u = 1.0; mat_uv_scale2_v = 1.0; mat_uv_trs2_u = 0; mat_uv_trs2_v = 0
                mat_color_r = 1.0; mat_color_g = 1.0; mat_color_b = 1.0
                mat_color1_r = 1.0; mat_color1_g = 1.0; mat_color1_b = 1.0
                mat_color2_r = 1.0; mat_color2_g = 1.0; mat_color2_b = 1.0
                mat_color3_r = 1.0; mat_color3_g = 1.0; mat_color3_b = 1.0
                mat_color4_r = 12312312.0; mat_color4_g = 12312312.0; mat_color4_b = 12312312.0

                mat_emcolor1_r = 0.0; mat_emcolor1_g = 0.0; mat_emcolor1_b = 0.0
                mat_emcolor2_r = 0.0; mat_emcolor2_g = 0.0; mat_emcolor2_b = 0.0
                mat_emcolor3_r = 0.0; mat_emcolor3_g = 0.0; mat_emcolor3_b = 0.0
                mat_emcolor4_r = 0.0; mat_emcolor4_g = 0.0; mat_emcolor4_b = 0.0
                mat_emcolor5_r = 0.0; mat_emcolor5_g = 0.0; mat_emcolor5_b = 0.0
                mat_ssscolor_r = 0.0; mat_ssscolor_g = 0.0; mat_ssscolor_b = 0.0
                mat_rgh_layer0 = 1.0; mat_rgh_layer1 = 1.0; mat_rgh_layer2 = 1.0; mat_rgh_layer3 = 1.0; mat_rgh_layer4 = 1.0
                mat_mtl_layer0 = 0.0; mat_mtl_layer1 = 0.0; mat_mtl_layer2 = 0.0; mat_mtl_layer3 = 0.0; mat_mtl_layer4 = 0.0
                mat_reflectance = 0.0
                mat_emm_intensity = 1.0
                mat_sss_offset = 0.0
                mat_offset = ftell(trmtr) + readlong(trmtr)
                mat_ret = ftell(trmtr)

                mat_enable_base_color_map = False
                mat_enable_normal_map = False
                mat_enable_ao_map = False
                mat_enable_emission_color_map = False
                mat_enable_roughness_map = False
                mat_enable_metallic_map = False
                mat_enable_displacement_map = False
                mat_enable_highlight_map = False
                mat_num_material_layer = 0
                fseek(trmtr, mat_offset)
                print("--------------------")
                mat_struct = ftell(trmtr) - readlong(trmtr); fseek(trmtr, mat_struct)
                mat_struct_len = readshort(trmtr)

                if mat_struct_len != 0x0024:
                    raise AssertionError("Unexpected material struct length!")
                mat_struct_section_len = readshort(trmtr)
                mat_struct_ptr_param_a = readshort(trmtr)
                mat_struct_ptr_param_b = readshort(trmtr)
                mat_struct_ptr_param_c = readshort(trmtr)
                mat_struct_ptr_param_d = readshort(trmtr)
                mat_struct_ptr_param_e = readshort(trmtr)
                mat_struct_ptr_param_f = readshort(trmtr)
                mat_struct_ptr_param_g = readshort(trmtr)
                mat_struct_ptr_param_h = readshort(trmtr)
                mat_struct_ptr_param_i = readshort(trmtr)
                mat_struct_ptr_param_j = readshort(trmtr)
                mat_struct_ptr_param_k = readshort(trmtr)
                mat_struct_ptr_param_l = readshort(trmtr)
                mat_struct_ptr_param_m = readshort(trmtr)
                mat_struct_ptr_param_n = readshort(trmtr)
                mat_struct_ptr_param_o = readshort(trmtr)
                mat_struct_ptr_param_p = readshort(trmtr)

                if mat_struct_ptr_param_a != 0:
                    fseek(trmtr, mat_offset + mat_struct_ptr_param_a)
                    mat_param_a_start = ftell(trmtr) + readlong(trmtr); fseek(trmtr, mat_param_a_start)
                    mat_name_len = readlong(trmtr)
                    mat_name = readfixedstring(trmtr, mat_name_len)
                    print(f"Material properties for {mat_name}:")
                if mat_struct_ptr_param_b != 0:
                    fseek(trmtr, mat_offset + mat_struct_ptr_param_b)
                    mat_param_b_start = ftell(trmtr) + readlong(trmtr); fseek(trmtr, mat_param_b_start)
                    mat_param_b_section_count = readlong(trmtr)
                    for z in range(mat_param_b_section_count):
                        mat_param_b_offset = ftell(trmtr) + readlong(trmtr)
                        mat_param_b_ret = ftell(trmtr)
                        fseek(trmtr, mat_param_b_offset)
                        mat_param_b_struct = ftell(trmtr) - readlong(trmtr); fseek(trmtr, mat_param_b_struct)
                        mat_param_b_struct_len = readshort(trmtr)

                        if mat_param_b_struct_len != 0x0008:
                            raise AssertionError("Unexpected material param b struct length!")
                        mat_param_b_struct_section_len = readshort(trmtr)
                        mat_param_b_struct_ptr_string = readshort(trmtr)
                        mat_param_b_struct_ptr_params = readshort(trmtr)

                        if mat_param_b_struct_ptr_string != 0:
                            fseek(trmtr, mat_param_b_offset + mat_param_b_struct_ptr_string)
                            mat_param_b_shader_start = ftell(trmtr) + readlong(trmtr); fseek(trmtr, mat_param_b_shader_start)
                            mat_param_b_shader_len = readlong(trmtr)
                            mat_param_b_shader_string = readfixedstring(trmtr, mat_param_b_shader_len)
                            print(f"Shader: {mat_param_b_shader_string}")
                            mat_shader = mat_param_b_shader_string
                        if mat_param_b_struct_ptr_params != 0:
                            fseek(trmtr, mat_param_b_offset + mat_param_b_struct_ptr_params)
                            mat_param_b_sub_start = ftell(trmtr) + readlong(trmtr); fseek(trmtr, mat_param_b_sub_start)
                            mat_param_b_sub_count = readlong(trmtr)
                            for y in range(mat_param_b_sub_count):
                                mat_param_b_sub_offset = ftell(trmtr) + readlong(trmtr)
                                mat_param_b_sub_ret = ftell(trmtr)
                                fseek(trmtr, mat_param_b_sub_offset)
                                mat_param_b_sub_struct = ftell(trmtr) - readlong(trmtr); fseek(trmtr, mat_param_b_sub_struct)
                                mat_param_b_sub_struct_len = readshort(trmtr)

                                if mat_param_b_sub_struct_len != 0x0008:
                                    raise AssertionError("Unexpected material param b sub struct length!")
                                mat_param_b_sub_struct_section_len = readshort(trmtr)
                                mat_param_b_sub_struct_ptr_string = readshort(trmtr)
                                mat_param_b_sub_struct_ptr_value = readshort(trmtr)

                                if mat_param_b_sub_struct_ptr_string != 0:
                                    fseek(trmtr, mat_param_b_sub_offset + mat_param_b_sub_struct_ptr_string)
                                    mat_param_b_sub_string_start = ftell(trmtr) + readlong(trmtr); fseek(trmtr, mat_param_b_sub_string_start)
                                    mat_param_b_sub_string_len = readlong(trmtr)
                                    mat_param_b_sub_string = readfixedstring(trmtr, mat_param_b_sub_string_len)
                                if mat_param_b_sub_struct_ptr_value != 0:
                                    fseek(trmtr, mat_param_b_sub_offset + mat_param_b_sub_struct_ptr_value)
                                    mat_param_b_sub_value_start = ftell(trmtr) + readlong(trmtr); fseek(trmtr, mat_param_b_sub_value_start)
                                    mat_param_b_sub_value_len = readlong(trmtr)
                                    mat_param_b_sub_value = readfixedstring(trmtr, mat_param_b_sub_value_len)
                                    print(f"(param_b) {mat_param_b_sub_string}: {mat_param_b_sub_value}")

                                if mat_param_b_sub_string == "EnableBaseColorMap": mat_enable_base_color_map = mat_param_b_sub_value == "True"
                                if mat_param_b_sub_string == "EnableNormalMap": mat_enable_normal_map = mat_param_b_sub_value == "True"
                                if mat_param_b_sub_string == "EnableAOMap": mat_enable_ao_map = mat_param_b_sub_value == "True"
                                if mat_param_b_sub_string == "EnableEmissionColorMap": mat_enable_emission_color_map = mat_param_b_sub_value == "True"
                                if mat_param_b_sub_string == "EnableRoughnessMap": mat_enable_roughness_map = mat_param_b_sub_value == "True"
                                if mat_param_b_sub_string == "EnableMetallicMap": mat_enable_metallic_map = mat_param_b_sub_value == "True"
                                if mat_param_b_sub_string == "EnableDisplacementMap": mat_enable_displacement_map = mat_param_b_sub_value == "True"
                                if mat_param_b_sub_string == "EnableHighlight": mat_enable_highlight_map = mat_param_b_sub_value == "True"
                                if mat_param_b_sub_string == "EnableOverrideColor": mat_enable_override_color = mat_param_b_sub_value == "True"
                                if mat_param_b_sub_string == "NumMaterialLayer": mat_num_material_layer = int(mat_param_b_sub_value)
                                fseek(trmtr, mat_param_b_sub_ret)
                        fseek(trmtr, mat_param_b_ret)

                if mat_struct_ptr_param_c != 0:
                    fseek(trmtr, mat_offset + mat_struct_ptr_param_c)
                    mat_param_c_start = ftell(trmtr) + readlong(trmtr); fseek(trmtr, mat_param_c_start)
                    mat_param_c_count = readlong(trmtr)

                    for z in range(mat_param_c_count):
                        mat_param_c_offset = ftell(trmtr) + readlong(trmtr)
                        mat_param_c_ret = ftell(trmtr)
                        fseek(trmtr, mat_param_c_offset)
                        mat_param_c_struct = ftell(trmtr) - readlong(trmtr); fseek(trmtr, mat_param_c_struct)
                        mat_param_c_struct_len = readshort(trmtr)

                        if mat_param_c_struct_len == 0x0008:
                            mat_param_c_struct_section_len = readshort(trmtr)
                            mat_param_c_struct_ptr_string = readshort(trmtr)
                            mat_param_c_struct_ptr_value = readshort(trmtr)
                            mat_param_c_struct_ptr_id = 0
                        elif mat_param_c_struct_len == 0x000A:
                            mat_param_c_struct_section_len = readshort(trmtr)
                            mat_param_c_struct_ptr_string = readshort(trmtr)
                            mat_param_c_struct_ptr_value = readshort(trmtr)
                            mat_param_c_struct_ptr_id = readshort(trmtr)
                        else:
                            raise AssertionError("Unexpected material param c struct length!")

                        if mat_param_c_struct_ptr_string != 0:
                            fseek(trmtr, mat_param_c_offset + mat_param_c_struct_ptr_string)
                            mat_param_c_string_start = ftell(trmtr) + readlong(trmtr); fseek(trmtr, mat_param_c_string_start)
                            mat_param_c_string_len = readlong(trmtr)
                            mat_param_c_string = readfixedstring(trmtr, mat_param_c_string_len)
                        if mat_param_c_struct_ptr_value != 0:
                            fseek(trmtr, mat_param_c_offset + mat_param_c_struct_ptr_value)
                            mat_param_c_value_start = ftell(trmtr) + readlong(trmtr); fseek(trmtr, mat_param_c_value_start)
                            mat_param_c_value_len = readlong(trmtr)  # - 5 # Trimming the ".bntx" from the end.
                            mat_param_c_value = readfixedstring(trmtr, mat_param_c_value_len)
                        if mat_param_c_struct_ptr_id != 0:
                            fseek(trmtr, mat_param_c_offset + mat_param_c_struct_ptr_id)
                            mat_param_c_id = readlong(trmtr)
                        else:
                            mat_param_c_id = 0

                        if mat_param_c_string == "BaseColorMap": mat_col0 = mat_param_c_value
                        if mat_param_c_string == "LayerMaskMap": mat_lym0 = mat_param_c_value
                        if mat_param_c_string == "NormalMap": mat_nrm0 = mat_param_c_value
                        if mat_param_c_string == "AOMap": mat_ao0 = mat_param_c_value
                        if mat_param_c_string == "EmissionColorMap": mat_emi0 = mat_param_c_value
                        if mat_param_c_string == "RoughnessMap": mat_rgh0 = mat_param_c_value
                        if mat_param_c_string == "MetallicMap": mat_mtl0 = mat_param_c_value
                        if mat_param_c_string == "DisplacementMap": mat_msk0 = mat_param_c_value
                        if mat_param_c_string == "HighlightMaskMap": mat_highmsk0 = mat_param_c_value
                        if mat_param_c_string == "SSSMaskMap": mat_sssmask0 = mat_param_c_value
                        # -- There's also all of the following, which aren't automatically assigned to keep things simple.
                        # -- "AOMap"
                        # -- "AOMap1"
                        # -- "AOMap2"
                        # -- "BaseColorMap1"
                        # -- "DisplacementMap"
                        # -- "EyelidShadowMaskMap"
                        # -- "FlowMap"
                        # -- "FoamMaskMap"
                        # -- "GrassCollisionMap"
                        # -- "HighlightMaskMap"
                        # -- "LowerEyelidColorMap"
                        # -- "NormalMap1"
                        # -- "NormalMap2"
                        # -- "PackedMap"
                        # -- "UpperEyelidColorMap"
                        # -- "WeatherLayerMaskMap"
                        # -- "WindMaskMap"

                        print(f"(param_c) {mat_param_c_string}: {mat_param_c_value} [{mat_param_c_id}]")
                        fseek(trmtr, mat_param_c_ret)

                if mat_struct_ptr_param_d != 0:
                    fseek(trmtr, mat_offset + mat_struct_ptr_param_d)
                    mat_param_d_start = ftell(trmtr) + readlong(trmtr); fseek(trmtr, mat_param_d_start)
                    mat_param_d_count = readlong(trmtr)

                    for z in range(mat_param_d_count):
                        mat_param_d_offset = ftell(trmtr) + readlong(trmtr)
                        mat_param_d_ret = ftell(trmtr)
                        fseek(trmtr, mat_param_d_offset)
                        mat_param_d_struct = ftell(trmtr) - readlong(trmtr); fseek(trmtr, mat_param_d_struct)
                        mat_param_d_struct_len = readshort(trmtr)

                        if mat_param_d_struct_len != 0x001E:
                            raise AssertionError("Unexpected material param d struct length!")
                        mat_param_d_struct_section_len = readshort(trmtr)
                        mat_param_d_struct_ptr_a = readshort(trmtr)
                        mat_param_d_struct_ptr_b = readshort(trmtr)
                        mat_param_d_struct_ptr_c = readshort(trmtr)
                        mat_param_d_struct_ptr_d = readshort(trmtr)
                        mat_param_d_struct_ptr_e = readshort(trmtr)
                        mat_param_d_struct_ptr_f = readshort(trmtr)
                        mat_param_d_struct_ptr_g = readshort(trmtr)
                        mat_param_d_struct_ptr_h = readshort(trmtr)
                        mat_param_d_struct_ptr_i = readshort(trmtr)
                        mat_param_d_struct_ptr_j = readshort(trmtr)
                        mat_param_d_struct_ptr_k = readshort(trmtr)
                        mat_param_d_struct_ptr_l = readshort(trmtr)
                        mat_param_d_struct_ptr_m = readshort(trmtr)

                        if mat_param_d_struct_ptr_a != 0:
                            fseek(trmtr, mat_param_d_offset + mat_param_d_struct_ptr_a)
                            mat_param_d_value_a = readlong(trmtr)
                        else: mat_param_d_value_a = 0
                        if mat_param_d_struct_ptr_b != 0:
                            fseek(trmtr, mat_param_d_offset + mat_param_d_struct_ptr_b)
                            mat_param_d_value_b = readlong(trmtr)
                        else: mat_param_d_value_b = 0
                        if mat_param_d_struct_ptr_c != 0:
                            fseek(trmtr, mat_param_d_offset + mat_param_d_struct_ptr_c)
                            mat_param_d_value_c = readlong(trmtr)
                        else: mat_param_d_value_c = 0
                        if mat_param_d_struct_ptr_d != 0:
                            fseek(trmtr, mat_param_d_offset + mat_param_d_struct_ptr_d)
                            mat_param_d_value_d = readlong(trmtr)
                        else: mat_param_d_value_d = 0
                        if mat_param_d_struct_ptr_e != 0:
                            fseek(trmtr, mat_param_d_offset + mat_param_d_struct_ptr_e)
                            mat_param_d_value_e = readlong(trmtr)
                        else: mat_param_d_value_e = 0
                        if mat_param_d_struct_ptr_f != 0:
                            fseek(trmtr, mat_param_d_offset + mat_param_d_struct_ptr_f)
                            mat_param_d_value_f = readlong(trmtr)
                        else: mat_param_d_value_f = 0
                        if mat_param_d_struct_ptr_g != 0:
                            fseek(trmtr, mat_param_d_offset + mat_param_d_struct_ptr_g)
                            mat_param_d_value_g = readlong(trmtr)
                        else: mat_param_d_value_g = 0
                        if mat_param_d_struct_ptr_h != 0:
                            fseek(trmtr, mat_param_d_offset + mat_param_d_struct_ptr_h)
                            mat_param_d_value_h = readlong(trmtr)
                        else: mat_param_d_value_h = 0
                        if mat_param_d_struct_ptr_i != 0:
                            fseek(trmtr, mat_param_d_offset + mat_param_d_struct_ptr_i)
                            mat_param_d_value_i = readlong(trmtr)
                        else: mat_param_d_value_i = 0
                        if mat_param_d_struct_ptr_j != 0:
                            fseek(trmtr, mat_param_d_offset + mat_param_d_struct_ptr_j)
                            mat_param_d_value_j = readlong(trmtr)
                        else: mat_param_d_value_j = 0
                        if mat_param_d_struct_ptr_k != 0:
                            fseek(trmtr, mat_param_d_offset + mat_param_d_struct_ptr_k)
                            mat_param_d_value_k = readlong(trmtr)
                        else: mat_param_d_value_k = 0
                        if mat_param_d_struct_ptr_l != 0:
                            fseek(trmtr, mat_param_d_offset + mat_param_d_struct_ptr_l)
                            mat_param_d_value_l = readlong(trmtr)
                        else: mat_param_d_value_l = 0
                        if mat_param_d_struct_ptr_m != 0:
                            fseek(trmtr, mat_param_d_offset + mat_param_d_struct_ptr_m)
                            mat_param_d_value_m1 = readfloat(trmtr); mat_param_d_value_m2 = readfloat(trmtr); mat_param_d_value_m3 = readfloat(trmtr)
                        else: mat_param_d_value_m1 = 0; mat_param_d_value_m2 = 0; mat_param_d_value_m3 = 0

                        print(f"Flags #{z}: {mat_param_d_value_a} | {mat_param_d_value_b} | {mat_param_d_value_c} | {mat_param_d_value_d} | {mat_param_d_value_e} | {mat_param_d_value_f} | {mat_param_d_value_g} | {mat_param_d_value_h} | {mat_param_d_value_i} | {mat_param_d_value_j} | {mat_param_d_value_k} | {mat_param_d_value_l} | {mat_param_d_value_m1} | {mat_param_d_value_m2} | {mat_param_d_value_m3}")
                        fseek(trmtr, mat_param_d_ret)

                if mat_struct_ptr_param_e != 0:
                    fseek(trmtr, mat_offset + mat_struct_ptr_param_e)
                    mat_param_e_start = ftell(trmtr) + readlong(trmtr); fseek(trmtr, mat_param_e_start)
                    mat_param_e_count = readlong(trmtr)

                    for z in range(mat_param_e_count):
                        mat_param_e_offset = ftell(trmtr) + readlong(trmtr)
                        mat_param_e_ret = ftell(trmtr)
                        fseek(trmtr, mat_param_e_offset)
                        mat_param_e_struct = ftell(trmtr) - readlong(trmtr); fseek(trmtr, mat_param_e_struct)
                        mat_param_e_struct_len = readshort(trmtr)

                        if mat_param_e_struct_len == 0x0006:
                            mat_param_e_struct_section_len = readshort(trmtr)
                            mat_param_e_struct_ptr_string = readshort(trmtr)
                            mat_param_e_struct_ptr_value = 0
                        elif mat_param_e_struct_len == 0x0008:
                            mat_param_e_struct_section_len = readshort(trmtr)
                            mat_param_e_struct_ptr_string = readshort(trmtr)
                            mat_param_e_struct_ptr_value = readshort(trmtr)
                        else:
                            raise Exception(f"Unknown mat_param_e struct length!")

                        if mat_param_e_struct_ptr_string != 0:
                            fseek(trmtr, mat_param_e_offset + mat_param_e_struct_ptr_string)
                            mat_param_e_string_start = ftell(trmtr) + readlong(trmtr); fseek(trmtr, mat_param_e_string_start)
                            mat_param_e_string_len = readlong(trmtr)
                            mat_param_e_string = readfixedstring(trmtr, mat_param_e_string_len)

                        if mat_param_e_struct_ptr_value != 0:
                            fseek(trmtr, mat_param_e_offset + mat_param_e_struct_ptr_value)
                            mat_param_e_value = readfloat(trmtr)
                        else: mat_param_e_value = 0

                        if mat_param_e_string == "Roughness": mat_rgh_layer0 = mat_param_e_value
                        elif mat_param_e_string == "RoughnessLayer1": mat_rgh_layer1 = mat_param_e_value
                        elif mat_param_e_string == "RoughnessLayer2": mat_rgh_layer2 = mat_param_e_value
                        elif mat_param_e_string == "RoughnessLayer3": mat_rgh_layer3 = mat_param_e_value
                        elif mat_param_e_string == "RoughnessLayer4": mat_rgh_layer4 = mat_param_e_value
                        elif mat_param_e_string == "Metallic": mat_mtl_layer0 = mat_param_e_value
                        elif mat_param_e_string == "MetallicLayer1": mat_mtl_layer1 = mat_param_e_value
                        elif mat_param_e_string == "MetallicLayer2": mat_mtl_layer2 = mat_param_e_value
                        elif mat_param_e_string == "MetallicLayer3": mat_mtl_layer3 = mat_param_e_value
                        elif mat_param_e_string == "MetallicLayer4": mat_mtl_layer4 = mat_param_e_value
                        elif mat_param_e_string == "Reflectance": mat_reflectance = mat_param_e_value
                        elif mat_param_e_string == "EmissionIntensity": mat_emm_intensity = mat_param_e_value
                        elif mat_param_e_string == "SSSMaskOffset": mat_sss_offset = mat_param_e_value
                        print(f"(param_e) {mat_param_e_string}: {mat_param_e_value}")
                        fseek(trmtr, mat_param_e_ret)

                if mat_struct_ptr_param_f != 0:
                    fseek(trmtr, mat_offset + mat_struct_ptr_param_f)
                    mat_param_f_start = ftell(trmtr) + readlong(trmtr); fseek(trmtr, mat_param_f_start)
                    mat_param_f_count = readlong(trmtr)

                    for z in range(mat_param_f_count):
                        mat_param_f_offset = ftell(trmtr) + readlong(trmtr)
                        mat_param_f_ret = ftell(trmtr)
                        fseek(trmtr, mat_param_f_offset)
                        mat_param_f_struct = ftell(trmtr) - readlong(trmtr); fseek(trmtr, mat_param_f_struct)
                        mat_param_f_struct_len = readlong(trmtr)

                        if mat_param_f_struct_len != 0x0008:
                            raise Exception(f"Unknown mat_param_f struct length!")
                        mat_param_f_struct_section_len = readshort(trmtr)
                        mat_param_f_struct_ptr_string = readshort(trmtr)
                        mat_param_f_struct_ptr_values = readshort(trmtr)

                        if mat_param_f_struct_ptr_string != 0:
                            fseek(trmtr, mat_param_f_offset + mat_param_f_struct_ptr_string)
                            mat_param_f_string_start = ftell(trmtr) + readlong(trmtr); fseek(trmtr, mat_param_f_string_start)
                            mat_param_f_string_len = readlong(trmtr)
                            mat_param_f_string = readfixedstring(trmtr, mat_param_f_string_len)

                        if mat_param_f_struct_ptr_values != 0:
                            fseek(trmtr, mat_param_f_offset + mat_param_f_struct_ptr_values)
                            mat_param_f_value1 = readfloat(trmtr)
                            mat_param_f_value2 = readfloat(trmtr)
                        else: mat_param_f_value1 = mat_param_f_value2 = 0

                        print(f"(param_f) {mat_param_f_string}: {mat_param_f_value1}, {mat_param_f_value2}")
                        fseek(trmtr, mat_param_f_ret)

                if mat_struct_ptr_param_g != 0:
                    fseek(trmtr, mat_offset + mat_struct_ptr_param_g)
                    mat_param_g_start = ftell(trmtr) + readlong(trmtr); fseek(trmtr, mat_param_g_start)
                    mat_param_g_count = readlong(trmtr)

                    for z in range(mat_param_g_count):
                        mat_param_g_offset = ftell(trmtr) + readlong(trmtr)
                        mat_param_g_ret = ftell(trmtr)
                        fseek(trmtr, mat_param_g_offset)
                        mat_param_g_struct = ftell(trmtr) - readlong(trmtr); fseek(trmtr, mat_param_g_struct)
                        mat_param_g_struct_len = readlong(trmtr)

                        if mat_param_g_struct_len != 0x0008:
                            raise Exception(f"Unknown mat_param_g struct length!")
                        mat_param_g_struct_section_len = readshort(trmtr)
                        mat_param_g_struct_ptr_string = readshort(trmtr)
                        mat_param_g_struct_ptr_values = readshort(trmtr)

                        if mat_param_g_struct_ptr_string != 0:
                            fseek(trmtr, mat_param_g_offset + mat_param_g_struct_ptr_string)
                            mat_param_g_string_start = ftell(trmtr) + readlong(trmtr); fseek(trmtr, mat_param_g_string_start)
                            mat_param_g_string_len = readlong(trmtr)
                            mat_param_g_string = readfixedstring(trmtr, mat_param_g_string_len)

                        if mat_param_g_struct_ptr_values != 0:
                            fseek(trmtr, mat_param_g_offset + mat_param_g_struct_ptr_values)
                            mat_param_g_value1 = readfloat(trmtr)
                            mat_param_g_value2 = readfloat(trmtr)
                            mat_param_g_value3 = readfloat(trmtr)
                        else: mat_param_g_value1 = mat_param_g_value2 = mat_param_g_value3 = 0

                        print(f"(param_g) {mat_param_g_string}: {mat_param_g_value1}, {mat_param_g_value2}, {mat_param_g_value3}")
                        fseek(trmtr, mat_param_g_ret)

                if mat_struct_ptr_param_h != 0:
                    fseek(trmtr, mat_offset + mat_struct_ptr_param_h)
                    mat_param_h_start = ftell(trmtr) + readlong(trmtr); fseek(trmtr, mat_param_h_start)
                    mat_param_h_count = readlong(trmtr)

                    for z in range(mat_param_h_count):
                        mat_param_h_offset = ftell(trmtr) + readlong(trmtr)
                        mat_param_h_ret = ftell(trmtr)
                        fseek(trmtr, mat_param_h_offset)
                        mat_param_h_struct = ftell(trmtr) - readlong(trmtr); fseek(trmtr, mat_param_h_struct)
                        mat_param_h_struct_len = readshort(trmtr)

                        if mat_param_h_struct_len != 0x0008:
                            raise Exception(f"Unknown mat_param_h struct length!")
                        mat_param_h_struct_section_len = readshort(trmtr)
                        mat_param_h_struct_ptr_string = readshort(trmtr)
                        mat_param_h_struct_ptr_values = readshort(trmtr)

                        if mat_param_h_struct_ptr_string != 0:
                            fseek(trmtr, mat_param_h_offset + mat_param_h_struct_ptr_string)
                            mat_param_h_string_start = ftell(trmtr) + readlong(trmtr); fseek(trmtr, mat_param_h_string_start)
                            mat_param_h_string_len = readlong(trmtr)
                            mat_param_h_string = readfixedstring(trmtr, mat_param_h_string_len)

                        if mat_param_h_struct_ptr_values != 0:
                            fseek(trmtr, mat_param_h_offset + mat_param_h_struct_ptr_values)
                            mat_param_h_value1 = readfloat(trmtr)
                            mat_param_h_value2 = readfloat(trmtr)
                            mat_param_h_value3 = readfloat(trmtr)
                            mat_param_h_value4 = readfloat(trmtr)
                        else: mat_param_h_value1 = mat_param_h_value2 = mat_param_h_value3 = mat_param_h_value4 = 0

                        if mat_param_h_string == "UVScaleOffset": mat_uv_scale_u = mat_param_h_value1; mat_uv_scale_v = mat_param_h_value2; mat_uv_trs_u = mat_param_h_value3; mat_uv_trs_v = mat_param_h_value4
                        elif mat_param_h_string == "UVScaleOffset1": mat_uv_scale2_u = mat_param_h_value1; mat_uv_scale2_v = mat_param_h_value2; mat_uv_trs2_u = mat_param_h_value3; mat_uv_trs2_v = mat_param_h_value4
                        elif mat_param_h_string == "BaseColor": mat_color_r = mat_param_h_value1; mat_color_g = mat_param_h_value2; mat_color_b = mat_param_h_value3
                        elif mat_param_h_string == "BaseColorLayer1": mat_color1_r = mat_param_h_value1; mat_color1_g = mat_param_h_value2; mat_color1_b = mat_param_h_value3
                        elif mat_param_h_string == "BaseColorLayer2": mat_color2_r = mat_param_h_value1; mat_color2_g = mat_param_h_value2; mat_color2_b = mat_param_h_value3
                        elif mat_param_h_string == "BaseColorLayer3": mat_color3_r = mat_param_h_value1; mat_color3_g = mat_param_h_value2; mat_color3_b = mat_param_h_value3
                        elif mat_param_h_string == "BaseColorLayer4": mat_color4_r = mat_param_h_value1; mat_color4_g = mat_param_h_value2; mat_color4_b = mat_param_h_value3
                        elif mat_param_h_string == "EmissionColorLayer1": mat_emcolor1_r = mat_param_h_value1; mat_emcolor1_g = mat_param_h_value2; mat_emcolor1_b = mat_param_h_value3
                        elif mat_param_h_string == "EmissionColorLayer2": mat_emcolor2_r = mat_param_h_value1; mat_emcolor2_g = mat_param_h_value2; mat_emcolor2_b = mat_param_h_value3
                        elif mat_param_h_string == "EmissionColorLayer3": mat_emcolor3_r = mat_param_h_value1; mat_emcolor3_g = mat_param_h_value2; mat_emcolor3_b = mat_param_h_value3
                        elif mat_param_h_string == "EmissionColorLayer4": mat_emcolor4_r = mat_param_h_value1; mat_emcolor4_g = mat_param_h_value2; mat_emcolor4_b = mat_param_h_value3
                        elif mat_param_h_string == "EmissionColorLayer5": mat_emcolor5_r = mat_param_h_value1; mat_emcolor5_g = mat_param_h_value2; mat_emcolor5_b = mat_param_h_value3
                        elif mat_param_h_string == "SubsurfaceColor":  mat_ssscolor_r = mat_param_h_value1; mat_ssscolor_g = mat_param_h_value2; mat_ssscolor_b = mat_param_h_value3
                        else: print(f"Unknown mat_param_h: {mat_param_h_string}")

                        print(f"(param_h) {mat_param_h_string}: {mat_param_h_value1}, {mat_param_h_value2}, {mat_param_h_value3}, {mat_param_h_value4}")
                        fseek(trmtr, mat_param_h_ret)

                if mat_struct_ptr_param_i != 0:
                    fseek(trmtr, mat_offset + mat_struct_ptr_param_i)
                    mat_param_i_start = ftell(trmtr) + readlong(trmtr); fseek(trmtr, mat_param_i_start)
                    mat_param_i_struct = ftell(trmtr) - readlong(trmtr); fseek(trmtr, mat_param_i_struct)
                    mat_param_i_struct_len = readlong(trmtr)

                    if mat_param_i_struct_len != 0x0000:
                        raise Exception(f"Unknown mat_param_i struct length!")

                if mat_struct_ptr_param_j != 0:
                    fseek(trmtr, mat_offset + mat_struct_ptr_param_j)
                    mat_param_j_start = ftell(trmtr) + readlong(trmtr); fseek(trmtr, mat_param_j_start)
                    mat_param_j_count = readlong(trmtr)

                    for y in range(mat_param_j_count):
                        mat_param_j_offset = ftell(trmtr) + readlong(trmtr)
                        mat_param_j_ret = ftell(trmtr)
                        fseek(trmtr, mat_param_j_offset)
                        mat_param_j_struct = ftell(trmtr) - readlong(trmtr); fseek(trmtr, mat_param_j_struct)
                        mat_param_j_struct_len = readshort(trmtr)

                        if mat_param_j_struct_len == 0x0006:
                            mat_param_j_struct_section_len = readshort(trmtr)
                            mat_param_j_struct_ptr_string = readshort(trmtr)
                            mat_param_j_struct_ptr_value = 0
                        elif mat_param_j_struct_len == 0x0008:
                            mat_param_j_struct_section_len = readshort(trmtr)
                            mat_param_j_struct_ptr_string = readshort(trmtr)
                            mat_param_j_struct_ptr_value = readshort(trmtr)
                        else:
                            raise Exception(f"Unknown mat_param_j struct length!")

                        if mat_param_j_struct_ptr_string != 0:
                            fseek(trmtr, mat_param_j_offset + mat_param_j_struct_ptr_string)
                            mat_param_j_string_start = ftell(trmtr) + readlong(trmtr); fseek(trmtr, mat_param_j_string_start)
                            mat_param_j_string_len = readlong(trmtr)
                            mat_param_j_string = readfixedstring(trmtr, mat_param_j_string_len)

                        if mat_param_j_struct_ptr_value != 0:
                            fseek(trmtr, mat_param_j_offset + mat_param_j_struct_ptr_value)
                            mat_param_j_value = readlong(trmtr)
                        else: mat_param_j_value = "0" # why is this a string?

                        print(f"(param_j) {mat_param_j_string}: {mat_param_j_value}")
                        fseek(trmtr, mat_param_j_ret)

                if mat_struct_ptr_param_k != 0:
                    fseek(trmtr, mat_offset + mat_struct_ptr_param_k)
                    mat_param_k_start = ftell(trmtr) + readlong(trmtr); fseek(trmtr, mat_param_k_start)
                    mat_param_k_struct = ftell(trmtr) - readlong(trmtr); fseek(trmtr, mat_param_k_struct)
                    mat_param_k_struct_len = readlong(trmtr)

                    if mat_param_k_struct_len != 0x0000:
                        raise Exception(f"Unexpected mat_param_k struct length!")

                if mat_struct_ptr_param_l != 0:
                    fseek(trmtr, mat_offset + mat_struct_ptr_param_l)
                    mat_param_l_start = ftell(trmtr) + readlong(trmtr); fseek(trmtr, mat_param_l_start)
                    mat_param_l_struct = ftell(trmtr) - readlong(trmtr); fseek(trmtr, mat_param_l_struct)
                    mat_param_l_struct_len = readlong(trmtr)

                    if mat_param_l_struct_len != 0x0000:
                        raise Exception(f"Unexpected mat_param_l struct length!")

                if mat_struct_ptr_param_m != 0:
                    fseek(trmtr, mat_offset + mat_struct_ptr_param_m)
                    mat_param_m_start = ftell(trmtr) + readlong(trmtr); fseek(trmtr, mat_param_m_start)
                    mat_param_m_struct = ftell(trmtr) - readlong(trmtr); fseek(trmtr, mat_param_m_struct)
                    mat_param_m_struct_len = readlong(trmtr)

                    if mat_param_m_struct_len != 0x0000:
                        raise Exception(f"Unexpected mat_param_m struct length!")

                if mat_struct_ptr_param_n != 0:
                    fseek(trmtr, mat_offset + mat_struct_ptr_param_n)
                    mat_param_n_start = ftell(trmtr) + readlong(trmtr); fseek(trmtr, mat_param_n_start)
                    mat_param_n_struct = ftell(trmtr) - readlong(trmtr); fseek(trmtr, mat_param_n_struct)
                    mat_param_n_struct_len = readshort(trmtr)

                    if mat_param_n_struct_len == 0x0004:
                        mat_param_n_struct_section_len = readshort(trmtr)
                        mat_param_n_struct_unk = 0
                    elif mat_param_n_struct_len == 0x0006:
                        mat_param_n_struct_section_len = readshort(trmtr)
                        mat_param_n_struct_unk = readshort(trmtr)
                    else:
                        raise Exception(f"Unexpected mat_param_n struct length!")

                    if mat_param_n_struct_unk != 0:
                        fseek(trmtr, mat_param_n_start + mat_param_n_struct_unk)
                        mat_param_n_value =  readbyte(trmtr)
                        print(f"Unknown value A = {mat_param_n_value}")

                if mat_struct_ptr_param_o != 0:
                    fseek(trmtr, mat_offset + mat_struct_ptr_param_o)
                    mat_param_o_start = ftell(trmtr) + readlong(trmtr); fseek(trmtr, mat_param_o_start)
                    mat_param_o_struct = ftell(trmtr) - readlong(trmtr); fseek(trmtr, mat_param_o_struct)
                    mat_param_o_struct_len = readshort(trmtr)

                    if mat_param_o_struct_len == 0x0004:
                        mat_param_o_struct_section_len = readshort(trmtr)
                        mat_param_o_struct_unk = 0
                        mat_param_o_struct_value = 0
                    elif mat_param_o_struct_len == 0x0008:
                        mat_param_o_struct_section_len = readshort(trmtr)
                        mat_param_o_struct_unk = readshort(trmtr)
                        mat_param_o_struct_value = readshort(trmtr)
                    else:
                        raise Exception(f"Unexpected mat_param_o struct length!")

                    if mat_param_o_struct_unk != 0:
                        fseek(trmtr, mat_param_o_start + mat_param_o_struct_unk)
                        mat_param_o_value =  readbyte(trmtr)
                        print(f"Unknown value B = {mat_param_o_value}")

                if mat_struct_ptr_param_p != 0:
                    fseek(trmtr, mat_offset + mat_struct_ptr_param_p)
                    mat_param_p_start = ftell(trmtr) + readlong(trmtr); fseek(trmtr, mat_param_p_start)
                    mat_param_p_string_len = readlong(trmtr)
                    mat_param_p_string = readfixedstring(trmtr, mat_param_p_string_len)
                    print(mat_param_p_string)

                mat_data_array.append({
                    "mat_name": mat_name,
                    "mat_shader": mat_shader,
                    "mat_col0": mat_col0,
                    "mat_lym0": mat_lym0,
                    "mat_nrm0": mat_nrm0,
                    "mat_ao0": mat_ao0,
                    "mat_emi0": mat_emi0,
                    "mat_rgh0": mat_rgh0,
                    "mat_mtl0": mat_mtl0,
                    "mat_msk0": mat_msk0,
                    "mat_highmsk0": mat_highmsk0,
                    "mat_sssmask0": mat_sssmask0,
                    "mat_color_r": mat_color_r, "mat_color_g": mat_color_g, "mat_color_b": mat_color_b,
                    "mat_color1_r": mat_color1_r, "mat_color1_g": mat_color1_g, "mat_color1_b": mat_color1_b,
                    "mat_color2_r": mat_color2_r, "mat_color2_g": mat_color2_g, "mat_color2_b": mat_color2_b,
                    "mat_color3_r": mat_color3_r, "mat_color3_g": mat_color3_g, "mat_color3_b": mat_color3_b,
                    "mat_color4_r": mat_color4_r, "mat_color4_g": mat_color4_g, "mat_color4_b": mat_color4_b,
                    "mat_emcolor1_r": mat_emcolor1_r, "mat_emcolor1_g": mat_emcolor1_g, "mat_emcolor1_b": mat_emcolor1_b,
                    "mat_emcolor2_r": mat_emcolor2_r, "mat_emcolor2_g": mat_emcolor2_g, "mat_emcolor2_b": mat_emcolor2_b,
                    "mat_emcolor3_r": mat_emcolor3_r, "mat_emcolor3_g": mat_emcolor3_g, "mat_emcolor3_b": mat_emcolor3_b,
                    "mat_emcolor4_r": mat_emcolor4_r, "mat_emcolor4_g": mat_emcolor4_g, "mat_emcolor4_b": mat_emcolor4_b,
                    "mat_emcolor5_r": mat_emcolor5_r, "mat_emcolor5_g": mat_emcolor5_g, "mat_emcolor5_b": mat_emcolor5_b,
                    "mat_ssscolor_r": mat_ssscolor_r, "mat_ssscolor_g": mat_ssscolor_g, "mat_ssscolor_b": mat_ssscolor_b,
                    "mat_rgh_layer0": mat_rgh_layer0, "mat_rgh_layer1": mat_rgh_layer1, "mat_rgh_layer2": mat_rgh_layer2, "mat_rgh_layer3": mat_rgh_layer3, "mat_rgh_layer4": mat_rgh_layer4,
                    "mat_mtl_layer0": mat_mtl_layer0, "mat_mtl_layer1": mat_mtl_layer1, "mat_mtl_layer2": mat_mtl_layer2, "mat_mtl_layer3": mat_mtl_layer3, "mat_mtl_layer4": mat_mtl_layer4,
                    "mat_reflectance": mat_reflectance,
                    "mat_emm_intensity": mat_emm_intensity,
                    "mat_sss_offset": mat_sss_offset,
                    "mat_uv_scale_u": mat_uv_scale_u, "mat_uv_scale_v": mat_uv_scale_v,
                    "mat_uv_scale2_u": mat_uv_scale2_u, "mat_uv_scale2_v": mat_uv_scale2_v,
                    "mat_enable_base_color_map": mat_enable_base_color_map,
                    "mat_enable_normal_map": mat_enable_normal_map,
                    "mat_enable_ao_map": mat_enable_ao_map,
                    "mat_enable_emission_color_map": mat_enable_emission_color_map,
                    "mat_enable_roughness_map": mat_enable_roughness_map,
                    "mat_enable_metallic_map": mat_enable_metallic_map,
                    "mat_enable_displacement_map": mat_enable_displacement_map,
                    "mat_enable_highlight_map": mat_enable_highlight_map,
                    "mat_num_material_layer": mat_num_material_layer
                })
                fseek(trmtr, mat_ret)
            print("--------------------")
        mat_data_array = sorted(mat_data_array, key=lambda x: x['mat_name'])

        fclose(trmtr)
        
        if IN_BLENDER_ENV:
            addons_path = bpy.utils.user_resource('SCRIPTS')

            if not 'ScViShader' in bpy.data.materials or not 'ScViShader' in bpy.data.materials:
                try:
                    response = requests.get("https://github.com/ChicoEevee/Pokemon-Switch-V2-Model-Importer-Blender/raw/refs/heads/main/SCVIShader.blend", stream=True)
                    with open(os.path.join(addons_path,"addons/SCVIShader.blend"), 'wb') as file:
                        file.write(response.content)
                except:
                    print("Offline Mode")
                with bpy.data.libraries.load(os.path.join(addons_path,"addons/SCVIShader.blend"), link=False) as (data_from, data_to):
                    data_to.materials = data_from.materials
                    print('! Loaded shader blend file.')
            for m, mat in enumerate(mat_data_array):
                if "eye" in mat["mat_name"] and "pm" in trmtr.name:
                    material = bpy.data.materials["ScViMonEyeShader"].copy()
                else:
                    material = bpy.data.materials["ScViShader"].copy()
                    
                material.name = mat["mat_name"]
                materials.append(material)
                shadegroupnodes = material.node_tree.nodes['Group']
                try:
                    shadegroupnodes.inputs['BaseColor'].default_value = (mat["mat_color_r"], mat["mat_color_g"], mat["mat_color_b"], 1.0)
                except:
                    print("")
                if os.path.exists(os.path.join(filep, mat["mat_lym0"][:-5] + textureextension)) == True:
                    lym_image_texture = material.node_tree.nodes.new("ShaderNodeTexImage")
                    lym_image_texture.image = bpy.data.images.load(os.path.join(filep, mat["mat_lym0"][:-5] + textureextension))
                    lym_image_texture.image.colorspace_settings.name = "Non-Color"
                
                color1 = (mat["mat_color1_r"], mat["mat_color1_g"], mat["mat_color1_b"], 1.0)
                color2 = (mat["mat_color2_r"], mat["mat_color2_g"], mat["mat_color2_b"], 1.0)
                color3 = (mat["mat_color3_r"], mat["mat_color3_g"], mat["mat_color3_b"], 1.0)
                color4 = (mat["mat_color4_r"], mat["mat_color4_g"], mat["mat_color4_b"], 1.0)
                emcolor1 = (mat["mat_emcolor1_r"], mat["mat_emcolor1_g"], mat["mat_emcolor1_b"], 1.0)
                emcolor2 = (mat["mat_emcolor2_r"], mat["mat_emcolor2_g"], mat["mat_emcolor2_b"], 1.0)
                emcolor3 = (mat["mat_emcolor3_r"], mat["mat_emcolor3_g"], mat["mat_emcolor3_b"], 1.0)                   
                emcolor4 = (mat["mat_emcolor4_r"], mat["mat_emcolor4_g"], mat["mat_emcolor4_b"], 1.0)
                shadegroupnodes.inputs['BaseColorLayer1'].default_value = color1
                shadegroupnodes.inputs['BaseColorLayer2'].default_value = color2
                shadegroupnodes.inputs['BaseColorLayer3'].default_value = color3
                shadegroupnodes.inputs['BaseColorLayer4'].default_value = color4
                shadegroupnodes.inputs['EmissionColorLayer1'].default_value = emcolor1
                shadegroupnodes.inputs['EmissionColorLayer2'].default_value = emcolor2
                shadegroupnodes.inputs['EmissionColorLayer3'].default_value = emcolor3
                shadegroupnodes.inputs['EmissionColorLayer4'].default_value = emcolor4
                if os.path.exists(os.path.join(filep, mat["mat_lym0"][:-5] + textureextension)) == True:
                    lym_image_texture = material.node_tree.nodes.new("ShaderNodeTexImage")
                    lym_image_texture.image = bpy.data.images.load(os.path.join(filep, mat["mat_lym0"][:-5] + textureextension))
                    lym_image_texture.image.colorspace_settings.name = "Non-Color"
                    material.node_tree.links.new(lym_image_texture.outputs[0], shadegroupnodes.inputs['Lym_color'])
                    if color4 != (12312312.0,12312312.0,12312312.0,1.0):
                        material.node_tree.links.new(lym_image_texture.outputs[1], shadegroupnodes.inputs['Lym_alpha'])
                if os.path.exists(os.path.join(filep, mat["mat_col0"][:-5] + textureextension)) == True:
                    alb_image_texture = material.node_tree.nodes.new("ShaderNodeTexImage")
                    alb_image_texture.image = bpy.data.images.load(os.path.join(filep, mat["mat_col0"][:-5] + textureextension))
                    material.node_tree.links.new(alb_image_texture.outputs[0], shadegroupnodes.inputs['Albedo'])
                    material.node_tree.links.new(alb_image_texture.outputs[1], shadegroupnodes.inputs['AlbedoAlpha'])


                if mat["mat_enable_highlight_map"]:
                    highlight_image_texture = material.node_tree.nodes.new("ShaderNodeTexImage")                        
                    if os.path.exists(os.path.join(filep, mat["mat_highmsk0"][:-5] + ".png")) == True:
                        highlight_image_texture.image = bpy.data.images.load(os.path.join(filep, mat["mat_highmsk0"][:-5] + ".png"))
                        highlight_image_texture.image.colorspace_settings.name = "Non-Color"
                    elif os.path.exists(os.path.join(filep, mat["mat_col0"][:-8] + "msk.png")) == True:
                        highlight_image_texture.image = bpy.data.images.load(os.path.join(filep, mat["mat_col0"][:-8] + "msk.png"))
                        highlight_image_texture.image.colorspace_settings.name = "Non-Color"
                    elif os.path.exists(os.path.join(filep, mat["mat_col0"][:-8] + "msk.png")) == True:
                        highlight_image_texture.image = bpy.data.images.load(os.path.join(filep, mat["mat_col0"][:-8] + "msk.png"))
                        highlight_image_texture.image.colorspace_settings.name = "Non-Color"
                    elif os.path.exists(os.path.join(filep, mat["mat_col0"][:-12] + "r_eye_msk.png")) == True and mat["mat_name"] == "eye_r":
                        highlight_image_texture.image = bpy.data.images.load(os.path.join(filep, mat["mat_col0"][:-12] + "r_eye_msk.png"))
                        highlight_image_texture.image.colorspace_settings.name = "Non-Color"
                    elif os.path.exists(os.path.join(filep, mat["mat_col0"][:-12] + "l_eye_msk.png")) == True and mat["mat_name"] == "eye_l":
                        highlight_image_texture.image = bpy.data.images.load(os.path.join(filep, mat["mat_col0"][:-12] + "l_eye_msk.png"))
                        highlight_image_texture.image.colorspace_settings.name = "Non-Color"
                    else:
                        try:
                            for x in range(10,30):
                                if os.path.exists(os.path.join(filep.replace(f"pm0025_{x}_00", "pm0025_00_00"), "pm0025_00_00_eye_msk.png")) == True and "pm0025" in trmtr.name:
                                    highlight_image_texture.image = bpy.data.images.load(os.path.join(filep.replace(f"pm0025_{x}_00", "pm0025_00_00"), "pm0025_00_00_eye_msk.png"))
                                    highlight_image_texture.image.colorspace_settings.name = "Non-Color"
                        except:
                            print("No Highlight")
                    material.node_tree.links.new(highlight_image_texture.outputs[0], shadegroupnodes.inputs['Mask'])
                if mat["mat_enable_normal_map"]:
                    normal_image_texture = material.node_tree.nodes.new("ShaderNodeTexImage")
                    if os.path.exists(os.path.join(filep, mat["mat_nrm0"][:-5] + textureextension)) == True:
                        normal_image_texture.image = bpy.data.images.load(os.path.join(filep, mat["mat_nrm0"][:-5] + textureextension))
                        normal_image_texture.image.colorspace_settings.name = "Non-Color"
                    separate_color2 = material.node_tree.nodes.new("ShaderNodeSeparateRGB")
                    combine_color2 = material.node_tree.nodes.new("ShaderNodeCombineColor")
                    normal_map2 = material.node_tree.nodes.new("ShaderNodeNormalMap")
                    material.node_tree.links.new(normal_image_texture.outputs[0], separate_color2.inputs[0])
                    material.node_tree.links.new(separate_color2.outputs[0], combine_color2.inputs[0])
                    material.node_tree.links.new(separate_color2.outputs[1], combine_color2.inputs[1])
                    material.node_tree.links.new(normal_image_texture.outputs[1], combine_color2.inputs[2])
                    material.node_tree.links.new(combine_color2.outputs[0], shadegroupnodes.inputs['NormalMap'])

                if mat["mat_enable_emission_color_map"]:
                    emission_image_texture = material.node_tree.nodes.new("ShaderNodeTexImage")
                    if os.path.exists(os.path.join(filep, mat["mat_emi0"][:-5] + textureextension)) == True:
                        emission_image_texture.image = bpy.data.images.load(os.path.join(filep, mat["mat_emi0"][:-5] + textureextension))
                    material.node_tree.links.new(emission_image_texture.outputs[0], shadegroupnodes.inputs['Emission'])
                
                if mat["mat_enable_roughness_map"]:
                    roughness_image_texture = material.node_tree.nodes.new("ShaderNodeTexImage")
                    if os.path.exists(os.path.join(filep, mat["mat_rgh0"][:-5] + textureextension)) == True:
                        roughness_image_texture.image = bpy.data.images.load(os.path.join(filep, mat["mat_rgh0"][:-5] + textureextension))
                        roughness_image_texture.image.colorspace_settings.name = "Non-Color"
                    material.node_tree.links.new(roughness_image_texture.outputs[0], shadegroupnodes.inputs['Roughness'])

                if mat["mat_enable_metallic_map"]:
                    roughness_image_texture = material.node_tree.nodes.new("ShaderNodeTexImage")
                    if os.path.exists(os.path.join(filep, mat["mat_mtl0"][:-5] + textureextension)) == True:
                        roughness_image_texture.image = bpy.data.images.load(os.path.join(filep, mat["mat_mtl0"][:-5] + textureextension))
                        roughness_image_texture.image.colorspace_settings.name = "Non-Color"
                    material.node_tree.links.new(roughness_image_texture.outputs[0], shadegroupnodes.inputs['Metallic'])

 

    if loadlods == False:
        trmsh_count = 1
                        
    for w in range(trmsh_count):
        if os.path.exists(os.path.join(filep, trmsh_lods_array[w])):
            poly_group_array = []
            trmsh = open(os.path.join(filep, trmsh_lods_array[w]), "rb")
            trmsh_file_start = readlong(trmsh)
            print("Parsing TRMSH...")
            fseek(trmsh, trmsh_file_start)
            trmsh_struct = ftell(trmsh) - readlong(trmsh); fseek(trmsh, trmsh_struct)
            trmsh_struct_len = readshort(trmsh)

            if trmsh_struct_len != 0x000A:
                raise AssertionError("Unexpected TRMSH header struct length!")
            trmsh_struct_section_len = readshort(trmsh)
            trmsh_struct_start = readshort(trmsh)
            trmsh_struct_poly_group = readshort(trmsh)
            trmsh_struct_trmbf = readshort(trmsh)

            if trmsh_struct_trmbf != 0:
                fseek(trmsh, trmsh_file_start + trmsh_struct_trmbf)
                trmbf_filename_start = ftell(trmsh) + readlong(trmsh)
                fseek(trmsh, trmbf_filename_start)
                trmbf_filename_len = readlong(trmsh)
                trmbf_filename = readfixedstring(trmsh, trmbf_filename_len)
                print(trmbf_filename)

                trmbf = None
                if os.path.exists(os.path.join(filep, trmbf_filename)):
                    trmbf = open(os.path.join(filep, trmbf_filename), "rb")
                else:
                    raise AssertionError(f"Can't find {trmbf_filename}!")

                if trmbf != None:
                    print("Parsing TRMBF...")
                    trmbf_file_start = readlong(trmbf); fseek(trmbf, trmbf_file_start)
                    trmbf_struct = ftell(trmbf) - readlong(trmbf); fseek(trmbf, trmbf_struct)
                    trmbf_struct_len = readshort(trmbf)

                    if trmbf_struct_len != 0x0008:
                        raise AssertionError("Unexpected TRMBF header struct length!")
                    trmbf_struct_section_len = readshort(trmbf)
                    trmbf_struct_start = readshort(trmbf)
                    trmbf_struct_buffer = readshort(trmbf)

                    if trmsh_struct_poly_group != 0:
                        fseek(trmsh, trmsh_file_start + trmsh_struct_poly_group)
                        poly_group_start = ftell(trmsh) + readlong(trmsh)
                        fseek(trmsh, poly_group_start)
                        poly_group_count = readlong(trmsh)

                        fseek(trmbf, trmbf_file_start + trmbf_struct_buffer)
                        vert_buffer_start = ftell(trmbf) + readlong(trmbf)
                        vert_buffer_count = readlong(trmbf)

                        for x in range(poly_group_count):
                            vert_array = []
                            normal_array = []
                            color_array = []
                            alpha_array = []
                            uv_array = []
                            uv2_array = []
                            uv3_array = []
                            uv4_array = []
                            face_array = []
                            face_mat_id_array = []
                            b1_array = []
                            w1_array = []
                            weight_array = []
                            Morphs_array = []
                            MorphName_array = []
                            groupoffset_array = []
                            mat_array = []
                            poly_group_name = ""; vis_group_name = ""; vert_buffer_stride = 0; mat_id = 0
                            positions_fmt = "None"; normals_fmt = "None"; tangents_fmt = "None"; bitangents_fmt = "None"; tritangents_fmt = "None"
                            uvs_fmt = "None"; uvs2_fmt = "None"; uvs3_fmt = "None"; uvs4_fmt = "None"
                            colors_fmt = "None"; colors2_fmt = "None"; bones_fmt = "None"; weights_fmt = "None"; svunk_fmt = "None"

                            poly_group_offset = ftell(trmsh) + readlong(trmsh)
                            poly_group_ret = ftell(trmsh)
                            fseek(trmsh, poly_group_offset)
                            poly_group_struct = ftell(trmsh) - readlong(trmsh)
                            fseek(trmsh, poly_group_struct)
                            poly_group_struct_len = readshort(trmsh)


                            if poly_group_struct_len == 0x001E:
                                poly_group_struct_section_len = readshort(trmsh)
                                poly_group_struct_ptr_poly_group_name = readshort(trmsh)
                                poly_group_struct_ptr_bbbox = readshort(trmsh)
                                poly_group_struct_ptp_unc_a = readshort(trmsh)
                                poly_group_struct_ptr_vert_buff = readshort(trmsh)
                                poly_group_struct_ptr_mat_list = readshort(trmsh)
                                poly_group_struct_ptr_unk_b = readshort(trmsh)
                                poly_group_struct_ptr_unk_c = readshort(trmsh)
                                poly_group_struct_ptr_unk_d = readshort(trmsh)
                                poly_group_struct_ptr_unk_e = readshort(trmsh)
                                poly_group_struct_ptr_unk_float = readshort(trmsh)
                                poly_group_struct_ptr_unk_g = readshort(trmsh)
                                poly_group_struct_ptr_morphname = readshort(trmsh)
                                poly_group_struct_ptr_vis_group_name = readshort(trmsh)
                                poly_group_struct_ptr_unk_i = 0
                                poly_group_struct_ptr_group_name = 0
                            elif poly_group_struct_len == 0x0022:
                                poly_group_struct_section_len = readshort(trmsh)
                                poly_group_struct_ptr_poly_group_name = readshort(trmsh)
                                poly_group_struct_ptr_bbbox = readshort(trmsh)
                                poly_group_struct_ptp_unc_a = readshort(trmsh)
                                poly_group_struct_ptr_vert_buff = readshort(trmsh)
                                poly_group_struct_ptr_mat_list = readshort(trmsh)
                                poly_group_struct_ptr_unk_b = readshort(trmsh)
                                poly_group_struct_ptr_unk_c = readshort(trmsh)
                                poly_group_struct_ptr_unk_d = readshort(trmsh)
                                poly_group_struct_ptr_unk_e = readshort(trmsh)
                                poly_group_struct_ptr_unk_float = readshort(trmsh)
                                poly_group_struct_ptr_unk_g = readshort(trmsh)
                                poly_group_struct_ptr_morphname = readshort (trmsh)
                                poly_group_struct_ptr_vis_group_name = readshort (trmsh)
                                poly_group_struct_ptr_unk_i = readshort(trmsh)
                                poly_group_struct_ptr_group_name = readshort(trmsh)

                            if poly_group_struct_ptr_mat_list != 0:
                                fseek(trmsh, poly_group_offset + poly_group_struct_ptr_mat_list)
                                mat_offset = ftell(trmsh) + readlong(trmsh)
                                fseek(trmsh, mat_offset)
                                mat_count = readlong(trmsh)
                                for y in range(mat_count):
                                    mat_entry_offset = ftell(trmsh) + readlong(trmsh)
                                    mat_ret = ftell(trmsh)
                                    fseek(trmsh, mat_entry_offset)
                                    mat_struct = ftell(trmsh) - readlong(trmsh)
                                    fseek(trmsh, mat_struct)
                                    mat_struct_len = readshort(trmsh)

                                    if mat_struct_len != 0x000E:
                                        raise AssertionError("Unexpected material struct length!")
                                    mat_struct_section_len = readshort(trmsh)
                                    mat_struct_ptr_facepoint_count = readshort(trmsh)
                                    mat_struct_ptr_facepoint_start = readshort(trmsh)
                                    mat_struct_ptr_unk_c = readshort(trmsh)
                                    mat_struct_ptr_string = readshort(trmsh)
                                    mat_struct_ptr_unk_d = readshort(trmsh)

                                    if mat_struct_ptr_facepoint_count != 0:
                                        fseek(trmsh, mat_entry_offset + mat_struct_ptr_facepoint_count)
                                        mat_facepoint_count = int(readlong(trmsh) / 3)

                                    if mat_struct_ptr_facepoint_start != 0:
                                        fseek(trmsh, mat_entry_offset + mat_struct_ptr_facepoint_start)
                                        mat_facepoint_start = int(readlong(trmsh) / 3)
                                    else: mat_facepoint_start = 0

                                    if mat_struct_ptr_unk_c != 0:
                                        fseek(trmsh, mat_entry_offset + mat_struct_ptr_unk_c)
                                        mat_unk_c = readlong(trmsh)

                                    if mat_struct_ptr_string != 0:
                                        fseek(trmsh, mat_entry_offset + mat_struct_ptr_string)
                                        mat_name_offset = ftell(trmsh) + readlong(trmsh)
                                        fseek(trmsh, mat_name_offset)
                                        mat_name_len = readlong(trmsh)
                                        mat_name = readfixedstring(trmsh, mat_name_len)
                                        mat_array.append(mat_name)
                                    if mat_struct_ptr_unk_d != 0:
                                        fseek(trmsh, mat_entry_offset + mat_struct_ptr_unk_d)
                                        mat_unk_d = readlong(trmsh)

                                    mat_id = 0
                                    for z in range(len(mat_data_array)):
                                        if mat_data_array[z]["mat_name"] == mat_name:
                                            mat_id = z
                                            break

                                    for z in range(mat_facepoint_count):
                                        face_mat_id_array.append(mat_id)

                                    #print(f"Material {mat_name}: FaceCount = {mat_facepoint_count}, FaceStart = {mat_facepoint_start}")
                                    fseek(trmsh, mat_ret)

                            if poly_group_struct_ptr_poly_group_name != 0:
                                fseek(trmsh, poly_group_offset + poly_group_struct_ptr_poly_group_name)
                                poly_group_name_offset = ftell(trmsh) + readlong(trmsh); fseek(trmsh, poly_group_name_offset)
                                poly_group_name_len = readlong(trmsh)
                                poly_group_name = readfixedstring(trmsh, poly_group_name_len)
                                
                            if poly_group_struct_ptr_group_name != 0:
                                fseek(trmsh, poly_group_offset + poly_group_struct_ptr_group_name)
                                group_name_header_offset = ftell(trmsh) + readlong(trmsh); fseek(trmsh, group_name_header_offset)
                                group_name_count = readlong(trmsh)
                                for g in range(group_name_count):
                                    group_name_offset = ftell(trmsh) + readlong(trmsh)
                                    groupoffset_array.append(group_name_offset)
                                    
                            if poly_group_struct_ptr_vis_group_name != 0:
                                fseek(trmsh, poly_group_offset + poly_group_struct_ptr_vis_group_name)
                                vis_group_name_offset = ftell(trmsh) + readlong(trmsh); fseek(trmsh, vis_group_name_offset)
                                vis_group_name_len = readlong(trmsh)
                                vis_group_name = readfixedstring(trmsh, vis_group_name_len)
                                
                            if poly_group_struct_ptr_morphname !=0:
                                fseek(trmsh, poly_group_offset + poly_group_struct_ptr_morphname)
                                morph_name_header_offset = ftell(trmsh) + readlong(trmsh); fseek(trmsh, morph_name_header_offset)
                                morph_name_count = readlong(trmsh)
                                for m in range(morph_name_count):
                                    morph_name_header_offset = ftell (trmsh) + readlong (trmsh)
                                    morph_ret = ftell (trmsh)
                                    fseek (trmsh, morph_name_header_offset)
                                    morph_name_struct = ftell (trmsh) - readlong (trmsh)
                                    fseek (trmsh, morph_name_struct)
                                    morph_name_struct_len = readshort (trmsh)
                                    if morph_name_struct_len == 0x0008:
                                        morph_name_struct_section_len = readshort (trmsh)
                                        morph_name_struct_ptr_ID = readshort (trmsh)
                                        morph_name_struct_ptr_name = readshort (trmsh)
                                    else:
                                        raise AssertionError("Unexpected morph name struct length!")
                                    fseek (trmsh, morph_name_header_offset + morph_name_struct_ptr_ID)
                                    morph_name_ID = readlong (trmsh)
                                    fseek (trmsh, morph_name_header_offset + morph_name_struct_ptr_name)
                                    morph_name_start = ftell (trmsh) + readlong (trmsh)
                                    fseek (trmsh, morph_name_start)
                                    morph_name_len = readlong (trmsh)
                                    morph_name = readfixedstring (trmsh, morph_name_len)
                                    MorphName_array.append(morph_name)
                                    fseek (trmsh, morph_ret)
                            if poly_group_struct_ptr_vert_buff != 0:
                                fseek(trmsh, poly_group_offset + poly_group_struct_ptr_vert_buff)
                                poly_group_vert_buff_offset = ftell(trmsh) + readlong(trmsh)
                                fseek(trmsh, poly_group_vert_buff_offset)
                                vert_buff_count = readlong(trmsh)
                                vert_buff_offset = ftell(trmsh) + readlong(trmsh)
                                fseek(trmsh, vert_buff_offset)
                                vert_buff_struct = ftell(trmsh) - readlong(trmsh)
                                fseek(trmsh, vert_buff_struct)
                                vert_buff_struct_len = readshort(trmsh)

                                if vert_buff_struct_len != 0x0008:
                                    raise AssertionError("Unexpected VertexBuffer struct length!")
                                vert_buff_struct_section_len = readshort(trmsh)
                                vert_buff_struct_ptr_param = readshort(trmsh)
                                vert_buff_struct_ptr_b = readshort(trmsh)

                                if vert_buff_struct_ptr_param != 0:
                                    fseek(trmsh, vert_buff_offset + vert_buff_struct_ptr_param)
                                    vert_buff_param_offset = ftell(trmsh) + readlong(trmsh)
                                    fseek(trmsh, vert_buff_param_offset)
                                    vert_buff_param_count = readlong(trmsh)
                                    for y in range(vert_buff_param_count):
                                        vert_buff_param_offset = ftell(trmsh) + readlong(trmsh)
                                        vert_buff_param_ret = ftell(trmsh)
                                        fseek(trmsh, vert_buff_param_offset)
                                        vert_buff_param_struct = ftell(trmsh) - readlong(trmsh)
                                        fseek(trmsh, vert_buff_param_struct)
                                        vert_buff_param_struct_len = readshort(trmsh)

                                        if vert_buff_param_struct_len == 0x000C:
                                            vert_buff_param_struct_section_len = readshort(trmsh)
                                            vert_buff_param_ptr_unk_a = readshort(trmsh)
                                            vert_buff_param_ptr_type = readshort(trmsh)
                                            vert_buff_param_ptr_layer = readshort(trmsh)
                                            vert_buff_param_ptr_fmt = readshort(trmsh)
                                            vert_buff_param_ptr_position = 0
                                        elif vert_buff_param_struct_len == 0x000E:
                                            vert_buff_param_struct_section_len = readshort(trmsh)
                                            vert_buff_param_ptr_unk_a = readshort(trmsh)
                                            vert_buff_param_ptr_type = readshort(trmsh)
                                            vert_buff_param_ptr_layer = readshort(trmsh)
                                            vert_buff_param_ptr_fmt = readshort(trmsh)
                                            vert_buff_param_ptr_position = readshort(trmsh)
                                        else:
                                            raise AssertionError("Unknown vertex buffer parameter struct length!")

                                        vert_buff_param_layer = 0

                                        if vert_buff_param_ptr_type != 0:
                                            fseek(trmsh, vert_buff_param_offset + vert_buff_param_ptr_type)
                                            vert_buff_param_type = readlong(trmsh)
                                        if vert_buff_param_ptr_layer != 0:
                                            fseek(trmsh, vert_buff_param_offset + vert_buff_param_ptr_layer)
                                            vert_buff_param_layer = readlong(trmsh)
                                        if vert_buff_param_ptr_fmt != 0:
                                            fseek(trmsh, vert_buff_param_offset + vert_buff_param_ptr_fmt)
                                            vert_buff_param_format = readlong(trmsh)
                                        if vert_buff_param_ptr_position != 0:
                                            fseek(trmsh, vert_buff_param_offset + vert_buff_param_ptr_position)
                                            vert_buff_param_position = readlong(trmsh)
                                        else:
                                            vert_buff_param_position = 0

                                        # -- Types:
                                        # -- 0x01: = Positions
                                        # -- 0x02 = Normals
                                        # -- 0x03 = Tangents
                                        # -- 0x05 = Colors
                                        # -- 0x06 = UVs
                                        # -- 0x07 = NodeIDs
                                        # -- 0x08 = Weights
                                        #
                                        # -- Formats:
                                        # -- 0x14 = 4 bytes as float
                                        # -- 0x16 = 4 bytes
                                        # -- 0x27 = 4 shorts as float
                                        # -- 0x2B = 4 half-floats
                                        # -- 0x30 = 2 floats
                                        # -- 0x33 = 3 floats
                                        # -- 0x36 = 4 floats
                                        #print(f'vert_buff_param_type = {vert_buff_param_type}')
                                        if vert_buff_param_type == 0x01:
                                            if vert_buff_param_layer != 0:
                                                raise AssertionError("Unexpected positions layer!")

                                            if vert_buff_param_format != 0x33:
                                                raise AssertionError("Unexpected positions format!")

                                            positions_fmt = "3Floats"; vert_buffer_stride = vert_buffer_stride + 0x0C
                                        elif vert_buff_param_type == 0x02:
                                            if vert_buff_param_layer != 0:
                                                raise AssertionError("Unexpected normals layer!")

                                            if vert_buff_param_format != 0x2B:
                                                raise AssertionError("Unexpected normals format!")

                                            normals_fmt = "4HalfFloats"; vert_buffer_stride = vert_buffer_stride + 0x08
                                        elif vert_buff_param_type == 0x03:
                                            if vert_buff_param_layer == 0:
                                                if vert_buff_param_format != 0x2B:
                                                    raise AssertionError("Unexpected tangents format!")

                                                tangents_fmt = "4HalfFloats"; vert_buffer_stride = vert_buffer_stride + 0x08
                                            elif vert_buff_param_layer == 1:
                                                if vert_buff_param_format != 0x2B:
                                                    raise AssertionError("Unexpected bitangents format!")

                                                bitangents_fmt = "4HalfFloats"; vert_buffer_stride = vert_buffer_stride + 0x08
                                            elif vert_buff_param_layer == 2:
                                                if vert_buff_param_format != 0x2B:
                                                    raise AssertionError("Unexpected tritangents format!")

                                                tritangents_fmt = "4HalfFloats"; vert_buffer_stride = vert_buffer_stride + 0x08
                                            else:
                                                raise AssertionError("Unexpected tangents layer!")
                                                
                                                
                                                
                                        
                                        elif vert_buff_param_type == 0x05:
                                            if vert_buff_param_layer == 0:
                                                if vert_buff_param_format == 0x14:
                                                    colors_fmt = "4BytesAsFloat"; vert_buffer_stride = vert_buffer_stride + 0x04
                                                elif vert_buff_param_format == 0x16:
                                                    colors_fmt = "4Bytes"; vert_buffer_stride = vert_buffer_stride + 0x04
                                                elif vert_buff_param_format == 0x36:
                                                    colors_fmt = "4Floats"; vert_buffer_stride = vert_buffer_stride + 0x10
                                                else:
                                                    raise AssertionError(hex(vert_buff_param_format))
                                            elif vert_buff_param_layer == 1:
                                                if vert_buff_param_format == 0x14:
                                                    colors2_fmt = "4BytesAsFloat"; vert_buffer_stride = vert_buffer_stride + 0x04
                                                elif vert_buff_param_format == 0x16:
                                                    colors_fmt = "4Bytes"; vert_buffer_stride = vert_buffer_stride + 0x04
                                                elif vert_buff_param_format == 0x36:
                                                    colors2_fmt = "4Floats"; vert_buffer_stride = vert_buffer_stride + 0x10
                                                else:
                                                    raise AssertionError("Unexpected colors2 format!")
                                                    
                                                    

                                        elif vert_buff_param_type == 0x06:
                                            if vert_buff_param_layer == 0:
                                                if vert_buff_param_format != 0x30:
                                                    raise AssertionError("Unexpected UVs format!")

                                                uvs_fmt = "2Floats"; vert_buffer_stride = vert_buffer_stride + 0x08
                                            elif vert_buff_param_layer == 1:
                                                if vert_buff_param_format != 0x30:
                                                    raise AssertionError("Unexpected UVs2 format!")

                                                uvs2_fmt = "2Floats"; vert_buffer_stride = vert_buffer_stride + 0x08
                                            elif vert_buff_param_layer == 2:
                                                if vert_buff_param_format != 0x30:
                                                    raise AssertionError("Unexpected UVs3 format!")

                                                uvs3_fmt = "2Floats"; vert_buffer_stride = vert_buffer_stride + 0x08
                                            elif vert_buff_param_layer == 3:
                                                if vert_buff_param_format != 0x30:
                                                    raise AssertionError("Unexpected UVs4 format!")

                                                uvs4_fmt = "2Floats"; vert_buffer_stride = vert_buffer_stride + 0x08
                                            else:
                                                raise AssertionError("Unexpected UVs layer!")
                                        elif vert_buff_param_type == 0x07:
                                            if vert_buff_param_layer != 0:
                                                raise AssertionError("Unexpected node IDs layer!")

                                            if vert_buff_param_format != 0x16:
                                                raise AssertionError("Unexpected node IDs format!")

                                            bones_fmt = "4Bytes"; vert_buffer_stride = vert_buffer_stride + 0x04
                                        elif vert_buff_param_type == 0x08:
                                            if vert_buff_param_layer != 0:
                                                raise AssertionError("Unexpected weights layer!")

                                            ##if vert_buff_param_format != 0x27:
                                            ##    raise AssertionError("Unexpected weights format!")
                                            if vert_buff_param_format == 0x16:
                                                weights_fmt = "4Bytes"; vert_buffer_stride = vert_buffer_stride + 0x04
                                            else:
                                                weights_fmt = "4ShortsAsFloat"; vert_buffer_stride = vert_buffer_stride + 0x08
                                        elif vert_buff_param_type == 0x09:
                                            if vert_buff_param_layer != 0:
                                                raise AssertionError("Unexpected ?????? layer!")

                                            if vert_buff_param_format != 0x24:
                                                raise AssertionError("Unexpected ?????? layer!")

                                            svunk_fmt = "1Long?"; vert_buffer_stride = vert_buffer_stride + 0x04
                                        else:
                                            raise AssertionError("Unknown vertex type!")


                                        fseek(trmsh, vert_buff_param_ret)

                            poly_group_array.append(
                                {
                                    "poly_group_name": poly_group_name,
                                    "vis_group_name": vis_group_name,
                                    "vert_buffer_stride": vert_buffer_stride,
                                    "positions_fmt": positions_fmt,
                                    "normals_fmt": normals_fmt,
                                    "tangents_fmt": tangents_fmt,
                                    "bitangents_fmt": bitangents_fmt,
                                    "tritangents_fmt":tritangents_fmt,
                                    "uvs_fmt": uvs_fmt,
                                    "uvs2_fmt": uvs2_fmt,
                                    "uvs3_fmt": uvs3_fmt,
                                    "uvs4_fmt": uvs4_fmt,
                                    "colors_fmt": colors_fmt,
                                    "colors2_fmt": colors2_fmt,
                                    "bones_fmt": bones_fmt,
                                    "weights_fmt": weights_fmt,
                                    "svunk_fmt":svunk_fmt
                                }
                            )
                            fseek(trmsh, poly_group_ret)

                            vert_buffer_offset = ftell(trmbf) + readlong(trmbf)
                            vert_buffer_ret = ftell(trmbf)
                            fseek(trmbf, vert_buffer_offset)
                            vert_buffer_struct = ftell(trmbf) - readlong(trmbf); fseek(trmbf, vert_buffer_struct)
                            vert_buffer_struct_len = readshort(trmbf)
                            if vert_buffer_struct_len == 0x0008:
                                vert_buffer_struct_section_length = readshort(trmbf)
                                vert_buffer_struct_ptr_faces = readshort(trmbf)
                                vert_buffer_struct_ptr_verts = readshort(trmbf)
                                vert_buffer_struct_ptr_groups = 0
                            elif vert_buffer_struct_len == 0x000A:
                                vert_buffer_struct_section_length = readshort(trmbf)
                                vert_buffer_struct_ptr_faces = readshort(trmbf)
                                vert_buffer_struct_ptr_verts = readshort(trmbf)
                                vert_buffer_struct_ptr_groups = readshort(trmbf)
                            else:
                                raise AssertionError("Unexpected vertex buffer struct length!")

                            if vert_buffer_struct_ptr_verts != 0:
                                fseek(trmbf, vert_buffer_offset + vert_buffer_struct_ptr_verts)
                                vert_buffer_sub_start = ftell(trmbf) + readlong(trmbf); fseek(trmbf, vert_buffer_sub_start)
                                vert_buffer_sub_count = readlong(trmbf)

                                for y in range(vert_buffer_sub_count):
                                    vert_buffer_sub_offset = ftell(trmbf) + readlong(trmbf)
                                    vert_buffer_sub_ret = ftell(trmbf)
                                    fseek(trmbf, vert_buffer_sub_offset)
                                    ##if y == 0:
                                    ##    print(f"Vertex buffer {x} header: {hex(ftell(trmbf))}")
                                    ##else:
                                    ##    print(f"Vertex buffer {x} morph {y} header: {hex(ftell(trmbf))}")
                                    vert_buffer_sub_struct = ftell(trmbf) - readlong(trmbf); fseek(trmbf, vert_buffer_sub_struct)
                                    vert_buffer_sub_struct_len = readshort(trmbf)

                                    if vert_buffer_sub_struct_len != 0x0006:
                                        raise AssertionError("Unexpected vertex buffer struct length!")
                                    vert_buffer_sub_struct_section_length = readshort(trmbf)
                                    vert_buffer_sub_struct_ptr = readshort(trmbf)

                                    if vert_buffer_sub_struct_ptr != 0:
                                        fseek(trmbf, vert_buffer_sub_offset + vert_buffer_sub_struct_ptr)
                                        vert_buffer_start = ftell(trmbf) + readlong(trmbf); fseek(trmbf, vert_buffer_start)
                                        vert_buffer_byte_count = readlong(trmbf)
                                        if y == 0:

                                            for v in range(vert_buffer_byte_count // poly_group_array[x]["vert_buffer_stride"]):
                                                if poly_group_array[x]["positions_fmt"] == "4HalfFloats":
                                                    vx = readhalffloat(trmbf)
                                                    vy = readhalffloat(trmbf)
                                                    vz = readhalffloat(trmbf)
                                                    vq = readhalffloat(trmbf)
                                                elif poly_group_array[x]["positions_fmt"] == "3Floats":
                                                    vx = readfloat(trmbf)
                                                    vy = readfloat(trmbf)
                                                    vz = readfloat(trmbf)
                                                else:
                                                    raise AssertionError("Unknown positions type!")

                                                if poly_group_array[x]["normals_fmt"] == "4HalfFloats":
                                                    nx = readhalffloat(trmbf)
                                                    ny = readhalffloat(trmbf)
                                                    nz = readhalffloat(trmbf)
                                                    nq = readhalffloat(trmbf)
                                                elif poly_group_array[x]["normals_fmt"] == "3Floats":
                                                    nx = readfloat(trmbf)
                                                    ny = readfloat(trmbf)
                                                    nz = readfloat(trmbf)
                                                else:
                                                    raise AssertionError("Unknown normals type!")

                                                if poly_group_array[x]["tangents_fmt"] == "None":
                                                    pass
                                                elif poly_group_array[x]["tangents_fmt"] == "4HalfFloats":
                                                    tanx = readhalffloat(trmbf)
                                                    tany = readhalffloat(trmbf)
                                                    tanz = readhalffloat(trmbf)
                                                    tanq = readhalffloat(trmbf)
                                                elif poly_group_array[x]["tangents_fmt"] == "3Floats":
                                                    tanx = readfloat(trmbf)
                                                    tany = readfloat(trmbf)
                                                    tanz = readfloat(trmbf)
                                                else:
                                                    raise AssertionError("Unknown tangents type!")

                                                if poly_group_array[x]["bitangents_fmt"] == "None":
                                                    pass
                                                elif poly_group_array[x]["bitangents_fmt"] == "4HalfFloats":
                                                    bitanx = readhalffloat(trmbf)
                                                    bitany = readhalffloat(trmbf)
                                                    bitanz = readhalffloat(trmbf)
                                                    bitanq = readhalffloat(trmbf)
                                                elif poly_group_array[x]["bitangents_fmt"] == "3Floats":
                                                    bitanx = readfloat(trmbf)
                                                    bitany = readfloat(trmbf)
                                                    bitanz = readfloat(trmbf)
                                                else:
                                                    raise AssertionError("Unknown bitangents type!")

                                                if poly_group_array[x]["tritangents_fmt"] == "None":
                                                    pass
                                                elif poly_group_array[x]["tritangents_fmt"] == "4HalfFloats":
                                                    tritanx = readhalffloat(trmbf)
                                                    tritany = readhalffloat(trmbf)
                                                    tritanz = readhalffloat(trmbf)
                                                    tritanq = readhalffloat(trmbf)
                                                elif poly_group_array[x]["tritangents_fmt"] == "3Floats":
                                                    tritanx = readfloat(trmbf)
                                                    tritany = readfloat(trmbf)
                                                    tritanz = readfloat(trmbf)
                                                else:
                                                    raise AssertionError("Unknown bitangents type!")

                                                if poly_group_array[x]["uvs_fmt"] == "None":
                                                    tu = 0
                                                    tv = 0
                                                elif poly_group_array[x]["uvs_fmt"] == "2Floats":
                                                    tu = readfloat(trmbf)
                                                    tv = readfloat(trmbf)
                                                else:
                                                    raise AssertionError("Unknown uvs type!")

                                                if poly_group_array[x]["uvs2_fmt"] == "None":
                                                    pass
                                                elif poly_group_array[x]["uvs2_fmt"] == "2Floats":
                                                    tu2 = readfloat(trmbf)
                                                    tv2 = readfloat(trmbf)
                                                    uv2_array.append((tu2, tv2))
                                                else:
                                                    raise AssertionError("Unknown uvs2 type!")

                                                if poly_group_array[x]["uvs3_fmt"] == "None":
                                                    pass
                                                elif poly_group_array[x]["uvs3_fmt"] == "2Floats":
                                                    tu3 = readfloat(trmbf)
                                                    tv3 = readfloat(trmbf)
                                                    uv3_array.append((tu3, tv3))
                                                else:
                                                    raise AssertionError("Unknown uvs3 type!")

                                                if poly_group_array[x]["uvs4_fmt"] == "None":
                                                    pass
                                                elif poly_group_array[x]["uvs4_fmt"] == "2Floats":
                                                    tu4 = readfloat(trmbf)
                                                    tv4 = readfloat(trmbf)
                                                    uv4_array.append((tu4, tv4))
                                                else:
                                                    raise AssertionError("Unknown uvs4 type!")

                                                if poly_group_array[x]["colors_fmt"] == "None":
                                                    colorr = 255
                                                    colorg = 255
                                                    colorb = 255
                                                    colora = 1
                                                elif poly_group_array[x]["colors_fmt"] == "4BytesAsFloat":
                                                    colorr = readbyte(trmbf)
                                                    colorg = readbyte(trmbf)
                                                    colorb = readbyte(trmbf)
                                                    colora = readbyte(trmbf)
                                                elif poly_group_array[x]["colors_fmt"] == "4Floats":
                                                    colorr = readfloat(trmbf) * 255
                                                    colorg = readfloat(trmbf) * 255
                                                    colorb = readfloat(trmbf) * 255
                                                    colora = readfloat(trmbf)
                                                else:
                                                    raise AssertionError("Unknown colors type!")

                                                if poly_group_array[x]["colors2_fmt"] == "None":
                                                    colorr2 = 255
                                                    colorg2 = 255
                                                    colorb2 = 255
                                                    colora2 = 1
                                                elif poly_group_array[x]["colors2_fmt"] == "4BytesAsFloat":
                                                    colorr2 = readbyte(trmbf)
                                                    colorg2 = readbyte(trmbf)
                                                    colorb2 = readbyte(trmbf)
                                                    colora2 = readbyte(trmbf)
                                                elif poly_group_array[x]["colors2_fmt"] == "4Floats":
                                                    colorr2 = readfloat(trmbf) * 255
                                                    colorg2 = readfloat(trmbf) * 255
                                                    colorb2 = readfloat(trmbf) * 255
                                                    colora2 = readfloat(trmbf)
                                                else:
                                                    raise AssertionError("Unknown colors 2 type!")

                                                if poly_group_array[x]["bones_fmt"] == "None":
                                                    bone1 = 0
                                                    bone2 = 0
                                                    bone3 = 0
                                                    bone4 = 0
                                                elif poly_group_array[x]["bones_fmt"] == "4Bytes":
                                                    bone1 = readbyte(trmbf)
                                                    bone2 = readbyte(trmbf)
                                                    bone3 = readbyte(trmbf)
                                                    bone4 = readbyte(trmbf)
                                                else:
                                                    raise AssertionError("Unknown bones type!")

                                                if poly_group_array[x]["weights_fmt"] == "None":
                                                    weight1 = 0
                                                    weight2 = 0
                                                    weight3 = 0
                                                    weight4 = 0
                                                elif poly_group_array[x]["weights_fmt"] == "4ShortsAsFloat":
                                                    weight1 = readshort(trmbf) / 65535
                                                    weight2 = readshort(trmbf) / 65535
                                                    weight3 = readshort(trmbf) / 65535
                                                    weight4 = readshort(trmbf) / 65535
                                                else:
                                                    raise AssertionError("Unknown weights type!")
                                                
                                                if poly_group_array[x]["svunk_fmt"] == "None":
                                                    SVUnk = 0
                                                elif poly_group_array[x]["svunk_fmt"] == "1Long?":
                                                    SVUnk = readlong(trmbf)
                                                else:
                                                    raise AssertionError("Unknown ?????? type!")
                                                
                                                vert_array.append((vx, vy, vz))
                                                normal_array.append((nx, ny, nz))
                                                
                                                
                                                uv_array.append((tu, tv))
                                                
                                                color_array.append((colorr, colorg, colorb))
                                                alpha_array.append(colora)
                                                if trskl is not None:
                                                    w1_array.append({"weight1": weight1, "weight2": weight2, "weight3": weight3, "weight4": weight4})
                                                    b1_array.append({"bone1": bone1, "bone2": bone2, "bone3": bone3, "bone4": bone4})

                                        else:
                                            MorphVert_array = []
                                            MorphNormal_array = []
                                            for v in range(int(vert_buffer_byte_count / 0x1C)):
                                                #Morphs always seem to use this setup.
                                                vx = readfloat(trmbf)
                                                vy = readfloat(trmbf)
                                                vz = readfloat(trmbf)
                                                nx = readhalffloat(trmbf)
                                                ny = readhalffloat(trmbf)
                                                nz = readhalffloat(trmbf)
                                                nq = readhalffloat(trmbf)
                                                tanx = readhalffloat(trmbf)
                                                tany = readhalffloat(trmbf)
                                                tanz = readhalffloat(trmbf)
                                                tanq = readhalffloat(trmbf)
                                                MorphVert_array.append((vx, vy, vz))
                                                MorphNormal_array.append((nx, ny, nz))
                                            Morphs_array.append(MorphVert_array)
                                            #TODO: Continue implementing after line 3814
                                    fseek(trmbf,vert_buffer_sub_ret)

                            if vert_buffer_struct_ptr_faces != 0:
                                fseek(trmbf, vert_buffer_offset + vert_buffer_struct_ptr_faces)
                                face_buffer_start = ftell(trmbf) + readlong(trmbf); fseek(trmbf, face_buffer_start)
                                face_buffer_count = readlong(trmbf)

                                for y in range(face_buffer_count):
                                    face_buff_offset = ftell(trmbf) + readlong(trmbf)
                                    face_buff_ret = ftell(trmbf)
                                    fseek(trmbf, face_buff_offset)
                                    face_buff_struct = ftell(trmbf) - readlong(trmbf); fseek(trmbf, face_buff_struct)
                                    face_buff_struct_len = readshort(trmbf)

                                    if face_buff_struct_len != 0x0006:
                                        raise AssertionError("Unexpected face buffer struct length!")
                                    face_buffer_struct_section_length = readshort(trmbf)
                                    face_buffer_struct_ptr = readshort(trmbf)

                                    if face_buffer_struct_ptr != 0:
                                        fseek(trmbf, face_buff_offset + face_buffer_struct_ptr)
                                        facepoint_start = ftell(trmbf) + readlong(trmbf); fseek(trmbf, facepoint_start)
                                        facepoint_byte_count = readlong(trmbf)
                                        
                                        if len(vert_array) > 65536: # is this a typo? I would imagine it to be 65535
                                            for v in range(facepoint_byte_count // 12):
                                                fa = readlong(trmbf)
                                                fb = readlong(trmbf)
                                                fc = readlong(trmbf)
                                                face_array.append([fa, fb, fc])
                                        else:
                                            for v in range(facepoint_byte_count // 6):
                                                fa = readshort(trmbf)
                                                fb = readshort(trmbf)
                                                fc = readshort(trmbf)
                                                face_array.append([fa, fb, fc])
                                    fseek(trmbf, face_buff_ret)

                            if vert_buffer_struct_ptr_groups != 0:
                                fseek(trmbf, vert_buffer_offset + vert_buffer_struct_ptr_groups)
                                group_start = ftell(trmbf) + readlong(trmbf); fseek(trmbf, group_start)
                                group_count = readlong(trmbf)
                                if group_count > 0:
                                    MorphNameNext = 1
                                    for g in range(group_count):
                                        fseek(trmsh, groupoffset_array[g])
                                        group_namestruct = ftell(trmsh) - readlong(trmsh)
                                        fseek(trmsh, group_namestruct)
                                        groupnamestructlen = readshort(trmsh)
                                        if groupnamestructlen == 0x000A:
                                            group_structsectionlen = readshort(trmsh)
                                            group_structptrparama = readshort(trmsh)
                                            group_structptrparammorph = readshort(trmsh)
                                            group_structprtparamname = readshort(trmsh)
                                        else:
                                            raise AssertionError("Unexpected morph group buffer struct length!")
                                        
                                        fseek(trmsh, groupoffset_array[g] + group_structprtparamname)
                                        group_nameoffset = ftell(trmsh) + readlong(trmsh)
                                        fseek(trmsh, group_nameoffset)
                                        group_namelen = readlong(trmsh)
                                        group_name = readfixedstring(trmsh, group_namelen)
                                        
                                        
                                        fseek(trmsh, groupoffset_array[g] + group_structptrparammorph)
                                        group_morphoffset = ftell(trmsh) + readlong(trmsh)
                                        fseek(trmsh, group_morphoffset)
                                        group_morphnamecount = readlong(trmsh)
                                        for y in range(group_morphnamecount):
                                            group_morphnameoffset = ftell(trmsh) + readlong(trmsh)
                                            group_morhpnameret = ftell(trmsh)
                                            fseek(trmsh, group_morphnameoffset)
                                            
                                            group_namemorphstruct = ftell(trmsh) - readlong(trmsh)
                                            fseek(trmsh, group_namemorphstruct)
                                            group_namemorphstructlen = readshort(trmsh)
                                            if group_namemorphstructlen == 0x000A:
                                                group_namemorphstructsectionlen = readshort(trmsh)
                                                group_namemorphstructptrparamid = readshort(trmsh)
                                                group_namemorphstructptrparamname = readshort(trmsh)
                                                group_namemorphstructptrparamflag = readshort(trmsh)
                                            else:
                                                raise AssertionError("Unexpected morph group buffer struct length!")
                                            fseek(trmsh, group_morphnameoffset + group_namemorphstructptrparamname)
                                            group_morphnameoffset = ftell(trmsh) + readlong(trmsh)
                                            fseek(trmsh, group_morphnameoffset)
                                            group_morphnamelen = readlong(trmsh)
                                            group_morphname = readfixedstring(trmsh, group_morphnamelen)
                                            MorphName_array.append(group_morphname)
                                            fseek(trmsh, group_morhpnameret)
                                        
                                        MorphVertIDs_array = []
                                        group_offset = ftell(trmbf) + readlong(trmbf)
                                        group_ret = ftell(trmbf)
                                        fseek(trmbf, group_offset)
                                        group_struct = ftell(trmbf) - readlong(trmbf)
                                        fseek(trmbf, group_struct)
                                        group_structlen = readshort(trmbf)
                                        if group_structlen == 0x0006:
                                            group_structsectionlen = readshort(trmbf)
                                            group_structptrparam = readshort(trmbf)
                                        else:
                                            raise AssertionError("Unexpected morph group buffer struct lenght!")
                                        
                                        fseek(trmbf, group_offset + group_structptrparam)
                                        group_morphsoffset = ftell(trmbf) + readlong(trmbf)
                                        fseek(trmbf, group_morphsoffset)
                                        group_morphscount = readlong(trmbf)
                                        
                                        for y in range(group_morphscount):
                                            morphgroupoffset = ftell(trmbf) + readlong(trmbf)
                                            groupret = ftell(trmbf)
                                            fseek(trmbf, morphgroupoffset)
                                            bufferstruct = ftell(trmbf) - readlong(trmbf)
                                            fseek(trmbf, bufferstruct)
                                            morphbufferstructlen = readshort(trmbf)
                                            if morphbufferstructlen == 0x0006:
                                                morphbuffersectionlen = readshort(trmbf)
                                                morphbufferstructptrparam = readshort(trmbf)
                                            else:
                                                raise AssertionError("Unexpected group sub buffer struct lenght!")
                                            
                                            fseek(trmbf, morphgroupoffset + morphbufferstructptrparam)
                                            morphbuffergroupsuboffset = ftell(trmbf) + readlong(trmbf)
                                            morphbuffergroupsbytecount = readlong(trmbf)
                                            if y == 0:
                                                for v in range(morphbuffergroupsbytecount // 0x04):
                                                    MorphVertID = readlong(trmbf)
                                                    MorphVertIDs_array.append(MorphVertID)
                                            else:
                                                MorphVert_array = []
                                                MorphNormal_array = []
                                                for v in range(len(vert_array)):
                                                    MorphVert_array.append(vert_array[v])
                                                    MorphNormal_array.append(normal_array[v])
                                                for v in range(morphbuffergroupsbytecount // 0x1C):
                                                    #Morphs always seem to use this setup.
                                                    vx = readfloat(trmbf)
                                                    vy = readfloat(trmbf)
                                                    vz = readfloat(trmbf)
                                                    nx = readhalffloat(trmbf)
                                                    ny = readhalffloat(trmbf)
                                                    nz = readhalffloat(trmbf)
                                                    nq = readhalffloat(trmbf)
                                                    tanx = readhalffloat(trmbf)
                                                    tany = readhalffloat(trmbf)
                                                    tanz = readhalffloat(trmbf)
                                                    tanq = readhalffloat(trmbf)
                                                    if MorphVertIDs_array[v] != 0:
                                                        MorphVert_array[MorphVertIDs_array[v]] = [vert_array[MorphVertIDs_array[v]][0] + vx, vert_array[MorphVertIDs_array[v]][1] + vy, vert_array[MorphVertIDs_array[v]][2] + vz]
                                                        MorphNormal_array[MorphVertIDs_array[v]] = [vert_array[MorphVertIDs_array[v]][0] + nx, vert_array[MorphVertIDs_array[v]][1] + ny, vert_array[MorphVertIDs_array[v]][2] + nz]
                                                Morphs_array.append(MorphVert_array)
                                            fseek(trmbf, groupret)
                                        fseek(trmbf, group_ret)
                            fseek(trmbf, vert_buffer_ret)                                                          

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

                            if IN_BLENDER_ENV:
                                # LINE 3257

                                new_mesh = bpy.data.meshes.new(poly_group_name)
                                new_mesh.from_pydata(vert_array, [], face_array)
                                new_mesh.update()
                                for p in new_mesh.polygons:
                                    p.use_smooth = True
                                new_object = bpy.data.objects.new(poly_group_name.replace("_shape",""), new_mesh)
                                if len(MorphName_array) > 0:
                                    sk_basis = new_object.shape_key_add(name='Basis')
                                    sk_basis.interpolation = 'KEY_LINEAR'
                                    new_object.data.shape_keys.use_relative = True
                                    for m in range(len(MorphName_array)):
                                        sk = new_object.shape_key_add(name=MorphName_array[m])
                                        for i in range(len(Morphs_array[m])):
                                            sk.data[i].co = Morphs_array[m][i]

                                if bone_structure != None:
                                    new_object.parent = bone_structure
                                    new_object.modifiers.new(name='Skeleton', type='ARMATURE')
                                    new_object.modifiers['Skeleton'].object = bone_structure

                                    for face in new_object.data.polygons:
                                        for vert_idx, loop_idx in zip(face.vertices, face.loop_indices):
                                            w = weight_array[vert_idx]
                                            for i in range(len(w["boneids"])):
                                                try:
                                                    bone_id = bone_id_map[w['boneids'][i]]
                                                except:
                                                    bone_id = None
                                                if bone_id:
                                                    weight = w['weights'][i]

                                                    group = None
                                                    if new_object.vertex_groups.get(bone_id) == None:
                                                        group = new_object.vertex_groups.new(name=bone_id)
                                                    else:
                                                        group = new_object.vertex_groups[bone_id]

                                                    group.add([vert_idx], weight, 'REPLACE')

                                # # vertex colours
                                color_layer = new_object.data.vertex_colors.new(name="Color")
                                new_object.data.vertex_colors.active = color_layer
                                #print(f"color_array: {len(color_array)}")
                                #print(f"polygons: {len(new_object.data.polygons)}")
                                for i, poly in enumerate(new_object.data.polygons):
                                    #print(f"poly: {i}")
                                    for v, vert in enumerate(poly.vertices):
                                        loop_index = poly.loop_indices[v]
                                
                                        #print(f"loop_index: {loop_index}")
                                        #print(color_array[vert][0], color_array[vert][1], color_array[vert][2], alpha_array[vert])
                                        
                                        if alpha_array[vert] == 0:
                                            alpha_array[vert] = 1
                                        color_layer.data[loop_index].color = (color_array[vert][0] / alpha_array[vert], color_array[vert][1] / alpha_array[vert], color_array[vert][2] / alpha_array[vert], alpha_array[vert])
                                for mat in materials:
                                    for x in range(len(mat_array)):
                                        if mat.name.split(".")[0] == sorted(mat_array)[x]:
                                            new_object.data.materials.append(mat)

                                # materials

                                # uvs
                                uv_layers = new_object.data.uv_layers
                                uv_layer = uv_layers.new(name="UVMap")
                                if len(uv2_array) > 0:
                                    uv2_layer = uv_layers.new(name="UV2Map")
                                if len(uv3_array) > 0:
                                    uv3_layer = uv_layers.new(name="UV3Map")
                                if len(uv4_array) > 0:
                                    uv4_layer = uv_layers.new(name="UV4Map")
                                uv_layers.active = uv_layer




                                for i, poly in enumerate(new_object.data.polygons):
                                    for x in range(len(mat_array)):
                                        if materials[face_mat_id_array[i]].name.split(".")[0] == sorted(mat_array)[x]:
                                            poly.material_index = x

                                try:
                                    for face in new_object.data.polygons:
                                        for vert_idx, loop_idx in zip(face.vertices, face.loop_indices):
                                            uv_layer.data[loop_idx].uv = uv_array[vert_idx]
                                            if len(uv2_array) > 0:
                                                uv2_layer.data[loop_idx].uv = uv2_array[vert_idx]
                                            if len(uv3_array) > 0:
                                                uv3_layer.data[loop_idx].uv = uv3_array[vert_idx]
                                            if len(uv4_array) > 0:
                                                uv4_layer.data[loop_idx].uv = uv4_array[vert_idx]
                                except:
                                    continue    
                                #normals
                                if blender_version[0] < 3:
                                    new_object.data.use_auto_smooth = True
                                new_object.data.normals_split_custom_set_from_vertices(normal_array)
                                new_object.data.update()
                                new_collection.objects.link(new_object)


def readbyte(file):
    return int.from_bytes(file.read(1), byteorder='little')


def readshort(file):
    return int.from_bytes(file.read(2), byteorder='little')


# SIGNED!!!!
def readlong(file):
    bytes_data = file.read(4)
    # print(f"readlong: {bytes_data}")
    return int.from_bytes(bytes_data, byteorder='little', signed=True)


def readfloat(file):
    return struct.unpack('<f', file.read(4))[0]


def readhalffloat(file):
    return struct.unpack('<e', file.read(2))[0]


def readfixedstring(file, length):
    bytes_data = file.read(length)
    # print(f"readfixedstring ({length}): {bytes_data}")
    return bytes_data.decode('utf-8')


def fseek(file, offset):
    # print(f"Seeking to {offset}")
    file.seek(offset)


def ftell(file):
    return file.tell()


def fclose(file):
    file.close()