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
    plate_margin: float = 4.0  # plate outline beyond the sled envelope
    plate_corner_r: float = 3.0
    lip_h: float = 2.0  # how far the lip tabs stand proud of the mating plane
    lip_overhang: float = 4.0  # how far each tab reaches in over the board

    # --- fasteners ---------------------------------------------------------
    screw_clear_d: float = 2.5
    csk_d: float = 4.0
    csk_angle: float = 90.0
    tap_drill_d: float = 1.6  # M2 x 0.4
    thread_depth: float = 3.0

    # --- manufacturing -----------------------------------------------------
    tool_d: float = 3.0  # rougher: channel, pocket, body relief
    fine_tool_d: float = 2.0  # finisher: corner reliefs, apertures, lip
    edge_break: float = 0.5
    min_web: float = 2.0  # thinnest strip of metal left beside a cut-out
    min_bearing: float = 1.0  # least ledge the board may be left sitting on

    # --- data --------------------------------------------------------------
    apertures: tuple[Aperture, ...] = ()
    body_mount_holes: tuple[tuple[float, float], ...] = ()

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
        return self.sled_w + 2 * self.plate_margin

    @property
    def plate_h(self) -> float:
        return self.sled_h + 2 * self.plate_margin

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
    "cycfi": ChassisSpec(
        name="cycfi",
        pcb_w=50.0,
        pcb_depth=60.0,
        top_clear=8.0,
        bot_clear=3.0,
        # Aperture x is from the board's centreline, z from its underside.
        apertures=(
            Aperture("usb_c", x=-10.0, z=3.2, w=10.0, h=4.0, corner_r=1.6),
            Aperture("jack_6mm", x=10.0, z=4.5, w=10.0, kind="round"),
        ),
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
