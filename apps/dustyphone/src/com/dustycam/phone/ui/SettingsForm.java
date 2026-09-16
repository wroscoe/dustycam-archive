package com.dustycam.phone.ui;

import android.content.Context;
import android.text.InputType;
import android.util.TypedValue;
import android.view.View;
import android.widget.EditText;
import android.widget.LinearLayout;
import android.widget.ScrollView;
import android.widget.Switch;
import android.widget.TextView;
import android.widget.Toast;

import org.json.JSONArray;
import org.json.JSONException;
import org.json.JSONObject;

import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/**
 * Data-driven tuning form, schema off the wire (docs/phone_app_plan.md §2
 * {@code cfg.schema}: {@code {"id","camera","keys":[{name,type,default,help}]}}),
 * values from {@code cfg.get}. One row per key: int/float -&gt; numeric
 * EditText, bool -&gt; Switch, str -&gt; EditText, list -&gt; comma-separated
 * EditText; current value shown, default as the field's hint, help as a
 * subtext line. {@link #collectChangedCfg} returns only the keys whose value
 * actually changed, ready to go straight into a {@code cfg.set} request's
 * {@code cfg} object.
 *
 * <p>Pure view-building + diffing — CameraActivity owns the network calls
 * (cfg.schema/cfg.get/cfg.set), the Save button, and the cfg_src badge
 * wiring around this form.
 */
public class SettingsForm {

    private final Context ctx;
    private final ScrollView scrollView;
    private final LinearLayout rowsContainer;

    private static final class Row {
        String name;
        String type;
        Object initialValue; // as parsed from cfg.get: String/Integer/Double/Boolean/JSONArray/null
        View input;          // EditText or Switch
    }

    private final Map<String, Row> rows = new LinkedHashMap<>();

    // The firmware truncates `keep_labels` silently past these limits rather
    // than rejecting it (bench finding) — the app refuses to send anything
    // over them instead of letting them go in and get quietly mangled.
    private static final String KEEP_LABELS = "keep_labels";
    private static final int KEEP_LABELS_MAX_ITEMS = 4;
    private static final int KEEP_LABELS_MAX_LEN = 11;
    private static final String KEEP_LABELS_LIMIT_TEXT = "(max " + KEEP_LABELS_MAX_ITEMS
            + ", " + KEEP_LABELS_MAX_LEN + " chars each)";

    public SettingsForm(Context ctx) {
        this.ctx = ctx;
        rowsContainer = new LinearLayout(ctx);
        rowsContainer.setOrientation(LinearLayout.VERTICAL);
        rowsContainer.setPadding(dp(16), dp(8), dp(16), dp(16));
        scrollView = new ScrollView(ctx);
        scrollView.addView(rowsContainer, new ScrollView.LayoutParams(
                ScrollView.LayoutParams.MATCH_PARENT, ScrollView.LayoutParams.WRAP_CONTENT));
    }

    public View getView() { return scrollView; }

    private int dp(int v) { return Math.round(v * ctx.getResources().getDisplayMetrics().density); }

    /**
     * Rebuilds the form from a fresh {@code cfg.schema} + {@code cfg.get}
     * pair. Accepts the schema either nested under {@code "schema"} (the
     * firmware's newer shape, avoiding two top-level {@code "id"} keys — one
     * for the op envelope, one for the camera id) or flat with {@code "keys"}
     * at the top level (the older shape) — {@code rsp.optJSONObject("schema")}
     * is tried first.
     */
    public void render(JSONObject schemaRsp, JSONObject values) {
        rowsContainer.removeAllViews();
        rows.clear();
        if (schemaRsp == null) return;
        JSONObject nested = schemaRsp.optJSONObject("schema");
        JSONObject schema = nested != null ? nested : schemaRsp;
        JSONArray keys = schema.optJSONArray("keys");
        if (keys == null) return;
        for (int i = 0; i < keys.length(); i++) {
            JSONObject key = keys.optJSONObject(i);
            if (key == null) continue;
            String name = key.optString("name", null);
            if (name == null) continue;
            String type = key.optString("type", "str");
            Object def = key.opt("default");
            String help = key.optString("help", "");
            Object current = values != null ? values.opt(name) : null;
            addRow(name, type, def, help, current);
        }
    }

    private void addRow(String name, String type, Object def, String help, Object current) {
        LinearLayout block = new LinearLayout(ctx);
        block.setOrientation(LinearLayout.VERTICAL);
        block.setPadding(0, dp(10), 0, dp(10));

        TextView label = new TextView(ctx);
        label.setText(name + "  (" + type + ")");
        label.setTextSize(TypedValue.COMPLEX_UNIT_SP, 14);
        label.setTypeface(null, android.graphics.Typeface.BOLD);
        block.addView(label);

        Row row = new Row();
        row.name = name;
        row.type = type;
        row.initialValue = current;

        View input;
        if ("bool".equals(type)) {
            Switch sw = new Switch(ctx);
            boolean checked = current instanceof Boolean ? (Boolean) current
                    : (def instanceof Boolean && (Boolean) def);
            sw.setChecked(checked);
            input = sw;
        } else {
            EditText et = new EditText(ctx);
            if ("int".equals(type)) {
                et.setInputType(InputType.TYPE_CLASS_NUMBER | InputType.TYPE_NUMBER_FLAG_SIGNED);
            } else if ("float".equals(type)) {
                et.setInputType(InputType.TYPE_CLASS_NUMBER
                        | InputType.TYPE_NUMBER_FLAG_DECIMAL | InputType.TYPE_NUMBER_FLAG_SIGNED);
            } // else str/list: default text input
            et.setText(displayString(type, current));
            String hint = displayString(type, def);
            if (hint != null && !hint.isEmpty()) et.setHint(hint);
            input = et;
        }
        row.input = input;
        block.addView(input);

        String displayHelp = help;
        if (KEEP_LABELS.equals(name)) {
            // The firmware silently truncates over-limit input rather than
            // rejecting it — show the limit so the user doesn't rely on that.
            displayHelp = (help == null || help.isEmpty() ? "" : help + " ") + KEEP_LABELS_LIMIT_TEXT;
        }
        if (displayHelp != null && !displayHelp.isEmpty()) {
            TextView helpView = new TextView(ctx);
            helpView.setText(displayHelp);
            helpView.setTextSize(TypedValue.COMPLEX_UNIT_SP, 12);
            helpView.setTextColor(0xFF757575);
            block.addView(helpView);
        }

        rowsContainer.addView(block);
        rows.put(name, row);
    }

    /** Renders int/float/str as their plain string form, list as a comma-separated string. */
    private String displayString(String type, Object v) {
        if (v == null) return "";
        if ("list".equals(type) && v instanceof JSONArray) {
            JSONArray arr = (JSONArray) v;
            StringBuilder sb = new StringBuilder();
            for (int i = 0; i < arr.length(); i++) {
                if (i > 0) sb.append(", ");
                sb.append(arr.opt(i));
            }
            return sb.toString();
        }
        return String.valueOf(v);
    }

    public void setEnabled(boolean enabled) {
        for (Row r : rows.values()) r.input.setEnabled(enabled);
    }

    /**
     * Only the keys whose rendered value actually differs from what {@code
     * cfg.get} returned at {@link #render} time — the {@code cfg.set} request
     * body per the plan (§2: "changed keys only").
     *
     * <p>Two guards beyond a plain diff (both bench findings): an emptied
     * str/list field is treated as "leave unchanged" rather than "set to
     * empty" (clearing a field by accident while editing is easy, and a
     * silent {@code ""} is a confusing way to find that out later); and
     * {@code keep_labels} is validated against the firmware's item-count/
     * length limits before being sent, since the firmware truncates instead
     * of rejecting an over-limit value.
     */
    public JSONObject collectChangedCfg() {
        JSONObject out = new JSONObject();
        boolean sawEmptySkipped = false;
        boolean sawKeepLabelsRejected = false;
        for (Row r : rows.values()) {
            Object newVal = readRowValue(r);
            if (newVal == INVALID) continue; // unparsable number: leave it out rather than crash/clobber
            if (isEmptyValue(r.type, newVal)) {
                if (!isEmptyValue(r.type, r.initialValue)) sawEmptySkipped = true;
                continue; // never send an emptied str/list value
            }
            if (KEEP_LABELS.equals(r.name) && !isKeepLabelsValid(newVal)) {
                sawKeepLabelsRejected = true;
                continue;
            }
            if (!valuesEqual(r.initialValue, newVal)) {
                try {
                    out.put(r.name, newVal);
                } catch (JSONException ignored) {}
            }
        }
        if (sawEmptySkipped) {
            toast("empty values are ignored");
        }
        if (sawKeepLabelsRejected) {
            toast(KEEP_LABELS + ": " + KEEP_LABELS_LIMIT_TEXT + " — not saved");
        }
        return out;
    }

    private boolean isEmptyValue(String type, Object v) {
        if ("str".equals(type)) return v == null || (v instanceof String && ((String) v).isEmpty());
        if ("list".equals(type)) return v instanceof JSONArray && ((JSONArray) v).length() == 0;
        return false;
    }

    private boolean isKeepLabelsValid(Object v) {
        if (!(v instanceof JSONArray)) return true;
        JSONArray arr = (JSONArray) v;
        if (arr.length() > KEEP_LABELS_MAX_ITEMS) return false;
        for (int i = 0; i < arr.length(); i++) {
            if (String.valueOf(arr.opt(i)).length() > KEEP_LABELS_MAX_LEN) return false;
        }
        return true;
    }

    private void toast(String message) {
        Toast.makeText(ctx, message, Toast.LENGTH_SHORT).show();
    }

    private static final Object INVALID = new Object();

    private Object readRowValue(Row r) {
        if ("bool".equals(r.type)) {
            return ((Switch) r.input).isChecked();
        }
        String text = ((EditText) r.input).getText().toString().trim();
        switch (r.type) {
            case "int":
                try { return Integer.parseInt(text); } catch (NumberFormatException e) { return INVALID; }
            case "float":
                try { return Double.parseDouble(text); } catch (NumberFormatException e) { return INVALID; }
            case "list": {
                JSONArray arr = new JSONArray();
                if (!text.isEmpty()) {
                    for (String part : text.split(",")) {
                        String t = part.trim();
                        if (!t.isEmpty()) arr.put(t);
                    }
                }
                return arr;
            }
            default:
                return text;
        }
    }

    private boolean valuesEqual(Object a, Object b) {
        if (a == null) a = "";
        if (b == null) b = "";
        if (a instanceof JSONArray || b instanceof JSONArray) {
            return listStrings(a).equals(listStrings(b));
        }
        if (a instanceof Number && b instanceof Number) {
            return ((Number) a).doubleValue() == ((Number) b).doubleValue();
        }
        return String.valueOf(a).equals(String.valueOf(b));
    }

    private List<String> listStrings(Object v) {
        List<String> out = new ArrayList<>();
        if (v instanceof JSONArray) {
            JSONArray arr = (JSONArray) v;
            for (int i = 0; i < arr.length(); i++) out.add(String.valueOf(arr.opt(i)));
        } else if (v != null && !"".equals(v)) {
            for (String part : String.valueOf(v).split(",")) {
                String t = part.trim();
                if (!t.isEmpty()) out.add(t);
            }
        }
        return out;
    }
}
