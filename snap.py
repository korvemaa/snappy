import bpy

class ScaleGrid(bpy.types.Operator):
    """Scale the grid by an amount"""
    
    bl_idname = "view3d.scale_grid"
    bl_label = "Scale grid"

    scale: bpy.props.FloatProperty(name="Scale", default=0.5, min=0, max=4)

    def execute(self, context):
        context.space_data.overlay.grid_scale *= self.scale
        return {'FINISHED'}

def draw_header(self, context):
    layout: bpy.types.UILayout = self.layout
    layout = layout.box();
    layout.emboss = "PULLDOWN_MENU"

    row = layout.row(align=True)
    row.ui_units_x -= 42;
    
    decrement = row.operator(operator=ScaleGrid.bl_idname, text="", icon='REMOVE')
    decrement.scale = 0.5;
    
    row.scale_x = -1.25
    row.prop(context.space_data.overlay, "grid_scale", text="", expand=False, emboss=False, slider=True)

    row.scale_x = 0
    increment = row.operator(operator=ScaleGrid.bl_idname, text="", icon='ADD')
    increment.scale = 2;

_addon_keymaps = []

def enable():
    bpy.utils.register_class(ScaleGrid)
    bpy.types.VIEW3D_HT_header.append(draw_header)

    wm = bpy.context.window_manager
    kc = wm.keyconfigs.addon

    if kc:
        km = kc.keymaps.new(name='Object Mode', region_type='WINDOW')
        kmi = km.keymap_items.new(ScaleGrid.bl_idname, 'RIGHT_BRACKET', 'PRESS', shift=False)
        kmi.properties.scale = 2
        _addon_keymaps.append((km, kmi))

        kmi = km.keymap_items.new(ScaleGrid.bl_idname, 'LEFT_BRACKET', 'PRESS', shift=False)
        kmi.properties.scale = 0.5
        _addon_keymaps.append((km, kmi))

def disable():
    for km, kmi in _addon_keymaps:
        km.keymap_items.remove(kmi)

    _addon_keymaps.clear()
    bpy.types.VIEW3D_HT_header.remove(draw_header)
    bpy.utils.unregister_class(ScaleGrid)