"""Parameter sets for the Violet PCB chassis.

Every dimension in the model originates here. The geometry modules
(:mod:`sled`, :mod:`faceplate`, :mod:`mock`) contain no numeric literals -- they
read a :class:`ChassisSpec` or one of its derived properties. To cut a chassis
for a different board, add an entry to :data:`SPECS`; no other file changes.

All dimensions are millimetres, all angles degrees.

Coordinate frame
----------------
The origin is the centre of the *mating plane* -- the faceplate's rear face,
where the sled's front face lands.

    X   across the plate, symmetric about 0 (the PCB's width)
    Y   insertion depth; the sled occupies [0, sled_depth] and goes into the
        instrument, the faceplate occupies [-plate_t, 0] and stays outside
    Z   Z = 0 is the PCB's underside

The sled is a tray folded from sheet; the faceplate is machined from plate.

Tray cross-section, looking down -Y::

     z_top  ||                                      ||   folded side walls
            ||                                      ||
     Z=0    ||    ..............................    ||   PCB
            ||      []                    []        ||   adhesive standoffs
    floor   ++======================================++   flat floor
     z_bot

Nothing supports the board but the standoffs, so its solder joints never reach
the metal. That is deliberate: the board is dense with through-hole joints.
"""

import math
from dataclasses import dataclass

# Slack for geometric comparisons. Dimensions here are sums of decimals that do
# not land exactly in binary, so an exact-limit spec would otherwise fail.
TOL = 1e-9

# ---------------------------------------------------------------------------
# Faceplate cut-outs
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Aperture:
    """A cut-out through the faceplate, positioned in the *PCB's* own frame.

    Because ``x`` is measured from the board's centreline and ``z`` from the
    board's underside, aperture positions can be read straight off the PCB
    layout without re-referencing them to the chassis.
    """

    name: str
    x: float
    z: float
    w: float
    h: float = 0.0
    kind: str = "rect"  # "rect" | "round"; for "round", w is the diameter
    corner_r: float = 0.5

    def __post_init__(self) -> None:
        if self.kind not in ("rect", "round"):
            raise ValueError(f"aperture {self.name!r}: kind must be 'rect' or 'round'")
        if self.kind == "rect" and self.h <= 0:
            raise ValueError(f"aperture {self.name!r}: rect needs a positive h")

    @property
    def bounds(self) -> tuple[float, float, float, float]:
        """(x_min, x_max, z_min, z_max) of the opening."""
        half_h = (self.w if self.kind == "round" else self.h) / 2
        return (self.x - self.w / 2, self.x + self.w / 2, self.z - half_h, self.z + half_h)


# ---------------------------------------------------------------------------
# The chassis itself
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ChassisSpec:
    """One complete chassis: a sled and the faceplate it docks to."""

    name: str

    # --- the board ---------------------------------------------------------
    pcb_w: float  # board width, across the plate
    pcb_depth: float  # board length, into the instrument
    pcb_t: float = 1.6
    pcb_corner_r: float = 0.0  # the board's own corner radius; 0.0 means square
    top_clear: float = 8.0  # tallest component on the top side

    # --- fits --------------------------------------------------------------
    # Formed sheet holds around +/-0.3 where milling held +/-0.05, so these are
    # deliberately looser than the machined design's were.
    # Set by the standoffs, not the board: cycfi's mounting holes sit 2.52 mm
    # from its edge, so a standoff reaches past the board and needs flat floor
    # under it, beyond where the wall's bend starts. 2.0 leaves about 1 mm of
    # placement margin, which matters because the bases are stuck on by hand.
    side_clear: float = 2.0  # per side, board edge to the folded wall
    slot_clear: float = 0.2  # board top face to lip underside
    end_clear: float = 0.5  # board far edge to the back wall
    lip_clear: float = 0.3  # lip tab to wall, a slip fit

    # --- sled: folded sheet ------------------------------------------------
    material: str = "5052-H32"  # folds at ~1x t; 6061 cracks and needs 3-4x
    sheet_t: float = 1.0
    bend_r: float = 1.0  # inside radius, about 1x thickness for 5052
    # Bend allowance is shop-specific. 0.38 is reasonable for 5052 at this
    # radius, but the report prints it so a fabricator can substitute theirs.
    k_factor: float = 0.38
    bend_relief_w: float = 1.5  # slot at each bend end, stops the corner tearing
    # Set by the M2 hole, not by the screw: a hole punched flat has to sit 4t
    # clear of the bend it will be folded near or forming pulls it oval, and 2t
    # clear of the sheared tip. Those two plus the hole and the bend radius need
    # 9.5, which leaves exactly one legal position; 10.0 buys 0.5 mm of
    # manufacturing margin either side of it.
    wing_w: float = 10.0  # how far each wing flange stands out from the wall
    cable_slot_w: float = 6.0
    cable_slot_floor_z: float = 3.0  # notch floor, above the board underside

    # --- board support -----------------------------------------------------
    # Nylon standoffs with adhesive bases, stuck to the flat floor. Insulating
    # at the only points of contact, which matters: the board's through-hole
    # solder joints must never reach bare aluminium.
    standoff_h: float = 3.0
    standoff_od: float = 5.0
    board_hole_d: float = 2.2  # M2 clearance in the board

    # --- faceplate ---------------------------------------------------------
    plate_t: float = 4.0
    # Plate outline beyond the sled envelope. Wider than tall on purpose: the
    # extra width either side forms the ears that carry the body-fixing screws,
    # while above and below the aperture the plate only has to cover the hole.
    #
    # 12.0 leaves 3 mm of metal between a 6 mm head and both the aperture and
    # the plate edge. 10.0 is the arithmetic minimum but leaves nothing in hand.
    plate_margin_x: float = 12.0
    plate_margin_z: float = 4.0
    plate_corner_r: float = 3.0
    lip_h: float = 2.0  # how far the lip tabs stand proud of the mating plane
    lip_overhang: float = 4.0  # how far each tab reaches in over the board

    # --- fasteners ---------------------------------------------------------
    # M2, sled wings into the faceplate, driven from inside the cavity.
    screw_clear_d: float = 2.5
    csk_d: float = 4.0
    csk_angle: float = 90.0
    tap_drill_d: float = 1.6  # M2 x 0.4
    thread_depth: float = 3.0
    # M3, faceplate into threaded inserts in the instrument, driven from outside.
    body_screw_clear_d: float = 3.4
    body_csk_d: float = 6.0

    # --- manufacturing -----------------------------------------------------
    tool_d: float = 3.0  # rougher: channel, pocket, body relief
    fine_tool_d: float = 2.0  # finisher: corner reliefs, apertures, lip
    edge_break: float = 0.5
    min_web: float = 2.0  # thinnest strip of metal left beside a cut-out

    # --- data --------------------------------------------------------------
    apertures: tuple[Aperture, ...] = ()
    # Standoff positions, taken from the board's own mounting holes: x from its
    # centreline, y from its front edge.
    board_holes: tuple[tuple[float, float], ...] = ()

    # -- derived: tools -----------------------------------------------------

    @property
    def tool_r(self) -> float:
        return self.tool_d / 2

    @property
    def fine_tool_r(self) -> float:
        return self.fine_tool_d / 2

    # -- derived: X ---------------------------------------------------------

    @property
    def channel_w(self) -> float:
        """Clear width between the inside faces of the two folded walls."""
        return self.pcb_w + 2 * self.side_clear

    @property
    def body_w(self) -> float:
        """Width over the folded walls, behind the wings."""
        return self.channel_w + 2 * self.sheet_t

    @property
    def sled_w(self) -> float:
        """Full envelope, measured across the wing flanges."""
        return self.body_w + 2 * self.wing_w

    # -- derived: Y ---------------------------------------------------------

    @property
    def wing_y(self) -> tuple[float, float]:
        """(front, back) of the wing flange; its front face beds on the plate."""
        return (0.0, self.sheet_t)

    @property
    def board_y0(self) -> float:
        """Y of the board's front edge, clear of the wing flange."""
        return self.sheet_t

    @property
    def channel_depth(self) -> float:
        """Y of the back wall's inside face."""
        return self.board_y0 + self.pcb_depth + self.end_clear

    @property
    def sled_depth(self) -> float:
        return self.channel_depth + self.sheet_t

    # -- derived: Z ---------------------------------------------------------

    @property
    def z_top(self) -> float:
        """Top edge of the folded walls."""
        return self.pcb_t + self.top_clear

    @property
    def z_floor_inner(self) -> float:
        """Inside face of the floor; the standoffs stand on this."""
        return -self.standoff_h

    @property
    def z_bot(self) -> float:
        return self.z_floor_inner - self.sheet_t

    @property
    def z_mid(self) -> float:
        """Vertical centre of the sled envelope; the wings and plate centre here."""
        return (self.z_top + self.z_bot) / 2

    @property
    def sled_h(self) -> float:
        return self.z_top - self.z_bot

    # -- derived: interface -------------------------------------------------

    @property
    def standoff_xy(self) -> tuple[tuple[float, float], ...]:
        """(x, y) of each standoff, in chassis coordinates."""
        return tuple((x, self.board_y0 + y) for x, y in self.board_holes)

    @property
    def wing_hole_xz(self) -> tuple[tuple[float, float], ...]:
        """(x, z) of the two M2 positions, shared by the wings and the plate."""
        x = self.body_w / 2 + self.wing_hole_offset
        return ((-x, self.z_mid), (x, self.z_mid))

    @property
    def lip_tab_x(self) -> tuple[tuple[float, float], ...]:
        """(x_inner, x_outer) of each retention tab, left then right."""
        outer = self.channel_w / 2 - self.lip_clear
        inner = outer - self.lip_overhang
        return ((-outer, -inner), (inner, outer))

    @property
    def lip_tab_z(self) -> tuple[float, float]:
        """(bottom, top) of the retention tabs; the bottom bears on the board."""
        return (self.pcb_t + self.slot_clear, self.z_top)

    # -- derived: faceplate -------------------------------------------------

    @property
    def plate_w(self) -> float:
        return self.sled_w + 2 * self.plate_margin_x

    @property
    def plate_h(self) -> float:
        return self.sled_h + 2 * self.plate_margin_z

    @property
    def body_mount_xz(self) -> tuple[tuple[float, float], ...]:
        """(x, z) of the two screws that fix the plate to the instrument.

        One centred in each ear, on the plate's horizontal centreline. Derived
        rather than listed so it stays right for any board: the ear only exists
        because the plate is wider than the sled, and this is the middle of it.

        Two is enough. The sled sitting in the routed aperture is what stops the
        plate rotating; the screws only have to clamp it.
        """
        x = self.sled_w / 2 + self.plate_margin_x / 2
        return ((-x, self.z_mid), (x, self.z_mid))

    # -- derived: manufacturing ---------------------------------------------

    @property
    def aperture_required(self) -> tuple[float, float]:
        """The (width, height) hole to rout in the instrument's edge."""
        return (self.sled_w, self.sled_h)

    @property
    def stock_plate(self) -> tuple[float, float, float]:
        return (self.plate_w, self.plate_h, self.plate_t + self.lip_h)

    @property
    def screw_len(self) -> float:
        """Minimum M2 pan-head screw length: through the wing flange, into the plate."""
        return self.sheet_t + self.thread_depth

    @property
    def bend_allowance(self) -> float:
        """Material consumed by one 90 degree bend, along the neutral axis.

        The one number that decides whether the folded part comes out the right
        size. Sheet does not shorten by the full corner: it stretches on the
        outside and compresses on the inside, and the neutral axis sits at
        ``k_factor`` of the way through.
        """
        return (math.pi / 2) * (self.bend_r + self.k_factor * self.sheet_t)

    @property
    def setback(self) -> float:
        """Distance from the bend's apex to where a flange's flat actually starts."""
        return self.bend_r + self.sheet_t

    @property
    def wing_z0(self) -> float:
        """Bottom of the wing flange.

        Clear of the floor's bend by a thickness, so the wing's own outer bend
        radius has somewhere to run out. Carried lower it would collide with the
        curve where the wall meets the floor.
        """
        return self.z_floor_inner + self.bend_r + self.sheet_t

    @property
    def flat_floor_half_w(self) -> float:
        """Half-width of the floor's genuinely flat part.

        The floor stops being flat one bend radius short of the wall, where the
        bend's inner surface goes tangent. Anything that has to bed down, such as
        an adhesive standoff, has to stay inside this.
        """
        return self.channel_w / 2 - self.bend_r

    @property
    def min_edge_dist(self) -> float:
        """Least metal from a hole's edge to the edge of the sheet.

        The sheet-metal equivalent of ``min_web``, and a different rule: punching
        or cutting closer than about twice the thickness distorts the edge.
        """
        return 2 * self.sheet_t

    @property
    def min_flange(self) -> float:
        """Shortest flange a press brake can form, measured from the bend tangent.

        Bend radius plus 4t, not 4t alone: the radius consumes flange before any
        straight material exists for the tool to hold.
        """
        return self.bend_r + 4 * self.sheet_t

    @property
    def min_feature_to_bend(self) -> float:
        """Least metal from a hole's edge to a bend line it will be folded beside.

        Closer than this and forming drags the hole out of round, because the
        material around it is still being stretched as the bend forms.
        """
        return 4 * self.sheet_t

    @property
    def wing_hole_offset(self) -> float:
        """Hole centre out from the wall's outer face, along the wing flange.

        Not the flange's midpoint. The hole is squeezed between two rules pulling
        opposite ways, 4t clear of the bend and 2t clear of the tip, so it is
        placed midway between those two limits instead. Centring it would need a
        flange 12.5 mm long rather than 10, and every millimetre of flange is two
        more millimetres of hole in the instrument.
        """
        nearest = self.bend_r + self.min_feature_to_bend + self.screw_clear_d / 2
        furthest = self.wing_w - self.min_edge_dist - self.screw_clear_d / 2
        return (nearest + furthest) / 2

    @property
    def wing_hole_from_bend(self) -> float:
        """Distance from the wing hole's near edge back to its bend tangent."""
        return self.wing_hole_offset - self.bend_r - self.screw_clear_d / 2

    @property
    def wing_hole_from_tip(self) -> float:
        """Distance from the wing hole's far edge to the flange's sheared tip."""
        return self.wing_w - self.wing_hole_offset - self.screw_clear_d / 2

    # -- checks on the aperture data ----------------------------------------

    def aperture_warnings(self) -> list[str]:
        """Faults in the cut-out list that geometry alone will not reveal.

        These are data problems, not modelling errors, so they are reported
        rather than raised: the parts still build, and the list travels with the
        manufacturing report. The one that scraps a plate is an opening that
        looks fine on its own but lands on the solid front face of the sled, so
        the connector behind it never sees daylight.
        """
        notes: list[str] = []

        for ap in self.apertures:
            x0, x1, z0, z1 = ap.bounds
            where = f"aperture {ap.name!r}"

            # Enough plate left around the opening to hold together.
            if max(-x0, x1) > self.plate_w / 2 - self.min_web:
                notes.append(f"{where}: less than {self.min_web} mm of plate beside it")
            if z1 > self.z_mid + self.plate_h / 2 - self.min_web:
                notes.append(f"{where}: less than {self.min_web} mm of plate above it")
            if z0 < self.z_mid - self.plate_h / 2 + self.min_web:
                notes.append(f"{where}: less than {self.min_web} mm of plate below it")

            # Visible into the tray, not blanked off by a folded wall.
            if max(-x0, x1) > self.channel_w / 2:
                notes.append(f"{where}: opens onto a folded wall, not into the tray")
            if z1 > self.z_top or z0 < self.z_floor_inner:
                notes.append(f"{where}: reaches outside the tray's opening")

            # The retention tabs pass through the plate's rear face here.
            tab_z0, tab_z1 = self.lip_tab_z
            for tab_x0, tab_x1 in self.lip_tab_x:
                if x0 < tab_x1 and x1 > tab_x0 and z0 < tab_z1 and z1 > tab_z0:
                    notes.append(f"{where}: overlaps a retention tab and would cut it away")

        return notes

    # -- validation ---------------------------------------------------------

    def __post_init__(self) -> None:
        def require(ok: bool, msg: str) -> None:
            if not ok:
                raise ValueError(f"{self.name}: {msg}")

        # Forming limits.
        require(self.bend_r >= self.sheet_t - TOL,
                f"inside bend radius {self.bend_r} is tighter than 1x thickness; "
                f"{self.material} will crack")
        require(0.0 < self.k_factor < 0.5,
                "k_factor is a fraction of thickness to the neutral axis, so 0 to 0.5")
        require(self.bend_relief_w >= self.sheet_t,
                "bend relief narrower than the sheet will tear at the corner")
        require(self.wing_hole_from_tip >= self.min_edge_dist - TOL,
                f"M2 wing hole sits {self.wing_hole_from_tip:.2f} mm from the flange tip, "
                f"inside the {self.min_edge_dist:.1f} mm needed")
        require(self.wing_w - self.bend_r >= self.min_flange - TOL,
                f"wing flange is shorter than the {self.min_flange} mm a brake can form")
        require(self.wing_hole_from_bend >= self.min_feature_to_bend - TOL,
                f"M2 wing hole sits {self.wing_hole_from_bend:.2f} mm from its bend, inside "
                f"the {self.min_feature_to_bend:.1f} mm needed; widen wing_w to at least "
                f"{2 * (self.min_feature_to_bend + self.bend_r + self.screw_clear_d / 2):.1f}")

        # Machining limits, which now apply only to the faceplate.
        require(self.thread_depth <= self.plate_t - 0.8,
                "tapped hole would break through the visible face of the plate")
        require(self.lip_overhang >= self.fine_tool_d,
                "lip tab is narrower than the tool that has to cut around it")
        require(self.fine_tool_d <= self.tool_d,
                "fine_tool_d is meant to be the smaller of the two cutters")

        require(self.lip_h > 0 and self.lip_h < self.pcb_depth,
                "lip_h must be positive and shorter than the board")
        require(self.cable_slot_floor_z > self.pcb_t,
                "cable notch floor must clear the board")
        require(self.cable_slot_w <= self.channel_w,
                "cable notch is wider than the tray")
        require(self.pcb_corner_r < min(self.pcb_w, self.pcb_depth) / 2,
                f"pcb_corner_r {self.pcb_corner_r} is too large for the board outline")

        # Standoffs have to sit wholly on the flat floor. The flat ends where the
        # bend's inner surface becomes tangent to it, one bend radius short of
        # the wall, and an adhesive base lapping onto that curve would tilt the
        # board.
        for x, y in self.board_holes:
            require(abs(x) + self.standoff_od / 2 <= self.flat_floor_half_w + TOL,
                    f"standoff at x={x:.2f} laps onto the wall's bend radius; "
                    f"raise side_clear to at least "
                    f"{self.standoff_od / 2 - self.pcb_w / 2 + self.bend_r + abs(x):.2f}")
            require(0 <= y <= self.pcb_depth,
                    f"standoff at y={y:.2f} is off the board")

        # The body-fixing heads have to land on solid plate. Too far in and the
        # screw opens into the routed aperture with nothing behind it; too far
        # out and it breaks through the plate's edge.
        # Compared with a tolerance: a spec sitting exactly on a limit is legal,
        # and these values are sums of decimals that do not land exactly.
        head_r = self.body_csk_d / 2
        for x, _z in self.body_mount_xz:
            require(abs(x) - head_r >= self.sled_w / 2 + self.min_web - TOL,
                    f"body-fixing head at x={x:.2f} comes within {self.min_web} mm of the "
                    "aperture; widen plate_margin_x")
            require(abs(x) + head_r <= self.plate_w / 2 - self.min_web + TOL,
                    f"body-fixing head at x={x:.2f} comes within {self.min_web} mm of the "
                    "plate edge; widen plate_margin_x")
            for wx, _wz in self.wing_hole_xz:
                require(abs(abs(x) - abs(wx)) >= head_r + self.csk_d / 2 - TOL,
                        f"body-fixing head at x={x:.2f} fouls the M2 wing head at x={wx:.2f}")


# ---------------------------------------------------------------------------
# The builds
# ---------------------------------------------------------------------------
#
# Two chassis are needed, one per board. Placeholder dimensions -- overwrite
# pcb_w / pcb_depth / top_clear / bot_clear and the aperture list with the real
# numbers; everything else follows.
#
# Which board is the larger of the two has been guessed. If it is the wrong way
# round, swap the dimension blocks -- nothing else depends on the mapping.

SPECS: dict[str, ChassisSpec] = {
    # Cycfi Nu Series internal breakout board.
    #
    # Outline, corner radius and part placement measured from the Eagle layout at
    # github.com/cycfi/nu, commit dc334a32f05f (2021-12-14):
    #   internal_breakout/internal_breakout.brd
    # That work is CC BY-NC 4.0. Nothing of theirs is redistributed here; these
    # are dimensions taken from it.
    #
    # Measured: pcb_w, pcb_depth, pcb_corner_r, board_holes.
    # Assumed:  pcb_t (a fab parameter, not in a .brd) and top_clear (chosen to
    #           clear the 0.1 inch headers with mating sockets and strain relief).
    #
    # The board carries 17 headers and no panel connectors, so the faceplate is
    # solid and the loom leaves through the tray's back-wall notch.
    #
    # Its four M2 mounting holes carry the standoffs. Measured at (2.52, 32.42),
    # (2.52, 2.52), (47.52, 32.52) and (47.52, 2.52) in the layout's own 50 x 35
    # frame, converted here to x from the centreline and y from the front edge.
    # The nearest solder joint to any of them is 3.78 mm away, so a standoff up
    # to 7.6 mm across clears every one.
    "cycfi": ChassisSpec(
        name="cycfi",
        pcb_w=50.0,
        pcb_depth=35.0,
        pcb_corner_r=1.5,
        top_clear=15.0,
        apertures=(),
        board_holes=(
            (-22.48, 32.42),
            (-22.48, 2.52),
            (22.52, 32.52),
            (22.52, 2.52),
        ),
    ),
    # Entirely placeholder, including the standoff pattern, which is inset from
    # the assumed outline the way cycfi's real one happens to sit. Replace all of
    # it once the board is measured.
    "rmc": ChassisSpec(
        name="rmc",
        pcb_w=36.0,
        pcb_depth=44.0,
        top_clear=6.0,
        apertures=(
            Aperture("jack_3mm5", x=0.0, z=2.5, w=6.5, kind="round"),
        ),
        board_holes=(
            (-15.5, 41.5),
            (-15.5, 2.5),
            (15.5, 41.5),
            (15.5, 2.5),
        ),
    ),
}
