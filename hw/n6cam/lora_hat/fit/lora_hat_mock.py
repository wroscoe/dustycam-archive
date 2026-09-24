"""N6 LoRa hat -- build123d envelope for the camera_puck fitcheck (BUILD.md
Phase 5). NOT a printable/fabricated artifact: it is the mechanical
occurrence appended to `camera_puck/fitcheck.step.py::reference_parts()` so
`check.py`'s interference sweep and slide-in check include the hat.

Frame: identical to `camera_puck/ref/openmv-n6.py` -- origin at the N6 PCB
bottom-left corner on the PCB bottom face, +X across, +Y toward the lens,
+Z along the optical axis, ZT = 1.30 = PCB top. The hat's own PCB outline
(`index.circuit.tsx`, Option A) is literally in this frame already, so its
STEP export needs no re-basing in X/Y -- only a Z lift.

Z stack (PLAN.md section 3): N6 female header top at ZT + 8.50 = 9.80; male
header insulator (2.54) -> hat PCB 12.34 .. 13.94; E22 module -> 16.94;
u.FL + plug + cable -> ~19.5 (front-cup ceiling 23.50, ~3.5 mm to spare).
"""

from pathlib import Path

from build123d import Align, Axis, Box, Compound, Cylinder, Pos, import_step

HERE = Path(__file__).resolve().parent
STEP_PATH = HERE.parent / "dist" / "lora_hat.step"

Z_LIFT = 13.14  # hat PCB midplane in the N6 frame (board is +-0.8 mm thick)

# Literal N6 header hole coordinates (BUILD.md / PLAN.md section 3).
HDR_X = [1.600, 4.140, 31.460, 34.000]
HDR_Y0 = 1.599
HDR_PITCH = 2.54
HDR_ROWS = 8

# Male header body envelopes (2 x 2x8, 2.54 mm), insulator z 9.80..12.34.
HDR_BLOCKS_X = [(0.33, 5.41), (30.19, 35.27)]
HDR_Y_SPAN = (0.33, 20.65)
HDR_Z = (9.80, 12.34)

# Pin tips poking up through the hat PCB into the module airspace.
PIN_TIP_Z = (13.94, 16.94)
PIN_TIP_SIDE = 0.64

# E22-900M22S module envelope (index.circuit.tsx: U2 at (18.30, 7.00)).
MODULE_X = (11.3, 25.3)
MODULE_Y = (-2.5, 17.5)
MODULE_Z = (13.94, 16.94)

# u.FL jack + mating plug + cable run to the -Y overhang edge.
# J4 center (index.circuit.tsx, real C88373 land -> BUILD.md deviation):
# (6.80, -0.229), was BUILD.md's literal (6.35, -0.23).
UFL_XY = (6.80, -0.229)
UFL_PLUG_D = 3.0
UFL_Z = (13.94, 19.5)
CABLE_SIDE = 1.2
CABLE_Z = (18.0, 19.5)
Y_MIN = -7.5  # hat -Y overhang edge (index.circuit.tsx)


def _box(x0, y0, z0, x1, y1, z1):
    return Pos((x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2) * Box(
        x1 - x0, y1 - y0, z1 - z0, align=(Align.CENTER,) * 3
    )


def hat_parts():
    """One fused solid, labelled `lora_hat`: the real PCB (imported STEP,
    largest solid only) + explicit envelope boxes for the male header pins,
    the E22 module, and the u.FL jack/plug/cable run."""
    imported = import_step(str(STEP_PATH))
    solids = imported.solids()
    pcb = max(solids, key=lambda s: s.volume)
    pcb = Pos(0, 0, Z_LIFT) * pcb

    bb = pcb.bounding_box()
    expect = {
        "x": (-0.30, 35.70),
        "y": (Y_MIN, 21.0),
        "z": (12.34, 13.94),
    }
    for axis, (lo, hi) in expect.items():
        got_lo = getattr(bb.min, axis.upper())
        got_hi = getattr(bb.max, axis.upper())
        if abs(got_lo - lo) > 0.01 or abs(got_hi - hi) > 0.01:
            raise AssertionError(
                f"lora_hat.step {axis} bbox {got_lo:.4f}..{got_hi:.4f} "
                f"!= expected {lo:.2f}..{hi:.2f} (Option A frame check)"
            )

    parts = [pcb]

    # Male header bodies (both 2x8 blocks), insulator z 9.80..12.34.
    for x0, x1 in HDR_BLOCKS_X:
        parts.append(_box(x0, HDR_Y_SPAN[0], HDR_Z[0], x1, HDR_Y_SPAN[1], HDR_Z[1]))

    # 32 pin tips, 0.64 mm square, z 13.94..16.94.
    half = PIN_TIP_SIDE / 2
    for x in HDR_X:
        for n in range(HDR_ROWS):
            y = HDR_Y0 + HDR_PITCH * n
            parts.append(_box(x - half, y - half, PIN_TIP_Z[0], x + half, y + half, PIN_TIP_Z[1]))

    # E22-900M22S module envelope.
    parts.append(_box(MODULE_X[0], MODULE_Y[0], MODULE_Z[0], MODULE_X[1], MODULE_Y[1], MODULE_Z[1]))

    # u.FL jack + mating plug, cylindrical, z 13.94..19.5.
    ufl = Pos(UFL_XY[0], UFL_XY[1], (UFL_Z[0] + UFL_Z[1]) / 2) * Cylinder(
        radius=UFL_PLUG_D / 2, height=UFL_Z[1] - UFL_Z[0], align=(Align.CENTER, Align.CENTER, Align.CENTER)
    )
    parts.append(ufl)

    # Cable run from the u.FL out through the -Y overhang, z 18..19.5.
    cable_half = CABLE_SIDE / 2
    parts.append(
        _box(
            UFL_XY[0] - cable_half, Y_MIN, CABLE_Z[0],
            UFL_XY[0] + cable_half, UFL_XY[1], CABLE_Z[1],
        )
    )

    # The sub-boxes are Z-stacked mechanical zones that don't geometrically
    # overlap (header pins sit below the module, which sits below the u.FL
    # run), so a boolean union can't reduce them to one topological solid.
    # Explicitly build a Compound with every child already baked to its
    # absolute position (sarg: "build123d Compound intersect ignores
    # Location on a moved Compound" -- baking per-solid, not moving the
    # assembled Compound, is what keeps check.py's intersect() correct).
    fused = Compound(children=parts)
    fused.label = "lora_hat"
    return fused


if __name__ == "__main__":
    hp = hat_parts()
    print(hp.label, "solids:", len(hp.solids()), "bbox:", hp.bounding_box())
