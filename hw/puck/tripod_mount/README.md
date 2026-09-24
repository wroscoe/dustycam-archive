# Universal glue-on 1/4-20 tripod pad

A deliberately simple, one-piece adapter to glue onto the flat face of either
the PowerPuc or camera puck. The adapter accepts a 1/4-20 heat-set insert so
the puck can mount to standard tripod hardware.

## CAD brief

- Model: one monolithic printable tripod adapter, in millimetres.
- Origin/datum: centered in XY on the glue face; glue face is `z=0`; tripod
  side is `+Z`.
- Pad: 40 × 32 × 3 mm, outside corner radius 4 mm.
- Boss: centered, Ø16 mm, from `z=3` to `z=14.5` (11.5 mm proud of the pad).
- Insert pocket: centered blind Ø8 × 13.5 mm bore from the tripod side to
  `z=1`, preserving a 1.0 mm glue-side floor.
- Outputs: `universal_tripod_pad.step` plus `export/universal_tripod_pad.stl`
  and `export/universal_tripod_pad.3mf`, all generated from
  `universal_tripod_pad.py`.

The 40 × 32 mm bonding pad fits inside the documented common minimum
47.21 × 80.80 mm plain puck-face envelope when centered, leaving 3.605 mm
margin on the 47.21 mm direction and 24.4 mm on the 80.80 mm direction.

## Assembly

1. Print one pad and install a Ruthex RX-1/4-20 heat-set insert from the boss
   (tripod) side into the Ø8 mm blind pocket.
2. Lightly roughen the puck face and glue face, then clean both.
3. Center the pad on the selected flat puck face and bond with an adhesive
   suitable for the puck material; allow it to fully cure before loading.
4. Thread the tripod screw into the installed insert.

The puck face supports and locates the part; the adhesive retains it. Adhesive
strength, surface material, and applied load have not been physically tested.

## Print

Print with the glue face down and the boss upward. This orientation requires
no supports. PETG is a reasonable first prototype material; use a suitable
material and adhesive for the actual environmental and load conditions.

## Build and verify

From the repository root:

```sh
/home/wroscoe/.agents/skills/cad/.venv/bin/python \
  /home/wroscoe/.agents/skills/cad/scripts/step \
  hardware/tripod_mount/universal_tripod_pad.py \
  --stl export/universal_tripod_pad.stl \
  --3mf export/universal_tripod_pad.3mf
/home/wroscoe/.agents/skills/cad/.venv/bin/python \
  hardware/tripod_mount/verify.py
```

`verify.py` fails closed on generation exceptions, non-finite values, invalid
or split solids, named dimensions, overall bounds, pocket clearance/floor, and
the assumed puck-face margins.

## Assumptions and completion level

- The named insert is Ruthex RX-1/4-20; Ø8 × 13.5 mm is the approved
  first-pass pocket envelope, not a measured insert fit.
- The common minimum flat-face envelope is taken from the existing PowerPuc
  and camera-puck parametric sources: 47.21 × 80.80 mm.
- This is **geometry builds** level: the CAD checks geometry only. Print and
  pull/load-test the adhesive joint and verify insert fit before relying on it.
