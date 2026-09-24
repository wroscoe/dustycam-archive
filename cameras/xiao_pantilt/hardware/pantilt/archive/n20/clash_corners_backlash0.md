# xiao_pantilt interference sweep

backlash 0.0 mm, 5 poses, struct tolerance 1.0 mm^3, gear tolerance 0.5 mm^3, 8 s

## Static checks

| check | value | unit | ok |
|---|---|---|---|
| lens barrel bbox Z centre vs Z_TILT | -0.003 | mm | PASS |
| lens barrel X range | (-3.8, 1.96) | axis X=0 inside | PASS |
| pan centre distance | 30.0 | mm | PASS |
| tilt centre distance | 24.0 | mm | PASS |
| sector to left arm Y gap | 1.0 | mm | PASS |
| sector lowest Z vs plate top | 5.62 | mm clearance | PASS |
| cable bore | 8.0 | mm | PASS |

## Result: PASS (0 failing pair-poses, 0 nonzero overlaps)

| pan | tilt | a | b | volume mm^3 | kind | ok |
|---|---|---|---|---|---|---|
| - | - | - | - | 0 | - | ok |
