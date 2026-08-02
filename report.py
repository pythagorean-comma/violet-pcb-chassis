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
    from flatten import flat_pattern, plate_pattern

    ap_w, ap_h = spec.aperture_required
    flat = flat_pattern(spec)
    plate = plate_pattern(spec)

    lines = [
        f"\n{'=' * 68}",
        f"  {spec.name}  -  PCB {spec.pcb_w} x {spec.pcb_depth} x {spec.pcb_t} mm",
        f"{'=' * 68}",
        f"  Two sheet parts, both {spec.material}:",
        f"    Tray       {spec.sheet_t:.1f} mm, laser cut then folded",
        f"    Faceplate  {spec.plate_t:.1f} mm, laser cut only",
        "  Nothing is machined and nothing is tapped.",
    ]

    lines.append(_rule("Stock"))
    lines.append(f"  Tray blank   {flat.width:.1f} x {flat.height:.1f} mm of "
                 f"{spec.sheet_t:.1f} mm  (see the DXF)")
    lines.append(f"  Plate blank  {plate.width:.1f} x {plate.height:.1f} mm of "
                 f"{spec.plate_t:.1f} mm  (see the DXF)")

    lines.append(_rule("Instrument preparation"))
    lines.append(f"  Rout the edge aperture  {ap_w:.1f} wide x {ap_h:.1f} high")
    lines.append(f"  Depth into the body     {spec.sled_depth:.1f} mm minimum")
    lines.append("  Only the tray body enters the hole. Its wings stay outside,")
    lines.append("  clamped between the faceplate and the instrument's face.")
    lines.append(f"  Faceplate covers it by  "
                 f"{(spec.plate_w - ap_w) / 2:.1f} mm each side,"
                 f" {spec.plate_margin_z:.1f} mm top and bottom")
    lines.append(f"  Fit M3 threaded inserts at X {spec.fixing_xz[0][0]:+.2f}"
                 f" and {spec.fixing_xz[1][0]:+.2f}, on the aperture's centreline")

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

    lines.append(_rule("Fits"))
    lines.append(f"  Board to wall        {spec.side_clear:.2f} mm each side")
    lines.append(f"  Board above floor    {spec.standoff_h:.2f} mm on the standoffs")
    lines.append(f"  Board to back wall   {spec.end_clear:.2f} mm")
    lines.append(f"  Plate off the body   {spec.sheet_t:.2f} mm, the wing sitting under it")

    lines.append(_rule("Fasteners"))
    lines.append(f"  2 off  M3 x 0.5 pan or button head, {spec.screw_len:.0f} mm minimum")
    lines.append("  One screw does the whole job at each side: through the")
    lines.append("  faceplate, through the tray's wing, into an insert in the body.")
    lines.append(f"  Both parts    {spec.body_screw_clear_d:.1f} mm clearance, no countersink")
    for x, z in spec.fixing_xz:
        lines.append(f"                at X {x:+.2f}, Z {z:+.2f}")
    lines.append("  Nothing is tapped in either part.")
    lines.append("")
    lines.append(f"  4 off  M2, board down onto the standoffs "
                 f"({spec.board_hole_d:.1f} mm clearance in the board)")

    lines.append(_rule("Assembly"))
    lines.append("  1. Stick the standoffs to the tray floor, then screw the board down.")
    lines.append("  2. Offer the tray into the aperture from outside; its wings stop it")
    lines.append("     passing through and locate it against the instrument's face.")
    lines.append("  3. Place the faceplate over the wings.")
    lines.append("  4. Two screws through plate, wing and insert hold all three together.")
    lines.append("")
    lines.append("  Note the tray and plate are not joined until step 4, so there is no")
    lines.append("  pre-assembled module to offer up as one piece.")

    lines.append(_rule("Keep-outs on the PCB"))
    lines.append(f"  Top side     {spec.top_clear:.1f} mm clear above the board")
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
