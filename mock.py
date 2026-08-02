"""A stand-in for the PCB, and the clearance checks it makes possible.

The mock is never machined and never exported as a part. It exists so the fit
can be proved arithmetically instead of by eye: if the board-plus-keep-outs
solid shares any volume with either machined part, the assembly does not go
together, and :func:`check_clearance` says so in millimetres.

Keep-out envelope
-----------------
The board slab itself, plus:

* **top** -- the full board footprint up to ``top_clear``. Nothing reaches in
  over the board any more, so nothing is given back.
* **bottom** -- the full footprint down to the standoff height. Unlike the
  machined design there is no ledge under the board's edges, so nothing is
  excluded: the whole underside has to clear the tray floor.

The standoffs are modelled too, since they are what holds the board off the
floor and they are the parts most likely to foul something.
"""

import cadquery as cq

from params import ChassisSpec
from tooling import OVERSHOOT, block, rod

# Thickness of the slice taken for the section preview.
SECTION_T = 2.0

# Volume the kernel may report where two parts are meant to touch face to face.
# Well under the size of any real interference, which starts in whole cubic mm.
CONTACT_TOL = 0.5


def _outline_prism(spec: ChassisSpec, z0: float, z1: float) -> cq.Workplane:
    """The board's outline, extruded between two heights.

    Real boards are routed with a cutter and so have rounded corners. Modelling
    that matters: whether the board's corners are sharper than the fillets left
    in the channel is exactly what decides if it seats against the back wall, so
    a check run against a squared-off outline would be answering the wrong
    question. The keep-out volumes above the board share the outline for the same
    reason, since a squared-off envelope would foul those fillets even when the
    board itself does not.
    """
    half_w = spec.pcb_w / 2
    prism = block(-half_w, half_w, 0.0, spec.pcb_depth, z0, z1)
    if spec.pcb_corner_r > 0:
        prism = prism.edges("|Z").fillet(spec.pcb_corner_r)
    return prism


def build_pcb_board(spec: ChassisSpec) -> cq.Workplane:
    """The bare board -- outline and thickness, no keep-outs.

    Separate from :func:`build_pcb_mock` because the assembly wants a board that
    looks like a board, while the clearance check wants the board plus every
    volume its components claim. Both start from the same outline so the two
    cannot drift apart.
    """
    return _outline_prism(spec, 0.0, spec.pcb_t)


def build_pcb_mock(spec: ChassisSpec) -> cq.Workplane:
    """The board and everything that must stay clear of metal around it.

    The whole footprint, top and bottom, with nothing given back. The plate has
    no tabs reaching in over the board any more, and the board rests only on its
    standoffs rather than on a ledge, so there is no longer any region where
    metal is expected to intrude.
    """
    top = _outline_prism(spec, spec.pcb_t, spec.z_top)
    bottom = _outline_prism(spec, spec.z_floor_inner, 0.0)
    return build_pcb_board(spec).union(top).union(bottom)


def build_standoffs(spec: ChassisSpec) -> cq.Workplane:
    """The nylon standoffs, as they sit between the floor and the board."""
    pillars = [
        rod(x, y, spec.standoff_od, spec.z_floor_inner, 0.0)
        for x, y in spec.standoff_xy
    ]
    if not pillars:
        return cq.Workplane("XY")
    stack = pillars[0]
    for pillar in pillars[1:]:
        stack = stack.union(pillar)
    return stack


def build_channel_section(spec: ChassisSpec) -> cq.Workplane:
    """A slice through the tray, with the board on its standoffs.

    The isometric preview cannot show the gap the standoffs hold open under the
    board, which is the whole point of them. This can: metal, standoffs and
    board in one plane.

    Sliced through a standoff row rather than at mid-depth, so the standoffs
    actually appear. They are kept as separate solids in a compound: a union
    would swallow the board into the metal and leave nothing to see.
    """
    from sled import build_sled

    y = spec.standoff_xy[0][1] if spec.standoff_xy else spec.channel_depth / 2
    slab = block(
        -spec.sled_w, spec.sled_w,
        y - SECTION_T / 2, y + SECTION_T / 2,
        spec.z_bot - 1.0, spec.z_top + 1.0,
    )
    parts = [
        build_sled(spec).intersect(slab),
        build_pcb_board(spec).intersect(slab),
        build_standoffs(spec).intersect(slab),
    ]
    solids = [s for p in parts for s in p.solids().vals()]
    return cq.Workplane("XY").add(cq.Compound.makeCompound(solids))


def _overlap(a: cq.Workplane, b: cq.Workplane) -> float:
    """Shared volume of two solids, in cubic millimetres."""
    shared = a.intersect(b)
    solids = shared.solids().vals()
    return sum(s.Volume() for s in solids)


def check_clearance(spec: ChassisSpec) -> list[str]:
    """Prove the three parts fit. Returns a list of failures, empty if they do.

    Interference is measured, not eyeballed, so a fit that is wrong by a tenth
    of a millimetre fails here rather than at the bench.
    """
    from faceplate import build_faceplate
    from sled import build_sled

    failures: list[str] = []
    sled = build_sled(spec)
    plate = build_faceplate(spec)
    pcb = build_pcb_mock(spec)

    def require(ok: bool, msg: str) -> None:
        if not ok:
            failures.append(msg)

    # Nothing may share space with anything else.
    for name, a, b in (
        ("board fouls the sled", pcb, sled),
        ("board fouls the faceplate", pcb, plate),
        ("sled fouls the faceplate", sled, plate),
    ):
        volume = _overlap(a, b)
        require(volume <= 0.0, f"{name}: {volume:.3f} mm3 of interference")

    # Standoffs have to bed on flat floor, not lap onto a bend, or the board tilts.
    # These sit *on* the floor, so a coplanar contact patch is expected and the
    # kernel reports a sliver for it. CONTACT_TOL passes that while still
    # catching a standoff that genuinely runs into a wall.
    standoffs = build_standoffs(spec)
    if spec.standoff_xy:
        volume = _overlap(standoffs, sled)
        require(volume <= CONTACT_TOL, f"a standoff fouls the tray: {volume:.3f} mm3")
        for x, y in spec.standoff_xy:
            reach = abs(x) + spec.standoff_od / 2
            require(
                reach <= spec.flat_floor_half_w + 1e-9,
                f"standoff at x={x:.2f} reaches {reach:.2f}, past the flat floor's "
                f"{spec.flat_floor_half_w:.2f}",
            )
    else:
        require(False, "no standoffs: the board would rest on bare metal")

    # The module has to get in, and only the body goes through the hole. Measured
    # behind the wing flanges rather than taken from the bounding box, because
    # the box includes the wings and they stay outside the instrument. The whole
    # width saving rests on that, so it is worth measuring rather than assuming.
    aperture_w, aperture_h = spec.aperture_required
    body = sled.intersect(
        block(
            -spec.sled_w, spec.sled_w,
            spec.channel_depth / 2 - 0.5, spec.channel_depth / 2 + 0.5,
            spec.z_bot - 1.0, spec.z_top + 1.0,
        )
    )
    bb = body.val().BoundingBox()
    require(
        bb.xlen <= aperture_w + 1e-6 and bb.zlen <= aperture_h + 1e-6,
        f"tray body is {bb.xlen:.2f} x {bb.zlen:.2f}, larger than the reported "
        f"{aperture_w:.2f} x {aperture_h:.2f} aperture",
    )
    require(
        sled.val().BoundingBox().xlen > aperture_w + 1e-6,
        "the wings do not reach past the aperture, so nothing stops the tray "
        "falling through it",
    )

    # Each part must survive as one piece.
    for label, part in (("sled", sled), ("faceplate", plate)):
        count = len(part.solids().vals())
        require(count == 1, f"{label} came apart into {count} solids")

    # One screw has to pass cleanly through both parts at each fixing.
    for x, z in spec.fixing_xz:
        shaft = rod(x, 0.0, spec.body_screw_clear_d, -1.0, 1.0)
        shaft = shaft.rotate((0, 0, 0), (1, 0, 0), -90).translate((0, 0, z))
        blocked = _overlap(shaft, sled) + _overlap(shaft, plate)
        require(
            blocked <= CONTACT_TOL,
            f"the fixing at x={x:.2f} is obstructed by {blocked:.3f} mm3 of metal",
        )

    failures.extend(spec.aperture_warnings())
    return failures
