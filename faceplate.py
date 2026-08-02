"""The faceplate: a flat sheet cover that closes the aperture from outside.

Same conventions as :mod:`sled` -- one transform per fabrication feature, all
positions derived from the spec in absolute coordinates, material removed by
subtracting the cutter's swept volume.

There is nothing to machine here any more. The plate was a 6 mm billet with
proud retention tabs and tapped holes; it is now 2.0 mm sheet with an outline and
four holes, cut flat in one operation alongside the tray's blank.

Two changes made that possible. The board is screwed to standoffs, so nothing
needs holding down and the tabs had no work left to do. And a single screw per
side now passes through the plate, through the tray's wing flange and into the
instrument, so the plate carries no thread and needs no thickness to carry one.

The plate stands ``sheet_t`` proud of the instrument, since the wings are clamped
underneath it. That is deliberate and needs no rebate at 1 mm.
"""

from typing import Callable

import cadquery as cq

from params import Aperture, ChassisSpec
from tooling import OVERSHOOT, block, rod, rounded_slab

Transform = Callable[[cq.Workplane, ChassisSpec], cq.Workplane]


def make_plate_blank(spec: ChassisSpec) -> cq.Workplane:
    """The outline, cut from sheet. No relief, no tabs, no second thickness."""
    return rounded_slab(
        w=spec.plate_w,
        h=spec.plate_h,
        y_front=-spec.plate_t,
        y_back=0.0,
        z_centre=spec.z_mid,
        corner_r=spec.plate_corner_r,
    )


def _aperture_cutter(ap: Aperture, spec: ChassisSpec) -> cq.Workplane:
    """The volume one cut-out removes, straight through the plate."""
    y0 = -spec.plate_t - OVERSHOOT
    y1 = OVERSHOOT

    if ap.kind == "round":
        return rod(ap.x, 0.0, ap.w, y0, y1).rotate((0, 0, 0), (1, 0, 0), -90).translate(
            (0, 0, ap.z)
        )

    cutter = block(ap.x - ap.w / 2, ap.x + ap.w / 2, y0, y1, ap.z - ap.h / 2, ap.z + ap.h / 2)
    return cutter.edges("|Y").fillet(max(ap.corner_r, spec.sheet_t))


def cut_apertures(part: cq.Workplane, spec: ChassisSpec) -> cq.Workplane:
    """Cut the connector and control openings listed in the spec."""
    for ap in spec.apertures:
        part = part.cut(_aperture_cutter(ap, spec))
    return part


def drill_fixings(part: cq.Workplane, spec: ChassisSpec) -> cq.Workplane:
    """Punch the two M3 holes that fix everything to the instrument.

    Plain clearance holes, not countersunk. A laser cannot sink a head, and
    countersinking would make this a two-operation part for no structural gain,
    so these take pan or button heads that stand proud of the visible face.

    The same holes appear in the tray's wing flanges: one screw goes through
    both parts and into the instrument, which is why there is no separate
    tray-to-plate fastening left to model.
    """
    for x, z in spec.fixing_xz:
        hole = rod(0.0, 0.0, spec.body_screw_clear_d, -spec.plate_t - OVERSHOOT, OVERSHOOT)
        part = part.cut(
            hole.rotate((0, 0, 0), (1, 0, 0), -90).translate((x, 0, z))
        )
    return part


PIPELINE: tuple[Transform, ...] = (
    cut_apertures,
    drill_fixings,
)


def build_faceplate(spec: ChassisSpec, upto: int | None = None) -> cq.Workplane:
    """Run the pipeline, optionally stopping after ``upto`` transforms."""
    part = make_plate_blank(spec)
    for transform in PIPELINE[:upto]:
        part = transform(part, spec)
    return part
