"""The sled: a tray folded from sheet, carrying the PCB on adhesive standoffs.

Read :data:`PIPELINE` as a fabrication sequence. Each entry is one identifiable
feature of the folded part, in the order it comes into being, and any of them can
be exported alone via ``build.py --stage N``.

Conventions, unchanged from when this was a machined part:

1. Every transform is ``(part, spec) -> part``.
2. No transform selects on geometry a previous transform produced. Positions come
   from the spec in absolute coordinates.
3. No numeric literals; everything comes from the spec or its derived values.

How the folds are modelled
--------------------------
The tray body is built as an outer envelope minus an inner cavity, both with
filleted corners. That is not a shortcut: because the inner fillet is ``bend_r``
and the outer is ``bend_r + sheet_t``, the two arcs come out concentric on their
own, so every bend has the right radius and the wall is exactly one sheet
thickness everywhere. The wing folds are made the same way, by filleting the
inside and outside corners of the junction after the flange is added.

One deliberate idealisation: where the side walls meet the back wall this model
runs the material continuously round the corner, whereas the real part has a
bend relief slot there. The relief is in the flat pattern, which is what gets
cut. Treat the STEP as the folded form and :mod:`flatten` as the manufacturing
truth.
"""

from typing import Callable

import cadquery as cq

from params import ChassisSpec
from tooling import OVERSHOOT, block, rod

Transform = Callable[[cq.Workplane, ChassisSpec], cq.Workplane]


def make_tray_shell(spec: ChassisSpec) -> cq.Workplane:
    """Floor, two side walls and the back wall, in one folded shell.

    Open at the top, where the board goes in, and open at the front, where the
    faceplate closes it.
    """
    outer = block(
        -spec.body_w / 2, spec.body_w / 2,
        spec.sheet_t, spec.sled_depth,
        spec.z_bot, spec.z_top,
    ).edges("(not >Z) and (not <Y)").fillet(spec.bend_r + spec.sheet_t)

    cavity = block(
        -spec.channel_w / 2, spec.channel_w / 2,
        spec.sheet_t - OVERSHOOT, spec.channel_depth,
        spec.z_floor_inner, spec.z_top + OVERSHOOT,
    ).edges("(not >Z) and (not <Y)").fillet(spec.bend_r)

    return outer.cut(cavity)


def add_wing_flanges(part: cq.Workplane, spec: ChassisSpec) -> cq.Workplane:
    """Fold a flange outward at the front of each side wall.

    These bed against the faceplate and carry the screws that hold the two parts
    together. Folding them outward rather than inward keeps the tray's opening
    clear, at the cost of the aperture being that much wider.

    Each flange reaches back to the wall's inner face rather than starting at its
    outer one, so the two share a whole face and fuse into a single solid. Butted
    at the outer face they would touch along a line only, and the fold would come
    apart.

    It spans the wall's flat height only, starting clear of the floor's bend. A
    flange carried down into that curve would have nothing straight to fold from,
    and the outer bend radius would have no room to run out at the bottom, which
    is why the real part is relieved there too.
    """
    for sign in (-1, 1):
        flange = block(
            sign * spec.channel_w / 2, sign * (spec.body_w / 2 + spec.wing_w),
            0.0, spec.sheet_t,
            spec.wing_z0, spec.z_top,
        )
        part = part.union(flange)
    return part


def form_wing_bends(part: cq.Workplane, spec: ChassisSpec) -> cq.Workplane:
    """Round the wing folds to the bend radius, inside and out.

    The flange arrives butted square to the wall; sheet cannot turn a sharp
    corner. Filleting the inside at ``bend_r`` and the outside at
    ``bend_r + sheet_t`` puts the two arcs concentric, which is what a brake
    actually leaves.
    """
    for sign in (-1, 1):
        inside = cq.selectors.NearestToPointSelector(
            (sign * spec.body_w / 2, spec.sheet_t, spec.z_mid)
        )
        part = part.edges("|Z").edges(inside).fillet(spec.bend_r)

        outside = cq.selectors.NearestToPointSelector(
            (sign * spec.channel_w / 2, 0.0, spec.z_mid)
        )
        part = part.edges("|Z").edges(outside).fillet(spec.bend_r + spec.sheet_t)
    return part


def cut_cable_relief(part: cq.Workplane, spec: ChassisSpec) -> cq.Workplane:
    """Notch the back wall so the loom can leave the far end of the board.

    Open at the top, so it is part of the flat blank's outline rather than a
    closed hole, and costs nothing extra to cut.
    """
    cutter = block(
        -spec.cable_slot_w / 2, spec.cable_slot_w / 2,
        spec.channel_depth - OVERSHOOT, spec.sled_depth + OVERSHOOT,
        spec.cable_slot_floor_z, spec.z_top + OVERSHOOT,
    )
    return part.cut(cutter)


def drill_wing_holes(part: cq.Workplane, spec: ChassisSpec) -> cq.Workplane:
    """Punch the two M3 clearance holes the fixing screws pass through.

    The tray is not screwed to the faceplate. One screw per side goes through
    the plate, through this flange, and into a threaded insert in the
    instrument, clamping the wing between the two. So this is a plain clearance
    hole and the flange is sized to hold it clear of the fold rather than to
    suit a screw head.
    """
    for x, z in spec.fixing_xz:
        hole = rod(0.0, 0.0, spec.body_screw_clear_d, -OVERSHOOT, spec.sheet_t + OVERSHOOT)
        part = part.cut(
            hole.rotate((0, 0, 0), (1, 0, 0), -90).translate((x, 0, z))
        )
    return part


PIPELINE: tuple[Transform, ...] = (
    add_wing_flanges,
    form_wing_bends,
    cut_cable_relief,
    drill_wing_holes,
)


def build_sled(spec: ChassisSpec, upto: int | None = None) -> cq.Workplane:
    """Run the pipeline, optionally stopping after ``upto`` transforms."""
    part = make_tray_shell(spec)
    for transform in PIPELINE[:upto]:
        part = transform(part, spec)
    return part
