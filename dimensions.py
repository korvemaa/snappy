"""Dimensions overlay for meshes and objects"""

import bpy
import blf
import mathutils
from bpy_extras.view3d_utils import location_3d_to_region_2d

_text_draw_handle = None

def get_bounds(obj):
    depsgraph = bpy.context.evaluated_depsgraph_get()
    eval_obj = obj.evaluated_get(depsgraph)

    return [eval_obj.matrix_world @ mathutils.Vector(corner) for corner in eval_obj.bound_box]

def view_camera_position(rv3d):
    return rv3d.view_matrix.inverted().translation

def axis_face_centers_minmax(bounds):
    xs = [v.x for v in bounds]
    ys = [v.y for v in bounds]
    zs = [v.z for v in bounds]

    min_x, max_x = min(xs), max(xs)
    min_y, max_y = min(ys), max(ys)
    min_z, max_z = min(zs), max(zs)

    cx = (min_x + max_x) * 0.5
    cy = (min_y + max_y) * 0.5
    cz = (min_z + max_z) * 0.5

    return {
        'X': (
            mathutils.Vector((min_x, cy, cz)),
            mathutils.Vector((max_x, cy, cz)),
        ),
        'Y': (
            mathutils.Vector((cx, min_y, cz)),
            mathutils.Vector((cx, max_y, cz)),
        ),
        'Z': (
            mathutils.Vector((cx, cy, min_z)),
            mathutils.Vector((cx, cy, max_z)),
        ),
    }

def closest_faces_to_camera(bounds, rv3d):
    cam_pos = view_camera_position(rv3d)
    faces = axis_face_centers_minmax(bounds)

    result = {}
    for axis, (a, b) in faces.items():
        da = (a - cam_pos).length_squared
        db = (b - cam_pos).length_squared
        result[axis] = a if da < db else b

    return result

def draw_text(font_id, screen_pos, text, color, font_size):
    w, h = blf.dimensions(font_id, text)

    blf.size(font_id, font_size)
    blf.color(font_id, color[0], color[1], color[2], 1)
    blf.position(font_id, screen_pos.x - w * 0.5, screen_pos.y - h * 0.5, 0)

    blf.draw(font_id, text)

def draw_object_label():
    context = bpy.context
    region = context.region
    rv3d = context.region_data

    obj = context.active_object
    if not obj:
        return

    bounds = get_bounds(obj)
    faces = closest_faces_to_camera(bounds, rv3d)
    dims = obj.dimensions

    ui = bpy.context.preferences.themes[0].user_interface
    color = {
        'X': ui.axis_x,
        'Y': ui.axis_y,
        'Z': ui.axis_z
    }

    for axis, world_pos in faces.items():
        screen_pos = location_3d_to_region_2d(region, rv3d, world_pos)
        if not screen_pos:
            continue
        
        font_id = 0
        font_size = 12
        text = f"{axis.lower()}: {getattr(dims, axis.lower()):.2f}"
        
        draw_text(font_id, screen_pos, text, color[axis], font_size);

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