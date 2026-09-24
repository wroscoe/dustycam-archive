# xiao_pantilt interference sweep (v6 direct-drive, tube, battery bay)

backlash 0.0 mm, 13 poses, struct tolerance 1.0 mm^3, gear tolerance 0.5 mm^3, 27 s

## Static checks

| check | value | unit | ok |
|---|---|---|---|
| pod max radius | 16.85 | mm vs tube ID/2 22.25 | PASS |
| pod top vs cap plug underside | 5.8 | mm | PASS |
| pod top above cover seat | 44.2 | mm | PASS |
| foot bottom vs base top plate | 4.5 | mm | PASS |
| USB plug space under the board | 12.2 | mm (>= 8 right-angle plug) | PASS |
| servo ear reach vs hollow radius | 4.2 | mm | PASS |
| servo bottom above bench | 7.75 | mm | PASS |
| cable hole vs groove inner radius | 3.15 | mm | PASS |
| cable hole vs servo body (Y) | 2.9 | mm | PASS |
| pan servo travel | 180.0 | deg (direct) | PASS |
| battery top vs servo bottom | 1.25 | mm | PASS |
| lid + frame max radius vs hollow | 0.2 | mm | PASS |
| base height | 30.1 | mm | PASS |

## Result: PASS (0 failing pair-poses, 0 nonzero overlaps)

| pan | tilt | a | b | volume mm^3 | kind | ok |
|---|---|---|---|---|---|---|
| - | - | - | - | 0 | - | ok |
