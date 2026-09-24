# xiao_pantilt interference sweep

backlash 0.0 mm, 5 poses, struct tolerance 1.0 mm^3, gear tolerance 0.5 mm^3, 9 s

## Static checks

| check | value | unit | ok |
|---|---|---|---|
| lens barrel Z centre vs Z_TILT | -0.003 | mm | PASS |
| lens barrel X range | (-3.8, 1.96) | axis X=0 inside | PASS |
| pan centre distance | 28.0 | mm | PASS |
| tilt centre distance | 23.0 | mm | PASS |
| sector inner face vs arm outer face | 5.5 | mm gap (outside the arm) | PASS |
| sector tip vs cover inner wall | 15.0 | mm r vs cavity x 17.8 | PASS |
| cover bottom vs pan pinion top | 1.5 | mm | PASS |
| cradle lowest at tilt max vs tilt servo top | 2.09 | mm | PASS |
| tilt servo bottom vs plate top | 5.1 | mm | PASS |
| pan servo travel | 156.0 | deg (<= 170) | PASS |
| tilt servo travel | 140.0 | deg (<= 170) | PASS |
| cable bore | 7.0 | mm | PASS |

## Result: PASS (0 failing pair-poses, 0 nonzero overlaps)

| pan | tilt | a | b | volume mm^3 | kind | ok |
|---|---|---|---|---|---|---|
| - | - | - | - | 0 | - | ok |
