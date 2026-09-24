# xiao_pantilt interference sweep (cover: none)

backlash 0.15 mm, 130 poses, struct tolerance 1.0 mm^3, gear tolerance 0.5 mm^3, 128 s

## Static checks

| check | value | unit | ok |
|---|---|---|---|
| lens barrel Z vs tilt axis (design: -6.95) | -6.95 | mm | PASS |
| pan centre distance | 28.15 | mm | PASS |
| tilt centre distance | 26.15 | mm | PASS |
| moving envelope max radius | 46.0 | mm | FAIL |
| moving envelope top above cover seat | 34.5 | mm | PASS |
| tilt servo front face vs cradle sweep radius | 1.16 | mm | PASS |
| tilt servo bottom ear vs plate top (notch) | 0.5 | mm | PASS |
| pan pinion top vs ring underside | 4.5 | mm | PASS |
| pan pinion tip vs well wall | 1.55 | mm | PASS |
| pan servo travel | 156.0 | deg (<= 170) | PASS |
| tilt servo travel | 122.7 | deg (<= 170) | PASS |
| cable bore | 7.0 | mm | PASS |

## Result: PASS (0 failing pair-poses, 0 nonzero overlaps)

| pan | tilt | a | b | volume mm^3 | kind | ok |
|---|---|---|---|---|---|---|
| - | - | - | - | 0 | - | ok |
