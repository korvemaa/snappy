bl_info = {
    "name": "Snappy",
    "blender": (5, 0, 0),
    "category": "View3D"
}

import bpy

class IncrementGrid(bpy.types.Operator):
    bl_idname = "view3d.increment_grid"
    bl_label = "Increment Grid"

    def execute(self, context):
        context.space_data.overlay.grid_scale *= 2
        return {'FINISHED'}

class DecrementGrid(bpy.types.Operator):
    bl_idname = "view3d.decrement_grid"
    bl_label = "Decrement Grid"

    def execute(self, context):
        context.space_data.overlay.grid_scale *= 0.5
        return {'FINISHED'}

addon_keymaps = []

def register():
    bpy.utils.register_class(IncrementGrid)
    bpy.utils.register_class(DecrementGrid)

    print("hello world")

    wm = bpy.context.window_manager
    kc = wm.keyconfigs.addon

    if kc:
        km = kc.keymaps.new(name='View3D', space_type='EMPTY')
        kmi = km.keymap_items.new(IncrementGrid.bl_idname, 'LEFT_BRACKET', 'PRESS')
        addon_keymaps.append((km, kmi))

def unregister():
    for km, kmi in addon_keymaps:
        km.keymap_items.remove(kmi)

    addon_keymaps.clear()

    bpy.utils.unregister_class(IncrementGrid)
    bpy.utils.unregister_class(DecrementGrid)

if __name__ == "__main__":
    register()