"""The tray's developed blank: what actually gets cut before anything is folded.

For a folded part the flat pattern is the manufacturing file, not the 3D model,
so this is computed from the same :class:`ChassisSpec` the folded solid is built
from. Neither is derived from the other, which is the point: if the two ever
disagree, the volume check in :func:`mock.check_clearance` catches it rather than
a fabricator discovering it on the brake.

Bend allowance
--------------
Sheet does not shorten by the full corner when it folds. The outside stretches,
the inside compresses, and some fibre in between keeps its length. That fibre
sits ``k_factor`` of the way through the thickness, so a 90 degree bend consumes

    (pi / 2) * (bend_r + k_factor * sheet_t)

of blank rather than the ``bend_r + sheet_t`` the corner appears to take. Getting
this wrong does not produce an obviously broken part: it produces a part that is
quietly the wrong size, which is why the report prints the K-factor rather than
burying it.

The blank is laid out with the floor in the middle: side walls unfold left and
right, the back wall unfolds beyond the floor's far edge, and each wing unfolds
forward of its side wall.
"""

from dataclasses import dataclass

from params import ChassisSpec


@dataclass(frozen=True)
class Bend:
    """One bend line on the flat blank.

    ``start`` and ``end`` bound the line along its own length, so each is drawn
    only across the metal it actually folds. Without them the two wing bends,
    which share a y, would be drawn as identical full-width lines crossing the
    gap between the wings where there is no material at all.
    """

    name: str
    direction: str  # "up" or "out", as seen with the floor lying flat
    axis: str  # "x": a line of constant x; "y": a line of constant y
    position: float
    start: float
    end: float

    @property
    def ends(self) -> tuple[tuple[float, float], tuple[float, float]]:
        """The line's two endpoints, in blank coordinates."""
        if self.axis == "x":
            return ((self.position, self.start), (self.position, self.end))
        return ((self.start, self.position), (self.end, self.position))

    @property
    def midpoint(self) -> tuple[float, float]:
        (x0, y0), (x1, y1) = self.ends
        return ((x0 + x1) / 2, (y0 + y1) / 2)


@dataclass(frozen=True)
class FlatPattern:
    """A developed blank: its outline, holes, bend lines and extents.

    Everything cut while the sheet is flat has to be here. A blank missing its
    holes is not a slightly wrong drawing, it is a scrap part.
    """

    outline: tuple[tuple[float, float], ...]
    holes: tuple[tuple[float, float, float], ...]  # (x, y, diameter)
    bends: tuple[Bend, ...]
    width: float
    height: float
    shortest_flange: float

    @property
    def area(self) -> float:
        """Enclosed area by the shoelace formula, for checking against the solid."""
        pts = self.outline
        total = sum(
            pts[i][0] * pts[i - 1][1] - pts[i - 1][0] * pts[i][1]
            for i in range(len(pts))
        )
        return abs(total) / 2


def _flange_lengths(spec: ChassisSpec) -> dict[str, float]:
    """Flat length of each flange: its outside dimension less one setback.

    The side and back walls stand the full height of the tray, so their outside
    dimension is ``sled_h`` measured from the floor's underside. The wings are
    measured from the wall's inner face out to the flange tip.
    """
    return {
        "side_wall": spec.sled_h - spec.setback,
        "back_wall": spec.sled_h - spec.setback,
        "wing": spec.wing_w - spec.bend_r,
    }


def flat_pattern(spec: ChassisSpec) -> FlatPattern:
    """Develop the tray into a flat blank.

    Laid out floor-centred, with the blank's x across the tray and y along its
    depth. The side walls unfold left and right of the floor; the back wall
    unfolds past the floor's far edge; and each wing unfolds *forward* of its
    side wall, because it folds from that wall's front edge rather than its outer
    one. Unfolding the wings sideways instead is the obvious mistake, and it
    silently produces a blank several percent too large.

    Nothing is drawn where a side wall meets the back wall. That absence is the
    bend relief: two perpendicular flanges off the same floor cannot share
    material, and trying to keep it is what tears a corner.
    """
    flange = _flange_lengths(spec)
    ba = spec.bend_allowance

    # Across: wall flat | bend | floor flat | bend | wall flat
    fx = spec.channel_w / 2 - spec.bend_r  # floor's flat half-width
    bx = fx + ba  # where each wall's flat begins
    wx = bx + flange["side_wall"]  # wall tip
    gx = bx + spec.sheet_t  # inboard limit of the wing, from wing_z0

    # Along: wing flat | bend | floor flat | bend | back wall flat
    fy1 = spec.channel_depth - spec.bend_r - spec.sheet_t  # floor's flat depth
    by = fy1 + ba
    ky = by + flange["back_wall"]
    wy = -(ba + flange["wing"])

    back_half = fx - spec.bend_relief_w

    # The cable notch is cut into the back wall's far edge while the sheet is
    # flat, so it belongs in the outline rather than being a separate feature.
    # Its depth off that edge is the notch's height in the folded part.
    notch_half = spec.cable_slot_w / 2
    notch_y = ky - (spec.z_top - spec.cable_slot_floor_z)

    # Written out vertex by vertex rather than generated: a flat pattern that is
    # subtly wrong is expensive, and this way every corner is checkable by eye.
    pts = [
        (-wx, fy1),
        (-wx, wy),
        (-gx, wy),
        (-gx, 0.0),
        (gx, 0.0),
        (gx, wy),
        (wx, wy),
        (wx, fy1),
        (back_half, fy1),
        (back_half, ky),
        (notch_half, ky),
        (notch_half, notch_y),
        (-notch_half, notch_y),
        (-notch_half, ky),
        (-back_half, ky),
        (-back_half, fy1),
    ]

    # The M2 holes, unfolded onto the wing flanges. Their distance along the
    # flange is measured from the bend, exactly as the folded part measures it
    # from the wall face, so the two cannot disagree.
    hole_y = -(ba / 2) - (spec.wing_hole_offset - spec.bend_r)
    hole_x = bx + spec.sheet_t + (spec.z_mid - (spec.z_floor_inner + spec.bend_r))
    holes = tuple(
        (sign * hole_x, hole_y, spec.screw_clear_d) for sign in (-1, 1)
    )

    bends = (
        Bend("wall L", "up", "x", -(fx + ba / 2), 0.0, fy1),
        Bend("wall R", "up", "x", fx + ba / 2, 0.0, fy1),
        Bend("wing L", "out", "y", -ba / 2, -wx, -gx),
        Bend("wing R", "out", "y", -ba / 2, gx, wx),
        Bend("back wall", "up", "y", fy1 + ba / 2, -back_half, back_half),
    )

    xs = [p[0] for p in pts]
    ys = [p[1] for p in pts]
    return FlatPattern(
        outline=tuple(pts),
        holes=holes,
        bends=bends,
        width=max(xs) - min(xs),
        height=max(ys) - min(ys),
        shortest_flange=min(flange.values()),
    )
