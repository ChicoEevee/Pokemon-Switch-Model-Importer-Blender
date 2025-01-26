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

# pylint: disable=import-outside-toplevel, wrong-import-position, import-error, unused-import
# pylint: disable=too-few-public-methods

bl_info = {
    "name": "Pokémon Switch V3 (.TRMDL, .GFBANM/.TRANM)",
    "author": "SomeKitten, Shararamosh, Tavi, Luma & ElChicoEevee",
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
    bl_label = "Export"
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


class PokeSVImport(bpy.types.Operator, ImportHelper):
    """
    Class for operator that imports TRMDL files.
    """
    bl_idname = "custom_import_scene.pokemonscarletviolet"
    bl_description = "Import TRMDL file"
    bl_label = "Import"
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
        layout = self.layout
        box = layout.box()
        box.prop(self, "rare")
        box = layout.box()
        box.prop(self, "multiple")
        box = layout.box()
        box.prop(self, "loadlods")
        box = layout.box()
        box.prop(self, "bonestructh")

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

    @classmethod
    def poll(cls, _context: bpy.types.Context):
        """
        Checking if operator can be active.
        :param _context: Blender's Context.
        :return: True if active, False otherwise.
        """
        return True


class ImportGfbanm(bpy.types.Operator, ImportHelper):
    """
    Class for operator that imports GFBANM files.
    """
    bl_idname = "import.gfbanm"
    bl_label = "Import GFBANM/TRANM"
    bl_description = "Import one or multiple GFBANM/TRANM files"
    directory: StringProperty()
    filter_glob: StringProperty(default="*.gfbanm;*.tranm", options={'HIDDEN'})
    files: CollectionProperty(type=bpy.types.PropertyGroup)
    ignore_origin_location: BoolProperty(
        name="Ignore Origin Location",
        description="Ignore Origin Location",
        default=False
    )

    def execute(self, context: bpy.types.Context):
        """
        Executing import menu.
        :param context: Blender's context.
        """
        if not attempt_install_flatbuffers(self):
            return {"CANCELLED"}
        from .gfbanm_importer import import_animation  # pylint: disable=import-outside-toplevel
        if self.files:
            b = False
            for file in self.files:
                file_path = os.path.join(str(self.directory), file.name)
                try:
                    import_animation(context, file_path, self.ignore_origin_location)
                except OSError as e:
                    file_path = os.path.join(str(self.directory), file.name)
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
        box = self.layout.box()
        box.prop(self, "ignore_origin_location", text="Ignore Origin Location")


class ExportGfbanm(bpy.types.Operator, ExportHelper):
    """
    Class for operator that exports GFBANM files.
    """
    bl_idname = "export.gfbanm"
    bl_label = "Export GFBANM (WIP)"
    bl_description = "Export current action as GFBANM file"
    bl_options = {"PRESET", "UNDO"}
    filename_ext = ".gfbanm"
    does_loop: BoolProperty(
        name="Looping action",
        description="Export as looping action",
        default=False,
    )

    def draw(self, _context: bpy.types.Context):
        """
        Drawing exporter's menu.
        :param _context: Blender's context.
        """
        layout = self.layout
        box = layout.box()
        box.prop(self, "does_loop")

    def execute(self, context: bpy.types.Context):
        """
        Executing export menu.
        :param context: Blender's context.
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


class ExportTranm(bpy.types.Operator, ExportHelper):
    """
    Class for operator that exports TRANM files.
    """
    bl_idname = "export.tranm"
    bl_label = "Export TRANM (WIP)"
    bl_description = "Export current action as TRANM file"
    filename_ext = ".tranm"
    does_loop: BoolProperty(
        name="Looping action",
        description="Export as looping action",
        default=False,
    )

    def draw(self, _context: bpy.types.Context):
        """
        Drawing exporter's menu.
        :param _context: Blender's context.
        """
        layout = self.layout
        box = layout.box()
        box.prop(self, "does_loop")

    def execute(self, context: bpy.types.Context):
        """
        Executing export menu.
        :param context: Blender's context.
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
        layout = self.layout
        layout.operator(PokeSVImport.bl_idname, text="Pokémon Trinity Model (.trmdl)")
        layout.operator(ImportGfbanm.bl_idname, text="Pokémon Switch Anim (.gfbanm, .tranm)")

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
        layout = self.layout
        layout.operator(TRSKLExport.bl_idname, text="Pokémon Trinity Skeleton (.trskl)")
        layout.operator(ExportGfbanm.bl_idname, text="Pokémon Sword/Shield Anim (.gfbanm)")
        layout.operator(ExportTranm.bl_idname, text="Pokémon Trinity Anim (.tranm)")


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
    register_class(ExportTranm)
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
    unregister_class(ExportTranm)
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
