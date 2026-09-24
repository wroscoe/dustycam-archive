// xiao_pantilt viewer sidecar (v5 direct-drive tube): pan pose only.
export default {
  manifest: {
    schemaVersion: 1,
    parameters: {
      pan_deg: { type: "number", label: "Pan", unit: "deg", min: -90, max: 90, step: 1, default: 0,
                 description: "Rotates the camera pod about the base axis; direct drive, pan = servo angle." },
      show_tube: { type: "boolean", label: "Show tube + cap", default: true },
    },
    features: {
      pod_group: { ref: "#o1.2", label: "Pod (pans)" },
      tube: { names: ["tube"] },
      cap: { names: ["cap"] },
    },
  },
  update({ params, effects }) {
    const pan = Number(params.pan_deg) || 0;
    effects.transform("pod_group", { rotate: { axis: [0, 0, 1], origin: [0, 0, 0], angleDeg: pan } });
    effects.visible("tube", params.show_tube !== false);
    effects.visible("cap", params.show_tube !== false);
  },
};
