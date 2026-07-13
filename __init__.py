bl_info = {
    "name": "Terrence Engine Header Export",
    "author": "Flowering",
    "version": (1, 0),
    "blender": (5, 0, 0),
    "location": "File > Export > Terrence Engine Header (.h)",
    "category": "Import-Export",
}

import bpy

from .exporter import ExportWiiMesh


def menu_func_export(self, context):
    self.layout.operator(
        ExportWiiMesh.bl_idname,
        text="Terrence Engine Header (.h)"
    )


def register():
    bpy.utils.register_class(ExportWiiMesh)

    bpy.types.TOPBAR_MT_file_export.append(
        menu_func_export
    )


def unregister():
    bpy.types.TOPBAR_MT_file_export.remove(
        menu_func_export
    )

    bpy.utils.unregister_class(ExportWiiMesh)


if __name__ == "__main__":
    register()