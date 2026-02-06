bl_info = {
    "name": "Snappy",
    "blender": (5, 0, 0),
    "category": "View3D"
}

from . import dimensions, snap

def register():
    dimensions.enable()
    snap.enable()

def unregister():
    dimensions.disable()
    snap.disable()