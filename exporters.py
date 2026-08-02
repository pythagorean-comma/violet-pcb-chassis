import os

import cadquery as cq

OUTPUT_PATH = "out"

PREVIEW_OPTS = {            # the fast visual check
    "projectionDir": (1, -1, 0.8),
    "width": 800, "height": 800,
    # CadQuery's own defaults here are marginLeft=200, marginTop=20, which
    # pushes a part this size off the left of the frame.
    "marginLeft": 60, "marginTop": 60,
    "showAxes": False,
    "showHidden": True,     # the pockets are the whole point; keep them visible
    "strokeColor": (0, 0, 0),
    "hiddenColor": (170, 170, 170),
}

def export_step_file(model, name):
    os.makedirs(OUTPUT_PATH, exist_ok=True)
    step_path = f"{OUTPUT_PATH}/{name}.step"
    cq.exporters.export(model, step_path)
    print("Exported:", step_path)

SECTION_OPTS = {            # looking down the insertion axis, at a slice
    "projectionDir": (0, -1, 0),
    "width": 800, "height": 400,
    "marginLeft": 40, "marginTop": 40,
    "showAxes": False,
    "showHidden": False,    # a section is already cut open; hidden lines add noise
    "strokeColor": (0, 0, 0),
}

def export_svg_preview(model, name):
    """Write the shaded-line preview render for `model`."""
    os.makedirs(OUTPUT_PATH, exist_ok=True)
    svg_path = f"{OUTPUT_PATH}/{name}.svg"
    cq.exporters.export(model, svg_path, opt=PREVIEW_OPTS)
    print("Exported:", svg_path)

def export_assembly_step(assembly, name):
    """Write a multi-part STEP for `assembly`.

    mode="default" keeps the parts as separate, named, coloured components, which
    is what anyone opening the file expects to find. mode="fused" would boolean
    them into a single solid and throw away which metal belonged to which part.

    Assembly.export, not Assembly.save -- save is deprecated in CadQuery 2.8 and
    warns that it goes away in the next release.
    """
    os.makedirs(OUTPUT_PATH, exist_ok=True)
    step_path = f"{OUTPUT_PATH}/{name}.step"
    assembly.export(step_path, "STEP", mode="default", unit="MM")
    print("Exported:", step_path)

def export_section_preview(model, name):
    """Write a preview looking down -Y, for a slice through the channel.

    This is the view that shows whether the ledge profile is right, which the
    isometric preview cannot. The model is rolled 90 degrees first because
    CadQuery picks its own up-vector for a projection along Y, and would
    otherwise lay the section on its side.
    """
    os.makedirs(OUTPUT_PATH, exist_ok=True)
    svg_path = f"{OUTPUT_PATH}/{name}.svg"
    upright = model.rotate((0, 0, 0), (0, 1, 0), 90)
    cq.exporters.export(upright, svg_path, opt=SECTION_OPTS)
    print("Exported:", svg_path)