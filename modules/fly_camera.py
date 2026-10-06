import bpy
import math
import time
from mathutils import Vector, Quaternion

speed_state = {"speed": 10}
class VIEW3D_OT_hold_fly(bpy.types.Operator):
    bl_idname = "view3d.hold_fly"
    bl_label = "Hold Fly Navigation"
    bl_options = {'BLOCKING', 'GRAB_CURSOR'}

    _BASE_SPEED = 10
    _MOUSE_SENSITIVITY = 0.002
    _SPEED_SCALE = 1.2
    _BOOST_MULTIPLIER  = 3.0
    _MAX_PITCH = math.radians(89)
    _SMOOTHING = 20.0  
    _EXIT_KEY = ["ESC", "LEFTMOUSE"]        

    # Pixels the mouse must travel before a click is treated as fly, not a context-menu click.
    _DRAG_THRESHOLD = 3

    def _boost_active(self):
        return 'LEFT_SHIFT' in self._keys or 'RIGHT_SHIFT' in self._keys

    def _update_header(self):
        if self._area is None:
            return

        self._area.header_text_set(
            f"Fly Speed: {speed_state['speed']:.2f}"
        )

    def _call_context_menu(self, context):
        mode_to_menu = {
            'OBJECT': 'VIEW3D_MT_object_context_menu',
            'EDIT_MESH': 'VIEW3D_MT_edit_mesh_context_menu',
        }

        menu_name = mode_to_menu.get(context.mode, 'VIEW3D_MT_object_context_menu')

        # Fall back safely if a mode-specific menu is missing in a given Blender version.
        if not hasattr(bpy.types, menu_name):
            menu_name = 'VIEW3D_MT_object_context_menu'

        bpy.ops.wm.call_menu(name=menu_name)

    def modal(self, context, event):
        rv3d = context.region_data

        # Exit when we release right mouse button
        if event.type == 'RIGHTMOUSE' and event.value == 'RELEASE':
            self.finish(context)
            if self._total_drag < self._DRAG_THRESHOLD:
                self._call_context_menu(context)
            return {'FINISHED'}

        # Exit if we forcefully exit
        if event.type in self._EXIT_KEY and event.value == 'PRESS':
            self.finish(context)
            return {'FINISHED'}
            
        # Keep track of input
        if event.value == 'PRESS':
            self._keys.add(event.type)
        elif event.value == 'RELEASE':
            self._keys.discard(event.type)

        if event.type == 'WHEELUPMOUSE':
            speed_state['speed'] *= self._SPEED_SCALE
        elif event.type == 'WHEELDOWNMOUSE':
            speed_state['speed'] /= self._SPEED_SCALE

        # Store mouse look to be used in TIMER event
        if event.type == 'MOUSEMOVE':
            if self._mouse_prev is not None:
                dx = event.mouse_region_x - self._mouse_prev[0]
                dy = event.mouse_region_y - self._mouse_prev[1]
                self._mouse_delta[0] += dx
                self._mouse_delta[1] += dy
                self._total_drag += abs(dx) + abs(dy)

            self._mouse_prev = (event.mouse_region_x, event.mouse_region_y)

        # Apply frame
        if event.type == 'TIMER':
            now = time.perf_counter()
            dt = now - self._last_time
            self._last_time = now

            if self._mouse_delta[0] or self._mouse_delta[1]:
                self.rotate_view(rv3d, self._mouse_delta[0], self._mouse_delta[1])
                self._mouse_delta = [0, 0]
            self.move_view(rv3d, dt)

        if self._total_drag >= self._DRAG_THRESHOLD:
            self._update_header()

        self._area.tag_redraw()
        return {'RUNNING_MODAL'}

    def rotate_view(self, rv3d: bpy.types.RegionView3D, dx, dy):
        # Compute the camera eye position before rotation — we rotate around
        # the eye, not the pivot, so view_distance never needs to change.
        eye = rv3d.view_location + rv3d.view_rotation @ Vector((0, 0, rv3d.view_distance))

        rot = rv3d.view_rotation.copy()

        # Yaw around world Z
        yaw = Quaternion(Vector((0, 0, 1)), -dx * self._MOUSE_SENSITIVITY)
        rot = yaw @ rot

        # Pitch around the camera's current local right axis.
        # Must use rot @ (1,0,0) — not world X — so pitch stays correct after yaw.
        # Clamp to prevent flipping over.
        forward = rot @ Vector((0, 0, -1))
        current_pitch = math.asin(max(-1.0, min(1.0, forward.z)))
        pitch_delta = max(
            -self._MAX_PITCH - current_pitch,
            min(self._MAX_PITCH - current_pitch, dy * self._MOUSE_SENSITIVITY),
        )
        if abs(pitch_delta) > 1e-7:
            right = rot @ Vector((1, 0, 0))
            pitch = Quaternion(right, pitch_delta)
            rot = pitch @ rot

        rv3d.view_rotation = rot
        # Reposition the pivot so the eye stays in place.
        rv3d.view_location = eye - rot @ Vector((0, 0, rv3d.view_distance))

    def move_view(self, rv3d: bpy.types.RegionView3D, dt: float):
        forward = rv3d.view_rotation @ Vector((0, 0, -1))
        right   = rv3d.view_rotation @ Vector((1, 0, 0))
        up      = Vector((0, 0, 1))

        target = Vector((0, 0, 0))

        if 'W' in self._keys:
            target += forward
        if 'S' in self._keys:
            target -= forward
        if 'A' in self._keys:
            target -= right
        if 'D' in self._keys:
            target += right
        if 'E' in self._keys:
            target += up
        if 'Q' in self._keys:
            target -= up

        if target.length > 0:
            target.normalize()
            if self._boost_active():
                target *= self._BOOST_MULTIPLIER
            target *= speed_state['speed']

        # Exponential smoothing: velocity eases toward the target each tick.
        t = min(1.0, self._SMOOTHING * dt)
        self._velocity = self._velocity.lerp(target, t)

        if self._velocity.length > 1e-6:
            rv3d.view_location += self._velocity * dt

    def invoke(self, context, event):
        if context.area is None or context.area.type != 'VIEW_3D':
            return {'PASS_THROUGH'}

        if context.region_data is None:
            return {'CANCELLED'}

        self._keys = set()
        self._timer = None
        self._mouse_prev = (event.mouse_region_x, event.mouse_region_y)
        self._mouse_delta = [0, 0]
        self._total_drag = 0
        self._velocity = Vector((0, 0, 0))
        self._last_time = time.perf_counter()
        self._area = context.area 

        context.window.cursor_modal_set('NONE')

        wm = context.window_manager
        self._timer = wm.event_timer_add(0, window=context.window)
        wm.modal_handler_add(self)

        return {'RUNNING_MODAL'}

    def finish(self, context):
        wm = context.window_manager

        if self._timer:
            wm.event_timer_remove(self._timer)
            self._timer = None

        if self._area is not None:
            self._area.header_text_set(None)

        context.window.cursor_modal_restore()

addon_keymaps = []

def enable():
    bpy.utils.register_class(VIEW3D_OT_hold_fly)

    wm = bpy.context.window_manager
    kc = wm.keyconfigs.addon

    if kc:
        km = kc.keymaps.new(name="Object Mode", space_type='EMPTY')
        addon_keymaps.append((km, km.keymap_items.new(
            VIEW3D_OT_hold_fly.bl_idname,
            type='RIGHTMOUSE',
            value='PRESS'
        )))

        km = kc.keymaps.new(name="Mesh", space_type='EMPTY')
        addon_keymaps.append((km, km.keymap_items.new(
            VIEW3D_OT_hold_fly.bl_idname,
            type='RIGHTMOUSE',
            value='PRESS'
        )))

def disable():
    for km, kmi in addon_keymaps:
        km.keymap_items.remove(kmi)
    addon_keymaps.clear()

    bpy.utils.unregister_class(VIEW3D_OT_hold_fly)