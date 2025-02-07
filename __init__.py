"""
    Blender addon for importing and exporting assets from Nintendo Switch Pokémon games.
"""
import os
import sys
import sysconfig
import subprocess
import bpy
from bpy.props import *
from bpy.utils import register_class, unregister_class
from bpy_extras.io_utils import ImportHelper, ExportHelper
import json
# pylint: disable=import-outside-toplevel, wrong-import-position, import-error, unused-import
# pylint: disable=too-few-public-methods

bl_info = {
    "name": "Pokémon Switch V3 (TRMDL, GFBANM/TRANM)",
    "author": "SomeKitten, Shararamosh, Tavi, Luma, mv & ElChicoEevee",
    "version": (3, 0, 0),
    "blender": (3, 3, 0),
    "location": "File > Import",
    "description": "Blender addon for importing and exporting Nintendo Switch Pokémon Assets.",
    "warning": "",
    "category": "Import",
}


class TRSKLExport(bpy.types.Operator, ExportHelper):
    """
    Class for operator that exports TRSKL files.
    """
    bl_idname = "custom_export_scene.trsklexport"
    bl_description = "Export current Armature as TRSKL file"
    bl_label = "Export as TRSKL"
    bl_options = {"PRESET", "UNDO"}
    filename_ext = ".trskl"  # Specify the default file extension

    def execute(self, context: bpy.types.Context):
        """
        Executing export menu.
        :param context: Blender's context.
        """
        directory = os.path.dirname(self.filepath)
        armature_obj = context.active_object
        from .trskl_exporter import export_skeleton
        if armature_obj and armature_obj.type == "ARMATURE":
            if not attempt_install_flatbuffers(self):
                return {"CANCELLED"}
            data = export_skeleton(armature_obj)
            # Save the data to a TRSKL file
            file_path = os.path.join(directory, self.filepath)
            with open(file_path, "wb") as file:
                file.write(data)
                print("Skeleton information successfully exported to " + file_path + ".")
            return {"FINISHED"}
        print("No armature selected.")
        return {"CANCELLED"}


class ExportTRMBFMSH(bpy.types.Operator, ExportHelper):
    """This appears in the tooltip of the operator and in the generated docs"""

    bl_idname = "export.trmshtrmbf"
    bl_label = "Export TRMSH TRMBF"

    # ExportHelper mixin class uses this
    filename_ext = ".json"

    filter_glob: StringProperty(
        default="*.trskl",
        options={"HIDDEN"},
        maxlen=255,  # Max internal buffer length, longer would be clamped.
    )

    # List of operator properties, the attributes will be assigned
    # to the class instance from the operator settings before calling.
    use_normal: BoolProperty(
        name="Use Normal",
        default=True,
    )

    use_tangent: BoolProperty(
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
    filenaming: StringProperty(
        name="Filename IMPORTANT",
        default="pm0133_00_00",
    )
    use_skinning: BoolProperty(name="Use Skinning", default=True)
    filepath: bpy.props.StringProperty(subtype="FILE_PATH")

    def draw(self, _context: bpy.types.Context):
        """
        Drawing exporter's menu.
        :param _context: Blender's context.
        """
        self.layout.prop(self, "use_normal")
        self.layout.prop(self, "use_tangent")
        self.layout.prop(self, "use_binormal")
        self.layout.prop(self, "use_uv")
        self.layout.prop(self, "uv_count")
        self.layout.prop(self, "use_color")
        self.layout.prop(self, "color_count")
        self.layout.prop(self, "filenaming")
        
        
    def execute(self, context):
        from .trmshbf_exporter import write_mesh_data
        from .trmshbf_exporter import write_buffer_data
        from .trmshbf_exporter import readtrskl
        dest_dir = os.path.dirname(self.filepath)
        bone_dict = readtrskl(self.filepath.replace(".json",".trskl"))
        export_settings = {
            "normal": self.use_normal,
            "tangent": self.use_tangent,
            "binormal": self.use_binormal,
            "uv": self.use_uv,
            "uv_count": self.uv_count,
            "color": self.use_color,
            "color_count": self.color_count,
            "skinning": self.use_skinning,
        }
        trmbf = []
        trmsh = []
        for obj in bpy.context.selected_objects:
            trmbf.append(write_buffer_data(
                context,
                obj,
                export_settings,
                bone_dict
            ))
            trmsh.append(write_mesh_data(
                context,
                obj,
                export_settings,
            ))
        complete_trmbf = {
            "unused": 0,
            "buffers": trmbf,
        }
        complete_trmsh = {
            "unk0": 0,
            "meshes": trmsh,
            "buffer_name": self.filenaming + ".trmbf",
        }
        
        # Export complete trmbf
        f = open(os.path.join(dest_dir, self.filenaming + ".trmbf" + self.filename_ext), "w", encoding="utf-8")
        f.write(json.dumps(complete_trmbf, indent=4))
        f.close()
        # Export complete_trmsh
        f = open(os.path.join(dest_dir, self.filenaming + ".trmsh" + self.filename_ext), "w", encoding="utf-8")
        f.write(json.dumps(complete_trmsh, indent=4))
        f.close()
        return {"FINISHED"}


class PokeSVImport(bpy.types.Operator, ImportHelper):
    """
    Class for operator that imports TRMDL files.
    """
    bl_idname = "custom_import_scene.pokemonscarletviolet"
    bl_label = "Import TRMDL"
    bl_description = "Import TRMDL file"
    bl_options = {"PRESET", "UNDO"}
    filename_ext = ".trmdl"
    filter_glob: StringProperty(
        default="*.trmdl",
        options={'HIDDEN'},
        maxlen=255,
    )
    filepath = bpy.props.StringProperty(subtype="FILE_PATH")
    files = CollectionProperty(type=bpy.types.PropertyGroup)
    rare: BoolProperty(
        name="Load Shiny",
        description="Uses rare material instead of normal one",
        default=False,
    )
    multiple: BoolProperty(
        name="Load All Folder",
        description="Uses rare material instead of normal one",
        default=False,
    )
    loadlods: BoolProperty(
        name="Load LODs",
        description="Uses rare material instead of normal one",
        default=False,
    )
    bonestructh: BoolProperty(
        name="Bone Extras (WIP)",
        description="Bone Extras (WIP)",
        default=False,
    )

    def draw(self, _context: bpy.types.Context):
        """
        Drawing importer's menu.
        :param _context: Blender's context.
        """
        self.layout.prop(self, "rare")
        self.layout.prop(self, "multiple")
        self.layout.prop(self, "loadlods")
        self.layout.prop(self, "bonestructh")

    def execute(self, _context: bpy.types.Context):
        """
        Executing import menu.
        :param _context: Blender's context.
        """
        if not attempt_install_flatbuffers(self):
            return {"CANCELLED"}
        from .PokemonSwitch import from_trmdlsv  # pylint: disable=import-outside-toplevel
        directory = os.path.dirname(self.filepath)
        if not self.multiple:
            filename = os.path.basename(self.filepath)
            from_trmdlsv(directory, filename, self.rare, self.loadlods, self.bonestructh)
            return {"FINISHED"}
        file_list = sorted(os.listdir(directory))
        obj_list = [item for item in file_list if item.endswith(".trmdl")]
        for item in obj_list:
            from_trmdlsv(directory, item, self.rare, self.loadlods, self.bonestructh)
        return {"FINISHED"}


class ImportGfbanm(bpy.types.Operator, ImportHelper):
    """
    Class for operator that imports Pokémon Animation files.
    """
    bl_idname = "import.gfbanm"
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

    def execute(self, context: bpy.types.Context) -> set[str]:
        """
        Executing import menu.
        :param context: Blender's context.
        :return: Result.
        """
        if not attempt_install_flatbuffers(self):
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
                    import_animation(context, file_path, self.ignore_origin_location)
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
            import_animation(context, self.filepath, self.ignore_origin_location)
        except OSError as e:
            self.report({"ERROR"}, f"Failed to import {self.filepath}. {str(e)}")
            return {"CANCELLED"}
        return {"FINISHED"}

    def draw(self, _context: bpy.types.Context):
        """
        Drawing importer's menu.
        :param _context: Blender's context.
        """
        self.layout.prop(self, "ignore_origin_location")


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
    if context.space_data.active_operator.bl_idname != "EXPORT_OT_gfbanm":
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
    bl_idname = "export.gfbanm"
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

    def check(self, _context: bpy.types.Context) -> bool:
        """
        Checks if operator needs to be updated.
        :param _context: Blender's Context.
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

    def draw(self, _context: bpy.types.Context):
        """
        Drawing exporter's menu.
        :param _context: Blender's context.
        """
        self.layout.prop(self, "export_format")
        self.layout.prop(self, "does_loop")

    def execute(self, context: bpy.types.Context) -> set[str]:
        """
        Executing export menu.
        :param context: Blender's context.
        :return: Result.
        """
        if not attempt_install_flatbuffers(self):
            return {"CANCELLED"}
        if context.active_object is None or context.active_object.type != "ARMATURE":
            self.report({"ERROR"}, "No Armature is selected for action export.")
            return {"CANCELLED"}
        directory = os.path.dirname(self.filepath)
        from .gfbanm_exporter import export_animation
        data = export_animation(context, self.does_loop)
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

    def draw(self, _context: bpy.types.Context):
        """
        Drawing menu.
        :param _context: Blender's context.
        """
        self.layout.operator(PokeSVImport.bl_idname, text="Pokémon Trinity Model (.trmdl)")
        self.layout.operator(ImportGfbanm.bl_idname, text="Pokémon Animation (.gfbanm/.tranm)")


class PokemonSwitchExportMenu(bpy.types.Menu):
    """
    Class for menu containing export operators.
    """
    bl_idname = "export_pokemonswitch"
    bl_label = "Nintendo Switch Pokémon Assets"

    def draw(self, _context: bpy.types.Context):
        """
        Drawing menu.
        :param _context: Blender's context.
        """
        self.layout.operator(TRSKLExport.bl_idname, text="Pokémon Trinity Skeleton (.trskl)")
        self.layout.operator(ExportGfbanm.bl_idname,
                             text="Pokémon Animation (.gfbanm/.tranm) [WIP]")
        self.layout.operator(ExportTRMBFMSH.bl_idname,
                             text="Trinity Mesh Buffer Jsons (.trmsh/.trmbf)")


def menu_func_import(operator: bpy.types.Operator, _context: bpy.types.Context):
    """
    Function that adds import operators.
    :param operator: Blender's operator.
    :param _context: Blender's Context.
    :return:
    """
    operator.layout.menu(PokemonSwitchImportMenu.bl_idname)


def menu_func_export(operator: bpy.types.Operator, _context: bpy.types.Context):
    """
    Function that adds export operators.
    :param operator: Blender's operator.
    :param _context: Blender's Context.
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
    bpy.types.TOPBAR_MT_file_import.remove(menu_func_import)
    unregister_class(PokemonSwitchExportMenu)
    unregister_class(TRSKLExport)
    unregister_class(ExportGfbanm)
    unregister_class(ExportTRMBFMSH)
    bpy.types.TOPBAR_MT_file_export.remove(menu_func_export)


def attempt_install_flatbuffers(operator: bpy.types.Operator = None) -> bool:
    """
    Attempts installing flatbuffers library if it's not installed using pip.
    :return: True if flatbuffers was found or successfully installed, False otherwise.
    """
    if are_flatbuffers_installed():
        return True
    subprocess.call([sys.executable, "-m", "ensurepip"])
    subprocess.call([sys.executable, "-m", "pip", "install", "--upgrade", "pip"])
    subprocess.call([sys.executable, "-m", "pip", "install", "--upgrade", "flatbuffers"])
    if are_flatbuffers_installed():
        msg = "Successfully installed flatbuffers library."
        if operator is not None:
            operator.report({"INFO"}, msg)
        else:
            print(msg)
        return True
    platlib_path = sysconfig.get_path("platlib")
    msg = ("Failed to install flatbuffers library using pip. "
           f"To use this addon, put Python flatbuffers library folder "
           f"to this path: {platlib_path}.")
    if operator is not None:
        operator.report({"ERROR"}, msg)
    else:
        print(msg)
    return False


def are_flatbuffers_installed() -> bool:
    """
    Checks if flatbuffers library is installed.
    :return: True or False.
    """
    try:
        import flatbuffers  # pylint: disable=import-outside-toplevel, unused-import
    except ModuleNotFoundError:
        return False
    return True


if __name__ == "__main__":
    register()
