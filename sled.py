"""The sled: the U-section carrier the PCB slides into.

Read :data:`PIPELINE` as a setup sheet. Each entry is one operation on the
emerging part, in the order a machinist would run it, and every one of them can
be exported on its own via ``build.py --stage N``.

Conventions, applied without exception:

1. Every transform is ``(part, spec) -> part``.
2. No transform selects on the geometry a previous transform produced. Positions
   come from the spec in absolute coordinates. Selector chains such as
   ``.faces(">Z")`` break silently the moment an upstream step changes topology,
   and that is how a model like this rots.
3. No numeric literals -- everything comes from the spec or its derived values.
4. Material is removed by building the cutter's swept volume and subtracting it.

The whole part is cut from +Z with a plain end mill. There are no undercuts and
no second setup: the upper channel forms the arms, and the narrower lower pocket
sunk into its floor leaves the two ledges the board rides on.
"""

from typing import Callable

import cadquery as cq

from params import ChassisSpec
from tooling import OVERSHOOT, block, break_edges_near, countersunk_hole, rod

Transform = Callable[[cq.Workplane, ChassisSpec], cq.Workplane]


def make_sled_blank(spec: ChassisSpec) -> cq.Workplane:
    """Stock: a rectangular bar at the full wing envelope."""
    return block(
        -spec.sled_w / 2, spec.sled_w / 2,
        0.0, spec.sled_depth,
        spec.z_bot, spec.z_top,
    )


def cut_body_relief(part: cq.Workplane, spec: ChassisSpec) -> cq.Workplane:
    """Profile the body down to ``body_w``, leaving the two wings proud at the front.

    The wings are what is *left behind* here rather than something added later,
    which is how they actually appear when the block is profiled. The corner
    where each wing meets the body is concave, so the cutter's matching corner
    is rounded off at the tool radius -- an end mill cannot leave it sharp.
    """
    cutters = []
    for sign in (-1, 1):
        x_inner = sign * spec.body_w / 2
        x_outer = sign * (spec.sled_w / 2 + OVERSHOOT)
        cutter = block(
            x_inner, x_outer,
            spec.wing_len, spec.sled_depth + OVERSHOOT,
            spec.z_bot - OVERSHOOT, spec.z_top + OVERSHOOT,
        )
        corner = cq.selectors.NearestToPointSelector((x_inner, spec.wing_len, spec.z_mid))
        cutters.append(cutter.edges("|Z").edges(corner).fillet(spec.tool_r))

    for cutter in cutters:
        part = part.cut(cutter)
    return part


def cut_upper_channel(part: cq.Workplane, spec: ChassisSpec) -> cq.Workplane:
    """Rough out the U -- the opening the board and its components live in.

    Open at the top and at the front, closed by the back wall. The two rear
    corners carry the tool radius.
    """
    cutter = block(
        -spec.channel_w / 2, spec.channel_w / 2,
        -OVERSHOOT, spec.channel_depth,
        0.0, spec.z_top + OVERSHOOT,
    )
    cutter = cutter.edges("|Z").edges(">Y").fillet(spec.tool_r)
    return part.cut(cutter)


def cut_lower_pocket(part: cq.Workplane, spec: ChassisSpec) -> cq.Workplane:
    """Sink the narrower pocket that leaves the two ledges the board sits on.

    Its floor gives the clearance for bottom-side components and solder tails;
    its walls stand one ``ledge_w`` inboard of the channel walls.
    """
    cutter = block(
        -spec.pocket_w / 2, spec.pocket_w / 2,
        -OVERSHOOT, spec.channel_depth,
        spec.z_pocket_floor, 0.0,
    )
    cutter = cutter.edges("|Z").edges(">Y").fillet(spec.tool_r)
    return part.cut(cutter)


def cut_corner_reliefs(part: cq.Workplane, spec: ChassisSpec) -> cq.Workplane:
    """Relieve the channel's rear corners so a square board can seat fully.

    A milled corner is round and a PCB corner is square, so without this the
    board fouls the fillet and stops short of the back wall. The relief is
    centred on the nominal corner with the finishing cutter, and runs the height
    of the channel.
    """
    for sign in (-1, 1):
        part = part.cut(
            rod(
                sign * spec.channel_w / 2,
                spec.channel_depth,
                spec.fine_tool_d,
                -OVERSHOOT,
                spec.z_top + OVERSHOOT,
            )
        )
    return part


def cut_cable_relief(part: cq.Workplane, spec: ChassisSpec) -> cq.Workplane:
    """Notch the back wall so the loom can leave the far end of the board.

    Open at the top, so it is another plunge from +Z in the same setup rather
    than a bored hole needing the part turned over.
    """
    cutter = block(
        -spec.cable_slot_w / 2, spec.cable_slot_w / 2,
        spec.channel_depth - OVERSHOOT, spec.sled_depth + OVERSHOOT,
        spec.cable_slot_floor_z, spec.z_top + OVERSHOOT,
    )
    return part.cut(cutter)


def drill_wing_holes(part: cq.Workplane, spec: ChassisSpec) -> cq.Workplane:
    """Countersink the two M2 clearance holes that dock the sled to the plate.

    The recess opens on the wings' rear faces: the screws are driven from behind
    while the module is on the bench, then the assembled module goes in as one.
    """
    for x, z in spec.wing_hole_xz:
        part = part.cut(
            countersunk_hole(
                x=x,
                z=z,
                y_face=spec.wing_len,
                depth=spec.wing_len,
                clear_d=spec.screw_clear_d,
                head_d=spec.csk_d,
                angle=spec.csk_angle,
            )
        )
    return part


def break_edges(part: cq.Workplane, spec: ChassisSpec) -> cq.Workplane:
    """Chamfer the nose, so the sled leads cleanly into the routed aperture."""
    return break_edges_near(
        part,
        spec.edge_break,
        -spec.sled_w, spec.sled_w,
        spec.sled_depth - spec.edge_break / 2, spec.sled_depth + OVERSHOOT,
        spec.z_bot - OVERSHOOT, spec.z_top + OVERSHOOT,
        what=f"sled {spec.name}",
    )


PIPELINE: tuple[Transform, ...] = (
    cut_body_relief,
    cut_upper_channel,
    cut_lower_pocket,
    cut_corner_reliefs,
    cut_cable_relief,
    drill_wing_holes,
    break_edges,
)


def build_sled(spec: ChassisSpec, upto: int | None = None) -> cq.Workplane:
    """Run the pipeline, optionally stopping after ``upto`` transforms."""
    part = make_sled_blank(spec)
    for transform in PIPELINE[:upto]:
        part = transform(part, spec)
    return part
