# n20_worm_v8 geometric validation

| check | result |
|---|---|
| worm lead = pi*module | PASS |
| 24:1 single-start ratio | PASS |
| pitch centre distance = 20 | PASS |
| continuous cable bore >= 7 mm | PASS |
| N20 shaft is 3 mm D-flat | PASS |
| DRV header keepout included | PASS |
| tube interface is 50.8 mm | PASS |
| usable sweep +/-90 inside +/-95 stops | PASS |
| platform clears tube ID | PASS |
| rotor platform fits deck opening | PASS |
| journal head fits rotor bore and retains top clip | PASS |
| separate stop-arm keyed attachment datum is registered | PASS |
| stop arm C-mouth clears Ø19 sleeve for lateral installation | PASS |
| rotor lower sleeve remains within wheel bore | PASS |
| wheel face spans worm axis | PASS |
| true swept worm crest >= 0.45 mm | PASS |
| coupon wheel shoulder exceeds bore radius | PASS |
| coupon wheel pilot clears bore and reaches >= 7 mm | PASS |
| coupon worm journal radial clearance <= 0.15 mm | PASS |
| all printable parts are one valid solid | PASS |
| zero-pose unintended intersections <= 0.01 mm3 | PASS |
| DRV nominally clears retention tabs | PASS |
| DRV tabs arrest 0.25 mm upward service lift | PASS |
| sampled collar/finger insertion routes clear base and rotor | PASS |
| 5-pose structural sweep <= 0.01 mm3 | PASS |
| 9-phase coupled mesh has no penetration | PASS |
| 9-phase coupled mesh stays within proximity envelope | PASS |
| coupon fixture clears normal worm | PASS |
| coupon fixture clears normal wheel | PASS |

- Worm-to-wheel response: -15.0 degrees platform pan per positive worm revolution.
- Mesh status: PROTOTYPE: radial trapezoid wheel; run printed mesh_coupon before use
- Coupled mesh proximity gap across one wheel-tooth pitch: 0.624..0.649 mm; this is not a torque-transfer claim.
- Coupon fixture intersections (worm/wheel): 0.000000 / 0.000000 mm3.
- DRV retainer vs nominal/lifted (+0.25 mm) envelope: 0.000000 / 9.520000 mm3.
- Fixed stops are at ±95°; the structural collision sweep samples the usable ±90° range in 45° steps.

## Zero-pose pair intersections

| pair | intersection mm3 |
|---|---:|
| base/lid | 0.000000 |
| base/tube | 0.000000 |
| base/worm | 0.000000 |
| base/N20 | 0.000000 |
| base/DRV8833 | 0.000000 |
| base/motor retainer | 0.000000 |
| base/DRV retainer | 0.000000 |
| base/rotor axial clip | 0.000000 |
| base/wheel | 0.000000 |
| base/wheel axial clip | 0.000000 |
| base/rotor | 0.000000 |
| base/bottom stop collar | 0.000000 |
| base/bottom stop finger | 0.000000 |
| base/bottom stop arm clip | 0.000000 |
| rotor/N20 | 0.000000 |
| wheel/rotor | 0.000000 |
| wheel/wheel axial clip | 0.000000 |
| wheel clip/bottom stop collar | 0.000000 |
| rotor/bottom stop collar | 0.000000 |
| rotor/bottom stop finger | 0.000000 |
| rotor/bottom stop arm clip | 0.000000 |
| bottom stop collar/finger | 0.000000 |
| bottom stop collar/clip | 0.000000 |
| bottom stop finger/clip | 0.000000 |
| rotor/rotor axial clip | 0.000000 |
| motor retainer/N20 | 0.000000 |
| DRV retainer/DRV | 0.000000 |
| rotor/holder | 0.000000 |
| holder/top latch | 0.000000 |
| top latch/camera | 0.000000 |
| holder/camera | 0.000000 |

## Sampled bottom-service insertion routes

| waypoint | base intersection mm3 | rotor intersection mm3 | installed collar intersection mm3 |
|---|---:|---:|---:|
| collar route 00 | 0.000000 | 0.000000 | 0.000000 |
| collar route 01 | 0.000000 | 0.000000 | 0.000000 |
| collar route 02 | 0.000000 | 0.000000 | 0.000000 |
| collar route 03 | 0.000000 | 0.000000 | 0.000000 |
| collar route 04 | 0.000000 | 0.000000 | 0.000000 |
| collar route 05 | 0.000000 | 0.000000 | 0.000000 |
| collar route 06 | 0.000000 | 0.000000 | 0.000000 |
| collar route 07 | 0.000000 | 0.000000 | 0.000000 |
| collar route 08 | 0.000000 | 0.000000 | 0.000000 |
| collar route 09 | 0.000000 | 0.000000 | 0.000000 |
| collar route 10 | 0.000000 | 0.000000 | 0.000000 |
| collar route 11 | 0.000000 | 0.000000 | 0.000000 |
| collar route 12 | 0.000000 | 0.000000 | 0.000000 |
| collar route 13 | 0.000000 | 0.000000 | 0.000000 |
| collar route 14 | 0.000000 | 0.000000 | 0.000000 |
| collar route 15 | 0.000000 | 0.000000 | 0.000000 |
| collar route 16 | 0.000000 | 0.000000 | 0.000000 |
| collar route 17 | 0.000000 | 0.000000 | 0.000000 |
| collar route 18 | 0.000000 | 0.000000 | 0.000000 |
| collar route 19 | 0.000000 | 0.000000 | 0.000000 |
| collar route 20 | 0.000000 | 0.000000 | 0.000000 |
| collar route 21 | 0.000000 | 0.000000 | 0.000000 |
| collar route 22 | 0.000000 | 0.000000 | 0.000000 |
| collar route 23 | 0.000000 | 0.000000 | 0.000000 |
| collar route 24 | 0.000000 | 0.000000 | 0.000000 |
| collar route 25 | 0.000000 | 0.000000 | 0.000000 |
| collar route 26 | 0.000000 | 0.000000 | 0.000000 |
| collar route 27 | 0.000000 | 0.000000 | 0.000000 |
| collar route 28 | 0.000000 | 0.000000 | 0.000000 |
| collar route 29 | 0.000000 | 0.000000 | 0.000000 |
| collar route 30 | 0.000000 | 0.000000 | 0.000000 |
| collar route 31 | 0.000000 | 0.000000 | 0.000000 |
| collar route 32 | 0.000000 | 0.000000 | 0.000000 |
| collar route 33 | 0.000000 | 0.000000 | 0.000000 |
| collar route 34 | 0.000000 | 0.000000 | 0.000000 |
| collar route 35 | 0.000000 | 0.000000 | 0.000000 |
| collar route 36 | 0.000000 | 0.000000 | 0.000000 |
| collar route 37 | 0.000000 | 0.000000 | 0.000000 |
| collar route 38 | 0.000000 | 0.000000 | 0.000000 |
| finger route 00 | 0.000000 | 0.000000 | 0.000000 |
| finger route 01 | 0.000000 | 0.000000 | 0.000000 |
| finger route 02 | 0.000000 | 0.000000 | 0.000000 |
| finger route 03 | 0.000000 | 0.000000 | 0.000000 |
| finger route 04 | 0.000000 | 0.000000 | 0.000000 |
| finger route 05 | 0.000000 | 0.000000 | 0.000000 |
| finger route 06 | 0.000000 | 0.000000 | 0.000000 |
| finger route 07 | 0.000000 | 0.000000 | 0.000000 |
| finger route 08 | 0.000000 | 0.000000 | 0.000000 |
| finger route 09 | 0.000000 | 0.000000 | 0.000000 |
| finger route 10 | 0.000000 | 0.000000 | 0.000000 |
| finger route 11 | 0.000000 | 0.000000 | 0.000000 |
| finger route 12 | 0.000000 | 0.000000 | 0.000000 |
| finger route 13 | 0.000000 | 0.000000 | 0.000000 |

## Structural sweep

| pan deg | worst pair | intersection mm3 |
|---:|---|---:|
| -90 | none | 0.000000 |
| -45 | none | 0.000000 |
| +0 | none | 0.000000 |
| +45 | none | 0.000000 |
| +90 | none | 0.000000 |
