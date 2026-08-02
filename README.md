# violet-pcb-chassis

A parametric [CadQuery](https://cadquery.readthedocs.io) model for a two-part machined
aluminium chassis that lets a PCB slide into the edge of a musical instrument body and come
back out for service without dismantling the instrument.

It emits CNC-ready STEP files for fabrication from 6061 stock.

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="docs/exploded-dark.svg">
  <img alt="Exploded view: sled, PCB, faceplate" src="docs/exploded-light.svg" width="100%">
</picture>

## What it is

Two machined parts, plus the board they carry:

- **Sled**: a U-section carrier. The board slides in along a stepped pocket and rests on a
  ledge down each side, with clearance underneath for solder tails and bottom-side parts.
- **Faceplate**: closes the aperture from outside. Two tabs on its rear face reach in over the
  board's side margins and hold its front edge down on the ledges.

They go together like this:

1. Slide the PCB into the sled channel until it meets the back wall.
2. Screw the faceplate to the sled's wings from behind, on the bench.
3. Insert the whole module through the aperture from outside.
4. Fix the faceplate to the instrument body.

Because the module is assembled first and inserted as one piece, the entire sled envelope has
to pass through the routed aperture; the wings are therefore local bosses inside that envelope,
not tabs overhanging it. The build prints the aperture size to rout.

## Quick start

```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
```

```bash
.venv/bin/python build.py
```

That checks the clearances, writes every part and preview to `out/`, and prints a
manufacturing report per variant: stock sizes, the aperture to rout, tooling, fastener
callouts and the PCB keep-outs.

Other things it does:

```bash
.venv/bin/python build.py --check
```

| Command | What it does |
| --- | --- |
| `build.py` | Everything: checks, exports, reports |
| `build.py --check` | Clearance checks only, no files written. Exit code 1 on failure |
| `build.py --list` | The defined variants and the machining steps for each part |
| `build.py --spec cycfi` | One variant only |
| `build.py --spec cycfi --stage 4` | The sled part-way through its pipeline, to eyeball a single operation |
| `build.py --docs` | Regenerate the README image above. Not part of a normal build |

## What gets built

Per variant, in `out/`:

| File | What it is |
| --- | --- |
| `sled_<name>.step` | The carrier, for machining |
| `faceplate_<name>.step` | The plate, for machining |
| `assembly_<name>.step` | Both parts and the board, fitted (separate named, coloured components) |
| `exploded_<name>.step` | The same, drawn apart in assembly order |
| `section_<name>.svg` | A slice through the channel showing the board on its ledges |
| `*.svg` | An isometric preview of each of the above |

## Configuring for your own board

Everything comes from a `ChassisSpec` in [`params.py`](params.py). `SPECS` maps a variant name
to one spec, and the build emits every entry; a second chassis for a different board is
therefore a second dictionary entry, not a second copy of the code.

Only the board's own numbers normally need touching:

| Field | Meaning |
| --- | --- |
| `pcb_w`, `pcb_depth`, `pcb_t` | Board outline and thickness |
| `top_clear`, `bot_clear` | Tallest component above and below the board |
| `apertures` | Connector and control cut-outs, positioned in the board's own frame (`x` from its centreline, `z` from its underside) |

Everything else is derived. Channel widths, ledge positions, wing and screw locations, plate
outline, stock sizes and the aperture to rout all follow from those fields, and the two parts
share one source for the interface between them, so they cannot disagree about where the screws
go.

The remaining fields are fits, wall thicknesses, fastener sizes and tool diameters, all with
defaults. Changing `tool_d` or `fine_tool_d` re-radiuses every internal corner in both parts.

When you change the numbers, run:

```bash
.venv/bin/python build.py --check
```

It measures actual interference between the board (plus its component keep-out volumes) and
both machined parts, rather than trusting the arithmetic. It also checks that the board has
enough ledge to sit on, that the module fits its own reported aperture, and that each part
survived as a single solid. Finally, it flags cut-outs that would land on the sled's front face
instead of the channel, which is the mistake that quietly scraps a faceplate.

## Sources

The `cycfi` variant is built around the [Cycfi Nu Series](https://github.com/cycfi/nu) internal
breakout board. Its outline (50 x 35 mm), 1.5 mm corner radius and part placement were taken
from the Eagle layout at
[`internal_breakout.brd`](https://github.com/cycfi/nu/blob/dc334a32f05f/internal_breakout/internal_breakout.brd),
pinned at commit `dc334a32f05f`.

That work is by Cycfi Research and licensed
[CC BY-NC 4.0](http://creativecommons.org/licenses/by-nc/4.0/). None of it is redistributed
here; only dimensions were measured from it.

## Status

`cycfi` uses the real board outline. Two of its numbers are still assumptions: `pcb_t` (1.6 mm
standard stackup, since board thickness is a fabrication parameter and does not appear in a
layout file) and `top_clear` (15 mm, chosen to clear the 0.1 inch headers with mating sockets
and some strain relief, not measured off an assembled board).

`rmc` is still entirely **placeholder**: plausible numbers standing in until that board is
measured. Replace them before cutting metal.

`body_mount_holes` is empty on both, so nothing yet fixes the faceplate to the instrument body.
It is a data field, so adding those holes is an edit to the spec rather than to any code. The
Cycfi board also carries four M2 mounting holes inset 2.5 mm from its corners, currently unused
because the sled captures the board mechanically.
