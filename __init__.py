bl_info = {
    "name": "Snappy",
    "blender": (5, 0, 0),
    "category": "View3D"
}

import bpy

class ScaleGrid(bpy.types.Operator):
    bl_idname = "view3d.scale_grid"
    bl_label = "Scale Grid"

    scale: bpy.props.FloatProperty(name="Scale", default=0.5, min=0, max=4)

    def execute(self, context):
        context.space_data.overlay.grid_scale *= self.scale
        self.report({'INFO'}, str(context.space_data.overlay.grid_scale))
        return {'FINISHED'}

def draw_header(self, context):
    layout = self.layout
    layout.alignment = 'CENTER'
    layout.label(text=str(context.space_data.overlay.grid_scale)+"m")


addon_keymaps = []

def register():
    bpy.utils.register_class(ScaleGrid)
    bpy.types.VIEW3D_HT_header.append(draw_header)

    wm = bpy.context.window_manager
    kc = wm.keyconfigs.addon

    if kc:
        km = kc.keymaps.new(name='Object Mode', region_type='WINDOW')
        kmi = km.keymap_items.new(ScaleGrid.bl_idname, 'RIGHT_BRACKET', 'PRESS', shift=False)
        kmi.properties.scale = 2
        addon_keymaps.append((km, kmi))

        kmi = km.keymap_items.new(ScaleGrid.bl_idname, 'LEFT_BRACKET', 'PRESS', shift=False)
        kmi.properties.scale = 0.5
        addon_keymaps.append((km, kmi))

def unregister():
    for km, kmi in addon_keymaps:
        km.keymap_items.remove(kmi)

    addon_keymaps.clear()
    bpy.types.VIEW3D_HT_header.remove(draw_header)
    bpy.utils.unregister_class(ScaleGrid)