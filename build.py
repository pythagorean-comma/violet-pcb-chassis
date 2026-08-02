#!/usr/bin/env python3
"""Build the Violet chassis parts.

    python build.py                        both variants: STEP, SVG, report
    python build.py --spec cycfi           just the one
    python build.py --spec cycfi --stage 4 the sled part-way through, to eyeball
    python build.py --check                clearance checks only, no export
    python build.py --list                 what is defined, and the steps
    python build.py --docs                 regenerate the committed README image
"""

import argparse
import sys

from assembly import build_assembly
from exporters import (
    DOC_THEMES,
    export_assembly_step,
    export_doc_svg,
    export_flat_dxf,
    export_flat_svg,
    export_section_preview,
    export_step_file,
    export_svg_preview,
)
from flatten import flat_pattern, plate_pattern
from faceplate import PIPELINE as PLATE_PIPELINE, build_faceplate
from mock import build_channel_section, check_clearance
from params import SPECS, ChassisSpec
from report import manufacturing_report
from sled import PIPELINE as SLED_PIPELINE, build_sled


def export_parts(spec: ChassisSpec) -> None:
    """Write the machined parts, the assemblies, and previews of all of them."""
    for label, part in (
        (f"sled_{spec.name}", build_sled(spec)),
        (f"faceplate_{spec.name}", build_faceplate(spec)),
    ):
        export_step_file(part, label)
        export_svg_preview(part, label)

    # For a folded part the flat blank is the file the shop actually cuts. The
    # SVG is rendered from the DXF just written, so it shows what they receive.
    for label, pattern in (
        (f"tray_flat_{spec.name}", flat_pattern(spec)),
        (f"plate_flat_{spec.name}", plate_pattern(spec)),
    ):
        export_flat_dxf(pattern, label)
        export_flat_svg(pattern, label)

    for label, exploded in ((f"assembly_{spec.name}", False), (f"exploded_{spec.name}", True)):
        assembly = build_assembly(spec, exploded=exploded)
        export_assembly_step(assembly, label)
        # toCompound() gives the existing preview exporter a shape it can take.
        export_svg_preview(assembly.toCompound(), label)

    export_section_preview(build_channel_section(spec), f"section_{spec.name}")


def export_docs(spec: ChassisSpec) -> None:
    """Write the README's hero image, in both colour themes.

    Kept out of `export_parts` on purpose. docs/ is committed, so regenerating it
    has to be a deliberate act -- otherwise every ordinary build dirties the
    working tree and the asset churns on every commit.
    """
    exploded = build_assembly(spec, exploded=True).toCompound()
    for theme in DOC_THEMES:
        export_doc_svg(exploded, "exploded", theme)


def export_stage(spec: ChassisSpec, stage: int) -> None:
    """Write the sled as it stands after ``stage`` operations."""
    if not 0 <= stage <= len(SLED_PIPELINE):
        raise SystemExit(f"--stage must be 0..{len(SLED_PIPELINE)}")
    step_name = "blank" if stage == 0 else SLED_PIPELINE[stage - 1].__name__
    label = f"sled_{spec.name}_{stage:02d}_{step_name}"
    part = build_sled(spec, upto=stage)
    export_step_file(part, label)
    export_svg_preview(part, label)


def list_specs() -> None:
    print("Specs:")
    for name, spec in SPECS.items():
        print(f"  {name:<12} PCB {spec.pcb_w} x {spec.pcb_depth} x {spec.pcb_t} mm")
    print("\nSled pipeline (--stage N runs the first N):")
    for i, step in enumerate(SLED_PIPELINE, start=1):
        print(f"  {i}  {step.__name__}")
    print("\nFaceplate pipeline:")
    for i, step in enumerate(PLATE_PIPELINE, start=1):
        print(f"  {i}  {step.__name__}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--spec", choices=sorted(SPECS), help="build one variant only")
    parser.add_argument("--stage", type=int, help="export the sled after N operations")
    parser.add_argument("--check", action="store_true", help="clearance checks only")
    parser.add_argument("--list", action="store_true", help="show specs and pipelines")
    parser.add_argument(
        "--docs", action="store_true", help="regenerate the committed README image"
    )
    args = parser.parse_args()

    if args.list:
        list_specs()
        return 0

    specs = [SPECS[args.spec]] if args.spec else list(SPECS.values())

    if args.docs:
        export_docs(specs[0])
        return 0

    if args.stage is not None:
        if not args.spec:
            raise SystemExit("--stage needs --spec")
        export_stage(specs[0], args.stage)
        return 0

    failed = False
    for spec in specs:
        problems = check_clearance(spec)
        if problems:
            failed = True
            print(f"\n{spec.name}: FAILED", file=sys.stderr)
            for problem in problems:
                print(f"  ! {problem}", file=sys.stderr)
        else:
            print(f"{spec.name}: clearances OK")

        if not args.check:
            export_parts(spec)
            print(manufacturing_report(spec))

    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
