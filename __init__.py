"""
    Init for GFBANM Importer addon.
"""
import os
import sys
import subprocess
import bpy
import json
from bpy.props import *
from bpy.utils import register_class, unregister_class
from bpy_extras.io_utils import ImportHelper, ExportHelper
sys.path.append(os.path.join(os.path.dirname(__file__), "."))
from Titan.Model.TRMDL import TRMDL
from Titan.Model.TRSKL import TRSKL
import flatbuffers
bl_info = {
    "name": "Pokémon Switch V3 (.TRMDL)",
    "author": "Scarlett/SomeKitten, Tavi, Luma & ElChicoEevee",
    "version": (2, 0, 0),
    "blender": (3, 3, 0),
    "location": "File > Import",
    "description": "Blender addon for import Pokémon Switch TRMDL",
    "warning": "",
    "category": "Import",
}

class TRSKLJsonExport(bpy.types.Operator, ExportHelper):
    bl_idname = "custom_export_scene.trskljsonexport"
    bl_label = "Export"
    bl_options = {'PRESET', 'UNDO'}

    filename_ext = ".json"  # Specify the default file extension

    def execute(self, context):
        directory = os.path.dirname(self.filepath)
        armature_obj = bpy.context.active_object
        from .ExportTRSKL import export_armature_matrix
        if armature_obj and armature_obj.type == 'ARMATURE':
            data = export_armature_matrix(armature_obj)
            # Save the data to a JSON file
            with open(os.path.join(directory, self.filepath), "w") as file:
                json.dump(data, file, indent=4)
            print("Bone matrices exported successfully.")
        else:
            print("No armature selected.")
        return {'FINISHED'}
class PokeSVImport(bpy.types.Operator, ImportHelper):
    bl_idname = "custom_import_scene.pokemonscarletviolet"
    bl_label = "Import"
    bl_options = {'PRESET', 'UNDO'}
    filename_ext = ".trmdl"
    filter_glob: StringProperty(
            default="*.trmdl",
            options={'HIDDEN'},
            maxlen=255,
    )
    filepath = bpy.props.StringProperty(subtype='FILE_PATH',)
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
            name="Load LODS",
            description="Uses rare material instead of normal one",
            default=False,
            )
    bonestructh: BoolProperty(
            name="Bone Extras (WIP)",
            description="Bone Extras (WIP)",
            default=False,
            )
    def draw(self, context):
        layout = self.layout

        box = layout.box()
        box.prop(self, 'rare')
        
        box = layout.box()
        box.prop(self, 'multiple')
        
        box = layout.box()
        box.prop(self, 'loadlods')

        box = layout.box()
        box.prop(self, 'bonestructh')
        

    def execute(self, context: bpy.types.Context):
        if not attempt_install_flatbuffers(self):
            self.report({"ERROR"}, "Failed to install flatbuffers library using pip. "
                                   "To use this addon, put Python flatbuffers library folder "
                                   "to this path: " + get_site_packages_path() + ".")
            return {"CANCELLED"}
        from .PokemonSwitch import from_trmdlsv
        directory = os.path.dirname(self.filepath)
        if self.multiple == False:
            filename = os.path.basename(self.filepath)        
            f = open(os.path.join(directory, filename), "rb")
            from_trmdlsv(directory, filename, self.rare, self.loadlods, self.bonestructh)
            f.close()
            return {'FINISHED'}  
        else:
            file_list = sorted(os.listdir(directory))
            obj_list = [item for item in file_list if item.endswith('.trmdl')]
            for item in obj_list:
                from_trmdlsv(directory, item, self.rare, self.loadlods, self.bonestructh)
                f.close()
            return {'FINISHED'}

    @classmethod
    def poll(cls, context: bpy.types.Context):
        """
        Checking if operator can be active.
        :param context: Blender's Context.
        :return: True if active, False otherwise.
        """
        return True
def menu_func_export(self, context):
    self.layout.operator(TRSKLJsonExport.bl_idname, text="Pokémon Trinity Skeleton (.json)")

def menu_func_import(operator: bpy.types.Operator, context: bpy.types.Context):
    """
    Function that adds GFBANM import operator.
    :param operator: Blender's operator.
    :param context: Blender's Context.
    :return:
    """
    operator.layout.operator(PokeSVImport.bl_idname, text="Pokémon Trinity Model (.trmdl)")


def register():
    """
    Registering addon.
    """
    register_class(PokeSVImport)
    bpy.types.TOPBAR_MT_file_import.append(menu_func_import)
    register_class(TRSKLJsonExport)
    bpy.types.TOPBAR_MT_file_export.append(menu_func_export)

def unregister():
    """
    Unregistering addon.
    :return:
    """
    unregister_class(PokeSVImport)
    bpy.types.TOPBAR_MT_file_import.remove(menu_func_import)
    unregister_class(TRSKLJsonExport)
    bpy.types.TOPBAR_MT_file_export.remove(menu_func_export)

def attempt_install_flatbuffers(operator: bpy.types.Operator = None) -> bool:
    """
    Attempts installing flatbuffers library if it's not installed using pip.
    :return: True if flatbuffers was found or successfully installed, False otherwise.
    """
    if are_flatbuffers_installed():
        return True
    target = get_site_packages_path()
    subprocess.call([sys.executable, "-m", 'ensurepip'])
    subprocess.call([sys.executable, "-m", "pip", "install", "--upgrade", "pip"])
    subprocess.call(
        [sys.executable, "-m", "pip", "install", "--upgrade", "flatbuffers", "-t", target])
    if are_flatbuffers_installed():
        if operator is not None:
            operator.report({"INFO"},
                            "Successfully installed flatbuffers library to " + target + ".")
        else:
            print("Successfully installed flatbuffers library to " + target + ".")
        return True
    return False


def are_flatbuffers_installed() -> bool:
    """
    Checks if flatbuffers library is installed.
    :return: True or False.
    """
    try:
        import flatbuffers
    except ModuleNotFoundError:
        return False
    return True


def get_site_packages_path():
    """
    Returns file path to lib/site-packages folder.
    :return: File path to lib/site-packages folder.
    """
    return os.path.join(sys.prefix, "lib", "site-packages")


if __name__ == "__main__":
    register()
