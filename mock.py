"""A stand-in for the PCB, and the clearance checks it makes possible.

The mock is never machined and never exported as a part. It exists so the fit
can be proved arithmetically instead of by eye: if the board-plus-keep-outs
solid shares any volume with either machined part, the assembly does not go
together, and :func:`check_clearance` says so in millimetres.

Keep-out envelope
-----------------
The board slab itself, plus:

* **top** -- the full board footprint up to ``top_clear``, except for a strip
  ``lip_overhang`` wide down each side over the first ``lip_h`` of board, where
  the faceplate's retention tabs come down. Tall parts must stay out of those
  two corners; everything else along the front edge, including the connectors,
  is free.
* **bottom** -- the footprint shrunk by ``bot_keepout_inset`` on the sides and
  the far end, down to ``bot_clear``. The board's own edges are excluded because
  that is where it rests on the ledges.
"""

import cadquery as cq

from params import ChassisSpec
from tooling import block

# How far inside the board outline tall bottom-side parts must stay. The board's
# edges sit on the ledges, so nothing can hang below them there.
BOT_KEEPOUT_INSET = 2.0

# Thickness of the slice taken for the section preview.
SECTION_T = 2.0


def build_pcb_board(spec: ChassisSpec) -> cq.Workplane:
    """The bare board -- outline and thickness, no keep-outs.

    Separate from :func:`build_pcb_mock` because the assembly wants a board that
    looks like a board, while the clearance check wants the board plus every
    volume its components claim. Both start from this one outline so the two
    cannot drift apart.
    """
    half_w = spec.pcb_w / 2
    return block(-half_w, half_w, 0.0, spec.pcb_depth, 0.0, spec.pcb_t)


def build_pcb_mock(spec: ChassisSpec) -> cq.Workplane:
    """The board and everything that must stay clear of metal around it."""
    half_w = spec.pcb_w / 2

    board = build_pcb_board(spec)

    # Top keep-out, in two pieces so the retention tabs have somewhere to land.
    top_main = block(
        -half_w, half_w,
        spec.lip_h, spec.pcb_depth,
        spec.pcb_t, spec.z_top,
    )
    top_front = block(
        -(half_w - spec.lip_overhang), half_w - spec.lip_overhang,
        0.0, spec.lip_h,
        spec.pcb_t, spec.z_top,
    )

    bottom = block(
        -(half_w - BOT_KEEPOUT_INSET), half_w - BOT_KEEPOUT_INSET,
        0.0, spec.pcb_depth - BOT_KEEPOUT_INSET,
        spec.z_pocket_floor, 0.0,
    )

    return board.union(top_main).union(top_front).union(bottom)


def build_channel_section(spec: ChassisSpec) -> cq.Workplane:
    """A slice through the sled at mid-channel, with the board sitting in it.

    The isometric preview cannot show whether the board actually lands on the
    ledges. This can: everything in one plane, metal and board together.

    The two are kept as separate solids in a compound rather than unioned. A
    union would swallow the board into the metal and leave nothing to see but
    the clearance gaps.
    """
    from sled import build_sled

    y = spec.channel_depth / 2
    slab = block(
        -spec.sled_w, spec.sled_w,
        y - SECTION_T / 2, y + SECTION_T / 2,
        spec.z_bot - 1.0, spec.z_top + 1.0,
    )
    metal = build_sled(spec).intersect(slab)
    board = build_pcb_mock(spec).intersect(slab)
    return cq.Workplane("XY").add(
        cq.Compound.makeCompound(metal.solids().vals() + board.solids().vals())
    )


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

    # The board has to be able to get in, and stay put once it has.
    slot_gap = spec.lip_tab_z[0] - spec.pcb_t
    require(slot_gap >= 0.0, f"retention tab bites into the board by {-slot_gap:.2f} mm")
    require(
        spec.bearing_w >= spec.min_bearing,
        f"board sits on only {spec.bearing_w:.2f} mm of ledge at full side "
        f"clearance, against a {spec.min_bearing:.2f} mm minimum",
    )

    # The module has to be able to get in too.
    aperture_w, aperture_h = spec.aperture_required
    bb = sled.val().BoundingBox()
    require(
        bb.xlen <= aperture_w + 1e-6 and bb.zlen <= aperture_h + 1e-6,
        f"sled is {bb.xlen:.2f} x {bb.zlen:.2f}, larger than the reported "
        f"{aperture_w:.2f} x {aperture_h:.2f} aperture",
    )

    # Each part must survive as one piece.
    for label, part in (("sled", sled), ("faceplate", plate)):
        count = len(part.solids().vals())
        require(count == 1, f"{label} came apart into {count} solids")

    # Screws must reach, without bottoming out.
    require(
        spec.thread_depth <= spec.plate_t - 0.8,
        "tapped hole breaks through the visible face of the plate",
    )

    failures.extend(spec.aperture_warnings())
    return failures
