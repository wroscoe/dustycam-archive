# tubecase checks
Overall: **PASS** (0 failing check(s))
## 1. Pairwise interference
Tolerance 1.0 mm^3. All pairs clean.

## 2. Static checks

| check | value | unit | ok |
|---|---|---|---|
| charger long edge to rib face | 1.125 | mm (>= 1.0) | PASS |
| charger components bottom vs battery swell top | 4.38 | mm (>= 2.0) | PASS |
| cradle max radius (no board) | 15.276 | mm (<= neck_id/2 - 0.5 = 19.950) | PASS |
| lens tip x vs tube inner wall | 4.0 | mm (>= 3.99) | PASS |
| cradle top vs cap plug underside | 5.97 | mm (>= 2.0) | PASS |
| SD-card top vs cap plug underside | 3.357 | mm (>= 2.0) | PASS |
| pin engagement into deck | 3.0 | mm (== pin_engage = 3.0) | PASS |
| pin to charger min XY clearance | 5.814 | mm (>= 1.0) | PASS |
| pin to battery envelope min XY clearance | 1.0 | mm (>= 1.0) | PASS |
| rib pilot inner wall | 3.15 | mm (>= 1.5) | PASS |
| deck disc top z | 23.5 | mm (== Z_DECK1 = 23.500) | PASS |
| deck max radius vs cone | 25.3 | mm (<= sleeve_id/2 - 0.15 = 25.350) | PASS |
| door ribs vs sleeve ribs | 0.5 | mm (>= 0.4) | PASS |
| lens height above seat | 19.0 | mm (== 19.0) | PASS |
| overall height (Z_CAP1) | 62.55 | mm | PASS |
| overall body diameter (sleeve_od) | 55.0 | mm | PASS |
| overall reach incl. jack flange (-X) | 44.5 | mm | PASS |
| overall reach incl. jack brow (-X) | 46.5 | mm | PASS |
| jack cavity clearance (y) | 2.0 | mm (>= 1.0) | PASS |
| jack cavity clearance (z) | 2.0 | mm (>= 1.0) | PASS |
| wire room, lug ends to sleeve bore | 4.0 | mm (>= 3.0) | PASS |
| jack lug ends to charger plugs | 8.5 | mm (>= 5.0) | PASS |
| rib bearing fill fraction | 99.5 | % (>= 90%) | PASS |

## 3. Bayonet install path

Rotation sweep (deck+charger about Z by -t, intersect with sleeve):

| t deg | dz mm | deck x sleeve | charger x sleeve | ok |
|---|---|---|---|---|
| 0 | - | 0.0000 | 0.0000 | ok |
| 2 | - | 0.0000 | 0.0000 | ok |
| 4 | - | 0.0000 | 0.0000 | ok |
| 6 | - | 0.0000 | 0.0000 | ok |
| 8 | - | 0.0000 | 0.0000 | ok |
| 10 | - | 0.0000 | 0.0000 | ok |
| 12 | - | 0.0000 | 0.0000 | ok |
| 14 | - | 0.0000 | 0.0000 | ok |
| 16 | - | 0.0000 | 0.0000 | ok |
| 18 | - | 0.0000 | 0.0000 | ok |
| 20 | - | 0.0000 | 0.0000 | ok |
| 20 | 0 | 0.0000 | 0.0000 | ok |
| 20 | 2 | 0.0000 | 0.0000 | ok |
| 20 | 4 | 0.0000 | 0.0000 | ok |
| 20 | 6 | 0.0000 | 0.0000 | ok |
| 20 | 8 | 0.0000 | 0.0000 | ok |
| 20 | 10 | 0.0000 | 0.0000 | ok |
| 20 | 12 | 0.0000 | 0.0000 | ok |
| 20 | 14 | 0.0000 | 0.0000 | ok |
| 20 | 16 | 0.0000 | 0.0000 | ok |
| 20 | 18 | 0.0000 | 0.0000 | ok |
| 20 | 20 | 0.0000 | 0.0000 | ok |
| 20 | 22 | 0.0000 | 0.0000 | ok |
| 20 | 24 | 0.0000 | 0.0000 | ok |

Door insertion sweep (door + pins, straight up, z -25..0):

| door z mm | x sleeve | x deck | x charger | ok |
|---|---|---|---|---|
| -25 | 0.0000 | 0.0000 | 0.0000 | ok |
| -20 | 0.0000 | 0.0000 | 0.0000 | ok |
| -15 | 0.0000 | 0.0000 | 0.0000 | ok |
| -10 | 0.0000 | 0.0000 | 0.0000 | ok |
| -5 | 0.0000 | 0.0000 | 0.0000 | ok |
| 0 | 0.0000 | 0.0000 | 0.0000 | ok |

## 4. Camera insertion

| lift mm | camera x deck mm^3 | ok |
|---|---|---|
| 5 | 0.0000 | ok |
| 25 | 0.0000 | ok |

