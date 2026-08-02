"""The chassis as one thing, rather than a pile of parts.

Two views, both as ``cq.Assembly`` so the parts stay separate, named and coloured
in the exported STEP:

* **assembled** -- the parts exactly where they end up.
* **exploded** -- the same parts drawn apart along the insertion axis, in the
  order they go together.

The assembled view needs no positioning at all. Both machined parts are already
modelled in the shared chassis frame at their fitted positions -- the sled over
``Y = [0, sled_depth]``, the faceplate over ``Y = [-plate_t, 0]`` -- which is
exactly what lets :func:`mock.check_clearance` assert that they do not overlap.
So the assembly is three ``.add()`` calls with identity locations, and only the
exploded view carries offsets.
"""

import cadquery as cq

from faceplate import build_faceplate
from mock import build_pcb_board
from params import ChassisSpec
from sled import build_sled

# How far apart to draw the parts in the exploded view, as a fraction of the
# sled's length. Proportional rather than absolute so both variants explode by a
# sensible amount. Presentation only -- nothing machined depends on it.
EXPLODE_FRACTION = 0.30

SLED_COLOUR = cq.Color("gray")
PLATE_COLOUR = cq.Color("darkslategray")
BOARD_COLOUR = cq.Color(0.05, 0.45, 0.15, 1.0)


def _explode_offsets(spec: ChassisSpec) -> tuple[float, float, float]:
    """(sled, board, faceplate) offsets along Y for the exploded view.

    The board has to travel at least its own length to leave the channel, so its
    offset clears ``pcb_depth`` before the gap is added. Everything moves towards
    -Y, the direction the module is actually taken apart in, which leaves the
    board sitting between the two metal parts in assembly order.
    """
    gap = spec.sled_depth * EXPLODE_FRACTION
    return (0.0, -(spec.pcb_depth + gap), -(spec.pcb_depth + 2 * gap))


def build_assembly(spec: ChassisSpec, exploded: bool = False) -> cq.Assembly:
    """Sled, faceplate and board, fitted together or drawn apart."""
    sled_dy, board_dy, plate_dy = _explode_offsets(spec) if exploded else (0.0, 0.0, 0.0)

    def at(dy: float) -> cq.Location:
        return cq.Location(cq.Vector(0, dy, 0))

    name = f"{spec.name}_exploded" if exploded else spec.name
    return (
        cq.Assembly(name=name)
        .add(build_sled(spec), name="sled", color=SLED_COLOUR, loc=at(sled_dy))
        .add(build_pcb_board(spec), name="pcb", color=BOARD_COLOUR, loc=at(board_dy))
        .add(build_faceplate(spec), name="faceplate", color=PLATE_COLOUR, loc=at(plate_dy))
    )
