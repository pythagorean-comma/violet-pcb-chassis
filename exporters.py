import os
import re

import cadquery as cq

OUTPUT_PATH = "out"
DOC_PATH = "docs"           # committed assets, regenerated only by build.py --docs

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

DOC_OPTS = {                # the README hero image
    "projectionDir": (1, -1, 0.8),
    "width": 1000, "height": 700,
    "marginLeft": 20, "marginTop": 20,
    "showAxes": False,
    "showHidden": False,    # dashed internals read as noise at README size
}

# Stroke colour per theme. Nothing else differs, and the background stays
# transparent in both -- each file is only ever shown against its own backdrop,
# and transparency lets the dark one sit correctly on every GitHub dark variant
# rather than just the default one.
DOC_THEMES = {
    "light": (32, 32, 32),
    "dark": (222, 222, 222),
}

DOC_PAD = 8.0               # breathing room around the drawing, in SVG units

_TRANSFORM_RE = re.compile(
    r"scale\(\s*([-\d.eE+]+)\s*,\s*([-\d.eE+]+)\s*\)\s*"
    r"translate\(\s*([-\d.eE+]+)\s*,\s*([-\d.eE+]+)\s*\)"
)
_D_ATTR_RE = re.compile(r'\bd="([^"]*)"')
_NUMBER_RE = re.compile(r"[-+]?\d*\.?\d+(?:[eE][-+]?\d+)?")
_SVG_OPEN_RE = re.compile(r"<svg\b[^>]*>")

def _tighten_svg(svg, pad=DOC_PAD):
    """Give a CadQuery SVG a viewBox cropped to the drawing.

    CadQuery emits a fixed 800x800 canvas with no viewBox and fills only three
    quarters of it, so as an <img> the result neither scales to the reader's
    column width nor crops to the part. Both are fixed here by measuring where
    the ink actually lands.

    The geometry sits inside one `<g transform="scale(s,-s) translate(tx,ty)">`,
    so a point maps to screen as (s*(x+tx), -s*(y+ty)) -- and the exporter emits
    only M and L commands, every curve already discretised into line segments,
    so reading the path data as plain coordinate pairs is exact rather than a
    guess that would misread arc parameters as points.
    """
    transform = _TRANSFORM_RE.search(svg)
    if not transform:
        raise ValueError("no scale/translate transform found; SVG format changed")
    scale_x, scale_y, offset_x, offset_y = (float(g) for g in transform.groups())

    xs, ys = [], []
    for path in _D_ATTR_RE.findall(svg):
        coords = [float(n) for n in _NUMBER_RE.findall(path)]
        xs.extend(scale_x * (x + offset_x) for x in coords[0::2])
        ys.extend(scale_y * (y + offset_y) for y in coords[1::2])
    if not xs:
        raise ValueError("no path data found; nothing to crop to")

    x0, y0 = min(xs) - pad, min(ys) - pad
    width, height = max(xs) + pad - x0, max(ys) + pad - y0

    opening = (
        '<svg xmlns="http://www.w3.org/2000/svg" '
        'xmlns:svg="http://www.w3.org/2000/svg" '
        f'width="{width:.1f}" height="{height:.1f}" '
        f'viewBox="{x0:.1f} {y0:.1f} {width:.1f} {height:.1f}">'
    )
    return _SVG_OPEN_RE.sub(opening, svg, count=1)

def export_doc_svg(model, name, theme):
    """Write a README-ready SVG for `model`, cropped and coloured for `theme`."""
    os.makedirs(DOC_PATH, exist_ok=True)
    shape = model.val() if hasattr(model, "val") else model
    opts = dict(DOC_OPTS, strokeColor=DOC_THEMES[theme])
    svg_path = f"{DOC_PATH}/{name}-{theme}.svg"
    with open(svg_path, "w") as handle:
        handle.write(_tighten_svg(cq.exporters.svg.getSVG(shape, opts)))
    print("Exported:", svg_path)