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
    from flatten import flat_pattern

    ap_w, ap_h = spec.aperture_required
    plate_x, plate_y, plate_z = spec.stock_plate
    flat = flat_pattern(spec)

    lines = [
        f"\n{'=' * 68}",
        f"  {spec.name}  -  PCB {spec.pcb_w} x {spec.pcb_depth} x {spec.pcb_t} mm",
        f"{'=' * 68}",
        "  Two parts, two processes:",
        f"    Tray       {spec.material} sheet, {spec.sheet_t:.1f} mm, laser cut and folded",
        "    Faceplate  6061-T6 aluminium, machined from plate",
    ]

    lines.append(_rule("Stock"))
    lines.append(f"  Tray blank {flat.width:.1f} x {flat.height:.1f} mm of "
                 f"{spec.sheet_t:.1f} mm sheet  (see the DXF)")
    lines.append(f"  Faceplate  {plate_x:.1f} x {plate_y:.1f} x {plate_z:.1f} mm")

    lines.append(_rule("Instrument preparation"))
    lines.append(f"  Rout the edge aperture  {ap_w:.1f} wide x {ap_h:.1f} high")
    lines.append(f"  Depth into the body     {spec.sled_depth:.1f} mm minimum")
    lines.append(
        f"  Faceplate overlaps it   {spec.plate_margin_x:.1f} mm each side,"
        f" {spec.plate_margin_z:.1f} mm top and bottom"
    )
    lines.append(f"  Fit M3 threaded inserts at X {spec.body_mount_xz[0][0]:+.2f}"
                 f" and {spec.body_mount_xz[1][0]:+.2f}, on the aperture's centreline")

    lines.append(_rule("Tray: bend schedule"))
    lines.append(f"  Material      {spec.material}, {spec.sheet_t:.1f} mm")
    lines.append(f"  Inside radius {spec.bend_r:.1f} mm  ({spec.bend_r / spec.sheet_t:.1f} x t)")
    lines.append(f"  K-factor      {spec.k_factor:.2f}  -> bend allowance "
                 f"{spec.bend_allowance:.3f} mm per 90 deg bend")
    lines.append("                CHECK THIS AGAINST YOUR OWN: bend allowance is")
    lines.append("                shop-specific and every flat dimension depends on it.")
    lines.append(f"  {len(flat.bends)} bends, all 90 deg:")
    for bend in flat.bends:
        lines.append(f"    {bend.name:<12} {bend.direction:<8} at {bend.position:6.2f} mm "
                     f"on the blank")
    lines.append(f"  Bend relief   {spec.bend_relief_w:.1f} mm at each bend end")
    lines.append("")
    lines.append("  DFM, rule against actual:")
    lines.append(f"    bend radius       1-2 x t          {spec.bend_r / spec.sheet_t:.1f} x t")
    lines.append(f"    min flange        R + 4t = {spec.min_flange:.1f}     "
                 f"{flat.shortest_flange:.1f} mm")
    lines.append(f"    hole to bend      4t = {spec.min_feature_to_bend:.1f}         "
                 f"{spec.wing_hole_from_bend:.2f} mm")
    lines.append(f"    hole to edge      2t = {spec.min_edge_dist:.1f}         "
                 f"{spec.wing_hole_from_tip:.2f} mm")
    lines.append("  The M2 holes are punched flat, so the wing flange is sized to")
    lines.append("  hold them clear of the fold rather than to suit the screw.")

    lines.append(_rule("Faceplate: tooling"))
    fine_work = ["apertures"] if spec.apertures else []
    fine_work.append("retention tabs")
    lines.append(f"  Roughing      {spec.tool_d:.1f} mm end mill  (outline, rear relief)")
    lines.append(f"  Finishing     {spec.fine_tool_d:.1f} mm end mill  ({', '.join(fine_work)})")

    lines.append(_rule("Fits"))
    lines.append(f"  Board to wall        {spec.side_clear:.2f} mm each side")
    lines.append(f"  Board above floor    {spec.standoff_h:.2f} mm on the standoffs")
    lines.append(f"  Board to tab         {spec.slot_clear:.2f} mm above")
    lines.append(f"  Board to back wall   {spec.end_clear:.2f} mm")

    lines.append(_rule("Fasteners"))
    lines.append(f"  2 off  M2 x 0.4 countersunk, {spec.screw_len:.0f} mm minimum length")
    lines.append(f"  Sled wings   {spec.screw_clear_d:.1f} clearance, {spec.csk_d:.1f} csk at {spec.csk_angle:.0f} deg included")
    lines.append(f"  Faceplate    tap M2 x 0.4, {spec.thread_depth:.1f} deep blind")
    lines.append(f"               modelled at {spec.tap_drill_d:.1f} tap drill; do not read thread from the STEP")
    for x, z in spec.wing_hole_xz:
        lines.append(f"               at X {x:+.2f}, Z {z:+.2f}")
    lines.append("")
    lines.append(f"  {len(spec.body_mount_xz)} off  M3 x 0.5 countersunk, into threaded inserts in the body")
    lines.append(f"  Faceplate    {spec.body_screw_clear_d:.1f} clearance,"
                 f" {spec.body_csk_d:.1f} csk at {spec.csk_angle:.0f} deg included,"
                 " opening on the outer face")
    for x, z in spec.body_mount_xz:
        lines.append(f"               at X {x:+.2f}, Z {z:+.2f}")
    lines.append("               driven from outside, after the module is in")

    lines.append(_rule("Assembly"))
    lines.append("  1. Stick the standoffs to the tray floor, then screw the board down.")
    lines.append("  2. Screw the faceplate to the tray's wing flanges from behind; the")
    lines.append("     retention tabs drop between the walls and register the two parts.")
    lines.append("  3. Insert the whole module through the aperture from outside.")
    lines.append("  4. Fix the faceplate to the body.")

    lines.append(_rule("Keep-outs on the PCB"))
    lines.append(f"  Top side     {spec.top_clear:.1f} mm clear above the board")
    lines.append(
        f"  Front corners  no tall parts within {spec.lip_overhang:.1f} mm of each side edge"
        f" over the first {spec.lip_h:.1f} mm -- the retention tabs land there"
    )
    lines.append(f"  Bottom side  {spec.standoff_h:.1f} mm clear, the standoff height")
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
