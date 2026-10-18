"""Dimensions overlay for meshes and objects"""

import bpy
import bmesh
import mathutils
from bpy_extras.view3d_utils import location_3d_to_region_2d
from . import draw, utility

class DimensionOverlaySettings(bpy.types.PropertyGroup):
    enable_edge_length: bpy.props.BoolProperty(name="Show Edge Length", description="Show the length of selected edges in the 3d viewport.", default=True)
    enable_dimensions: bpy.props.BoolProperty(name="Show Dimensions", description="Show the dimension/bounds length of the selected object.", default=True) 

def get_bounds(obj):
    depsgraph = bpy.context.evaluated_depsgraph_get()
    eval_obj = obj.evaluated_get(depsgraph)

    return [eval_obj.matrix_world @ mathutils.Vector(corner) for corner in eval_obj.bound_box]

def get_edges_axis_aligned(points, axis='Z'):
    idx = {'X': 0, 'Y': 1, 'Z': 2}[axis]
    other = [0, 1, 2]
    other.remove(idx)

    groups = {}
    for p in points:
        key = (round(p[other[0]], 6), round(p[other[1]], 6))
        groups.setdefault(key, []).append(p)

    edges = []
    for g in groups.values():
        g.sort(key=lambda p: p[idx])
        edges.append((g[0], g[1]))

    return edges

def expand_bounds_aabb(points, amount):
    min_v = mathutils.Vector((
        min(p.x for p in points),
        min(p.y for p in points),
        min(p.z for p in points),
    ))
    max_v = mathutils.Vector((
        max(p.x for p in points),
        max(p.y for p in points),
        max(p.z for p in points),
    ))

    min_v -= mathutils.Vector((amount, amount, amount))
    max_v += mathutils.Vector((amount, amount, amount))

    return [
        mathutils.Vector((x, y, z))
        for x in (min_v.x, max_v.x)
        for y in (min_v.y, max_v.y)
        for z in (min_v.z, max_v.z)
    ]

def get_axis(bounds, region, rv3d, growth): 
    cam_pos = rv3d.view_matrix.inverted().translation
    bounds = expand_bounds_aabb(bounds, growth)

    def closest(candidates):
        return min(candidates, key=lambda p: (p - cam_pos).length_squared)

    def midpoint_2d(edge):
        midpoint = mathutils.Vector.lerp(edge[0], edge[1], 0.5)
        return location_3d_to_region_2d(region, rv3d, midpoint)

    def axis_edge(axis, direction):
        outEdge = None
        for edge in get_edges_axis_aligned(bounds, axis):
            # Assign edge to first
            if outEdge is None:
                outEdge = edge
                continue

            half = mathutils.Vector.lerp(edge[0], edge[1], 0.5)
            oldHalf = mathutils.Vector.lerp(outEdge[0], outEdge[1], 0.5)
            
            if direction is not None:
                if direction == 'DOWN':
                    half_2d = location_3d_to_region_2d(region, rv3d, half)
                    oldHalf_2d = location_3d_to_region_2d(region, rv3d, oldHalf)

                    # In screen space, smaller Y is visually lower.
                    if half_2d is not None and oldHalf_2d is not None and half_2d.y > oldHalf_2d.y:
                        continue
                
            if closest([half, oldHalf]) == half:
                outEdge = edge

        return outEdge
    
    def z_most_right_edge():
        outEdge = None
        for edge in get_edges_axis_aligned(bounds, 'Z'):
            if outEdge is None:
                outEdge = edge
                continue

            half_2d = midpoint_2d(edge)
            oldHalf_2d = midpoint_2d(outEdge)

            # If projection failed, skip
            if half_2d is None or oldHalf_2d is None:
                continue

            # Compare X screen coordinates
            if half_2d.x > oldHalf_2d.x:
                outEdge = edge

        return outEdge

    
    return {
        'X': axis_edge('X', 'DOWN'),
        'Y': axis_edge('Y', 'DOWN'),
        'Z': z_most_right_edge()
    }

def label_offset(start, end, cam, distance = 0.3):
    middle = mathutils.Vector.lerp(start, end, 0.5)
    direction = (end - start).normalized()
    to_cam = (cam - middle).normalized()
    offset_dir = direction.cross(to_cam)

    # If vectors are nearly parallel, choose a stable fallback normal.
    if offset_dir.length_squared < 1e-12:
        fallback = mathutils.Vector((0.0, 0.0, 1.0))
        if abs(direction.dot(fallback)) > 0.95:
            fallback = mathutils.Vector((1.0, 0.0, 0.0))
        offset_dir = direction.cross(fallback)

    offset_dir.normalize()
    return middle + offset_dir * distance

TRANSFORM_PREFIXES = (
    "TRANSFORM_OT_",
    "MESH_OT_",
)
 
def is_editing_mesh ():
    for op in bpy.context.window.modal_operators:
        for prefix in TRANSFORM_PREFIXES:
            if op.bl_idname.startswith(prefix):
                return True
            
    return False

def edit_mode_overlay():
    # Edge Length overlay

    if bpy.context.scene.overlay_settings.enable_edge_length == False:
        return;
    
    context = bpy.context
    rv3d = context.region_data
    cam_pos = rv3d.view_matrix.inverted().translation

    obj = context.edit_object
    mesh = obj.data

    mw = obj.matrix_world
    bm = bmesh.from_edit_mesh(mesh)
                
    selected_edges = set()

    ui = bpy.context.preferences.themes[0].view_3d
    text_color = ui.edge_mode_select
    edge_color = ui.edge_mode_select

    select_count = 0

    for v in bm.verts:
        if v.select:
            select_count += 1
            
            for linked_e in v.link_edges:
                if linked_e.select or is_editing_mesh():
                    selected_edges.add(linked_e)

    # Don't draw anything to many things selected
    if select_count >= 8:
        return

    for edge in selected_edges:
        v1, v2 = edge.verts
        start = mathutils.Vector(mw @ v1.co)
        end = mathutils.Vector(mw @ v2.co)

        # Use world-space distance so overlay respects object scale.
        length = (end - start).length
        unit = utility.unit()
        formatted = f"{length:.2f}"
        formatted = formatted.rstrip('0').rstrip('.')

        color = (1, 1, 1, 1)
        font_size = 12
        
        if not edge.select: # surrounding verts
            color = (1, 1, 1, 0.5)
            font_size = 10
        
        draw.text_3d(label_offset(start, end, cam_pos, 0.05), f"{formatted}{unit}", color, font_size)

        draw.lines([start, end], (edge_color[0], edge_color[1], edge_color[2], 0.15))

def object_mode_overlay():
    # Dimension overlay   

    if bpy.context.scene.overlay_settings.enable_dimensions == False:
        return;

    context = bpy.context
    rv3d = context.region_data

    if len(context.selected_objects) == 0:
        return

    obj = context.active_object
    if not obj or obj.type != 'MESH':
        return

    growth_amount = 0.1
    cam_pos = rv3d.view_matrix.inverted().translation
    bounds = get_bounds(obj)
    edges = get_axis(bounds, context.region, rv3d, growth_amount)
    dims = obj.dimensions

    unit = utility.unit()
    ui = bpy.context.preferences.themes[0].user_interface
    theme = {
        'X': ui.axis_x,
        'Y': ui.axis_y,
        'Z': ui.axis_z
    }

    for axis, edge in edges.items():
        formatted = f"{getattr(dims, axis.lower()):.2f}"
        formatted = formatted.rstrip('0').rstrip('.')

        start = mathutils.Vector(edge[0])
        end = mathutils.Vector(edge[1])

        if axis != 'Z':
            start.z += growth_amount
            end.z += growth_amount

        direction = (end - start).normalized()
        start += direction * growth_amount
        end -= direction * growth_amount

        color = theme[axis]
        color = (color[0], color[1], color[2], 1)
        
        text = f"{axis.lower()}: {formatted}{unit}"
        draw.text_3d(label_offset(start, end, cam_pos), text, (1,1,1,1), 12)
        draw.lines([start, end], color)
        
# Registration

_draw_post_pixel = None
def draw_post_pixel():
    """Used for drawing screen space text"""
    pass

_draw_post_view = None
def draw_post_view():
    """Used for drawing meshes"""

    if bpy.context.object == None:
        return

    if bpy.context.space_data.overlay.show_overlays == False:
        return 

    mode = bpy.context.object.mode
    
    if mode == 'OBJECT':
        object_mode_overlay()
    elif mode == 'EDIT':
        edit_mode_overlay()

def draw_overlay_ui(self, context):
    layout: bpy.types.UILayout = self.layout
    layout.label(text="Measurement")
    
    props = context.scene.overlay_settings
    row = layout.row()
    row.prop(props, "enable_dimensions", text="Dimensions")
    row.prop(props, "enable_edge_length", text="Edge Length")

def enable():
    bpy.utils.register_class(DimensionOverlaySettings)
    bpy.types.Scene.overlay_settings = bpy.props.PointerProperty(type=DimensionOverlaySettings)

    view_3d = bpy.types.SpaceView3D
    view_overlay = bpy.types.VIEW3D_PT_overlay

    view_overlay.append(draw_overlay_ui)
    
    global _draw_post_view
    global _draw_post_pixel

    if _draw_post_view is None:
        _draw_post_view = view_3d.draw_handler_add(draw_post_view, (), 'WINDOW', 'POST_VIEW')

    if _draw_post_pixel is None:
        _draw_post_pixel = view_3d.draw_handler_add(draw_post_pixel, (), 'WINDOW', 'POST_PIXEL')


def disable():
    del bpy.types.Scene.overlay_settings
    bpy.utils.unregister_class(DimensionOverlaySettings)

    view_3d = bpy.types.SpaceView3D
    view_overlay = bpy.types.VIEW3D_PT_overlay

    view_overlay.remove(draw_overlay_ui)

    global _draw_post_view
    global _draw_post_pixel

    if _draw_post_view:
        view_3d.draw_handler_remove(_draw_post_view, 'WINDOW')
        _draw_post_view = None

    if _draw_post_pixel:
        view_3d.draw_handler_remove(_draw_post_pixel, 'WINDOW')
        _draw_post_pixel = None