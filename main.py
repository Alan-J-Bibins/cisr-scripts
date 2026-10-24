import colorsys
import os
import random
from typing import Literal, cast

import bpy
import shutil

from bpy.types import (
    ColorRamp,
    FloatProperty,
    NodeSocketFloat,
    ShaderNodeValToRGB,
)

CONFIG = {
    "terrains": {
        "woodlands": "./scene/woodlands.blend",
        "desert": "./scene/desert.blend",
        # "urban": "./scene/urban.blend",
    },
    "times_of_day": ["day", "night"],
    "camera_elevations": {
        0: {
            "front": -100.0,
            "front_left": -95.0,
            "left": -90.0,
            "back_left": -85.0,
            "back": -79.65,
            "back_right": -74.6,
            "right": -69.5,
            "front_right": -64.5,
        },
        1: {
            "front": -58.8,
            "front_left": -54.2,
            "left": -50.4,
            "back_left": -46.4,
            "back": -41.9,
            "back_right": -37.6,
            "right": -33.5,
            "front_right": -29.5,
        },
        2: {
            "front": -24.5,
            "front_left": -21.0,
            "left": -17.7,
            "back_left": -14.5,
            "back": -10.9,
            "back_right": -7.2,
            "right": -4.2,
            "front_right": -0.9,
        },
    },
}


def load_blender():
    blender_bin = shutil.which("blender")
    if blender_bin:
        print("Found: ", blender_bin)
        bpy.app.binary_path = blender_bin
    else:
        print("Unable to find blender!")


def load_blend_file(filepath: str):
    bpy.ops.wm.open_mainfile(filepath=filepath)
    if bpy.data.filepath:
        print("Loaded: ", bpy.data.filepath)
    else:
        print("Could not load ", filepath)


def change_time_of_day(choice: Literal["day", "night"]):
    world_material_node_tree = bpy.data.worlds["World"].node_tree
    if world_material_node_tree is None:
        return
    world_material_node = world_material_node_tree.nodes["Hue/Saturation/Value"]
    socket = world_material_node.inputs[2]
    if isinstance(socket, NodeSocketFloat):
        socket.default_value = 1.0 if choice == "day" else 0.2


def change_camera_position(offset: float):
    print("[DEBUG] Initiating Camera Position Change")
    camera_obj = bpy.data.objects.get("Camera")
    if camera_obj is None:
        print("[DEBUG] Cam not found")
        return

    if camera_obj.type != "CAMERA":
        print("[DEBUG] Object is not a camera type")
        return

    if "Follow Path" not in camera_obj.constraints:
        print("[DEBUG] Follow Path constraint missing on camera object")
        return

    camera_obj.constraints["Follow Path"].offset = offset
    print("[DEBUG] Set camera pos offset to ", offset)


def toggle_tank_visibility(is_visible: bool):
    collection = bpy.data.collections.get("Tank(Append)")
    if not collection:
        return
    collection.hide_render = not is_visible


def change_camouflage_seed(seed: float):
    tank_material_node_tree = bpy.data.materials["Tank"].node_tree
    if tank_material_node_tree is None:
        return
    seed_node = tank_material_node_tree.nodes["Value"]
    socket = seed_node.outputs[0]
    if isinstance(socket, NodeSocketFloat):
        socket.default_value = seed


def generate_tactical_palette(terrain: str, count: int = 4):
    colors = []

    for i in range(count):
        attempts = 0
        while attempts < 50:
            match terrain:
                case "woodlands":  # Temperate / Woodland Olive Greens
                    h = random.uniform(0.18, 0.32)
                    s = random.uniform(0.40, 0.65)
                    if i == 0:
                        v = random.uniform(0.15, 0.25)
                    elif i == 1:
                        v = random.uniform(0.25, 0.35)
                    elif i == 2:
                        v = random.uniform(0.35, 0.45)
                    else:
                        v = random.uniform(0.45, 0.60)
                case "desert":  # Arid / Desert Sandy Browns
                    h = random.uniform(0.05, 0.14)
                    s = random.uniform(0.20, 0.45)
                    if i == 0:
                        v = random.uniform(0.30, 0.40)
                    elif i == 1:
                        v = random.uniform(0.40, 0.50)
                    elif i == 2:
                        v = random.uniform(0.50, 0.60)
                    else:
                        v = random.uniform(0.60, 0.75)
                case _:  # Carbon / Dark Neutral Accents (urban)
                    h = random.uniform(0.0, 1.0)
                    s = random.uniform(0.0, 0.15)
                    if i == 0:
                        v = random.uniform(0.05, 0.08)
                    elif i == 1:
                        v = random.uniform(0.08, 0.12)
                    elif i == 2:
                        v = random.uniform(0.12, 0.16)
                    else:
                        v = random.uniform(0.16, 0.22)

            candidate_rgb = colorsys.hsv_to_rgb(h, s, v)

            too_close = False
            for existing in colors:
                dist = (
                    sum((c1 - c2) ** 2 for c1, c2 in zip(candidate_rgb, existing[:3]))
                    ** 0.5
                )
                if dist < 0.18:
                    too_close = True
                    break

            if not too_close or attempts == 49:
                colors.append(
                    (candidate_rgb[0], candidate_rgb[1], candidate_rgb[2], 1.0)
                )
                break
            attempts += 1

    return colors


def change_colorscheme(terrain: str):
    tank_material_node_tree = bpy.data.materials["Tank"].node_tree
    if tank_material_node_tree is None:
        return
    color_ramp_node = tank_material_node_tree.nodes["Color Ramp.001"]
    if not isinstance(color_ramp_node, ShaderNodeValToRGB):
        return

    color_ramp = color_ramp_node.color_ramp
    if not isinstance(color_ramp, ColorRamp):
        return

    palette = generate_tactical_palette(terrain, count=len(color_ramp.elements))

    for i, color in enumerate(palette):
        color_ramp.elements[i].color = cast(FloatProperty, color)


if __name__ == "__main__":
    load_blender()

    seed_val = random.random()

    output_dir = os.path.abspath("./outputs")
    os.makedirs(output_dir, exist_ok=True)

    for terrain, blend_path in CONFIG["terrains"].items():
        load_blend_file(blend_path)

        change_camouflage_seed(seed_val)
        change_colorscheme(terrain)

        for time_of_day in CONFIG["times_of_day"]:
            change_time_of_day(time_of_day)

            for elevation, angles in CONFIG["camera_elevations"].items():
                for angle_name, offset_value in angles.items():
                    change_camera_position(offset_value)

                    for tank_state in ["tank", "no-tank"]:
                        prefix = f"{terrain}_{time_of_day}_{tank_state}_elev{elevation}_{angle_name}"
                        
                        # Optimization: Skip rendering no-tank if one already exists for this exact camera/time/terrain combo
                        if tank_state == "no-tank":
                            existing_no_tank = [
                                f for f in os.listdir(output_dir)
                                if f.startswith(prefix) and f.endswith(".png")
                            ]
                            if existing_no_tank:
                                print(f"[INFO] Skipping existing no-tank render: {prefix}")
                                continue

                        toggle_tank_visibility(tank_state == "tank")

                        existing_files = [
                            f for f in os.listdir(output_dir)
                            if f.startswith(prefix) and f.endswith(".png")
                        ]
                        sl_no = len(existing_files) + 1

                        filename = f"{prefix}_sl{sl_no}.png"
                        output_filepath = os.path.join(output_dir, filename)

                        bpy.context.scene.render.filepath = output_filepath
                        bpy.ops.render.render(write_still=True)
                        print(f"Successfully rendered: {output_filepath}")
