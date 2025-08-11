# SPDX-License-Identifier: GPL-3.0-or-later

from typing import Sequence
import bpy
import gpu
from gpu_extras.batch import batch_for_shader
from bpy.utils import register_classes_factory

draw_handle = None


def shader_gamma_correction(color: Sequence[float]) -> list[float]:
    """
    Gamma-corrects a color from Blender prefs for sRGB shader output.
    """
    fixed_color = []
    for i in range(3):  # R, G, B
        corrected = pow(color[i], 1.0 / 2.2)
        fixed_color.append(corrected)
    fixed_color.append(color[3])  # A stays the same
    return fixed_color


def _in_local_view() -> bool:
    """
    Returns True if the current SpaceView3D is in Local View.
    In recent Blender builds, SpaceView3D.local_view is None when not in Local View.
    """
    sd = bpy.context.space_data
    # draw handler runs only for SpaceView3D, so sd should be SpaceView3D
    return getattr(sd, "local_view", None) is not None


def draw_callback_px() -> None:
    """Draws a border around the 3D viewport when in Local View."""
    # Only draw while in Local View
    if not _in_local_view():
        return

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


class LocalviewHighlightPreferences(bpy.types.AddonPreferences):
    """Preferences for the Local View Border Highlight addon."""
    bl_idname = __package__

    border_color: bpy.props.FloatVectorProperty(
        name="Border Color",
        description="Color of the border when in Local View",
        subtype='COLOR',
        size=4,
        default=(1.0, 0.05, 0.05, 0.5),
        min=0.0, max=1.0,
    )
    border_width: bpy.props.IntProperty(
        name="Border Width",
        description="Width of the border (pixels)",
        default=5,
        subtype='PIXEL',
        min=1,
        soft_max=10,
    )

    def draw(self, context):
        """Draws addon's preferences GUI"""
        layout = self.layout
        layout.label(text="Customize Border Appearance (Local View)")
        layout.prop(self, "border_color")
        layout.prop(self, "border_width")


Classes = (
    LocalviewHighlightPreferences,
)

register_classes, unregister_classes = register_classes_factory(Classes)


def register() -> None:
    """Register classes and add draw handler."""
    global draw_handle

    register_classes()

    if bpy.app.background:
        return  # don't register in background mode

    if draw_handle is None:
        draw_handle = bpy.types.SpaceView3D.draw_handler_add(
            draw_callback_px,
            (),
            'WINDOW',
            'POST_PIXEL'
        )


def unregister() -> None:
    """Remove draw handler and unregister classes."""
    global draw_handle

    if draw_handle is not None:
        bpy.types.SpaceView3D.draw_handler_remove(draw_handle, 'WINDOW')
        draw_handle = None

    unregister_classes()


if __package__ == "__main__":
    register()
