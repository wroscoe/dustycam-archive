"""Fail-closed static, interference, and coupled worm-phase checks for v8."""
from __future__ import annotations

import math
from pathlib import Path

import n20_worm_v8_lib as L


STRUCTURAL_TOL_MM3 = 0.01
MESH_PROXIMITY_MAX_MM = 0.70


def intersection_volume(a, b) -> float:
    result = a.intersect(b)
    volume = 0.0 if result is None else sum(shape.volume for shape in result)
    if not math.isfinite(volume):
        raise RuntimeError("non-finite boolean intersection")
    return volume


def main():
    printed = {
        "base": L.base_zero(),
        "lid": L.lid_zero(),
        "rotor": L.rotor_platform_zero(),
        "bottom stop collar": L.stop_collar_zero(),
        "bottom stop finger": L.stop_finger_zero(),
        "bottom stop arm axial clip": L.stop_arm_retainer_zero(),
        "worm": L.worm_zero(),
        "wheel": L.wheel_zero(),
        "wheel axial clip": L.wheel_retainer_zero(),
        "rotor axial clip": L.rotor_retainer_zero(),
        "motor retainer": L.motor_retainer_zero(),
        "DRV retainer": L.drv_retainer_zero(),
        "holder": L.holder_zero(),
        "holder top latch": L.holder_latch_zero(),
        "cap": L.cap_zero(),
        "mesh coupon fixture": L.mesh_coupon_zero(),
    }
    checks = {
        "worm lead = pi*module": abs(L.WORM_LEAD - math.pi * L.AXIAL_MODULE) < 1e-9,
        "24:1 single-start ratio": L.WHEEL_RATIO == 24.0,
        "pitch centre distance = 20": abs(L.CENTER_DISTANCE - (L.WORM_PITCH_D + L.WHEEL_PITCH_D) / 2) < 1e-9,
        "continuous cable bore >= 7 mm": L.CABLE_BORE_D >= 7.0,
        "N20 shaft is 3 mm D-flat": L.N20_SHAFT_D == 3.0 and L.N20_SHAFT_FLAT == 2.5,
        "DRV header keepout included": L.DRV_HEADER_CLEAR >= 6.0,
        "tube interface is 50.8 mm": L.TUBE_OD == 50.8,
        "usable sweep +/-90 inside +/-95 stops": (L.PAN_MIN_DEG, L.PAN_MAX_DEG, L.STOP_PHYSICAL_DEG) == (-90.0, 90.0, 95.0),
        "platform clears tube ID": 2 * L.ROTOR_R < L.TUBE_ID,
        "rotor platform fits deck opening": L.ROTOR_R < L.DECK_INNER_R,
        "journal head fits rotor bore and retains top clip": (
            L.CENTER_COLUMN_OD < L.ROTOR_BORE_D
            and L.CENTER_COLUMN_OD > 2 * 7.55
        ),
        "separate stop-arm keyed attachment datum is registered": (
            abs(L.STOP_ARM_Z1 - (L.STOP_Z0 + 0.15)) < 1e-9
            and L.STOP_ARM_HUB_R > 9.5
            and L.STOP_ARM_SLEEVE_CLEAR_R > 9.5
            and L.STOP_ARM_KEY_Y0 > L.CENTER_COLUMN_OD / 2
        ),
        "stop arm C-mouth clears Ø19 sleeve for lateral installation": (
            L.STOP_ARM_MOUTH_W >= 2 * L.STOP_ARM_SLEEVE_R + 0.25
        ),
        "rotor lower sleeve remains within wheel bore": L.STOP_ARM_SLEEVE_R < L.WHEEL_SLEEVE_CLEAR_R,
        "wheel face spans worm axis": L.WHEEL_Z0 < L.WORM_AXIS_Z < L.WHEEL_Z1,
        "true swept worm crest >= 0.45 mm": L.WORM_CREST_MIN_MM >= 0.45,
        "coupon wheel shoulder exceeds bore radius": L.COUPON_WHEEL_SHOULDER_R > L.WHEEL_SLEEVE_CLEAR_R,
        "coupon wheel pilot clears bore and reaches >= 7 mm": (
            L.COUPON_WHEEL_PILOT_R < L.WHEEL_SLEEVE_CLEAR_R
            and L.COUPON_AXIS_Z+3.5-(L.COUPON_AXIS_Z-L.WHEEL_FACE/2) >= 7.0
        ),
        "coupon worm journal radial clearance <= 0.15 mm": (
            0 < L.COUPON_WORM_JOURNAL_R-L.WORM_ROOT_D/2 <= 0.15
        ),
        "all printable parts are one valid solid": all(len(shape.solids()) == 1 and shape.is_valid for shape in printed.values()),
    }

    zero = L.build_parts(0.0)
    f0, r0 = zero["fixed"], zero["rotating"]
    zero_pairs = [
        ("base/lid", f0["printed_base"], f0["printed_bottom_lid"]),
        ("base/tube", f0["printed_base"], f0["purchased_50_8mm_tube_envelope"]),
        ("base/worm", f0["printed_base"], f0["printed_single_start_worm"]),
        ("base/N20", f0["printed_base"], f0["purchased_n20_envelope"]),
        ("base/DRV8833", f0["printed_base"], f0["clearance_envelope_adafruit_drv8833"]),
        ("base/motor retainer", f0["printed_base"], f0["printed_motor_service_retainer"]),
        ("base/DRV retainer", f0["printed_base"], f0["printed_drv8833_service_retainer"]),
        ("base/rotor axial clip", f0["printed_base"], f0["printed_rotor_axial_c_clip"]),
        ("base/wheel", f0["printed_base"], r0["printed_wheel_24t_prototype"]),
        ("base/wheel axial clip", f0["printed_base"], r0["printed_wheel_axial_c_clip"]),
        ("base/rotor", f0["printed_base"], r0["printed_rotor_platform"]),
        ("base/bottom stop collar", f0["printed_base"], r0["printed_bottom_stop_collar"]),
        ("base/bottom stop finger", f0["printed_base"], r0["printed_bottom_stop_finger"]),
        ("base/bottom stop arm clip", f0["printed_base"], r0["printed_bottom_stop_arm_axial_c_clip"]),
        ("rotor/N20", r0["printed_rotor_platform"], f0["purchased_n20_envelope"]),
        ("wheel/rotor", r0["printed_wheel_24t_prototype"], r0["printed_rotor_platform"]),
        ("wheel/wheel axial clip", r0["printed_wheel_24t_prototype"], r0["printed_wheel_axial_c_clip"]),
        ("wheel clip/bottom stop collar", r0["printed_wheel_axial_c_clip"], r0["printed_bottom_stop_collar"]),
        ("rotor/bottom stop collar", r0["printed_rotor_platform"], r0["printed_bottom_stop_collar"]),
        ("rotor/bottom stop finger", r0["printed_rotor_platform"], r0["printed_bottom_stop_finger"]),
        ("rotor/bottom stop arm clip", r0["printed_rotor_platform"], r0["printed_bottom_stop_arm_axial_c_clip"]),
        ("bottom stop collar/finger", r0["printed_bottom_stop_collar"], r0["printed_bottom_stop_finger"]),
        ("bottom stop collar/clip", r0["printed_bottom_stop_collar"], r0["printed_bottom_stop_arm_axial_c_clip"]),
        ("bottom stop finger/clip", r0["printed_bottom_stop_finger"], r0["printed_bottom_stop_arm_axial_c_clip"]),
        ("rotor/rotor axial clip", r0["printed_rotor_platform"], f0["printed_rotor_axial_c_clip"]),
        ("motor retainer/N20", f0["printed_motor_service_retainer"], f0["purchased_n20_envelope"]),
        ("DRV retainer/DRV", f0["printed_drv8833_service_retainer"], f0["clearance_envelope_adafruit_drv8833"]),
        ("rotor/holder", r0["printed_rotor_platform"], r0["printed_camera_holder_v7_dimensions"]),
        ("holder/top latch", r0["printed_camera_holder_v7_dimensions"], r0["printed_holder_top_latch"]),
        ("top latch/camera", r0["printed_holder_top_latch"], r0["purchased_xiao_camera_reference"]),
        ("holder/camera", r0["printed_camera_holder_v7_dimensions"], r0["purchased_xiao_camera_reference"]),
    ]
    zero_volumes = [(name, intersection_volume(a, b)) for name, a, b in zero_pairs]
    checks["zero-pose unintended intersections <= 0.01 mm3"] = all(v <= STRUCTURAL_TOL_MM3 for _, v in zero_volumes)
    nominal_drv_volume = intersection_volume(f0["printed_drv8833_service_retainer"],
                                              f0["clearance_envelope_adafruit_drv8833"])
    lifted_drv = f0["clearance_envelope_adafruit_drv8833"].moved(L.Location((0, 0, 0.25)))
    lifted_drv_volume = intersection_volume(f0["printed_drv8833_service_retainer"], lifted_drv)
    checks["DRV nominally clears retention tabs"] = nominal_drv_volume <= STRUCTURAL_TOL_MM3
    checks["DRV tabs arrest 0.25 mm upward service lift"] = lifted_drv_volume > STRUCTURAL_TOL_MM3

    # Sample the independently reviewed bottom-service routes, not merely the
    # final pose. Coordinates translate the corresponding final part. Collar:
    # bottom Z=12.7, -X-side semicircle at R=30, +Y 30->21 while low, lift,
    # then inward slide. Finger: low Y=-10->0 slide first (key below receiver),
    # then lift vertically against the already installed collar.
    collar_low_dz = 12.7 - L.STOP_ARM_Z0
    def segment(a, b, count):
        return [tuple(a[i] + (b[i]-a[i])*j/count for i in range(3)) for j in range(count+1)]

    collar_points = []
    # -X semicircle from (0,-30) to (0,+30), all with bottom at Z=12.7.
    for j in range(21):
        angle = -math.pi/2 + math.pi*j/20
        collar_points.append((-30.0*math.cos(angle), 30.0*math.sin(angle), collar_low_dz))
    collar_points += segment((0.0, 30.0, collar_low_dz), (0.0, 21.0, collar_low_dz), 5)[1:]
    collar_points += segment((0.0, 21.0, collar_low_dz), (0.0, 21.0, 0.0), 5)[1:]
    collar_points += segment((0.0, 21.0, 0.0), (0.0, 0.0, 0.0), 8)[1:]
    finger_points = segment((0.0, -10.0, collar_low_dz), (0.0, 0.0, collar_low_dz), 8)
    finger_points += segment((0.0, 0.0, collar_low_dz), (0.0, 0.0, 0.0), 5)[1:]
    insertion_waypoints = [
        *( (f"collar route {i:02d}", r0["printed_bottom_stop_collar"], point, None)
            for i, point in enumerate(collar_points) ),
        *( (f"finger route {i:02d}", r0["printed_bottom_stop_finger"], point,
            r0["printed_bottom_stop_collar"])
            for i, point in enumerate(finger_points) ),
    ]
    insertion_rows = []
    for name, shape, delta, installed_collar in insertion_waypoints:
        moving_shape = shape.moved(L.Location(delta))
        base_volume = intersection_volume(f0["printed_base"], moving_shape)
        rotor_volume = intersection_volume(r0["printed_rotor_platform"], moving_shape)
        collar_volume = 0.0 if installed_collar is None else intersection_volume(installed_collar, moving_shape)
        insertion_rows.append((name, base_volume, rotor_volume, collar_volume))
    checks["sampled collar/finger insertion routes clear base and rotor"] = all(
        base <= STRUCTURAL_TOL_MM3 and rotor <= STRUCTURAL_TOL_MM3 and collar <= STRUCTURAL_TOL_MM3
        for _, base, rotor, collar in insertion_rows
    )

    sweep_rows = []
    # Targeted default sweep keeps the CAD boolean check practical in CI; use
    # representative endpoints, quadrants and centre.  Mesh phase check below
    # independently samples one full 15° wheel pitch interval.
    for pan in (-90, -45, 0, 45, 90):
        parts = L.build_parts(float(pan))
        fixed, moving = parts["fixed"], parts["rotating"]
        pairs = [
            ("base/rotor", fixed["printed_base"], moving["printed_rotor_platform"]),
            ("base/bottom stop collar", fixed["printed_base"], moving["printed_bottom_stop_collar"]),
            ("base/bottom stop finger", fixed["printed_base"], moving["printed_bottom_stop_finger"]),
            ("base/bottom stop arm clip", fixed["printed_base"], moving["printed_bottom_stop_arm_axial_c_clip"]),
            ("base/wheel", fixed["printed_base"], moving["printed_wheel_24t_prototype"]),
            ("base/wheel clip", fixed["printed_base"], moving["printed_wheel_axial_c_clip"]),
            ("N20/rotor", fixed["purchased_n20_envelope"], moving["printed_rotor_platform"]),
            ("base/rotor clip", fixed["printed_base"], fixed["printed_rotor_axial_c_clip"]),
            ("DRV/rotor", fixed["clearance_envelope_adafruit_drv8833"], moving["printed_rotor_platform"]),
            ("tube/rotor", fixed["purchased_50_8mm_tube_envelope"], moving["printed_rotor_platform"]),
            ("tube/holder", fixed["purchased_50_8mm_tube_envelope"], moving["printed_camera_holder_v7_dimensions"]),
            ("tube/camera", fixed["purchased_50_8mm_tube_envelope"], moving["purchased_xiao_camera_reference"]),
            ("cap/holder", fixed["printed_tube_cap"], moving["printed_camera_holder_v7_dimensions"]),
            ("cap/camera", fixed["printed_tube_cap"], moving["purchased_xiao_camera_reference"]),
            ("holder/latch", moving["printed_camera_holder_v7_dimensions"], moving["printed_holder_top_latch"]),
        ]
        worst_name, worst_volume = "", 0.0
        for name, a, b in pairs:
            volume = intersection_volume(a, b)
            if volume > worst_volume:
                worst_name, worst_volume = name, volume
        sweep_rows.append((pan, worst_name or "none", worst_volume))
    checks["5-pose structural sweep <= 0.01 mm3"] = all(row[2] <= STRUCTURAL_TOL_MM3 for row in sweep_rows)

    mesh_rows = []
    for sample in range(9):
        pan = 15.0 * sample / 8.0
        parts = L.build_parts(pan)
        worm = parts["fixed"]["printed_single_start_worm"]
        wheel = parts["rotating"]["printed_wheel_24t_prototype"]
        volume = intersection_volume(worm, wheel)
        gap = worm.distance_to(wheel)
        if not math.isfinite(gap):
            raise RuntimeError("non-finite worm/wheel distance")
        mesh_rows.append((pan, L.worm_angle_for_pan(pan), volume, gap))
    checks["9-phase coupled mesh has no penetration"] = all(row[2] <= STRUCTURAL_TOL_MM3 for row in mesh_rows)
    # Distance alone proves only that the prototype pair stays near its intended
    # mesh envelope.  It does not prove flank contact, backlash, torque transfer,
    # wear, or efficiency; those are deliberately deferred to the printed coupon.
    checks["9-phase coupled mesh stays within proximity envelope"] = (
        max(row[3] for row in mesh_rows) <= MESH_PROXIMITY_MAX_MM
    )
    coupon = L.mesh_coupon_zero()
    coupon_worm = L.worm_zero().moved(L.Location((0, -L.CENTER_DISTANCE, L.COUPON_AXIS_Z)))
    coupon_wheel = L.wheel_zero().moved(L.Location((0, 0, L.COUPON_AXIS_Z-L.WORM_AXIS_Z)))
    coupon_worm_volume = intersection_volume(coupon, coupon_worm)
    coupon_wheel_volume = intersection_volume(coupon, coupon_wheel)
    checks["coupon fixture clears normal worm"] = coupon_worm_volume <= STRUCTURAL_TOL_MM3
    checks["coupon fixture clears normal wheel"] = coupon_wheel_volume <= STRUCTURAL_TOL_MM3

    lines = ["# n20_worm_v8 geometric validation", "", "| check | result |", "|---|---|"]
    lines.extend(f"| {name} | {'PASS' if ok else 'FAIL'} |" for name, ok in checks.items())
    lines += [
        "",
        f"- Worm-to-wheel response: {L.PAN_PER_WORM_REV_DEG:.1f} degrees platform pan per positive worm revolution.",
        f"- Mesh status: {L.MESH_STATUS}",
        f"- Coupled mesh proximity gap across one wheel-tooth pitch: {min(r[3] for r in mesh_rows):.3f}..{max(r[3] for r in mesh_rows):.3f} mm; this is not a torque-transfer claim.",
        f"- Coupon fixture intersections (worm/wheel): {coupon_worm_volume:.6f} / {coupon_wheel_volume:.6f} mm3.",
        f"- DRV retainer vs nominal/lifted (+0.25 mm) envelope: {nominal_drv_volume:.6f} / {lifted_drv_volume:.6f} mm3.",
        "- Fixed stops are at ±95°; the structural collision sweep samples the usable ±90° range in 45° steps.",
        "",
        "## Zero-pose pair intersections",
        "",
        "| pair | intersection mm3 |",
        "|---|---:|",
    ]
    lines.extend(f"| {name} | {volume:.6f} |" for name, volume in zero_volumes)
    lines += ["", "## Sampled bottom-service insertion routes", "", "| waypoint | base intersection mm3 | rotor intersection mm3 | installed collar intersection mm3 |", "|---|---:|---:|---:|"]
    lines.extend(f"| {name} | {base:.6f} | {rotor:.6f} | {collar:.6f} |" for name, base, rotor, collar in insertion_rows)
    lines += ["", "## Structural sweep", "", "| pan deg | worst pair | intersection mm3 |", "|---:|---|---:|"]
    lines.extend(f"| {pan:+d} | {name} | {volume:.6f} |" for pan, name, volume in sweep_rows)
    out = Path(__file__).with_name("static_validation.md")
    out.write_text("\n".join(lines) + "\n")
    if not all(checks.values()):
        failed = ", ".join(name for name, ok in checks.items() if not ok)
        raise SystemExit(f"geometric validation failed: {failed}")
    print(out)


if __name__ == "__main__":
    main()
