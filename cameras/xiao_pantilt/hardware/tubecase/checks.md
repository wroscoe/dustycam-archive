# tubecase v2 checks
Overall: **PASS** (0 failing check(s))
## 1. Pairwise interference
Tolerance 1.0 mm^3. All pairs clean.

## 2. Static checks

| check | value | unit | ok |
|---|---|---|---|
| base max radius vs tube OD | 22.05 | mm (<= 25.40) | PASS |
| mid_plate max radius vs tube OD | 22.05 | mm (<= 25.40) | PASS |
| cap max radius vs tube OD | 25.4 | mm (<= 25.40) | PASS |
| tube max radius vs tube OD | 25.4 | mm (<= 25.40) | PASS |
| charger_bq25185 max radius vs tube OD | 16.52 | mm (<= 25.40) | PASS |
| camera_xiao max radius vs tube OD | 18.354 | mm (<= 25.40) | PASS |
| battery_1578 max radius vs tube OD | 15.042 | mm (<= 25.40) | PASS |
| battery_swell_envelope max radius vs tube OD | 16.155 | mm (<= 25.40) | PASS |
| jack_envelope max radius vs tube OD | 10.8 | mm (<= 25.40) | PASS |
| base max radius vs tube ID (internal) | 22.05 | mm (<= 22.25) | PASS |
| mid_plate max radius vs tube ID (internal) | 22.05 | mm (<= 22.25) | PASS |
| charger_bq25185 max radius vs tube ID (internal) | 16.52 | mm (<= 22.25) | PASS |
| camera_xiao max radius vs tube ID (internal) | 18.354 | mm (<= 22.25) | PASS |
| battery_1578 max radius vs tube ID (internal) | 15.042 | mm (<= 22.25) | PASS |
| battery_swell_envelope max radius vs tube ID (internal) | 16.155 | mm (<= 22.25) | PASS |
| jack_envelope max radius vs tube ID (internal) | 10.8 | mm (<= 22.25) | PASS |
| cap plug max radius vs tube ID (internal) | 22.1 | mm (<= 22.25) | PASS |
| jack body to liner bore | 0.45 | mm (>= 0.4) | PASS |
| jack body to battery rib face | 1.5 | mm (>= 1.0) | PASS |
| charger PCB corner radius vs bore | 3.93 | mm (>= 1.0) | PASS |
| charger component corner vs bore | 1.17 | mm (>= 0.5) | PASS |
| charger measured max X (components, actual STEP) | 9.37 | mm (spec assumed 10.94) | PASS |
| charger top edge + 12mm plug room vs Z_MID0 | 0.4 | mm (>= 0, i.e. fits under Z_MID0) | PASS |
| battery top vs mid plate underside | 3.0 | mm (>= 2.0) | PASS |
| mid-plate boss bottom vs jack body top | 16.3 | mm (>= 5.0) | PASS |
| radial pilot vs vertical pilot separation | 1.65 | mm (>= 1.0) | PASS |
| cradle top vs cap plug underside | 5.85 | mm (>= 2.0) | PASS |
| SD-card top vs cap plug underside | 3.237 | mm (>= 2.0) | PASS |
| lens tip x vs tube inner wall | 4.0 | mm (>= 3.99) | PASS |
| wire notch vs cradle footprint | 0.0 | mm^3 (<= 1.0) | PASS |
| wire notch vs bosses (max pair volume) | 0.0 | mm^3 (<= 1.0) | PASS |
| lens height above floor bottom | 69.62 | mm | PASS |
| overall height (Z_CAP1) | 89.5 | mm (== 89.5) | PASS |
| overall body diameter (tube_od) | 50.8 | mm (== 50.8) | PASS |

## 3. Insertion paths

| sweep | dz mm | volumes | ok |
|---|---|---|---|
| charger vs base | 0 | base=0.0000 | ok |
| charger vs base | 5 | base=0.0000 | ok |
| charger vs base | 10 | base=0.0000 | ok |
| charger vs base | 15 | base=0.0000 | ok |
| charger vs base | 20 | base=0.0000 | ok |
| charger vs base | 25 | base=0.0000 | ok |
| charger vs base | 30 | base=0.0000 | ok |
| battery vs base | 0 | base=0.0000 | ok |
| battery vs base | 5 | base=0.0000 | ok |
| battery vs base | 10 | base=0.0000 | ok |
| battery vs base | 15 | base=0.0000 | ok |
| battery vs base | 20 | base=0.0000 | ok |
| battery vs base | 25 | base=0.0000 | ok |
| battery vs base | 30 | base=0.0000 | ok |
| mid_plate(+cradle) vs base | 0 | base=0.0000 | ok |
| mid_plate(+cradle) vs base | 5 | base=0.0000 | ok |
| mid_plate(+cradle) vs base | 10 | base=0.0000 | ok |
| camera vs mid_plate | 5 | mid_plate=0.0000 | ok |
| camera vs mid_plate | 25 | mid_plate=0.0000 | ok |
| chassis vs tube | 0 | tube=0.0000 | ok |
| chassis vs tube | 10 | tube=0.0000 | ok |
| chassis vs tube | 20 | tube=0.0000 | ok |
| chassis vs tube | 30 | tube=0.0000 | ok |
| chassis vs tube | 40 | tube=0.0000 | ok |
| chassis vs tube | 50 | tube=0.0000 | ok |
| chassis vs tube | 60 | tube=0.0000 | ok |
| chassis vs tube | 70 | tube=0.0000 | ok |
| chassis vs tube | 80 | tube=0.0000 | ok |
| chassis vs tube | 90 | tube=0.0000 | ok |
| cap vs tube+camera | 0 | tube=0.0000; camera=0.0000 | ok |
| cap vs tube+camera | 5 | tube=0.0000; camera=0.0000 | ok |
| cap vs tube+camera | 10 | tube=0.0000; camera=0.0000 | ok |

