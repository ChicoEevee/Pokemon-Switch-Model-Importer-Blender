"""
    Blender addon for importing and exporting assets from Nintendo Switch Pokémon games.
"""
import os

import sys
script_dir = os.path.dirname(__file__)
if script_dir not in sys.path:
    sys.path.append(script_dir)
import ensurepip
import sysconfig
import subprocess
from importlib import import_module
import bpy
from bpy.props import *
from bpy.utils import register_class, unregister_class
from bpy_extras.io_utils import ImportHelper, ExportHelper
import struct
import mathutils
from Titan.TrinityScene import trinity_Scene, trinity_SceneObject, SceneEntry
import TRINS
import INS
import math
# pylint: disable=import-outside-toplevel, wrong-import-position, import-error
# pylint: disable=too-few-public-methods

bl_info = {
    "name": "Pokémon Switch V3 (TRMDL, GFBANM/TRANM, TRSKL, TRMBF+TRMSH)",
    "author": "SomeKitten, Shararamosh, Tavi, Luma, mv & ElChicoEevee",
    "version": (3, 0, 0),
    "blender": (3, 3, 0),
    "location": "File > Import",
    "description": "Blender addon for importing and exporting Nintendo Switch Pokémon Assets.",
    "category": "Import-Export",
    "doc_url": "https://github.com/ChicoEevee/Pokemon-Switch-Model-Importer-Blender"
}

class TRSCNImport(bpy.types.Operator, ImportHelper):
    """Import TRSCN scene files"""
    bl_idname = "import_scene.trscn"
    bl_label = "Import TRSCN"
    bl_options = {'UNDO'}

    filename_ext = ".trscn"
    filter_glob: StringProperty(
        default="*.trscn",
        options={'HIDDEN'}
    )

    multiple: BoolProperty(
        name="Load All Folder + Subfolders",
        description="Load all TRSCN files in folder",
        default=False
    )

    def draw(self, context):
        self.layout.prop(self, "multiple")

    def execute(self, context):
        directory = os.path.dirname(self.filepath)

        if not self.multiple:
            filename = os.path.basename(self.filepath)
            self.import_trscn_file(directory, filename)
            return {"FINISHED"}

        # Load all TRSCN files in folder
        for root, dirs, files in os.walk(directory):
            for item in sorted(files):
                if item.endswith(".trscn"):
                    self.import_trscn_file(root, item)

        return {"FINISHED"}

    def import_trscn_file(self, directory, filename):
        filepath = os.path.join(directory, filename)
        with open(filepath, "rb") as f:
            buf = f.read()

        scene = trinity_Scene.trinity_Scene.GetRootAstrinity_Scene(buf, 0)

        root_name = os.path.splitext(filename)[0]
        root_empty = bpy.data.objects.new(root_name, None)
        bpy.context.collection.objects.link(root_empty)

        def parse_scene_entry(entry, parent_empty):
            """Recursively add SceneEntry objects as empties"""
            type_name = entry.TypeName()
            type_name_str = type_name.decode("utf-8") if type_name else ""
            obj_empty = None

            if type_name_str == "trinity_SceneObject":
                nested_bytes = entry.NestedTypeAsNumpy().tobytes()
                obj = trinity_SceneObject.trinity_SceneObject.GetRootAstrinity_SceneObject(nested_bytes, 0)

                # Build SRT
                srt = obj.Srt()
                scale = (srt.Scale().X(), srt.Scale().Y(), srt.Scale().Z())
                rot = (srt.Rotation().X(), srt.Rotation().Y(), srt.Rotation().Z())
                trans = (srt.Translation().X(), srt.Translation().Y(), srt.Translation().Z())

                obj_name = obj.Name().decode("utf-8") if obj.Name() else "Object"
                obj_name_full = f"{obj_name}_{entry.SubObjectsLength()}"

                obj_empty = bpy.data.objects.new(obj_name_full, None)
                bpy.context.collection.objects.link(obj_empty)
                obj_empty.parent = parent_empty
                obj_empty.location = trans
                obj_empty.rotation_mode = 'XYZ'
                obj_empty.rotation_euler = tuple(math.radians(r) for r in rot)
                obj_empty.scale = scale

            for i in range(entry.SubObjectsLength()):
                parse_scene_entry(entry.SubObjects(i), obj_empty if obj_empty else parent_empty)

        for i in range(scene.SceneObjectListLength()):
            entry = scene.SceneObjectList(i)
            parse_scene_entry(entry, root_empty)

        root_empty.rotation_mode = 'XYZ'
        root_empty.rotation_euler.x += math.radians(90)

        bpy.context.view_layer.objects.active = root_empty
        root_empty.select_set(True)
        bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)
        root_empty.select_set(False)
        if len(root_empty.children) == 0:
            bpy.data.objects.remove(root_empty, do_unlink=True)


class TRSKLExport(bpy.types.Operator, ExportHelper):
    """
    Class for operator that exports TRSKL files.
    """
    bl_idname = "export_scene.trskl"
    bl_description = "Export current Armature as TRSKL file"
    bl_label = "Export as TRSKL"
    bl_options = {"PRESET", "UNDO"}
    filename_ext = ".trskl"  # Specify the default file extension
    filter_glob: StringProperty(default="*.gfbanm;*.tranm", options={"HIDDEN"})
    filepath: bpy.props.StringProperty(subtype="FILE_PATH")

    def execute(self, context: bpy.types.Context):
        """
        Executing export menu.
        :param context: Blender's context.
        """
        armature_obj = context.active_object
        from .trskl_exporter import export_skeleton
        if armature_obj and armature_obj.type == "ARMATURE":
            if not attempt_install_flatbuffers(self, context):
                return {"CANCELLED"}
            data = export_skeleton(armature_obj)
            # Save the data to a TRSKL file
            with open(self.filepath, "wb") as file:
                file.write(data)
                print(f"Armature successfully exported to {self.filepath}.")
            return {"FINISHED"}
        self.report({"ERROR"}, "No Armature selected for export.")
        return {"CANCELLED"}


class ExportTRMBFMSH(bpy.types.Operator, ExportHelper):
    """
    Class for operator that exports meshes to TRMBF and TRMSH.
    """
    bl_idname = "export_scene.trmsh_trmbf"
    bl_description = "Export selected Meshes as TRMSH and TRMBF files for selected TRSKL file"
    bl_label = "Export as TRMSH, TRMBF"
    filename_ext = ".trskl"

    filter_glob: StringProperty(
        default="*.trskl",
        options={"HIDDEN"}
    )
    use_normal: BoolProperty(
        name="Use Normal",
        default=True,
    )

    use_tangent: BoolProperty(
        name="Use Tangent",
        default=True,
    )

    use_binormal: BoolProperty(
        name="Use Binormal",
        default=False,
    )

    use_uv: BoolProperty(
        name="Use UVs",
        default=True,
    )

    uv_count: IntProperty(
        name="UV Layer Count",
        default=1,
    )

    use_color: BoolProperty(
        name="Use Vertex Colors",
        default=False,
    )

    color_count: IntProperty(
        name="Color Layer Count",
        default=1,
    )
    use_skinning: BoolProperty(name="Use Skinning", default=True)
    filepath: bpy.props.StringProperty(subtype="FILE_PATH")

    def draw(self, context: bpy.types.Context):
        """
        Drawing exporter's menu.
        :param context: Blender's context.
        """
        self.layout.prop(self, "use_normal")
        self.layout.prop(self, "use_tangent")
        self.layout.prop(self, "use_binormal")
        self.layout.prop(self, "use_uv")
        self.layout.prop(self, "uv_count")
        self.layout.prop(self, "use_color")
        self.layout.prop(self, "color_count")

    def execute(self, context: bpy.types.Context):
        """
        Executing export menu.
        :param context: Blender's context.
        """
        if not os.path.isfile(self.filepath):
            self.report({"ERROR"}, f"{os.path.basename(self.filepath)} is not a TRSKL file.")
            return {"CANCELLED"}
        export_settings = {
            "normal": self.use_normal,
            "tangent": self.use_tangent,
            "binormal": self.use_binormal,
            "uv": self.use_uv,
            "uv_count": self.uv_count,
            "color": self.use_color,
            "color_count": self.color_count,
            "skinning": self.use_skinning
        }
        from .trmshbf_exporter import trskl_to_dict, export_trmbf_trmsh
        bone_dict = trskl_to_dict(self.filepath)
        filename, _ = os.path.splitext(self.filepath)
        file_path = filename + ".trmbf"
        trmbf, trmsh = export_trmbf_trmsh(export_settings, bone_dict, os.path.basename(file_path))
        # Export complete trmbf
        if trmbf is not None:
            with open(file_path, "wb") as file:
                file.write(trmbf)
                print(f"TRMBF successfully exported to {file_path}.")
        # Export complete trmsh
        if trmsh is not None:
            file_path = filename + ".trmsh"
            with open(file_path, "wb") as file:
                file.write(trmsh)
                print(f"TRMSH successfully exported to {file_path}.")
        return {"FINISHED"}


class TRINSImport(bpy.types.Operator, ImportHelper):
    """Import TRINS particle instance files"""
    bl_idname = "import_scene.trins"
    bl_label = "Import TRINS"
    bl_options = {'UNDO'}

    filename_ext = ".trins"
    filter_glob: StringProperty(
        default="*.trins",
        options={'HIDDEN'}
    )

    multiple: BoolProperty(
        name="Load All Folder + Subfolders",
        description="Load all TRINS files in folder",
        default=False
    )

    def draw(self, context):
        self.layout.prop(self, "multiple")

    def execute(self, context):
        directory = os.path.dirname(self.filepath)

        if not self.multiple:
            filename = os.path.basename(self.filepath)
            self.import_trins_file(directory, filename)
            return {"FINISHED"}

        # Load all TRINS files in folder
        for root, dirs, files in os.walk(directory):
            for item in sorted(files):
                if item.endswith(".trins"):
                    self.import_trins_file(root, item)

        return {"FINISHED"}

    def import_trins_file(self, directory, filename):
        filepath = os.path.join(directory, filename)
        with open(filepath, "rb") as f:
            buf = f.read()

        trins = TRINS.TRINS.GetRootAsTRINS(buf, 0)
        ins_buf = trins.Buffer()
        data_bytes = bytearray(ins_buf.DataAsNumpy())
        instances_count = trins.InstanceCount()

        root_name = os.path.splitext(filename)[0]
        root_empty = bpy.data.objects.new(root_name, None)
        bpy.context.collection.objects.link(root_empty)

        for i in range(instances_count):
            start = i * 16 * 4
            end = start + 16 * 4
            instances_bytes = data_bytes[start:end]
            floats = struct.unpack('<16f', instances_bytes)

            # Build 4x4 matrix
            matrix = mathutils.Matrix([
                floats[0:4],
                floats[4:8],
                floats[8:12],
                floats[12:16]
            ]).transposed()

            loc, rot, scale = matrix.decompose()

            # Create particle empty
            instance_name = f"{root_name}_{i}"
            empty = bpy.data.objects.new(instance_name, None)
            bpy.context.collection.objects.link(empty)

            # Parent to root
            empty.parent = root_empty
            empty.empty_display_size = 0.001
            # Apply SRT
            empty.location = loc
            empty.rotation_mode = 'QUATERNION'
            empty.rotation_quaternion = rot
            empty.scale = scale

        # --- Apply 90º X rotation to root ---
        
        root_empty.rotation_mode = 'XYZ'
        root_empty.rotation_euler.x += math.radians(90)

        # Apply the rotation (and scale, though scale is 1)
        bpy.context.view_layer.objects.active = root_empty
        root_empty.select_set(True)
        bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)
        root_empty.select_set(False)

class PokeSVImport(bpy.types.Operator, ImportHelper):
    """
    Class for operator that imports TRMDL files.
    """
    bl_idname = "import_scene.trmdl"
    bl_label = "Import TRMDL"
    bl_description = "Import TRMDL file"
    bl_options = {"PRESET", "UNDO"}
    filename_ext = ".trmdl"
    filter_glob: StringProperty(
        default="*.trmdl",
        options={'HIDDEN'}
    )
    filepath = bpy.props.StringProperty(subtype="FILE_PATH")
    files = CollectionProperty(type=bpy.types.PropertyGroup)
    rare: BoolProperty(
        name="Load Shiny",
        description="Uses rare material instead of normal one",
        default=False
    )
    multiple: BoolProperty(
        name="Load All Folder",
        description="Uses rare material instead of normal one",
        default=False
    )
    loadlods: BoolProperty(
        name="Load LODs",
        description="Uses rare material instead of normal one",
        default=False
    )
    laplayer: BoolProperty(
        name="Player Model from Arceus",
        description="Player Model from Arceus",
        default=False
    )

    def draw(self, context: bpy.types.Context):
        """
        Drawing importer's menu.
        :param context: Blender's context.
        """
        self.layout.prop(self, "rare")
        self.layout.prop(self, "multiple")
        self.layout.prop(self, "loadlods")
        self.layout.prop(self, "laplayer")

    def execute(self, context: bpy.types.Context):
        """
        Executing import menu.
        :param context: Blender's context.
        """
        if not attempt_install_flatbuffers(self, context):
            return {"CANCELLED"}
        from .PokemonSwitch import from_trmdlsv
        directory = os.path.dirname(self.filepath)
        if not self.multiple:
            filename = os.path.basename(self.filepath)
            from_trmdlsv(directory, filename, self.rare, self.loadlods, self.laplayer)
            return {"FINISHED"}
        file_list = sorted(os.listdir(directory))
        obj_list = [item for item in file_list if item.endswith(".trmdl")]
        for item in obj_list:
            from_trmdlsv(directory, item, self.rare, self.loadlods, self.laplayer)
        return {"FINISHED"}


class ImportGfbanm(bpy.types.Operator, ImportHelper):
    """
    Class for operator that imports Pokémon Animation files.
    """
    bl_idname = "import_scene.gfbanm"
    bl_label = "Import GFBANM/TRANM"
    bl_description = "Import one or multiple Nintendo Switch Pokémon Animation files"
    directory: StringProperty()
    filter_glob: StringProperty(default="*.gfbanm;*.tranm", options={"HIDDEN"})
    files: CollectionProperty(type=bpy.types.PropertyGroup)
    ignore_origin_location: BoolProperty(
        name="Ignore Origin Location",
        description="Whether to ignore location transforms for bone named Origin",
        default=False
    )
    use_scene_start: BoolProperty(
        name="Start at Scene range",
        description="Use Scene playback range start frame as first frame of animation",
        default=False
    )
    anim_offset: FloatProperty(
        name="Animation Offset",
        description="Offset to apply to animation during import, in frames",
        default=1.0
    )

    def execute(self, context: bpy.types.Context) -> set[str]:
        """
        Executing import menu.
        :param context: Blender's context.
        :return: Result.
        """
        if not attempt_install_flatbuffers(self, context):
            return {"CANCELLED"}
        if context.active_object is None or context.active_object.type != "ARMATURE":
            self.report({"ERROR"}, "No Armature is selected for action import.")
            return {"CANCELLED"}
        from .gfbanm_importer import import_animation
        if self.files:
            b = False
            for file in self.files:
                file_path = os.path.join(str(self.directory), file.name)
                try:
                    import_animation(context, file_path, self.ignore_origin_location,
                                     context.scene.frame_start if self.use_scene_start
                                     else self.anim_offset)
                except OSError as e:
                    self.report({"INFO"}, f"Failed to import {file_path}. {str(e)}")
                else:
                    b = True
                finally:
                    pass
            if b:
                return {"FINISHED"}
            return {"CANCELLED"}
        try:
            import_animation(context, self.filepath, self.ignore_origin_location,
                             context.scene.frame_start if self.use_scene_start
                             else self.anim_offset)
        except OSError as e:
            self.report({"ERROR"}, f"Failed to import {self.filepath}. {str(e)}")
            return {"CANCELLED"}
        return {"FINISHED"}

    def draw(self, context: bpy.types.Context):
        """
        Drawing importer's menu.
        :param context: Blender's context.
        """
        self.layout.prop(self, "ignore_origin_location")
        self.layout.prop(self, "use_scene_start")
        sub = self.layout.column()
        sub.enabled = not self.use_scene_start
        sub.prop(self, "anim_offset")


def on_export_format_changed(struct: bpy.types.bpy_struct, context: bpy.types.Context):
    """
    Called when export format was updated.
    :param struct: Struct that was changed.
    :param context: Blender's Context.
    """
    if isinstance(struct.id_data, bpy.types.Collection):
        struct.filepath = ExportGfbanm.ensure_filepath_matches_export_format(
            struct.filepath,
            struct.export_format
        )
    if not isinstance(context.space_data, bpy.types.SpaceFileBrowser):
        return
    if not context.space_data.active_operator:
        return
    if context.space_data.active_operator.bl_idname != "EXPORT_SCENE_OT_gfbanm":
        return
    context.space_data.params.filename = ExportGfbanm.ensure_filepath_matches_export_format(
        context.space_data.params.filename,
        struct.export_format,
    )
    if struct.export_format == "TRANM":
        context.space_data.params.filter_glob = "*.tranm"
    else:
        context.space_data.params.filter_glob = "*.gfbanm"
    bpy.ops.file.refresh()


class ExportGfbanm(bpy.types.Operator, ExportHelper):
    """
    Class for operator that exports GFBANM/TRANM files.
    """
    bl_idname = "export_scene.gfbanm"
    bl_label = "Export GFBANM/TRANM"
    bl_description = "Export current action as Nintendo Switch Pokémon Animation file"
    bl_options = {"PRESET", "UNDO"}
    filename_ext = ""
    filter_glob: StringProperty(default="*.gfbanm", options={"HIDDEN"})
    filepath: StringProperty(subtype="FILE_PATH")

    export_format: EnumProperty(
        name="Format",
        items=(("GFBANM", "GFBANM (.gfbanm)",
                "Exports action in format used by Pokémon Sword/Shield."),
               ("TRANM", "TRANM (.tranm)",
                "Exports action in format used by Pokémon Legends: Arceus and "
                "Pokémon Scarlet/Violet.")),
        description="Output format for action",
        default=0,
        update=on_export_format_changed
    )

    does_loop: BoolProperty(
        name="Looping",
        description="Export as looping animation",
        default=False
    )

    use_action_range: BoolProperty(
        name="Use action's frame range",
        description="If available, use action's frame range instead of scene's",
        default=False
    )

    @staticmethod
    def ensure_filepath_matches_export_format(filepath: str, export_format: str) -> str:
        """
        Ensures file path matches export format.
        :param filepath: File path string.
        :param export_format: Export format string.
        :return: Modified file path string.
        """
        filename = os.path.basename(filepath)
        if not filename:
            return filepath
        stem, ext = os.path.splitext(filename)
        if stem.startswith(".") and not ext:
            stem, ext = "", stem
        desired_ext = ".tranm" if export_format == "TRANM" else ".gfbanm"
        ext_lower = ext.lower()
        if ext_lower not in [".gfbanm", ".tranm"]:
            return filepath + desired_ext
        if ext_lower != desired_ext:
            filepath = filepath[:-len(ext)]
            return filepath + desired_ext
        return filepath

    def check(self, context: bpy.types.Context) -> bool:
        """
        Checks if operator needs to be updated.
        :param context: Blender's Context.
        :return: True if update is needed, False otherwise.
        """
        old_filepath = self.filepath
        self.filepath = ExportGfbanm.ensure_filepath_matches_export_format(self.filepath,
                                                                           self.export_format)
        return self.filepath != old_filepath

    def invoke(self, context: bpy.types.Context, _event: bpy.types.Event) -> set[str]:
        """
        Called when operator is invoked by user.
        :param context: Blender's Context.
        :param _event: Event invoked.
        :return: Result.
        """
        directory = os.path.dirname(self.filepath)
        filename = os.path.splitext(os.path.basename(context.blend_data.filepath))[0]
        obj = context.object
        if obj and obj.animation_data and obj.animation_data.action:
            filename = obj.animation_data.action.name
        self.filepath = ExportGfbanm.ensure_filepath_matches_export_format(
            os.path.join(directory, filename), self.export_format)
        context.window_manager.fileselect_add(self)
        return {"RUNNING_MODAL"}

    def draw(self, context: bpy.types.Context):
        """
        Drawing exporter's menu.
        :param context: Blender's context.
        """
        self.layout.prop(self, "export_format")
        self.layout.prop(self, "does_loop")
        self.layout.prop(self, "use_action_range")

    def execute(self, context: bpy.types.Context) -> set[str]:
        """
        Executing export menu.
        :param context: Blender's context.
        :return: Result.
        """
        if not attempt_install_flatbuffers(self, context):
            return {"CANCELLED"}
        if context.active_object is None or context.active_object.type != "ARMATURE":
            self.report({"ERROR"}, "No Armature is selected for action export.")
            return {"CANCELLED"}
        directory = os.path.dirname(self.filepath)
        from .gfbanm_exporter import export_animation
        data = export_animation(context, self.does_loop, self.use_action_range)
        file_path = os.path.join(directory, self.filepath)
        with open(file_path, "wb") as file:
            file.write(data)
            print(f"Armature action successfully exported to {file_path}.")
        return {"FINISHED"}


class PokemonSwitchImportMenu(bpy.types.Menu):
    """
    Class for menu containing import operators.
    """
    bl_idname = "import_pokemonswitch"
    bl_label = "Nintendo Switch Pokémon Assets"

    def draw(self, context: bpy.types.Context):
        """
        Drawing menu.
        :param context: Blender's context.
        """
        self.layout.operator(PokeSVImport.bl_idname, text="Pokémon Trinity Model (.trmdl)")
        self.layout.operator(ImportGfbanm.bl_idname, text="Pokémon Animation (.gfbanm/.tranm)")
        self.layout.operator(TRINSImport.bl_idname, text="Pokémon Map Instances (.trins)")
        self.layout.operator(TRSCNImport.bl_idname, text="Pokémon Scene Object (.trscn)")


class PokemonSwitchExportMenu(bpy.types.Menu):
    """
    Class for menu containing export operators.
    """
    bl_idname = "export_pokemonswitch"
    bl_label = "Nintendo Switch Pokémon Assets"

    def draw(self, context: bpy.types.Context):
        """
        Drawing menu.
        :param context: Blender's context.
        """
        self.layout.operator(TRSKLExport.bl_idname, text="Pokémon Trinity Skeleton (.trskl)")
        self.layout.operator(ExportGfbanm.bl_idname,
                             text="Pokémon Animation (.gfbanm/.tranm)")
        self.layout.operator(ExportTRMBFMSH.bl_idname,
                             text="Pokémon Trinity Mesh (.trmsh, .trmbf)")


def menu_func_import(operator: bpy.types.Operator, context: bpy.types.Context):
    """
    Function that adds import operators.
    :param operator: Blender's operator.
    :param context: Blender's Context.
    :return:
    """
    operator.layout.menu(PokemonSwitchImportMenu.bl_idname)


def menu_func_export(operator: bpy.types.Operator, context: bpy.types.Context):
    """
    Function that adds export operators.
    :param operator: Blender's operator.
    :param context: Blender's Context.
    :return:
    """
    operator.layout.menu(PokemonSwitchExportMenu.bl_idname)


def register():
    """
    Registering addon.
    """
    register_class(PokemonSwitchImportMenu)
    register_class(PokeSVImport)
    register_class(ImportGfbanm)
    register_class(TRSCNImport)
    register_class(TRINSImport)
    bpy.types.TOPBAR_MT_file_import.append(menu_func_import)
    register_class(PokemonSwitchExportMenu)
    register_class(TRSKLExport)
    register_class(ExportGfbanm)
    register_class(ExportTRMBFMSH)
    bpy.types.TOPBAR_MT_file_export.append(menu_func_export)


def unregister():
    """
    Unregistering addon.
    """
    unregister_class(PokemonSwitchImportMenu)
    unregister_class(PokeSVImport)
    unregister_class(ImportGfbanm)
    unregister_class(TRSCNImport)
    unregister_class(TRINSImport)
    bpy.types.TOPBAR_MT_file_import.remove(menu_func_import)
    unregister_class(PokemonSwitchExportMenu)
    unregister_class(TRSKLExport)
    unregister_class(ExportGfbanm)
    unregister_class(ExportTRMBFMSH)
    bpy.types.TOPBAR_MT_file_export.remove(menu_func_export)


def attempt_install_flatbuffers(operator: bpy.types.Operator, context: bpy.types.Context) -> bool:
    """
    Attempts installing flatbuffers library if it's not installed using pip.
    :return: True if flatbuffers was found or successfully installed, False otherwise.
    """
    if are_flatbuffers_installed():
        return True
    if bpy.app.version >= (4, 2, 0) and not bpy.app.online_access:
        msg = "Can't install flatbuffers library using pip - Internet access is not allowed."
        operator.report({"INFO"}, msg)
        return False
    modules_path = bpy.utils.user_resource("SCRIPTS", path="modules", create=True)
    site.addsitedir(modules_path)
    context.window_manager.progress_begin(0, 3)
    ensurepip.bootstrap()
    context.window_manager.progress_update(1)
    subprocess.call([sys.executable, "-m", "pip", "install", "--upgrade", "pip"])
    context.window_manager.progress_update(2)
    try:
        subprocess.check_call(
            [sys.executable, "-m", "pip", "install", "--upgrade", "--target", modules_path,
             "flatbuffers"])
    except subprocess.SubprocessError as e:
        context.window_manager.progress_update(3)
        context.window_manager.progress_end()
        msg = (f"Failed to install flatbuffers library using pip. {e}\n"
               f"To use this addon, put Python flatbuffers library folder for your platform"
               f"to this path: {modules_path}.")
        operator.report({"INFO"}, msg)
        return False
    context.window_manager.progress_update(3)
    context.window_manager.progress_end()
    if are_flatbuffers_installed():
        msg = "Successfully installed flatbuffers library."
        operator.report({"INFO"}, msg)
        return True
    msg = ("Failed to install flatbuffers library using pip."
           f"To use this addon, put Python flatbuffers library folder for your platform"
           f"to this path: {modules_path}.")
    operator.report({"ERROR"}, msg)
    return False

if __name__ == "__main__":
    register()
