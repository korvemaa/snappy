"""Draw is a debug library, not intended for use in production"""

import bpy
from bpy_extras.view3d_utils import location_3d_to_region_2d
import gpu
import blf
from gpu_extras.batch import batch_for_shader

def pixel_instruction(draw):
    global _inside_pixel_scope
    
    if _inside_pixel_scope:
        draw()
        return
    
    _post_pixel_instructions.append(draw)

def view_instruction(draw):
    global _inside_view_scope
    
    if _inside_view_scope:
        draw()
        return

    _post_view_instructions.append(draw)

def rect_2d(x, y, w, h, color = (0.1, 0.1, 0.1, 0.5)):
    def draw():
        shader = gpu.shader.from_builtin('UNIFORM_COLOR')
        verts = [(x,y), (x+w,y), (x+w,y+h), (x,y+h)]
        batch = batch_for_shader(shader, 'TRI_FAN', {"pos": verts})

        gpu.state.blend_set('ALPHA')
        shader.bind()
        shader.uniform_float("color", color)
        batch.draw(shader)
        gpu.state.blend_set('NONE')
    pixel_instruction(draw)

def points(points: list[(float, float, float)], color = (1, 0, 0, 1), size= 4.5):
    def draw():
        shader = gpu.shader.from_builtin('POINT_UNIFORM_COLOR')
        batch = batch_for_shader(shader, 'POINTS', {"pos": points})

        shader.bind()
        shader.uniform_float("color", color)

        gpu.state.point_size_set(size)

        batch.draw(shader)
    view_instruction(draw)

def lines(points: list[(float, float, float)], color = (1, 1, 0, 1), width = 1):
    def draw():
        shader = gpu.shader.from_builtin('POLYLINE_UNIFORM_COLOR')
        batch = batch_for_shader(shader, 'LINES', {"pos": points})

        gpu.state.blend_set('ALPHA')

        shader.bind()
        shader.uniform_float("viewportSize", gpu.state.viewport_get()[2:])
        shader.uniform_float("lineWidth", width)
        shader.uniform_float("color", color)
        shader.uniform_bool("lineSmooth", True)

        batch.draw(shader)

        gpu.state.blend_set('NONE')
    view_instruction(draw)

def box(min, max, color = (1, 1, 0, 1), width = 1):
    def draw():
        min_x, min_y, min_z = min
        max_x, max_y, max_z = max

        coords = (
            (min_x, min_y, min_z), (max_x, min_y, min_z),
            (min_x, max_y, min_z), (max_x, max_y, min_z),
            (min_x, min_y, max_z), (max_x, min_y, max_z),
            (min_x, max_y, max_z), (max_x, max_y, max_z),
        )

        indices = (
            (0, 1), (0, 2), (1, 3), (2, 3),
            (4, 5), (4, 6), (5, 7), (6, 7),
            (0, 4), (1, 5), (2, 6), (3, 7)) 

        shader = gpu.shader.from_builtin('POLYLINE_UNIFORM_COLOR')
        batch = batch_for_shader(shader, 'LINES', {"pos": coords}, indices=indices)
        shader.uniform_float("viewportSize", gpu.state.viewport_get()[2:])
        shader.uniform_float("lineWidth",width)
        shader.uniform_float("color", color)
        batch.draw(shader)
    view_instruction(draw)

def text_2d(point, text:str, color = (1,1,1,1), size = 14):
    def draw():
        pass
    pixel_instruction(draw)
    

def text_3d(point, text: str, color = (1, 1, 1, 1), size = 14, padding = 4, background_color = (0.1, 0.1, 0.1, 0.4)):
    def draw():
        context = bpy.context
        region = context.region
        rv3d = context.region_data

        screen_pos = location_3d_to_region_2d(region, rv3d, point)
        if not screen_pos:
            return
        
        font_id = 0
        blf.size(font_id, size)
        w, h = blf.dimensions(font_id, text)

        text_x = screen_pos.x - w * 0.5
        text_y = screen_pos.y - h * 0.5

        if background_color is not None:
            rect_2d(
                text_x - padding,
                text_y - padding,
                w + padding * 2,
                h + padding * 2,
                background_color,
            )

        blf.color(font_id, color[0], color[1], color[2], color[3])
        blf.position(font_id, text_x, text_y, 0)
        
        blf.enable(0, blf.SHADOW)
        blf.shadow(0, 6, 0, 0, 0, 0.6)

        blf.draw(font_id, text)

        blf.disable(0, blf.SHADOW)
    pixel_instruction(draw)

_post_pixel_instructions = list()
_inside_pixel_scope = False
_draw_post_pixel = None

def draw_post_pixel():
    """Used for drawing screen space text"""
    global _post_pixel_instructions
    global _inside_pixel_scope
    
    _inside_pixel_scope = True
    while len(_post_pixel_instructions) > 0:
        _post_pixel_instructions.pop()()
    _inside_pixel_scope = False

_post_view_instructions = list()
_inside_view_scope = False
_draw_post_view = None
def draw_post_view():
    """Used for drawing meshes"""
    global _post_view_instructions
    global _inside_view_scope
    
    _inside_view_scope = True
    while len(_post_view_instructions) > 0:
        _post_view_instructions.pop()()
    _inside_view_scope = False

def enable():
    view_3d = bpy.types.SpaceView3D

    global _post_view_instructions
    global _post_pixel_instructions

    _post_view_instructions = list()
    _post_pixel_instructions = list()
    
    global _draw_post_view
    if _draw_post_view is None:
        _draw_post_view = view_3d.draw_handler_add(draw_post_view, (), 'WINDOW', 'POST_VIEW')

    global _draw_post_pixel
    if _draw_post_pixel is None:
        _draw_post_pixel = view_3d.draw_handler_add(draw_post_pixel, (), 'WINDOW', 'POST_PIXEL')


def disable():
    global _post_view_instructions
    global _post_pixel_instructions

    del _post_view_instructions
    del _post_pixel_instructions

    global _draw_post_view
    global _draw_post_pixel

    if _draw_post_view:
        bpy.types.SpaceView3D.draw_handler_remove(_draw_post_view, 'WINDOW')
        _draw_post_view = None

    if _draw_post_pixel:
        bpy.types.SpaceView3D.draw_handler_remove(_draw_post_pixel, 'WINDOW')
        _draw_post_pixel = None