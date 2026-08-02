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
    Z   board thickness; Z = 0 is the ledge top, i.e. the PCB's underside

Sled cross-section, looking down -Y::

     z_top  +----+                          +----+   arms, wall_t thick
            |    |                          |    |
     Z=0    |    +--+                    +--+    |   ledge_w shelf, PCB sits here
            |    |  +--------------------+  |    |
    -bot    |    +--------------------------+    |   bottom-side component void
     z_bot  +--------------------------------+---+   floor, floor_t thick
"""

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
    bot_clear: float = 3.0  # tallest component / solder tail underneath

    # --- fits --------------------------------------------------------------
    side_clear: float = 0.3  # per side, board edge to channel wall
    slot_clear: float = 0.2  # board top face to lip underside
    end_clear: float = 0.5  # board far edge to the back wall
    ledge_w: float = 1.5  # how far each ledge reaches in under the board
    lip_clear: float = 0.15  # lip tab to channel wall, a slip fit

    # --- sled structure ----------------------------------------------------
    wall_t: float = 3.0  # arm thickness
    floor_t: float = 2.0
    back_wall_t: float = 3.0
    wing_w: float = 6.0  # how far each wing stands out from the body
    wing_len: float = 4.0  # wing depth along Y; also the screw's grip length
    cable_slot_w: float = 6.0
    cable_slot_floor_z: float = 3.0  # notch floor, above the board underside

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
    min_bearing: float = 1.0  # least ledge the board may be left sitting on

    # --- data --------------------------------------------------------------
    apertures: tuple[Aperture, ...] = ()

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
        """Width of the upper channel, between the arms."""
        return self.pcb_w + 2 * self.side_clear

    @property
    def pocket_w(self) -> float:
        """Width of the lower pocket; narrower by one ledge on each side."""
        return self.channel_w - 2 * self.ledge_w

    @property
    def body_w(self) -> float:
        """Width of the sled behind the wings."""
        return self.channel_w + 2 * self.wall_t

    @property
    def sled_w(self) -> float:
        """Full sled envelope, measured across the wings."""
        return self.body_w + 2 * self.wing_w

    # -- derived: Y ---------------------------------------------------------

    @property
    def channel_depth(self) -> float:
        """How far the channel runs in before it meets the back wall."""
        return self.pcb_depth + self.end_clear

    @property
    def sled_depth(self) -> float:
        return self.channel_depth + self.back_wall_t

    # -- derived: Z ---------------------------------------------------------

    @property
    def z_top(self) -> float:
        """Top of the arms."""
        return self.pcb_t + self.top_clear

    @property
    def z_pocket_floor(self) -> float:
        return -self.bot_clear

    @property
    def z_bot(self) -> float:
        return -(self.bot_clear + self.floor_t)

    @property
    def bearing_w(self) -> float:
        """Ledge actually left under the board once it sits at full side clearance."""
        return self.ledge_w - self.side_clear

    @property
    def z_mid(self) -> float:
        """Vertical centre of the sled envelope; the wings and plate centre here."""
        return (self.z_top + self.z_bot) / 2

    @property
    def sled_h(self) -> float:
        return self.z_top - self.z_bot

    # -- derived: interface -------------------------------------------------

    @property
    def wing_hole_xz(self) -> tuple[tuple[float, float], ...]:
        """(x, z) of the two M2 positions, shared by the wings and the plate."""
        x = self.body_w / 2 + self.wing_w / 2
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
    def stock_sled(self) -> tuple[float, float, float]:
        return (self.sled_w, self.sled_depth, self.sled_h)

    @property
    def stock_plate(self) -> tuple[float, float, float]:
        return (self.plate_w, self.plate_h, self.plate_t + self.lip_h)

    @property
    def screw_len(self) -> float:
        """Minimum M2 countersunk screw length: through the wing, into the plate."""
        return self.wing_len + self.thread_depth

    @property
    def max_reach(self) -> float:
        """Deepest cut from the sled's top face -- sets the tool stick-out."""
        return self.z_top - self.z_pocket_floor

    @property
    def needs_corner_reliefs(self) -> bool:
        """Whether the channel's milled corners have to be relieved.

        A board whose own corners are at least as round as the fillet the
        roughing cutter leaves drops straight in. A squarer one fouls those
        fillets and stops short of the back wall, so the corners need relieving.
        """
        return self.pcb_corner_r < self.tool_r

    @property
    def deep_cut_tool_d(self) -> float:
        """Smallest cutter that has to reach the full depth of the channel.

        The corner reliefs are the only feature cut with the finisher at full
        depth, so skipping them hands the deepest cut back to the rougher.
        """
        return self.fine_tool_d if self.needs_corner_reliefs else self.tool_d

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

            # Visible through the sled's front face, not blanked off by it.
            half = self.channel_w / 2 if z0 >= 0 else self.pocket_w / 2
            if max(-x0, x1) > half:
                notes.append(f"{where}: opens onto the sled's front face, not the channel")
            if z1 > self.z_top or z0 < self.z_pocket_floor:
                notes.append(f"{where}: reaches outside the sled's opening")

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

        require(self.pocket_w >= self.tool_d,
                f"lower pocket {self.pocket_w:.2f} is narrower than the {self.tool_d} tool")
        require(self.channel_w >= self.tool_d,
                f"channel {self.channel_w:.2f} is narrower than the {self.tool_d} tool")
        require(self.ledge_w > self.side_clear,
                "ledge_w must exceed side_clear or the board has nothing to sit on")
        require(self.wing_w >= self.csk_d + 2.0,
                f"wing_w {self.wing_w} leaves too little material around a {self.csk_d} head")
        require(self.wall_t > self.fine_tool_r,
                "corner reliefs would break through the arm; raise wall_t or drop fine_tool_d")
        require(self.thread_depth <= self.plate_t - 0.8,
                "tapped hole would break through the visible face of the plate")
        require(self.lip_overhang >= self.fine_tool_d,
                "lip tab is narrower than the tool that has to cut around it")
        require(self.lip_h > 0 and self.lip_h < self.pcb_depth,
                "lip_h must be positive and shorter than the board")
        require(self.cable_slot_floor_z > self.pcb_t,
                "cable notch floor must clear the board")
        require(self.cable_slot_w <= self.channel_w,
                "cable notch is wider than the channel")
        require(self.fine_tool_d <= self.tool_d,
                "fine_tool_d is meant to be the smaller of the two cutters")
        require(self.pcb_corner_r < min(self.pcb_w, self.pcb_depth) / 2,
                f"pcb_corner_r {self.pcb_corner_r} is too large for the board outline")

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
    # Measured: pcb_w, pcb_depth, pcb_corner_r.
    # Assumed:  pcb_t (a fab parameter, not in a .brd) and top_clear (chosen to
    #           clear the 0.1 inch headers with mating sockets and strain relief).
    #
    # The board carries 17 headers and no panel connectors, so the faceplate is
    # solid and the loom leaves through the sled's back-wall notch.
    #
    # It also has four M2 mounting holes inset 2.5 mm from each corner, unused
    # here because the sled captures the board mechanically.
    "cycfi": ChassisSpec(
        name="cycfi",
        pcb_w=50.0,
        pcb_depth=35.0,
        pcb_corner_r=1.5,
        top_clear=15.0,
        bot_clear=3.0,
        apertures=(),
    ),
    "rmc": ChassisSpec(
        name="rmc",
        pcb_w=36.0,
        pcb_depth=44.0,
        top_clear=6.0,
        bot_clear=2.5,
        apertures=(
            Aperture("jack_3mm5", x=0.0, z=2.5, w=6.5, kind="round"),
        ),
    ),
}
