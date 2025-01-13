"""
    Init for GFBANM Importer addon.
"""
import os
import sys
import subprocess
import bpy
from bpy.props import *
from bpy.utils import register_class, unregister_class
from bpy_extras.io_utils import ImportHelper, ExportHelper
bl_info = {
    "name": "Pokémon Switch V3 (.TRMDL)",
    "author": "SomeKitten, Shararamosh, Tavi, Luma & ElChicoEevee",
    "version": (2, 0, 0),
    "blender": (3, 3, 0),
    "location": "File > Import",
    "description": "Blender addon for import Pokémon Switch TRMDL",
    "warning": "",
    "category": "Import",
}

class TRSKLExport(bpy.types.Operator, ExportHelper):
    """
    Class for operator that exports TRSKL files.
    """
    bl_idname = "custom_export_scene.trsklexport"
    bl_label = "Export"
    bl_options = {'PRESET', 'UNDO'}
    filename_ext = ".trskl"  # Specify the default file extension
    def execute(self, context: bpy.types.Context):
        directory = os.path.dirname(self.filepath)
        armature_obj = context.active_object
        from .trskl_exporter import export_skeleton
        if armature_obj and armature_obj.type == "ARMATURE":
            if not attempt_install_flatbuffers(self):
                self.report({"ERROR"}, "Failed to install flatbuffers library using pip. "
                                       "To use this addon, put Python flatbuffers library folder "
                                       "to this path: " + get_site_packages_path() + ".")
                return {"CANCELLED"}
            data = export_skeleton(armature_obj)
            # Save the data to a TRSKL file
            file_path = os.path.join(directory, self.filepath)
            with open(file_path, "wb") as file:
                file.write(data)
                print("Skeleton information successfully exported to "+file_path+".")
            return {"FINISHED"}
        print("No armature selected.")
        return {"CANCELLED"}
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
    def draw(self, _context: bpy.types.Context):
        layout = self.layout

        box = layout.box()
        box.prop(self, 'rare')
        
        box = layout.box()
        box.prop(self, 'multiple')
        
        box = layout.box()
        box.prop(self, 'loadlods')

        box = layout.box()
        box.prop(self, 'bonestructh')
        

    def execute(self, _context: bpy.types.Context):
        if not attempt_install_flatbuffers(self):
            self.report({"ERROR"}, "Failed to install flatbuffers library using pip. "
                                   "To use this addon, put Python flatbuffers library folder "
                                   "to this path: " + get_site_packages_path() + ".")
            return {"CANCELLED"}
        from .PokemonSwitch import from_trmdlsv
        directory = os.path.dirname(self.filepath)
        if not self.multiple:
            filename = os.path.basename(self.filepath)
            from_trmdlsv(directory, filename, self.rare, self.loadlods, self.bonestructh)
            return {'FINISHED'}
        file_list = sorted(os.listdir(directory))
        obj_list = [item for item in file_list if item.endswith('.trmdl')]
        for item in obj_list:
            from_trmdlsv(directory, item, self.rare, self.loadlods, self.bonestructh)
        return {'FINISHED'}

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
            self.report({"ERROR"}, "Failed to install flatbuffers library using pip. "
                                   "To use this addon, put Python flatbuffers library folder "
                                   "to this path: " + get_site_packages_path() + ".")
            return {"CANCELLED"}
        from .gfbanm_importer import import_animation
        if self.files:
            b = False
            for file in self.files:
                try:
                    import_animation(context, os.path.join(str(self.directory), file.name),
                                     self.ignore_origin_location)
                except OSError as e:
                    self.report({"INFO"}, "Failed to import " + os.path.join(str(self.directory),
                                                                             file.name) + ".\n" + str(
                        e))
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
            self.report({"ERROR"}, "Failed to import " + self.filepath + ".\n" + str(e))
            return {"CANCELLED"}
        return {"FINISHED"}

    @classmethod
    def poll(cls, _context: bpy.types.Context):
        """
        Checking if operator can be active.
        :param _context: Blender's Context.
        :return: True if active, False otherwise.
        """
        return True

    def draw(self, _context: bpy.types.Context):
        box = self.layout.box()
        box.prop(self, "ignore_origin_location", text="Ignore Origin Location")

def menu_func_export(self, _context: bpy.types.Context):
    self.layout.operator(TRSKLExport.bl_idname, text="Pokémon Trinity Skeleton (.trskl)")

def menu_func_import(operator: bpy.types.Operator, _context: bpy.types.Context):
    operator.layout.operator(PokeSVImport.bl_idname, text="Pokémon Trinity Model (.trmdl)")
    operator.layout.operator(ImportGfbanm.bl_idname, text="Pokémon Switch Anim (.gfbanm, .tranm)")

def register():
    register_class(PokeSVImport)
    register_class(ImportGfbanm)
    bpy.types.TOPBAR_MT_file_import.append(menu_func_import)
    register_class(TRSKLExport)
    bpy.types.TOPBAR_MT_file_export.append(menu_func_export)

def unregister():
    unregister_class(PokeSVImport)
    unregister_class(ImportGfbanm)
    bpy.types.TOPBAR_MT_file_import.remove(menu_func_import)
    unregister_class(TRSKLExport)
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
