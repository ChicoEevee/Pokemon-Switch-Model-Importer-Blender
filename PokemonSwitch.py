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
from mathutils import Color
import math
from math import pow
import glob
import shutil
import sys
import numpy as np
import requests
sys.path.append(os.path.join(os.path.dirname(__file__), "."))
from Titan.Model.TRMDL import TRMDL
from Titan.Model.TRSKL import TRSKL
from Titan.Model import TRMTR, Material, Shader, Texture, FloatParameter, Float4Parameter, StringParameter
import flatbuffers
IN_BLENDER_ENV = True
blender_version = bpy.app.version

def find_player_base_path(filep, chara_check):
    """Determine the correct TRSKL path for the player character."""
    paths = []
    if chara_check == "SVProtag":
        paths = [
            "../../model_pc_base/model/p0_base.trskl",
            "../../../../p2/model/base/p2_base0001_00_default/p2_base0001_00_default.trskl",
            "../../p2/p2_base0001_00_default/p2_base0001_00_default.trskl"
        ]
    elif chara_check == "CommonNPCbu":
        paths = ["../../../model_cc_base/bu/bu_base.trskl", "../../base/cc_base0001_00_young_m/cc_base0001_00_young_m.trskl"]
    elif chara_check == "CommonNPCdm" or chara_check == "CommonNPCdf":
        paths = ["../../../model_cc_base/dm/dm_base.trskl", "../../base/cc_base0001_00_young_m/cc_base0001_00_young_m.trskl"]
    elif chara_check == "CommonNPCem":
        paths = ["../../../model_cc_base/em/em_base.trskl", "../../base/cc_base0001_00_young_m/cc_base0001_00_young_m.trskl"]
    elif chara_check == "CommonNPCfm" or chara_check == "CommonNPCff":
        paths = ["../../../model_cc_base/fm/fm_base.trskl", "../../base/cc_base0001_00_young_m/cc_base0001_00_young_m.trskl"]
    elif chara_check == "CommonNPCgm" or chara_check == "CommonNPCgf":
        paths = ["../../../model_cc_base/gm/gm_base.trskl", "../../base/cc_base0001_00_young_m/cc_base0001_00_young_m.trskl"]
    elif chara_check == "CommonNPCrv":
        paths = ["../../../model_cc_base/rv/rv_base.trskl", "../../base/cc_base0001_00_young_m/cc_base0001_00_young_m.trskl"]

    for path in paths:
        full_path = os.path.join(filep, path)
        if os.path.exists(full_path):
            print(path, "exists")
            return full_path
    return None


def from_trmdlsv(filep, trmdlname, rare, loadlods,use_shadow_table,rotate90):
    # make collection
    if IN_BLENDER_ENV:
        new_collection = bpy.data.collections.new(os.path.basename(trmdlname[:-6]))
        bpy.context.scene.collection.children.link(new_collection)
    mat_data_array = []
    textureextension = ".png"
    transform_nodes = []
    bones = []
    trsklmapped = []
    materials = []
    bone_structure = None
    trmsh = None
    trmtr_path = None
    player_base_trskl_path = None
    trmsh_lods_array = []
    bone_array = []
    bone_id_map = [None] * 1000
    bone_rig_array = []
    extra_transform_nodes = []

    trskl_bone_adjust = 0
    chara_check = "None"
    with open(os.path.join(filep, trmdlname), "rb") as f:
        trmdl_content = f.read()
        buf = bytearray(trmdl_content)
    trmdl = TRMDL.GetRootAsTRMDL(buf, 0)
    trmsh_count = trmdl.MeshesLength()
    trmtr_name = trmdl.Materials(0).decode('utf-8')
    if rare:
        trmtr_path = os.path.join(filep, Path(trmtr_name).stem + "_rare.trmtr")
    else:
        trmtr_path = os.path.join(filep, trmtr_name) 
    trmsh = trmdl.Meshes(0).Filename().decode('utf-8')
    try:
        trmsh_lod2 = trmdl.Meshes(2).Filename().decode('utf-8')
    except:
        trmsh_lod2 = None
    try:
        trmsh_lod1 = trmdl.Meshes(1).Filename().decode('utf-8')
    except:
        trmsh_lod1 = None
    trmsh_lods_array = [trmsh, trmsh_lod1, trmsh_lod2]
    try:
        trskl = trmdl.Skeleton().Filename().decode('utf-8')
    except:
        trskl = None
    if trmsh.startswith(('au_')): chara_check = "CommonNPCau"
    elif trmsh.startswith(('bu_')): chara_check = "CommonNPCbu"
    elif trmsh.startswith(('cf_')): chara_check = "CommonNPCcf"
    elif trmsh.startswith(('cm_')): chara_check = "CommonNPCcm"
    elif trmsh.startswith(('df_')): chara_check = "CommonNPCdf"
    elif trmsh.startswith(('dm_')): chara_check = "CommonNPCdm"
    elif trmsh.startswith(('ef_')): chara_check = "CommonNPCef"
    elif trmsh.startswith(('em_')): chara_check = "CommonNPCem"
    elif trmsh.startswith(('ff_')): chara_check = "CommonNPCff"
    elif trmsh.startswith(('fm_')): chara_check = "CommonNPCfm"
    elif trmsh.startswith(('gf_')): chara_check = "CommonNPCgf"
    elif trmsh.startswith(('gm_')): chara_check = "CommonNPCgm"
    elif trmsh.startswith(('rv_')): chara_check = "CommonNPCrv"
    elif trmsh.startswith(('p1')): chara_check = "SVProtag"
    elif trmsh.startswith(('p2')): chara_check = "SVProtag"
    elif trmsh.startswith(('p0')): chara_check = "SVProtag"
    else: chara_check = None
    try:
        if chara_check is not None:
            player_base_trskl_path = find_player_base_path(filep, chara_check)
            if player_base_trskl_path != None:
                with open(player_base_trskl_path, "rb") as f:
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
                        "parent_idx": node.ParentIdx() + 1,
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

                if trskl is not None:
                    # --- Load extra TRSKL ---
                    with open(os.path.join(filep, trskl), "rb") as f:
                        buf = bytearray(f.read())
                    extra_trskl = TRSKL.GetRootAsTRSKL(buf, 0)
                
                    rig_offset = extra_trskl.RigOffset()
                    base_transform_count = len(base_transform_nodes)
                    for i in range(extra_trskl.TransformNodesLength()):
                        node = extra_trskl.TransformNodes(i)
                        name = node.Name().decode('utf-8')
                        rig_idx = node.RigIdx() + rig_offset
                        parent_idx = node.ParentIdx()
                        effect_node_name = node.EffectNode()
                        
                        if effect_node_name:
                            effect_node_name = effect_node_name.decode('utf-8')
                            if effect_node_name in base_name_to_idx:
                                # Remove +1 here to match JSON merging
                                parent_idx = base_name_to_idx[effect_node_name]
                            else:
                                raise ValueError(f"Effect node '{effect_node_name}' not found in base skeleton.")
                        else:
                            parent_idx += rig_offset + 2
                        
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
                            "parent_idx": parent_idx + 1,
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
                    transform_nodes = base_transform_nodes + extra_transform_nodes
                    bones = base_bones + extra_bones
                    print(transform_nodes)
            else:
                with open(os.path.join(filep, trskl), "rb") as f:
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
        elif trskl is not None:
            with open(os.path.join(filep, trskl), "rb") as f:
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
                    if entry["bone"]["inherit_scale"] == True:
                        
                        if blender_version[0] == 4:
                            new_bone.inherit_scale = 'NONE'
                        else:
                            new_bone.use_inherit_scale = False
                
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
    except Exception as e:
        print("failed loading trskl", e)
        
    if trmtr_path is not None:
        with open(trmtr_path, "rb") as f:
            trmtr_bytes = f.read()
        trmtr2 = TRMTR.TRMTR.GetRootAsTRMTR(trmtr_bytes, 0)

        mat_count = trmtr2.MaterialsLength()
        for x in range(mat_count):
            mat_shader = ""; mat_col0 = ""; mat_lym0 = ""; mat_nrm0 = ""; mat_ao0 = ""; mat_emi0 = ""; mat_rgh0 = ""; mat_mtl0 = ""; mat_msk0 = ""; mat_highmsk0 = ""; mat_sssmask0 = "";mat_loweyemsk0 = "";mat_uppeyemsk0 = ""; mat_opacity_map = ""
            mat_uv_scale_u = 1.0; mat_uv_scale_v = 1.0; mat_uv_trs_u = 0.0; mat_uv_trs_v = 0.0
            mat_uv_scale2_u = 1.0; mat_uv_scale2_v = 1.0; mat_uv_trs2_u = 0.0; mat_uv_trs2_v = 0.0
            mat_spec_map0 = ""
            mat_uvcenter0_x = 0.0;mat_uvcenter0_y = 0.0
            mat_color_r = 1.0; mat_color_g = 1.0; mat_color_b = 1.0
            mat_color1_r = 1.0; mat_color1_g = 1.0; mat_color1_b = 1.0
            mat_color2_r = 1.0; mat_color2_g = 1.0; mat_color2_b = 1.0
            mat_color3_r = 1.0; mat_color3_g = 1.0; mat_color3_b = 1.0
            mat_color4_r = 1.0; mat_color4_g = 1.0; mat_color4_b = 1.0
            mat_color5_r = 1.0; mat_color5_g = 1.0; mat_color5_b = 1.0 ##used on mask color
            #Need to figure out what does the others BaseColorLayer8 its related to LowerEyelidColor
            mat_color8_r = 1.0; mat_color8_g = 1.0; mat_color8_b = 1.0

            mat_emcolor1_r = 0.0; mat_emcolor1_g = 0.0; mat_emcolor1_b = 0.0
            mat_emcolor2_r = 0.0; mat_emcolor2_g = 0.0; mat_emcolor2_b = 0.0
            mat_emcolor3_r = 0.0; mat_emcolor3_g = 0.0; mat_emcolor3_b = 0.0
            mat_emcolor4_r = 0.0; mat_emcolor4_g = 0.0; mat_emcolor4_b = 0.0
            mat_emcolor5_r = 0.0; mat_emcolor5_g = 0.0; mat_emcolor5_b = 0.0
            mat_ssscolor_r = 0.0; mat_ssscolor_g = 0.0; mat_ssscolor_b = 0.0
            mat_rgh_layer0 = 1.0; mat_rgh_layer1 = 1.0; mat_rgh_layer2 = 1.0; mat_rgh_layer3 = 1.0; mat_rgh_layer4 = 1.0
            mat_mtl_layer0 = 0.0; mat_mtl_layer1 = 0.0; mat_mtl_layer2 = 0.0; mat_mtl_layer3 = 0.0; mat_mtl_layer4 = 0.0
            mat_rgh_value = 0.5
            mat_reflectance = 0.0
            mat_emm_intensity = 1.0
            mat_emm_intensity1 = 0.0
            mat_emm_intensity2 = 0.0
            mat_emm_intensity3 = 0.0
            mat_emm_intensity4 = 0.0
            mat_sss_offset = 0.0
            mat_metallic = 0.0
            mat_lym_scale1 = 1.0; mat_lym_scale2 = 1.0; mat_lym_scale3 = 1.0; mat_lym_scale4 = 1.0
            mat_basecolor_index1 = -1; mat_basecolor_index2 = -1; mat_basecolor_index3 = -1; mat_basecolor_index4 = -1; mat_basecolor_index5 = -1; mat_basecolor_index6 = -1; mat_basecolor_index7 = -1; mat_basecolor_index8 = -1; mat_basecolor_index9 = -1; mat_basecolor_index10 = -1; mat_basecolor_index11 = -1; mat_basecolor_index12 = -1; mat_basecolor_index13 = -1; mat_basecolor_index14 = -1; mat_basecolor_index15 = -1; mat_basecolor_index16 = -1; mat_basecolor_index17 = -1; mat_basecolor_index18 = -1; mat_basecolor_index19 = -1; mat_basecolor_index20 = -1; mat_basecolor_index21 = -1; mat_basecolor_index22 = -1; mat_basecolor_index23 = -1; mat_basecolor_index24 = -1; mat_basecolor_index25 = -1; mat_basecolor_index26 = -1; mat_basecolor_index27 = -1; mat_basecolor_index28 = -1; mat_basecolor_index29 = -1; mat_basecolor_index30 = -1; mat_basecolor_index31 = -1; mat_basecolor_index32 = -1; mat_basecolor_index33 = -1; mat_basecolor_index34 = -1; mat_basecolor_index35 = -1; mat_basecolor_index36 = -1; mat_basecolor_index37 = -1; mat_basecolor_index38 = -1; mat_basecolor_index39 = -1; mat_basecolor_index40 = -1; mat_colortabledividenumber = -1; mat_colortable_tex = ""; mat_enablecolortablemap = False
            mat_alpha_setting = ""

            mat_enable_base_color_map = False
            mat_enable_normal_map = False
            mat_enable_ao_map = False
            mat_enable_emission_color_map = False
            mat_enable_roughness_map = False
            mat_enable_metallic_map = False
            mat_enable_displacement_map = False
            mat_enable_highlight_map = False
            mat_base_color_multiply = True
            mat_num_material_layer = 0
            mat_eyelid_type = ""
            mat_fb = trmtr2.Materials(x)

            mat_name = mat_fb.Name().decode("utf-8") if mat_fb.Name() else ""

            shaders = []
            for s in range(mat_fb.ShadersLength()):
                shader_fb = mat_fb.Shaders(s)
                shader_name = shader_fb.ShaderName().decode("utf-8") if shader_fb.ShaderName() else ""
                shader_values = []
                for v in range(shader_fb.ShaderValuesLength()):
                    val_fb = shader_fb.ShaderValues(v)
                    name = val_fb.StringName().decode("utf-8")
                    value = val_fb.StringValue().decode("utf-8")
                    shader_values.append({"name": name, "value": value})
                    
                    if name == "EnableBaseColorMap": mat_enable_base_color_map = value == "True"
                    if name == "EnableNormalMap": mat_enable_normal_map = value == "True"
                    if name == "EnableAOMap": mat_enable_ao_map = value == "True"
                    if name == "EnableEmissionColorMap": mat_enable_emission_color_map = value == "True"
                    if name == "EnableRoughnessMap": mat_enable_roughness_map = value == "True"
                    if name == "EnableMetallicMap": mat_enable_metallic_map = value == "True"
                    if name == "EnableDisplacementMap": mat_enable_displacement_map = value == "True"
                    if name == "EnableHighlight": mat_enable_highlight_map = value == "True"
                    if name == "BaseColorMultiply": mat_base_color_multiply = value
                    if name == "NumMaterialLayer": mat_num_material_layer = int(value)
                    if name == "EyelidType": mat_eyelid_type = value
                    if name == "EnableColorTableMap": mat_enablecolortablemap = value
                if shader_name: mat_shader = shader_name
                shaders.append({"shader_name": shader_name, "shader_values": shader_values})

            textures = []
            for t in range(mat_fb.TexturesLength()):
                tex_fb = mat_fb.Textures(t)
                texture_name = tex_fb.TextureName().decode("utf-8")
                texture_file = tex_fb.TextureFile().decode("utf-8")
                textures.append({"texture_name": texture_name, "texture_file": texture_file})
                
                if texture_name == "BaseColorMap": mat_col0 = texture_file
                if texture_name == "LayerMaskMap": mat_lym0 = texture_file
                if texture_name == "NormalMap": mat_nrm0 = texture_file
                if texture_name == "AOMap": mat_ao0 = texture_file
                if texture_name == "EmissionColorMap": mat_emi0 = texture_file
                if texture_name == "RoughnessMap": mat_rgh0 = texture_file
                if texture_name == "MetallicMap": mat_mtl0 = texture_file
                if texture_name == "DisplacementMap": mat_msk0 = texture_file
                if texture_name == "HighlightMaskMap": mat_highmsk0 = texture_file
                if texture_name == "LowerEyelidColorMap": mat_loweyemsk0 = texture_file
                if texture_name == "UpperEyelidColorMap": mat_uppeyemsk0 = texture_file
                if texture_name == "SSSMaskMap": mat_sssmask0 = texture_file
                if texture_name == "ColorTableMap": mat_colortable_tex = texture_file
                if texture_name == "OpacityMap1": mat_opacity_map = texture_file
                if texture_name == "SpecularMaskMap": mat_spec_map0 = texture_file

            for f in range(mat_fb.FloatParameterLength()):
                fparam = mat_fb.FloatParameter(f)
                name = fparam.FloatName().decode("utf-8")
                value = fparam.FloatValue()
                if name == "Roughness": mat_rgh_value = value
                elif name == "Reflectance": mat_reflectance = value
                elif name == "EmissionIntensity": mat_emm_intensity = value
                elif name == "EmissionIntensityLayer1": mat_emm_intensity1 = value
                elif name == "EmissionIntensityLayer2": mat_emm_intensity2 = value
                elif name == "EmissionIntensityLayer3": mat_emm_intensity3 = value
                elif name == "EmissionIntensityLayer4": mat_emm_intensity4 = value
                elif name == "LayerMaskScale1": mat_lym_scale1 = value
                elif name == "LayerMaskScale2": mat_lym_scale2 = value
                elif name == "LayerMaskScale3": mat_lym_scale3 = value
                elif name == "LayerMaskScale4": mat_lym_scale4 = value
                elif name == "Metallic": mat_metallic = value
            for f in range(mat_fb.IntParameterLength()):
                fparam = mat_fb.IntParameter(f)
                name = fparam.IntName().decode("utf-8")
                value = fparam.IntValue()
                if name == "ColorTableDivideNumber": mat_colortabledividenumber = value
                elif name == "BaseColorIndex1": mat_basecolor_index1 = value
                elif name == "BaseColorIndex2": mat_basecolor_index2 = value
                elif name == "BaseColorIndex3": mat_basecolor_index3 = value
                elif name == "BaseColorIndex4": mat_basecolor_index4 = value
                elif name == "BaseColorIndex5": mat_basecolor_index5 = value
                elif name == "BaseColorIndex6": mat_basecolor_index6 = value
                elif name == "BaseColorIndex7": mat_basecolor_index7 = value
                elif name == "BaseColorIndex8": mat_basecolor_index8 = value
                elif name == "BaseColorIndex9": mat_basecolor_index9 = value
                elif name == "BaseColorIndex10": mat_basecolor_index10 = value
                elif name == "BaseColorIndex11": mat_basecolor_index11 = value
                elif name == "BaseColorIndex12": mat_basecolor_index12 = value
                elif name == "BaseColorIndex13": mat_basecolor_index13 = value
                elif name == "BaseColorIndex14": mat_basecolor_index14 = value
                elif name == "BaseColorIndex15": mat_basecolor_index15 = value
                elif name == "BaseColorIndex16": mat_basecolor_index16 = value
                elif name == "BaseColorIndex17": mat_basecolor_index17 = value
                elif name == "BaseColorIndex18": mat_basecolor_index18 = value
                elif name == "BaseColorIndex19": mat_basecolor_index19 = value
                elif name == "BaseColorIndex20": mat_basecolor_index20 = value
                elif name == "BaseColorIndex21": mat_basecolor_index21 = value
                elif name == "BaseColorIndex22": mat_basecolor_index22 = value
                elif name == "BaseColorIndex23": mat_basecolor_index23 = value
                elif name == "BaseColorIndex24": mat_basecolor_index24 = value
                elif name == "BaseColorIndex25": mat_basecolor_index25 = value
                elif name == "BaseColorIndex26": mat_basecolor_index26 = value
                elif name == "BaseColorIndex27": mat_basecolor_index27 = value
                elif name == "BaseColorIndex28": mat_basecolor_index28 = value
                elif name == "BaseColorIndex29": mat_basecolor_index29 = value
                elif name == "BaseColorIndex30": mat_basecolor_index30 = value
                elif name == "BaseColorIndex31": mat_basecolor_index31 = value
                elif name == "BaseColorIndex32": mat_basecolor_index32 = value
                elif name == "BaseColorIndex33": mat_basecolor_index33 = value
                elif name == "BaseColorIndex34": mat_basecolor_index34 = value
                elif name == "BaseColorIndex35": mat_basecolor_index35 = value
                elif name == "BaseColorIndex36": mat_basecolor_index36 = value
                elif name == "BaseColorIndex37": mat_basecolor_index37 = value
                elif name == "BaseColorIndex38": mat_basecolor_index38 = value
                elif name == "BaseColorIndex39": mat_basecolor_index39 = value
                elif name == "BaseColorIndex40": mat_basecolor_index40 = value
            for f in range(mat_fb.Float4ParameterLength()):
                fparam = mat_fb.Float4Parameter(f)
                name = fparam.ColorName().decode("utf-8")
                color = fparam.ColorValue()
                if name == "BaseColor":  mat_color_r, mat_color_g, mat_color_b = color.R(), color.G(), color.B()
                elif name == "BaseColorLayer1": mat_color1_r, mat_color1_g, mat_color1_b = color.R(), color.G(), color.B()
                elif name == "BaseColorLayer2":  mat_color2_r, mat_color2_g, mat_color2_b = color.R(), color.G(), color.B()
                elif name == "BaseColorLayer3": mat_color3_r, mat_color3_g, mat_color3_b = color.R(), color.G(), color.B()
                elif name == "BaseColorLayer4": mat_color4_r, mat_color4_g, mat_color4_b = color.R(), color.G(), color.B()
                elif name == "BaseColorLayer5": mat_color5_r, mat_color5_g, mat_color5_b = color.R(), color.G(), color.B()
                elif name == "BaseColorLayer8": mat_color8_r, mat_color8_g, mat_color8_b = color.R(), color.G(), color.B()
                elif name == "EmissionColorLayer1": mat_emcolor1_r, mat_emcolor1_g, mat_emcolor1_b = color.R(), color.G(), color.B()
                elif name == "EmissionColorLayer2": mat_emcolor2_r, mat_emcolor2_g, mat_emcolor2_b = color.R(), color.G(), color.B()
                elif name == "EmissionColorLayer3": mat_emcolor3_r, mat_emcolor3_g, mat_emcolor3_b = color.R(), color.G(), color.B()
                elif name == "EmissionColorLayer4": mat_emcolor4_r, mat_emcolor4_g, mat_emcolor4_b = color.R(), color.G(), color.B()
                elif name == "EmissionColorLayer5": mat_emcolor5_r, mat_emcolor5_g, mat_emcolor5_b = color.R(), color.G(), color.B()
                elif name == "SubsurfaceColor": mat_ssscolor_r, mat_ssscolor_g, mat_ssscolor_b = color.R(), color.G(), color.B()
                elif name == "UVScaleOffset":
                    mat_uv_scale_u = color.R()
                    mat_uv_scale_v = color.G()
                    mat_uv_trs_u = color.B()
                    mat_uv_trs_v = color.A()
                elif name == "UVScaleOffset1":
                    mat_uv_scale_u2 = color.R()
                    mat_uv_scale_v2 = color.G()
                    mat_uv_trs_u2 = color.B()
                    mat_uv_trs_v2 = color.A()
                elif name == "UVCenter0":
                    mat_uvcenter0_x = color.G()
                    mat_uvcenter0_y = color.B()
                    
            mat_alpha_setting = mat_fb.AlphaType().decode("utf-8") if mat_fb.AlphaType() else ""

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
                "mat_loweyemsk0": mat_loweyemsk0,
                "mat_uppeyemsk0": mat_uppeyemsk0,
                "mat_spec_map0": mat_spec_map0,
                "mat_eyelid_type": mat_eyelid_type,
                "mat_uvcenter0_x": mat_uvcenter0_x,
                "mat_uvcenter0_y": mat_uvcenter0_y,
                "mat_opacity_map": mat_opacity_map,
                "mat_color_r": mat_color_r, "mat_color_g": mat_color_g, "mat_color_b": mat_color_b,
                "mat_color1_r": mat_color1_r, "mat_color1_g": mat_color1_g, "mat_color1_b": mat_color1_b,
                "mat_color2_r": mat_color2_r, "mat_color2_g": mat_color2_g, "mat_color2_b": mat_color2_b,
                "mat_color3_r": mat_color3_r, "mat_color3_g": mat_color3_g, "mat_color3_b": mat_color3_b,
                "mat_color4_r": mat_color4_r, "mat_color4_g": mat_color4_g, "mat_color4_b": mat_color4_b,
                "mat_color5_r": mat_color5_r, "mat_color5_g": mat_color5_g, "mat_color5_b": mat_color5_b,
                "mat_color8_r": mat_color8_r, "mat_color8_g": mat_color8_g, "mat_color8_b": mat_color8_b,
                "mat_emcolor1_r": mat_emcolor1_r, "mat_emcolor1_g": mat_emcolor1_g, "mat_emcolor1_b": mat_emcolor1_b,
                "mat_emcolor2_r": mat_emcolor2_r, "mat_emcolor2_g": mat_emcolor2_g, "mat_emcolor2_b": mat_emcolor2_b,
                "mat_emcolor3_r": mat_emcolor3_r, "mat_emcolor3_g": mat_emcolor3_g, "mat_emcolor3_b": mat_emcolor3_b,
                "mat_emcolor4_r": mat_emcolor4_r, "mat_emcolor4_g": mat_emcolor4_g, "mat_emcolor4_b": mat_emcolor4_b,
                "mat_emcolor5_r": mat_emcolor5_r, "mat_emcolor5_g": mat_emcolor5_g, "mat_emcolor5_b": mat_emcolor5_b,
                "mat_ssscolor_r": mat_ssscolor_r, "mat_ssscolor_g": mat_ssscolor_g, "mat_ssscolor_b": mat_ssscolor_b,
                "mat_rgh_layer0": mat_rgh_layer0, "mat_rgh_layer1": mat_rgh_layer1, "mat_rgh_layer2": mat_rgh_layer2, "mat_rgh_layer3": mat_rgh_layer3, "mat_rgh_layer4": mat_rgh_layer4,
                "mat_mtl_layer0": mat_mtl_layer0, "mat_mtl_layer1": mat_mtl_layer1, "mat_mtl_layer2": mat_mtl_layer2, "mat_mtl_layer3": mat_mtl_layer3, "mat_mtl_layer4": mat_mtl_layer4,
                "mat_reflectance": mat_reflectance,
                "mat_rgh_value": mat_rgh_value,
                "mat_emm_intensity": mat_emm_intensity,
                "mat_emm_intensity1": mat_emm_intensity1,
                "mat_emm_intensity2": mat_emm_intensity2,
                "mat_emm_intensity3": mat_emm_intensity3,
                "mat_emm_intensity4": mat_emm_intensity4,
                "mat_sss_offset": mat_sss_offset,
                "mat_uv_scale_u": mat_uv_scale_u, "mat_uv_scale_v": mat_uv_scale_v,
                "mat_uv_trs_u": mat_uv_trs_u, "mat_uv_trs_v": mat_uv_trs_v,
                "mat_uv_scale2_u": mat_uv_scale2_u, "mat_uv_scale2_v": mat_uv_scale2_v,
                "mat_uv_trs2_u": mat_uv_trs2_u, "mat_uv_trs2_v": mat_uv_trs2_v,
                "mat_enable_base_color_map": mat_enable_base_color_map,
                "mat_enable_normal_map": mat_enable_normal_map,
                "mat_base_color_multiply": mat_base_color_multiply,
                "mat_enable_ao_map": mat_enable_ao_map,
                "mat_enable_emission_color_map": mat_enable_emission_color_map,
                "mat_enable_roughness_map": mat_enable_roughness_map,
                "mat_enable_metallic_map": mat_enable_metallic_map,
                "mat_enable_displacement_map": mat_enable_displacement_map,
                "mat_enable_highlight_map": mat_enable_highlight_map,
                "mat_num_material_layer": mat_num_material_layer,
                "mat_lym_scale1": mat_lym_scale1,
                "mat_lym_scale2": mat_lym_scale2,
                "mat_lym_scale3": mat_lym_scale3,
                "mat_lym_scale4": mat_lym_scale4,
                "mat_enablecolortablemap": mat_enablecolortablemap,
                "mat_colortable_tex": mat_colortable_tex,
                "mat_colortabledividenumber": mat_colortabledividenumber,
                "mat_basecolor_index1": mat_basecolor_index1,
                "mat_basecolor_index2": mat_basecolor_index2,
                "mat_basecolor_index3": mat_basecolor_index3,
                "mat_basecolor_index4": mat_basecolor_index4,
                "mat_basecolor_index5": mat_basecolor_index5,
                "mat_basecolor_index6": mat_basecolor_index6,
                "mat_basecolor_index7": mat_basecolor_index7,
                "mat_basecolor_index8": mat_basecolor_index8,
                "mat_basecolor_index9": mat_basecolor_index9,
                "mat_basecolor_index10": mat_basecolor_index10,
                "mat_basecolor_index11": mat_basecolor_index11,
                "mat_basecolor_index12": mat_basecolor_index12,
                "mat_basecolor_index13": mat_basecolor_index13,
                "mat_basecolor_index14": mat_basecolor_index14,
                "mat_basecolor_index15": mat_basecolor_index15,
                "mat_basecolor_index16": mat_basecolor_index16,
                "mat_basecolor_index17": mat_basecolor_index17,
                "mat_basecolor_index18": mat_basecolor_index18,
                "mat_basecolor_index19": mat_basecolor_index19,
                "mat_basecolor_index20": mat_basecolor_index20,
                "mat_basecolor_index21": mat_basecolor_index21,
                "mat_basecolor_index22": mat_basecolor_index22,
                "mat_basecolor_index23": mat_basecolor_index23,
                "mat_basecolor_index24": mat_basecolor_index24,
                "mat_basecolor_index25": mat_basecolor_index25,
                "mat_basecolor_index26": mat_basecolor_index26,
                "mat_basecolor_index27": mat_basecolor_index27,
                "mat_basecolor_index28": mat_basecolor_index28,
                "mat_basecolor_index29": mat_basecolor_index29,
                "mat_basecolor_index30": mat_basecolor_index30,
                "mat_basecolor_index31": mat_basecolor_index31,
                "mat_basecolor_index32": mat_basecolor_index32,
                "mat_basecolor_index33": mat_basecolor_index33,
                "mat_basecolor_index34": mat_basecolor_index34,
                "mat_basecolor_index35": mat_basecolor_index35,
                "mat_basecolor_index36": mat_basecolor_index36,
                "mat_basecolor_index37": mat_basecolor_index37,
                "mat_basecolor_index38": mat_basecolor_index38,
                "mat_basecolor_index39": mat_basecolor_index39,
                "mat_basecolor_index40": mat_basecolor_index40,
                "mat_alpha_setting": mat_alpha_setting,
                "mat_metallic": mat_metallic
            })
        mat_data_array = sorted(mat_data_array, key=lambda x: x['mat_name'])
        
        if IN_BLENDER_ENV:
            if not 'ScViShader' in bpy.data.materials or not 'ScViShader' in bpy.data.materials:
                blend_path = os.path.join(os.path.dirname(__file__), "SCVIShader.blend")
                try:
                    response = requests.get("https://raw.githubusercontent.com/ChicoEevee/Pokemon-Switch-V2-Model-Importer-Blender/master/SCVIShader.blend", stream=True)
                    with open(blend_path, 'wb') as file:
                        file.write(response.content)
                except:
                    print("Offline Mode")
                with bpy.data.libraries.load(blend_path, link=False) as (data_from, data_to):
                    data_to.materials = data_from.materials
                    print('! Loaded shader blend file.')
            for m, mat in enumerate(mat_data_array):
                if "eye" in mat["mat_name"] and "pm" in trmtr_name:
                    material = bpy.data.materials["ScViMonEyeShader"].copy()
                else:
                    material = bpy.data.materials["ScViShader"].copy()
                    
                material.name = mat["mat_name"]
                materials.append(material)
                shadegroupnodes = material.node_tree.nodes['Group']
                basecolor = (mat["mat_color_r"], mat["mat_color_g"], mat["mat_color_b"], 1.0)
                try:
                    shadegroupnodes.inputs['BaseColor'].default_value = (mat["mat_color_r"], mat["mat_color_g"], mat["mat_color_b"], 1.0)
                    if basecolor == (1.0, 1.0, 1.0, 1.0) and "sh_white_msk" in mat["mat_col0"]:
                        shadegroupnodes.inputs['BaseColor'].default_value = (mat["mat_color1_r"], mat["mat_color1_g"], mat["mat_color1_b"], 1.0)
                except:
                    print("")
                
                color1 = (mat["mat_color1_r"], mat["mat_color1_g"], mat["mat_color1_b"], 1.0)
                color2 = (mat["mat_color2_r"], mat["mat_color2_g"], mat["mat_color2_b"], 1.0)
                color3 = (mat["mat_color3_r"], mat["mat_color3_g"], mat["mat_color3_b"], 1.0)
                color4 = (mat["mat_color4_r"], mat["mat_color4_g"], mat["mat_color4_b"], 1.0)
                color5 = (mat["mat_color5_r"], mat["mat_color5_g"], mat["mat_color5_b"], 1.0)
                color8 = (mat["mat_color8_r"], mat["mat_color8_g"], mat["mat_color8_b"], 1.0)
                if "eye" in mat["mat_name"] and "pm" in trmtr_name:
                    shadegroupnodes.inputs['LowEye_color'].default_value = color8
                emcolor1 = (mat["mat_emcolor1_r"], mat["mat_emcolor1_g"], mat["mat_emcolor1_b"], 1.0)
                emcolor2 = (mat["mat_emcolor2_r"], mat["mat_emcolor2_g"], mat["mat_emcolor2_b"], 1.0)
                emcolor3 = (mat["mat_emcolor3_r"], mat["mat_emcolor3_g"], mat["mat_emcolor3_b"], 1.0)
                emcolor4 = (mat["mat_emcolor4_r"], mat["mat_emcolor4_g"], mat["mat_emcolor4_b"], 1.0)
                shadegroupnodes.inputs['BaseColorLayer1'].default_value = color1
                shadegroupnodes.inputs['BaseColorLayer2'].default_value = color2
                shadegroupnodes.inputs['BaseColorLayer3'].default_value = color3
                shadegroupnodes.inputs['BaseColorLayer4'].default_value = color4
                shadegroupnodes.inputs['Mask_color'].default_value = color5
                shadegroupnodes.inputs['EmissionColorLayer1'].default_value = emcolor1
                shadegroupnodes.inputs['EmissionColorLayer2'].default_value = emcolor2
                shadegroupnodes.inputs['EmissionColorLayer3'].default_value = emcolor3
                shadegroupnodes.inputs['EmissionColorLayer4'].default_value = emcolor4
                shadegroupnodes.inputs['Roughness'].default_value = mat["mat_rgh_value"]
                shadegroupnodes.inputs['Metallic'].default_value = mat["mat_metallic"]
                shadegroupnodes.inputs['EmissionStrength'].default_value = mat["mat_emm_intensity"]
                shadegroupnodes.inputs['EmissionIntensityLayer1'].default_value = mat["mat_emm_intensity1"]
                shadegroupnodes.inputs['EmissionIntensityLayer2'].default_value = mat["mat_emm_intensity2"]
                shadegroupnodes.inputs['EmissionIntensityLayer3'].default_value = mat["mat_emm_intensity3"]
                shadegroupnodes.inputs['EmissionIntensityLayer4'].default_value = mat["mat_emm_intensity4"]
                shadegroupnodes.inputs['LayerMaskScale1'].default_value = mat["mat_lym_scale1"]
                shadegroupnodes.inputs['LayerMaskScale2'].default_value = mat["mat_lym_scale2"]
                shadegroupnodes.inputs['LayerMaskScale3'].default_value = mat["mat_lym_scale3"]
                shadegroupnodes.inputs['LayerMaskScale4'].default_value = mat["mat_lym_scale4"]
                if "Opaque" not in mat["mat_alpha_setting"]:
                    material.blend_method = 'BLEND'
                if mat["mat_uv_scale_u"] > 1 or mat["mat_uv_scale_v"] > 1:
                    tex_coord_node = material.node_tree.nodes.new(type="ShaderNodeTexCoord")
                    mapping_node = material.node_tree.nodes.new(type="ShaderNodeMapping")
                    mapping_node2 = material.node_tree.nodes.new(type="ShaderNodeMapping")
                    material.node_tree.links.new(tex_coord_node.outputs['UV'], mapping_node.inputs['Vector'])
                    material.node_tree.links.new(tex_coord_node.outputs['UV'], mapping_node2.inputs['Vector'])
                    mapping_node.inputs[3].default_value[0] = mat["mat_uv_scale_u"]
                    mapping_node.inputs[3].default_value[1] = mat["mat_uv_scale_v"]
                    
                    val_offset_x = material.node_tree.nodes.new(type="ShaderNodeValue")
                    val_offset_x.label = "X UV Location"
                    val_offset_x.outputs[0].default_value = mat["mat_uvcenter0_x"]
                    
                    val_offset_y = material.node_tree.nodes.new(type="ShaderNodeValue")
                    val_offset_y.label = "Y UV Location"
                    val_offset_y.outputs[0].default_value = 0.0
                    
                    add_node = material.node_tree.nodes.new(type="ShaderNodeMath")
                    add_node.operation = 'ADD'
                    add_node.inputs[1].default_value = mat["mat_uvcenter0_x"]
                    
                    mul_add_node = material.node_tree.nodes.new(type="ShaderNodeMath")
                    mul_add_node.operation = 'MULTIPLY_ADD'
                    mul_add_node.inputs[1].default_value = mat["mat_uv_scale_u"]
                    mul_add_node.inputs[2].default_value = mat["mat_uvcenter0_x"]
                    
                    combine_a = material.node_tree.nodes.new(type="ShaderNodeCombineXYZ")
                    combine_b = material.node_tree.nodes.new(type="ShaderNodeCombineXYZ")
                    material.node_tree.links.new(val_offset_x.outputs[0], mul_add_node.inputs[0])
                    material.node_tree.links.new(val_offset_x.outputs[0], add_node.inputs[0])
                    material.node_tree.links.new(add_node.outputs[0], combine_b.inputs[0])
                    material.node_tree.links.new(mul_add_node.outputs[0], combine_a.inputs[0])
                    material.node_tree.links.new(val_offset_y.outputs[0], combine_a.inputs[1])
                    material.node_tree.links.new(val_offset_y.outputs[0], combine_b.inputs[1])
                    material.node_tree.links.new(combine_a.outputs['Vector'], mapping_node.inputs[1])
                    material.node_tree.links.new(combine_b.outputs['Vector'], mapping_node2.inputs[1])
    
                    add_offset = material.node_tree.nodes.new(type="ShaderNodeVectorMath")
                    add_offset.operation = 'ADD'
                    add_offset.inputs[1].default_value[0] = mat["mat_uv_trs_u"]
                    add_offset.inputs[1].default_value[1] = mat["mat_uv_trs_v"]
                    material.node_tree.links.new(mapping_node.outputs['Vector'], add_offset.inputs[0])

                    mod_wrap = material.node_tree.nodes.new(type="ShaderNodeVectorMath")
                    mod_wrap.operation = 'MODULO'
                    mod_wrap.inputs[1].default_value[0] = mat["mat_uv_scale_u"]
                    mod_wrap.inputs[1].default_value[1] = mat["mat_uv_scale_v"]
                    material.node_tree.links.new(add_offset.outputs['Vector'], mod_wrap.inputs[0])

                    sep = material.node_tree.nodes.new(type="ShaderNodeSeparateXYZ")
                    material.node_tree.links.new(mod_wrap.outputs['Vector'], sep.inputs['Vector'])

                    compare = material.node_tree.nodes.new(type="ShaderNodeMath")
                    compare.operation = 'GREATER_THAN'
                    compare.inputs[1].default_value = mat["mat_uv_scale_u"] / 2
                    material.node_tree.links.new(sep.outputs['X'], compare.inputs[0])
    
                    flip = material.node_tree.nodes.new(type="ShaderNodeMath")
                    flip.operation = 'SUBTRACT'
                    flip.inputs[0].default_value = mat["mat_uv_scale_u"]
                    material.node_tree.links.new(sep.outputs['X'], flip.inputs[1])
    
                    mix = material.node_tree.nodes.new(type="ShaderNodeMixRGB")
                    mix.blend_type = 'MIX'
                    material.node_tree.links.new(compare.outputs[0], mix.inputs['Fac'])
                    material.node_tree.links.new(sep.outputs['X'], mix.inputs[1])
                    material.node_tree.links.new(flip.outputs[0], mix.inputs[2])
    
                    combine = material.node_tree.nodes.new(type="ShaderNodeCombineXYZ")
                    material.node_tree.links.new(mix.outputs['Color'], combine.inputs['X'])
                    material.node_tree.links.new(sep.outputs['Y'], combine.inputs['Y'])
                    material.node_tree.links.new(sep.outputs['Z'], combine.inputs['Z'])

                if os.path.exists(os.path.join(filep, mat["mat_lym0"][:-5] + textureextension)) == True:
                    lym_image_texture = material.node_tree.nodes.new("ShaderNodeTexImage")
                    lym_image_texture.image = bpy.data.images.load(os.path.join(filep, mat["mat_lym0"][:-5] + textureextension))
                    lym_image_texture.interpolation = "Closest"
                    lym_image_texture.image.colorspace_settings.name = "Non-Color"
                    if mat["mat_uv_scale_u"] > 1 or mat["mat_uv_scale_v"] > 1:
                        material.node_tree.links.new(combine.outputs[0], lym_image_texture.inputs[0])
                    material.node_tree.links.new(lym_image_texture.outputs[0], shadegroupnodes.inputs['Lym_color'])
                    material.node_tree.links.new(lym_image_texture.outputs[1], shadegroupnodes.inputs['Lym_alpha'])
                  
                if mat["mat_enablecolortablemap"] == "True":
                    if os.path.exists(os.path.join(filep, mat["mat_colortable_tex"][:-5] + textureextension)) == True:
                        colorsfromtable = extract_2x2_colors_blender(os.path.join(filep, mat["mat_colortable_tex"][:-5] + textureextension), mat["mat_colortabledividenumber"],mat["mat_name"])
                        tablecolor = []
                        for i in range(mat["mat_colortabledividenumber"]):
                            if use_shadow_table == True:
                                key = f"ShadowColorTable{i}"
                            else:
                                key = f"BaseColorTable{i}"
                            if key in colorsfromtable:
                                rgb = colorsfromtable[key]
                                rgba = (rgb[0], rgb[1], rgb[2], 1.0)
                                tablecolor.append(rgba)
                        try:
                            if mat["mat_basecolor_index1"] > 0.1:
                                shadegroupnodes.inputs['BaseColorLayer1'].default_value = tablecolor[mat["mat_basecolor_index1"]-1]
                            if mat["mat_basecolor_index2"]> 0.1:
                                shadegroupnodes.inputs['BaseColorLayer2'].default_value = tablecolor[mat["mat_basecolor_index2"]-1]
                            if mat["mat_basecolor_index3"]> 0.1:
                                shadegroupnodes.inputs['BaseColorLayer3'].default_value = tablecolor[mat["mat_basecolor_index3"]-1]
                            if mat["mat_basecolor_index4"]> 0.1:
                                shadegroupnodes.inputs['BaseColorLayer4'].default_value = tablecolor[mat["mat_basecolor_index4"]-1]
                        except Exception as e:
                            print("colormaptable failed:", e, mat["mat_basecolor_index1"],mat["mat_basecolor_index2"],mat["mat_basecolor_index3"],mat["mat_basecolor_index4"])
                          
                if os.path.exists(os.path.join(filep, mat["mat_col0"][:-5] + textureextension)) == True:
                    alb_image_texture = material.node_tree.nodes.new("ShaderNodeTexImage")
                    alb_image_texture.image = bpy.data.images.load(os.path.join(filep, mat["mat_col0"][:-5] + textureextension))
                    material.node_tree.links.new(alb_image_texture.outputs[0], shadegroupnodes.inputs['Albedo'])
                    if mat["mat_uv_scale_u"] > 1 or mat["mat_uv_scale_v"] > 1:
                        material.node_tree.links.new(combine.outputs[0], alb_image_texture.inputs[0])
                    material.node_tree.links.new(alb_image_texture.outputs[1], shadegroupnodes.inputs['AlbedoAlpha'])
                    alb_image_texture.interpolation = "Closest"

              
                if os.path.exists(os.path.join(filep, mat["mat_opacity_map"][:-5] + textureextension)) == True:
                    opacity_image_texture = material.node_tree.nodes.new("ShaderNodeTexImage")
                    opacity_image_texture.image = bpy.data.images.load(os.path.join(filep, mat["mat_opacity_map"][:-5] + textureextension))
                    material.node_tree.links.new(opacity_image_texture.outputs[0], shadegroupnodes.inputs['Mask'])
                    if mat["mat_uv_scale_u"] > 1 or mat["mat_uv_scale_v"] > 1:
                        material.node_tree.links.new(combine.outputs[0], opacity_image_texture.inputs[0])
                try:
                    if mat["mat_enable_highlight_map"]:
                        highlight_image_texture = material.node_tree.nodes.new("ShaderNodeTexImage")
                        try:
                            highlight_image_texture.image = bpy.data.images.load(os.path.join(filep, mat["mat_highmsk0"][:-5] + textureextension))
                        except:
                            if "r_eye" in material.name:
                                primary = base_path.replace("eye_lym", "r_eye_msk") + ".png"
                            elif "l_eye" in material.name:
                                primary = base_path.replace("eye_lym", "l_eye_msk") + ".png"
                            else:
                                primary = None
                        
                            fallback = base_path.replace("eye_lym", "eye_msk").replace("lym", "msk") + ".png"
                        
                            for path in [primary, fallback] if primary else [fallback]:
                                full_path = os.path.join(filep, path)
                                if os.path.exists(full_path):
                                    highlight_image_texture.image = bpy.data.images.load(full_path)
                                    break
                        material.node_tree.links.new(highlight_image_texture.outputs[0], shadegroupnodes.inputs['Mask'])
                except:
                    print("Issue loading hightlight map")
                #EyelidType Upper is Disabled for now~
                if mat["mat_eyelid_type"] == "Lower":
                    eyelid_image_texture = material.node_tree.nodes.new("ShaderNodeTexImage")
                    if mat["mat_eyelid_type"] == "Lower":
                        if os.path.exists(os.path.join(filep, mat["mat_loweyemsk0"][:-5] + textureextension)) == True:
                            eyelid_image_texture.image = bpy.data.images.load(os.path.join(filep, mat["mat_loweyemsk0"][:-5] + textureextension))
                        material.node_tree.links.new(eyelid_image_texture.outputs[1], shadegroupnodes.inputs['LowEye_alpha'])
                        material.node_tree.links.new(eyelid_image_texture.outputs[0], shadegroupnodes.inputs['LowEye_alb'])
                    elif mat["mat_eyelid_type"] == "Upper":
                        if os.path.exists(os.path.join(filep, mat["mat_uppeyemsk0"][:-5] + textureextension)) == True:
                            eyelid_image_texture.image = bpy.data.images.load(os.path.join(filep, mat["mat_uppeyemsk0"][:-5] + textureextension))
                        material.node_tree.links.new(eyelid_image_texture.outputs[1], shadegroupnodes.inputs['UpEye_alpha'])
                        material.node_tree.links.new(eyelid_image_texture.outputs[0], shadegroupnodes.inputs['UpEye_alb'])
                    if mat["mat_uv_scale_u"] > 1 or mat["mat_uv_scale_v"] > 1:
                        material.node_tree.links.new(mapping_node2.outputs[0], eyelid_image_texture.inputs[0])

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

                if os.path.exists(os.path.join(filep, mat["mat_spec_map0"][:-5] + textureextension)) == True:
                    specular_image_texture = material.node_tree.nodes.new("ShaderNodeTexImage")
                    specular_image_texture.image = bpy.data.images.load(os.path.join(filep, mat["mat_rgh0"][:-5] + textureextension))
                    specular_image_texture.image.colorspace_settings.name = "Non-Color"
                    material.node_tree.links.new(specular_image_texture.outputs[0], shadegroupnodes.inputs['SpecularMaskMap'])

                if mat["mat_enable_metallic_map"]:
                    roughness_image_texture = material.node_tree.nodes.new("ShaderNodeTexImage")
                    if os.path.exists(os.path.join(filep, mat["mat_mtl0"][:-5] + textureextension)) == True:
                        roughness_image_texture.image = bpy.data.images.load(os.path.join(filep, mat["mat_mtl0"][:-5] + textureextension))
                        roughness_image_texture.image.colorspace_settings.name = "Non-Color"
                    material.node_tree.links.new(roughness_image_texture.outputs[0], shadegroupnodes.inputs['Metallic'])

 

    if loadlods == False:
        trmsh_count = 1
                        
    for w in range(trmsh_count):
        if os.path.exists(os.path.join(filep, str(trmsh_lods_array[w]))):
            poly_group_array = []
            trmsh = open(os.path.join(filep, str(trmsh_lods_array[w])), "rb")
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
                            binormal_array = []
                            tangent_array = []
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
                            positions_fmt = "None"; normals_fmt = "None"; tangents_fmt = "None"; bitangents_fmt = "None"; tritangents_fmt = "None"; binormals_fmt = "None";
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
                                        elif vert_buff_param_struct_len == 0x0010:
                                            vert_buff_param_struct_section_len = readshort(trmsh)
                                            vert_buff_param_ptr_unk_a = readshort(trmsh)
                                            vert_buff_param_ptr_type = readshort(trmsh)
                                            vert_buff_param_ptr_layer = readshort(trmsh)
                                            vert_buff_param_ptr_fmt = readshort(trmsh)
                                            vert_buff_param_ptr_position = readshort(trmsh)
                                        else:
                                            print(vert_buff_param_struct_len, "errorerrorerror")
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
                                            print("vert_buff_param_position = 0")

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

                                            if vert_buff_param_format == 0x2B:
                                                normals_fmt = "4HalfFloats"
                                                vert_buffer_stride = vert_buffer_stride + 0x08
                                            elif vert_buff_param_format == 0x33:
                                                normals_fmt = "3Floats"
                                                vert_buffer_stride = vert_buffer_stride + 0x0C
                                            else:
                                                raise AssertionError("Unexpected normals format!")
                                        elif vert_buff_param_type == 0x03:
                                            if vert_buff_param_layer == 0:
                                                if vert_buff_param_format == 0x2B:
                                                    tangents_fmt = "4HalfFloats"; vert_buffer_stride = vert_buffer_stride + 0x08
                                                elif vert_buff_param_format == 0x33:
                                                    tangents_fmt = "3Floats"; vert_buffer_stride = vert_buffer_stride + 0x0C
                                            elif vert_buff_param_layer == 1:
                                                if vert_buff_param_format == 0x2B:
                                                    bitangents_fmt = "4HalfFloats"; vert_buffer_stride = vert_buffer_stride + 0x08
                                                elif vert_buff_param_format == 0x33:
                                                    bitangents_fmt = "3Floats"; vert_buffer_stride = vert_buffer_stride + 0x0C
                                            elif vert_buff_param_layer == 2:
                                                if vert_buff_param_format == 0x2B:
                                                    tritangents_fmt = "4HalfFloats"; vert_buffer_stride = vert_buffer_stride + 0x08
                                                elif vert_buff_param_format == 0x33:
                                                    tritangents_fmt = "3Floats"; vert_buffer_stride = vert_buffer_stride + 0x0C
                                            else:
                                                raise AssertionError("Unexpected tangents layer!")
                                        
                                        elif vert_buff_param_type == 0x04:
                                            if vert_buff_param_layer != 0:
                                                raise AssertionError("Unexpected normals layer!")
                                            print(vert_buff_param_format)
                                            if vert_buff_param_format == 0x2B:
                                                binormals_fmt = "4HalfFloats"
                                                vert_buffer_stride = vert_buffer_stride + 0x08
                                            elif vert_buff_param_format == 0x33:
                                                binormals_fmt = "3Floats"
                                                vert_buffer_stride = vert_buffer_stride + 0x0C
                                            else:
                                                raise AssertionError("Unexpected normals format!")    
                                        
                                        elif vert_buff_param_type == 0x05:
                                            if vert_buff_param_layer == 0:
                                                if vert_buff_param_format == 0x14:
                                                    colors_fmt = "4BytesAsFloat"; vert_buffer_stride = vert_buffer_stride + 0x04
                                                elif vert_buff_param_format == 0x36:
                                                    colors_fmt = "4Floats"; vert_buffer_stride = vert_buffer_stride + 0x10
                                                else:
                                                    raise AssertionError(hex(vert_buff_param_format))
                                            elif vert_buff_param_layer == 1:
                                                if vert_buff_param_format == 0x14:
                                                    colors2_fmt = "4BytesAsFloat"; vert_buffer_stride = vert_buffer_stride + 0x04
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

                                            if vert_buff_param_format == 0x16:
                                                bones_fmt = "4Bytes"; vert_buffer_stride = vert_buffer_stride + 0x04
                                            if vert_buff_param_format == 0x34:
                                                bones_fmt = "4UINTS32"; vert_buffer_stride = vert_buffer_stride + 0x10
                                        elif vert_buff_param_type == 0x08:
                                            if vert_buff_param_layer != 0:
                                                raise AssertionError("Unexpected weights layer!")
                                            if vert_buff_param_format == 0x27:
                                                weights_fmt = "4ShortsAsFloat"; vert_buffer_stride = vert_buffer_stride + 0x08
                                        elif vert_buff_param_type == 0x09:
                                            if vert_buff_param_layer != 0:
                                                raise AssertionError("Unexpected ?????? layer!")

                                            if vert_buff_param_format == 0x24:
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
                                    "binormals_fmt": binormals_fmt,
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
                                    if y == 0:
                                        print(f"Vertex buffer {x} header: {hex(ftell(trmbf))}")
                                    else:
                                        print(f"Vertex buffer {x} morph {y} header: {hex(ftell(trmbf))}")
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
                                                if poly_group_array[x]["binormals_fmt"] == "None":
                                                    pass
                                                elif poly_group_array[x]["binormals_fmt"] == "4HalfFloats":
                                                    bnx = readhalffloat(trmbf)
                                                    bny = readhalffloat(trmbf)
                                                    bnz = readhalffloat(trmbf)
                                                    bnq = readhalffloat(trmbf)
                                                elif poly_group_array[x]["binormals_fmt"] == "3Floats":
                                                    bnx = readfloat(trmbf)
                                                    bny = readfloat(trmbf)
                                                    bnz = readfloat(trmbf)
                                                else:
                                                    raise AssertionError("Unknown normals type!")
                                                
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
                                                elif poly_group_array[x]["bones_fmt"] == "4UINTS32":
                                                    bone1 = readulong(trmbf)
                                                    bone2 = readulong(trmbf)
                                                    bone3 = readulong(trmbf)
                                                    bone4 = readulong(trmbf)
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
                                                if poly_group_array[x]["binormals_fmt"] != "None":
                                                    binormal_array.append((bnx, bny, bnz))
                                                
                                                if poly_group_array[x]["tangents_fmt"] != "None":
                                                    tangent_array.append((tanx, tany, tanz))

                                                
                                                
                                                uv_array.append((tu, tv))
                                                
                                                color_array.append((colorr, colorg, colorb))
                                                alpha_array.append(colora)
                                                if trskl is not None or chara_check is not None:
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
                                    try:
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
                                    except:
                                        print("Error Loading Weights")
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
    if rotate90 == True:
        if bone_structure == None:
            for obj in new_collection.objects:
                obj.rotation_euler.x += math.radians(90)
        else:
            bone_structure.rotation_euler.x += math.radians(90)

def readbyte(file):
    return int.from_bytes(file.read(1), byteorder='little')


def readshort(file):
    return int.from_bytes(file.read(2), byteorder='little')


# SIGNED!!!!
def readlong(file):
    bytes_data = file.read(4)
    # print(f"readlong: {bytes_data}")
    return int.from_bytes(bytes_data, byteorder='little', signed=True)
# USIGNED!!!!
def readulong(file):
    bytes_data = file.read(4)
    # print(f"readlong: {bytes_data}")
    return int.from_bytes(bytes_data, byteorder='little', signed=False)


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

def get_pixel(x, y, w, h, pixels):
    flipped_y = h - 1 - y
    i = (flipped_y * w + x) * 4
    return pixels[i:i+3]

def srgb_to_linear(c):
    if c <= 0.04045:
        return c / 12.92
    else:
        return ((c + 0.055) / 1.055) ** 2.4

def rgb_srgb_to_linear(rgb):
    return [srgb_to_linear(c) for c in rgb]

def extract_2x2_colors_blender(image_path, max_columns=None, material_name=None):
    img = bpy.data.images.load(image_path)

    w, h = img.size
    pixels = list(img.pixels)

    rows = h // 2
    cols = w // 2
    if max_columns is not None:
        cols = min(cols, max_columns)

    colors = {}
    base_colors = []
    shadow_colors = []
    for row in range(rows):
        for col in range(cols):
            block = [get_pixel(col*2 + dx, row*2 + dy, w, h, pixels) for dy in range(2) for dx in range(2)]
            avg_rgb = [sum(p[i] for p in block)/4 for i in range(3)]
            avg_linear = rgb_srgb_to_linear(avg_rgb)
            avg_linear.append(1.0)
            color = tuple(round(c, 6) for c in avg_linear)

            if row == 0:
                key = f"BaseColorTable{col}"
                base_colors.append(color)
            else:
                key = f"ShadowColorTable{col}"
                shadow_colors.append(color)

            colors[key] = color

    def make_palette(name, color_list):
        full_name = f"{name}_{material_name}"
        # Remove if already exists
        if full_name in bpy.data.palettes:
            bpy.data.palettes.remove(bpy.data.palettes[full_name])
        palette = bpy.data.palettes.new(full_name)
        for col in color_list:
            color_entry = palette.colors.new()
            color_entry.color = col[:3]
        return palette
    
    make_palette("BaseColorPalette", base_colors)
    make_palette("ShadowColorPalette", shadow_colors)


    return colors
