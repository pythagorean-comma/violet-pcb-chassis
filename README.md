# violet-pcb-chassis

A parametric [CadQuery](https://cadquery.readthedocs.io) model for a two-part aluminium chassis
that carries a PCB into the edge of a musical instrument body and back out again for service,
without dismantling the instrument.

Both parts are cut from 5052 sheet: it emits a flat DXF for each, plus STEP models of the folded
and assembled result.

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="docs/exploded-dark.svg">
  <img alt="Exploded view: tray, PCB, faceplate" src="docs/exploded-light.svg" width="100%">
</picture>

## What it is

Two parts made two different ways, plus the board they carry:

- **Tray**: folded from 1.0 mm 5052-H32 sheet. A flat floor, two side walls, a back wall with a
  cable notch, and a flange at the front of each side wall. Five bends. The board sits on nylon
  standoffs with adhesive bases, which is what keeps its solder joints off the metal.
- **Faceplate**: 2.0 mm 5052 sheet. Cut flat and left that way: no bends, no machining, no
  threads. An outline, the connector apertures and two holes.

**One screw per side does everything.** It passes through the faceplate, through the tray's wing
flange, and into a threaded insert in the instrument, clamping all three together. There is no
separate tray-to-plate fastening, nothing is tapped in either part, and the whole chassis takes
two screws.

That has a consequence worth more than the fastener saving: **the wings never enter the
aperture**. Clamped outside it, they stop the tray falling through and locate it against the
instrument's face, so the hole only has to admit the tray body. It is 20 mm narrower than it
would otherwise be.

They go together like this:

1. Stick the standoffs to the tray floor, then screw the board down.
2. Offer the tray into the aperture; its wings stop it passing through.
3. Place the faceplate over the wings.
4. Two screws through plate, wing and insert hold all three together.

Note that the tray and plate are not joined until the last step, so there is no pre-assembled
module to offer up as one piece. The build prints the aperture size to rout.

**5052 rather than 6061 for the tray**: 6061-T6 cracks at tight bend radii and wants an inside
radius of three to four times material thickness. 5052-H32 folds happily at about one.

The report prints each forming rule next to what the design actually achieves, and separates
the ones that come from a published guide from the ones we chose. Taken from
[PCBWay's sheet-metal bending guide](https://www.pcbway.com/blog/PCB_Design_Layout/Sheet_Metal_Bending_Design_Guide_DFM_Rules_Bend_Radius_Bend_Allowance_and_Ma_cd445f27.html):
minimum flange of bend radius plus 4t, holes 4t clear of any bend, and an inside bend radius of
1 to 2 times thickness for 5052. Our own defaults, not from any published rule: the K-factor,
the bend relief width, and holes 2t clear of a sheared edge, measured against each part's own
gauge rather than a single figure (the tray is 1 mm, so 2 mm; the faceplate is 2 mm, so 4 mm,
and the plate's width is sized to whichever of that and the screw-head clearance is
larger). Any of those three is worth
confirming with whoever cuts the parts, and the K-factor most of all, since every dimension on
the flat blank depends on it.

The wing flanges are sized by that hole-to-bend rule rather than by the M3 screw, because the
holes are punched while the sheet is flat and forming would pull them oval otherwise. Drilling
after the folds would remove that constraint and take about 5 mm off the faceplate's width, at
the cost of an extra operation.

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
| `build.py --list` | The defined variants and the build steps for each part |
| `build.py --spec cycfi` | One variant only |
| `build.py --spec cycfi --stage 2` | The tray part-way through its pipeline, to eyeball a single feature |
| `build.py --docs` | Regenerate the README image above. Not part of a normal build |

## What gets built

Per variant, in `out/`:

| File | What it is |
| --- | --- |
| `tray_flat_<name>.dxf` | **The flat blank**, outline on a `CUT` layer and bend lines on a `BEND` layer. For a folded part this is the file the shop cuts from |
| `tray_flat_<name>.svg` | The same blank rendered back out of that DXF, drawn 1:1 with the bends labelled, so you can look at it or print it and check |
| `plate_flat_<name>.dxf` / `.svg` | The faceplate's blank, which is flat to begin with, in the same pair of formats |
| `sled_<name>.step` | The tray in its folded form |
| `faceplate_<name>.step` | The plate as a solid, for checking the fit |
| `assembly_<name>.step` | Both parts and the board, fitted (separate named, coloured components) |
| `exploded_<name>.step` | The same, drawn apart in assembly order |
| `section_<name>.svg` | A slice through a standoff row, showing the gap under the board |
| `*.svg` | An isometric preview of each of the above |

## Configuring for your own board

Everything comes from a `ChassisSpec` in [`params.py`](params.py). `SPECS` maps a variant name
to one spec, and the build emits every entry; a second chassis for a different board is
therefore a second dictionary entry, not a second copy of the code.

Only the board's own numbers normally need touching:

| Field | Meaning |
| --- | --- |
| `pcb_w`, `pcb_depth`, `pcb_t`, `pcb_corner_r` | Board outline, thickness and corner radius |
| `top_clear` | Tallest component above the board |
| `board_holes` | The board's own mounting holes, which become the standoff positions (`x` from its centreline, `y` from its front edge) |
| `apertures` | Connector and control cut-outs, in the same frame |

Everything else is derived. Tray width, wall heights, flange and screw locations, the flat
blank, the plate outline and the aperture to rout all follow from those fields, and the two
parts share one source for the interface between them, so they cannot disagree about where the
screws go.

The remaining fields are fits, sheet and forming parameters, fastener sizes and tool diameters,
all with defaults. Two are worth knowing about:

- **`k_factor`** decides bend allowance, and so every dimension on the flat blank. It is
  shop-specific. The default of 0.38 is reasonable for 5052 at this radius, but confirm it with
  whoever is folding the part; the report prints it for exactly that reason.
- **`standoff_od`** interacts with `side_clear`. The standoffs have to bed on the genuinely flat
  part of the floor, which stops one bend radius short of each wall, so a larger standoff forces
  a wider tray. The validation says so explicitly, with the value to raise.

When you change the numbers, run:

```bash
.venv/bin/python build.py --check
```

It measures actual interference between the board (plus its component keep-out volumes) and
both parts, rather than trusting the arithmetic. It also checks that every standoff beds on flat
floor rather than lapping onto a bend, that the module fits its own reported aperture, and that
each part survived as a single solid. Finally, it flags cut-outs that would land on a folded
wall instead of the tray's opening, which is the mistake that quietly scraps a faceplate.

## Sources

The `cycfi` variant is built around the [Cycfi Nu Series](https://github.com/cycfi/nu) internal
breakout board. Its outline (50 x 35 mm), 1.5 mm corner radius, mounting holes and part
placement were taken from the Eagle layout at
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

`rmc` uses the real board outline (77.2 x 82.4 mm), and that is the only measured number in it.
Its `pcb_t`, `pcb_corner_r` (left square), `top_clear`, aperture list and standoff pattern are
all still **placeholder** and must be replaced before cutting metal. The standoffs are inset
2.5 mm from the outline's corners so the pattern is plausibly shaped, but it is not where this
board's mounting holes are. `--check` will not object: a standoff anywhere on the board and
clear of the wall's bend radius is legal, so a hole in the wrong place validates exactly like
one in the right place.

Two things about the tray model are worth knowing when reading the STEP. Where the side walls
meet the back wall it runs material continuously round the corner, whereas the real part has a
bend relief there; the relief is in the flat pattern, which is what gets cut. And the flat
blank's area comes out about 4% under the folded solid's volume for exactly that reason, which
`--check` allows for deliberately rather than by loosening a tolerance until it passed.

The Cycfi board carries four M2 mounting holes inset 2.5 mm from its corners, currently unused
because the sled captures the board mechanically.

Fixing the plate to the instrument assumes **M3 threaded inserts** fitted into the body either
side of the aperture. The report prints where they go. Inserts rather than wood screws means the
plate can come off and back on repeatedly without chewing the timber, at the cost of fitting them
before first assembly.
