# xiao_pantilt interference sweep (v4 pan-only, tube)

backlash 0.15 mm, 13 poses, struct tolerance 1.0 mm^3, gear tolerance 0.5 mm^3, 32 s

## Static checks

| check | value | unit | ok |
|---|---|---|---|
| pan centre distance | 28.15 | mm | PASS |
| pod max radius | 16.85 | mm vs tube ID/2 22.25 | PASS |
| pod max radius vs ring opening | 2.65 | mm | PASS |
| pod top vs cap plug underside | 8.3 | mm | PASS |
| pod top above cover seat | 31.7 | mm | PASS |
| USB plug space under the board | 15.2 | mm (>= 12 straight plug) | PASS |
| pan pinion top vs ring underside | 4.5 | mm | PASS |
| pan pinion tip vs well wall | 1.55 | mm | PASS |
| pan servo travel | 156.0 | deg (<= 170) | PASS |
| cable bore | 7.0 | mm | PASS |

## Result: PASS (0 failing pair-poses, 0 nonzero overlaps)

| pan | tilt | a | b | volume mm^3 | kind | ok |
|---|---|---|---|---|---|---|
| - | - | - | - | 0 | - | ok |
