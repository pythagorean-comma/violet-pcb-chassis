"""The manufacturing report -- what a machinist needs that a STEP file does not say.

Thread callouts, stock sizes, tool reach and the aperture to rout in the
instrument are all decisions the model already contains implicitly. Printing
them keeps the numbers on the drawing and in the geometry from drifting apart.
"""

from params import ChassisSpec


def _rule(title: str) -> str:
    return f"\n{title}\n{'-' * len(title)}"


def manufacturing_report(spec: ChassisSpec) -> str:
    """Everything needed to quote and cut one chassis."""
    ap_w, ap_h = spec.aperture_required
    sled_x, sled_y, sled_z = spec.stock_sled
    plate_x, plate_y, plate_z = spec.stock_plate

    lines = [
        f"\n{'=' * 68}",
        f"  {spec.name}  -  PCB {spec.pcb_w} x {spec.pcb_depth} x {spec.pcb_t} mm",
        f"{'=' * 68}",
        "  Material: 6061-T6 aluminium, 2 parts",
    ]

    lines.append(_rule("Stock"))
    lines.append(f"  Sled       {sled_x:.1f} x {sled_y:.1f} x {sled_z:.1f} mm  (X x Y x Z)")
    lines.append(f"  Faceplate  {plate_x:.1f} x {plate_y:.1f} x {plate_z:.1f} mm")

    lines.append(_rule("Instrument preparation"))
    lines.append(f"  Rout the edge aperture  {ap_w:.1f} wide x {ap_h:.1f} high")
    lines.append(f"  Depth into the body     {spec.sled_depth:.1f} mm minimum")
    lines.append(f"  Faceplate covers it by  {spec.plate_margin:.1f} mm all round")

    lines.append(_rule("Tooling"))
    lines.append(f"  Roughing      {spec.tool_d:.1f} mm end mill  (channel, pocket, profile)")
    lines.append(f"  Finishing     {spec.fine_tool_d:.1f} mm end mill  (corner reliefs, apertures, lip)")
    lines.append(
        f"  Deepest cut   {spec.max_reach:.1f} mm from the sled's top face"
        f"  =  {spec.max_reach / spec.fine_tool_d:.1f} x D on the finisher"
    )
    lines.append(f"  Min internal radius  {spec.fine_tool_r:.2f} mm")
    lines.append("  Sled is one setup from +Z. No undercuts.")

    lines.append(_rule("Fits"))
    lines.append(f"  Board on the ledge   {spec.bearing_w:.2f} mm bearing each side")
    lines.append(f"  Board to arm         {spec.side_clear:.2f} mm each side")
    lines.append(f"  Board to tab         {spec.slot_clear:.2f} mm above")
    lines.append(f"  Board to back wall   {spec.end_clear:.2f} mm")

    lines.append(_rule("Fasteners"))
    lines.append(f"  2 off  M2 x 0.4 countersunk, {spec.screw_len:.0f} mm minimum length")
    lines.append(f"  Sled wings   {spec.screw_clear_d:.1f} clearance, {spec.csk_d:.1f} csk at {spec.csk_angle:.0f} deg included")
    lines.append(f"  Faceplate    tap M2 x 0.4, {spec.thread_depth:.1f} deep blind")
    lines.append(f"               modelled at {spec.tap_drill_d:.1f} tap drill; do not read thread from the STEP")
    for x, z in spec.wing_hole_xz:
        lines.append(f"               at X {x:+.2f}, Z {z:+.2f}")
    if not spec.body_mount_holes:
        lines.append("  Faceplate to instrument: not yet specified (body_mount_holes is empty)")
    else:
        lines.append(f"  {len(spec.body_mount_holes)} off  faceplate-to-body holes, {spec.screw_clear_d:.1f} clearance")

    lines.append(_rule("Assembly"))
    lines.append("  1. Slide the PCB into the sled channel until it meets the back wall.")
    lines.append("  2. Screw the faceplate to the sled wings from behind; the retention")
    lines.append("     tabs drop into the channel and hold the board's front edge down.")
    lines.append("  3. Insert the whole module through the aperture from outside.")
    lines.append("  4. Fix the faceplate to the body.")

    lines.append(_rule("Keep-outs on the PCB"))
    lines.append(f"  Top side     {spec.top_clear:.1f} mm clear above the board")
    lines.append(
        f"  Front corners  no tall parts within {spec.lip_overhang:.1f} mm of each side edge"
        f" over the first {spec.lip_h:.1f} mm -- the retention tabs land there"
    )
    lines.append(f"  Bottom side  {spec.bot_clear:.1f} mm clear, staying 2.0 mm inside the outline")
    lines.append(f"  Cable exit   {spec.cable_slot_w:.1f} mm notch in the back wall")

    if spec.apertures:
        lines.append(_rule("Faceplate cut-outs"))
        for ap in spec.apertures:
            size = (
                f"dia {ap.w:.1f}"
                if ap.kind == "round"
                else f"{ap.w:.1f} x {ap.h:.1f}, R{max(ap.corner_r, spec.fine_tool_r):.1f}"
            )
            lines.append(f"  {ap.name:<12} at X {ap.x:+.1f}, Z {ap.z:+.1f}   {size}")
        lines.append(
            f"  Connectors sit {spec.plate_t:.1f} mm behind the outer face -- check"
            " mating depth on anything that plugs in."
        )

    warnings = spec.aperture_warnings()
    if warnings:
        lines.append(_rule("WARNINGS"))
        lines.extend(f"  ! {w}" for w in warnings)

    return "\n".join(lines)
