"""Cutting-tool constructors shared by the two machined parts.

Material removal in this model is always expressed the way it happens on the
machine: build the volume the cutter sweeps, then subtract it. That keeps every
transform in :mod:`sled` and :mod:`faceplate` down to one readable operation and
makes each step's removed volume inspectable on its own.

Everything here is built in absolute chassis coordinates -- see :mod:`params`
for the frame -- so no transform has to depend on the topology left behind by
the transform before it.
"""

import math
import warnings

import cadquery as cq

# Overshoot pushed past an open boundary so a through-cut never leaves a
# zero-thickness sliver or a coplanar face for the kernel to trip over.
OVERSHOOT = 1.0


def block(x0: float, x1: float, y0: float, y1: float, z0: float, z1: float) -> cq.Workplane:
    """A rectangular volume spanning the given absolute bounds, in any order."""
    x0, x1 = sorted((x0, x1))
    y0, y1 = sorted((y0, y1))
    z0, z1 = sorted((z0, z1))
    return (
        cq.Workplane("XY")
        .box(x1 - x0, y1 - y0, z1 - z0, centered=False)
        .translate((x0, y0, z0))
    )


def rod(x: float, y: float, d: float, z0: float, z1: float) -> cq.Workplane:
    """A vertical cylinder -- what a plunging end mill leaves behind."""
    z0, z1 = sorted((z0, z1))
    return cq.Workplane("XY").circle(d / 2).extrude(z1 - z0).translate((x, y, z0))


def countersunk_hole(
    x: float,
    z: float,
    y_face: float,
    depth: float,
    clear_d: float,
    head_d: float,
    angle: float,
) -> cq.Workplane:
    """A countersunk clearance hole drilled along -Y from the face at ``y_face``.

    The head recess opens on the rear face, so the screws are driven from inside
    the cavity while the sled and plate are on the bench.
    """
    cone_h = (head_d - clear_d) / 2 / math.tan(math.radians(angle / 2))

    shank = cq.Solid.makeCylinder(
        clear_d / 2, depth + 2 * OVERSHOOT, cq.Vector(0, 0, -OVERSHOOT)
    )
    cone = cq.Solid.makeCone(
        clear_d / 2, head_d / 2, cone_h, cq.Vector(0, 0, depth - cone_h)
    )
    head = cq.Solid.makeCylinder(
        head_d / 2, OVERSHOOT, cq.Vector(0, 0, depth - 1e-6)
    )

    tool = shank.fuse(cone, head).clean()
    # Local +Z becomes global +Y, so the recess opens towards the cavity.
    return (
        cq.Workplane("XY")
        .add(tool)
        .rotate((0, 0, 0), (1, 0, 0), -90)
        .translate((x, y_face - depth, z))
    )


def rounded_slab(
    w: float,
    h: float,
    y_front: float,
    y_back: float,
    z_centre: float,
    corner_r: float,
) -> cq.Workplane:
    """A plate-shaped volume in the XZ plane, with rounded outside corners."""
    slab = block(-w / 2, w / 2, y_front, y_back, z_centre - h / 2, z_centre + h / 2)
    if corner_r > 0:
        slab = slab.edges("|Y").fillet(corner_r)
    return slab


def break_edges_near(
    part: cq.Workplane,
    size: float,
    x0: float,
    x1: float,
    y0: float,
    y1: float,
    z0: float,
    z1: float,
    what: str = "part",
) -> cq.Workplane:
    """Chamfer every edge lying wholly inside the given absolute box.

    The box is derived from the spec rather than from a face selector, so this
    survives changes to the steps that ran before it.

    An edge break is cosmetic, so a refusal from the kernel must not stop the
    part exporting -- but it is never noise either. It means two chamfers met in
    the middle of a web too thin to carry both, which is a design fault worth
    knowing about, so it is warned about loudly and the part is left sharp.
    """
    selector = cq.selectors.BoxSelector((x0, y0, z0), (x1, y1, z1))
    try:
        return part.edges(selector).chamfer(size)
    except Exception as exc:  # noqa: BLE001 - kernel raises bare Standard_Failure
        warnings.warn(
            f"{what}: edge break skipped ({exc.__class__.__name__}). A {size} mm "
            "chamfer does not fit -- usually a cut-out sitting too close to an "
            "edge. Check the aperture warnings; the part is exported sharp.",
            stacklevel=2,
        )
        return part
