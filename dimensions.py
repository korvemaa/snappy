"""Dimensions overlay for meshes and objects"""

import bpy
import blf
import mathutils
from bpy_extras.view3d_utils import location_3d_to_region_2d

_text_draw_handle = None

def get_bounds_center_world(obj):
    depsgraph = bpy.context.evaluated_depsgraph_get()
    eval_obj = obj.evaluated_get(depsgraph)

    bbox = [eval_obj.matrix_world @ mathutils.Vector(corner)
            for corner in eval_obj.bound_box]

    world_pos = sum(bbox, mathutils.Vector()) / 8
    return world_pos

def draw_object_label():
    context = bpy.context
    region = context.region
    rv3d = context.region_data

    obj = context.active_object
    if not obj:
        return

    world_pos = get_bounds_center_world(obj)
    screen_pos = location_3d_to_region_2d(region, rv3d, world_pos)

    if screen_pos is None:
        return

    font_id = 0
    blf.size(font_id, 12)
    blf.color(font_id, 0.1, 1.0, 0.5, 1.0)

    dims = obj.dimensions
    text = f"{dims.x:.2f} × {dims.y:.2f} × {dims.z:.2f}"

    w, h = blf.dimensions(font_id, text)
    blf.position(font_id, screen_pos.x - w / 2, screen_pos.y - h / 2, 0)
    blf.draw(font_id, text)

def enable():
    global _text_draw_handle
    if _text_draw_handle is None:
        _text_draw_handle = bpy.types.SpaceView3D.draw_handler_add(
            draw_object_label, (), 'WINDOW', 'POST_PIXEL'
        )

def disable():
    global _text_draw_handle
    if _text_draw_handle:
        bpy.types.SpaceView3D.draw_handler_remove(_text_draw_handle, 'WINDOW')
        _text_draw_handle = None