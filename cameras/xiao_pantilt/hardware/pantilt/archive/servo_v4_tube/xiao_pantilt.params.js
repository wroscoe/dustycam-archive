// xiao_pantilt viewer sidecar (v4 pan-only tube): pan pose + pinion spin.
const PAN_RATIO = 26 / 30;           // gear teeth / pinion teeth
const PAN_PINION = [-28.15, 0, 0];
export default {
  manifest: {
    schemaVersion: 1,
    parameters: {
      pan_deg: { type: "number", label: "Pan", unit: "deg", min: -90, max: 90, step: 1, default: 0,
                 description: "Rotates the camera pod about the base axis; pan pinion spins 0.867x the other way." },
      show_tube: { type: "boolean", label: "Show tube + cap", default: true },
    },
    features: {
      pod_group: { ref: "#o1.2", label: "Pod (pans)" },
      pan_pinion: { names: ["pan_pinion"] },
      tube: { names: ["tube"] },
      cap: { names: ["cap"] },
    },
  },
  update({ params, effects }) {
    const pan = Number(params.pan_deg) || 0;
    effects.transform("pod_group", { rotate: { axis: [0, 0, 1], origin: [0, 0, 0], angleDeg: pan } });
    effects.transform("pan_pinion", { rotate: { axis: [0, 0, 1], origin: PAN_PINION, angleDeg: -PAN_RATIO * pan } });
    effects.visible("tube", params.show_tube !== false);
    effects.visible("cap", params.show_tube !== false);
  },
};
