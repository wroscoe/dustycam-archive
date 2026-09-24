// xiao_pantilt viewer sidecar (v3 compact): pan/tilt pose + derived gear spins.
// Mirrors pantilt_lib.py (same axes, same mesh phase). Viewer-time only.
const Z_TILT = 60.3;
const PAN_RATIO = 26 / 30, TILT_RATIO = 30 / 22;   // gear teeth / pinion teeth
const PAN_PINION = [-28.15, 0, 0];
const TILT_PINION = [-26.15, 0, 60.3];   // world at pan 0, straight behind the tilt axis
export default {
  manifest: {
    schemaVersion: 1,
    parameters: {
      pan_deg:  { type: "number", label: "Pan",  unit: "deg", min: -90, max: 90, step: 1, default: 0,
                  description: "Rotates yoke, cradle and camera about the base axis; pan pinion spins 0.867x the other way." },
      tilt_deg: { type: "number", label: "Tilt", unit: "deg", min: -30, max: 60, step: 1, default: 0,
                  description: "Rotates cradle + camera about the lens axis (+ = look up); tilt pinion spins 1.36x the other way." },
    },
    features: {
      yoke_group: { ref: "#o1.2", label: "Yoke (pans)" },
      tilt_group: { ref: "#o1.2.7", label: "Cradle (tilts)" },
      pan_pinion: { names: ["pan_pinion"] },
      tilt_pinion: { names: ["tilt_pinion"] },
    },
  },
  update({ params, effects }) {
    const pan = Number(params.pan_deg) || 0;
    const tilt = Number(params.tilt_deg) || 0;
    // tilt first (in the yoke frame), then pan: effects premultiply, so world = P * T
    effects.transform("tilt_group", { rotate: { axis: [0, -1, 0], origin: [0, 0, Z_TILT], angleDeg: tilt } });
    effects.transform("tilt_pinion", { rotate: { axis: [0, -1, 0], origin: TILT_PINION, angleDeg: -TILT_RATIO * tilt } });
    effects.transform("yoke_group", { rotate: { axis: [0, 0, 1], origin: [0, 0, 0], angleDeg: pan } });
    effects.transform("pan_pinion", { rotate: { axis: [0, 0, 1], origin: PAN_PINION, angleDeg: -PAN_RATIO * pan } });
  },
};
