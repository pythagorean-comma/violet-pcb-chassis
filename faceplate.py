"""The faceplate: the plate the sled docks to, closing the aperture from outside.

Same conventions as :mod:`sled` -- one transform per machining operation, all
positions derived from the spec in absolute coordinates, material removed by
subtracting the cutter's swept volume.

The plate is machined from a blank one ``lip_h`` thicker than the finished
plate. Facing the rear back to size leaves two *retention tabs* standing proud,
which reach in over the board's side margins and hold its front edge down on the
ledges. They are a pair of tabs rather than one full-width bar so that the
middle of the board's front edge -- where the connectors are -- stays clear.
"""

from typing import Callable

import cadquery as cq

from params import Aperture, ChassisSpec
from tooling import OVERSHOOT, block, break_edges_near, rod, rounded_slab

Transform = Callable[[cq.Workplane, ChassisSpec], cq.Workplane]


def make_plate_blank(spec: ChassisSpec) -> cq.Workplane:
    """Stock: a plate one ``lip_h`` over-thick, centred on the sled's envelope."""
    return rounded_slab(
        w=spec.plate_w,
        h=spec.plate_h,
        y_front=-spec.plate_t,
        y_back=spec.lip_h,
        z_centre=spec.z_mid,
        corner_r=spec.plate_corner_r,
    )


def _lip_tabs(spec: ChassisSpec) -> list[cq.Workplane]:
    """The two tabs left standing when the rear face is faced back to size."""
    z0, z1 = spec.lip_tab_z
    tabs = []
    for x_a, x_b in spec.lip_tab_x:
        tab = block(x_a, x_b, 0.0, spec.lip_h, z0, z1)
        # The tab is surrounded by material being cut away, so every corner the
        # cutter has to walk around must carry its radius.
        tabs.append(tab.edges("|Y").fillet(spec.fine_tool_r))
    return tabs


def cut_rear_relief(part: cq.Workplane, spec: ChassisSpec) -> cq.Workplane:
    """Face the rear back to ``plate_t``, leaving the two retention tabs.

    The faced surface is what beds against the sled's front face; the tabs drop
    into the channel and locate the sled sideways as well as holding the board.
    """
    waste = block(
        -spec.plate_w, spec.plate_w,
        0.0, spec.lip_h,
        spec.z_mid - spec.plate_h, spec.z_mid + spec.plate_h,
    )
    for tab in _lip_tabs(spec):
        waste = waste.cut(tab)
    return part.cut(waste)


def _aperture_cutter(ap: Aperture, spec: ChassisSpec) -> cq.Workplane:
    """The volume one cut-out removes, straight through the plate."""
    y0 = -spec.plate_t - OVERSHOOT
    y1 = spec.lip_h + OVERSHOOT

    if ap.kind == "round":
        return rod(ap.x, 0.0, ap.w, y0, y1).rotate((0, 0, 0), (1, 0, 0), -90).translate(
            (0, 0, ap.z)
        )

    cutter = block(ap.x - ap.w / 2, ap.x + ap.w / 2, y0, y1, ap.z - ap.h / 2, ap.z + ap.h / 2)
    radius = max(ap.corner_r, spec.fine_tool_r)
    return cutter.edges("|Y").fillet(radius)


def cut_apertures(part: cq.Workplane, spec: ChassisSpec) -> cq.Workplane:
    """Cut the connector and control openings listed in the spec.

    Rect corners are opened out to the finishing tool's radius if the spec asks
    for something tighter than a cutter can produce.
    """
    for ap in spec.apertures:
        part = part.cut(_aperture_cutter(ap, spec))
    return part


def drill_mating_holes(part: cq.Workplane, spec: ChassisSpec) -> cq.Workplane:
    """Spot the M2 tap drills that receive the sled's wing screws.

    Modelled at tap-drill diameter and blind, so the thread never shows on the
    visible face. The ``M2 x 0.4`` callout travels with the manufacturing report
    rather than as modelled thread form in the STEP.
    """
    for x, z in spec.wing_hole_xz:
        hole = rod(0.0, 0.0, spec.tap_drill_d, -spec.thread_depth, OVERSHOOT)
        part = part.cut(
            hole.rotate((0, 0, 0), (1, 0, 0), -90).translate((x, 0, z))
        )
    return part


def drill_body_mounts(part: cq.Workplane, spec: ChassisSpec) -> cq.Workplane:
    """Countersink the holes that fix the plate to the instrument body.

    ``body_mount_holes`` is empty until the fixing method is settled, at which
    point this becomes a data change in the spec rather than a code change here.
    """
    for x, z in spec.body_mount_holes:
        hole = rod(0.0, 0.0, spec.screw_clear_d, -spec.plate_t - OVERSHOOT, OVERSHOOT)
        part = part.cut(
            hole.rotate((0, 0, 0), (1, 0, 0), -90).translate((x, 0, z))
        )
    return part


def break_edges(part: cq.Workplane, spec: ChassisSpec) -> cq.Workplane:
    """Chamfer the visible outside face -- the only edge anyone will run a finger over."""
    return break_edges_near(
        part,
        spec.edge_break,
        -spec.plate_w, spec.plate_w,
        -spec.plate_t - OVERSHOOT, -spec.plate_t + spec.edge_break / 2,
        spec.z_mid - spec.plate_h, spec.z_mid + spec.plate_h,
        what=f"faceplate {spec.name}",
    )


PIPELINE: tuple[Transform, ...] = (
    cut_rear_relief,
    cut_apertures,
    drill_mating_holes,
    drill_body_mounts,
    break_edges,
)


def build_faceplate(spec: ChassisSpec, upto: int | None = None) -> cq.Workplane:
    """Run the pipeline, optionally stopping after ``upto`` transforms."""
    part = make_plate_blank(spec)
    for transform in PIPELINE[:upto]:
        part = transform(part, spec)
    return part
