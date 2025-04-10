# SPDX-License-Identifier: GPL-3.0-or-later

import bpy
import gpu
from gpu_extras.batch import batch_for_shader
from bpy.app.handlers import persistent
from bpy.utils import register_classes_factory
from mathutils import Color

draw_handle = None
msgbus_owner = object()


def shader_gamma_correction(color):
    """
    Gamma-corrects a color from Blender prefs for sRGB shader output.
    """
    fixed_color = []
    for i in range(3):  # R, G, B
        corrected = pow(color[i], 1.0 / 2.2)
        fixed_color.append(corrected)
    fixed_color.append(color[3])  # A stays the same
    return fixed_color


def draw_callback_px():
    """Draws a border around the 3D viewport based on user preferences."""
    preferences = bpy.context.preferences.addons[__package__].preferences
    color = shader_gamma_correction(preferences.border_color)
    thickness = preferences.border_width + 1  # viewport 'eats' 1px away

    region_width = bpy.context.region.width
    region_height = bpy.context.region.height

    shader = gpu.shader.from_builtin('UNIFORM_COLOR')
    gpu.state.blend_set('ALPHA')

    def draw_rect(x1, y1, x2, y2):
        coords = [(x1, y1), (x2, y1), (x2, y2), (x1, y2)]
        batch = batch_for_shader(shader, 'TRI_FAN', {"pos": coords})
        shader.uniform_float("color", color)
        batch.draw(shader)

    # Top border
    draw_rect(
        0,
        region_height - thickness,
        region_width,
        region_height
    )
    # Bottom border
    draw_rect(
        0, 0,
        region_width,
        thickness
    )
    # Left border
    draw_rect(
        0,
        thickness,
        thickness,
        region_height - thickness
    )
    # Right border
    draw_rect(
        region_width - thickness,
        thickness, region_width,
        region_height - thickness
    )

    gpu.state.blend_set('NONE')


def refresh_viewport() -> None:
    """Refresh the viewport"""
    for window in bpy.context.window_manager.windows:
        for area in window.screen.areas:
            if area.type == 'VIEW_3D':
                area.tag_redraw()


def toggle_border():
    """Toggle the border based on the autokey state."""
    global draw_handle

    autokey_enabled = bpy.context.scene.tool_settings.use_keyframe_insert_auto

    if autokey_enabled and draw_handle is None:
        draw_handle = bpy.types.SpaceView3D.draw_handler_add(
            draw_callback_px,
            (),
            'WINDOW',
            'POST_PIXEL'
        )
    elif not autokey_enabled and draw_handle is not None:
        bpy.types.SpaceView3D.draw_handler_remove(
            draw_handle,
            'WINDOW'
        )
        draw_handle = None

    refresh_viewport()


def subscribe_to_autokey():
    """Subscribe to changes in the autokey property."""
    bpy.msgbus.subscribe_rna(
        key=(bpy.types.ToolSettings, "use_keyframe_insert_auto"),
        owner=msgbus_owner,
        args=(),
        notify=toggle_border,
        options={"PERSISTENT", }
    )


def unsubscribe_from_autokey():
    """Unsubscribe from changes in the autokey property."""
    bpy.msgbus.clear_by_owner(msgbus_owner)


@persistent
def persistent_load_handler(dummy):
    """
    Handles subscription on new loads
    https://docs.blender.org/api/current/bpy.app.handlers.html#persistent-handler-example
    """
    subscribe_to_autokey()
    init_toggle_border()


class AutokeyHighlightPreferences(bpy.types.AddonPreferences):
    """Preferences for the Autokey Border Highlight addon."""
    bl_idname = __package__

    border_color: bpy.props.FloatVectorProperty(
        name="Border Color",
        description="Color of the border",
        subtype='COLOR',
        size=4,
        default=(1.0, 0.1, 0.1, 1.0),
        min=0.0, max=1.0,
    )
    border_width: bpy.props.IntProperty(
        name="Border Width",
        description="Width of the border",
        default=5,
        subtype='PIXEL',
        min=1,
        soft_max=10,
    )

    def draw(self, context):
        """Draws addon's preferences GUI"""
        layout = self.layout
        layout.label(text="Customize Border Appearance")
        layout.prop(self, "border_color")
        layout.prop(self, "border_width")


def init_toggle_border():
    """Initialize the toggle_border logic safely."""
    if bpy.context.scene:  # Ensure the scene is available
        toggle_border()
    return None  # Stop the timer after execution


Classes = (
    AutokeyHighlightPreferences,
)

register_classes, unregister_classes = register_classes_factory(Classes)


def register():
    """Register classes, append handlers, subscribe msgbus"""
    register_classes()

    bpy.app.handlers.load_post.append(persistent_load_handler)
    subscribe_to_autokey()


def unregister():
    """Unsubscribe msgbus, cleanup global, unregister classes"""
    global draw_handle

    unsubscribe_from_autokey()

    if draw_handle is not None:
        bpy.types.SpaceView3D.draw_handler_remove(draw_handle, 'WINDOW')
        draw_handle = None

    unregister_classes()


if __package__ == "__main__":
    register()
