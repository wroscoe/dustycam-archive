package com.dustycam.phone;

import android.app.Activity;
import android.bluetooth.BluetoothAdapter;
import android.bluetooth.BluetoothManager;
import android.bluetooth.le.BluetoothLeScanner;
import android.bluetooth.le.ScanCallback;
import android.bluetooth.le.ScanResult;
import android.bluetooth.le.ScanSettings;
import android.content.ContentResolver;
import android.content.Intent;
import android.net.Uri;
import android.os.Bundle;
import android.os.Handler;
import android.os.Looper;
import android.text.method.ScrollingMovementMethod;
import android.util.Log;
import android.util.TypedValue;
import android.view.View;
import android.widget.Button;
import android.widget.EditText;
import android.widget.LinearLayout;
import android.widget.ScrollView;
import android.widget.TextView;

import com.dustycam.phone.ble.Crypto;
import com.dustycam.phone.ble.DustyLink;
import com.dustycam.phone.ui.Brand;

import org.json.JSONArray;
import org.json.JSONException;
import org.json.JSONObject;

import java.io.BufferedReader;
import java.io.InputStream;
import java.io.InputStreamReader;
import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.List;

/**
 * Field provisioning over BLE (docs/phone_app_plan.md §1 decisions 5 & 7,
 * §2 {@code prov.set}/{@code prov.get}): import a {@code dusty_phone.json}
 * profile, pick/type the target device id, then write identity to the
 * camera. Launched from {@link ScanActivity}, either by tapping an
 * unprovisioned ({@code dc-new-…}, manufacturer-data prov flag bit0 == 0)
 * row directly, or via the "Provision a camera" menu item.
 *
 * <p>Two wire paths, chosen from the connected camera's own {@code
 * info.prov} (§2 "Session" / decision 5), not from anything the user picks:
 * <ul>
 *   <li>{@code prov==0} (unprovisioned, inside its presence window): {@code
 *   prov.set} is sent <b>plaintext</b> — there is no {@code ble_key} on the
 *   camera yet to authenticate with, and the protocol exempts this op from
 *   auth specifically for this case. {@link DustyLink#connectForInfo} is used
 *   so hello/auth (which would otherwise fail — HMAC checked against a key
 *   the camera doesn't have yet) is never attempted.</li>
 *   <li>{@code prov==1} (already provisioned, e.g. re-provisioning with the
 *   owner's existing key): a full {@code hello}/{@code auth} session is
 *   established first (normal {@link DustyLink#connect}), then {@code
 *   prov.set} is sent as an AES-256-GCM envelope under the session key.</li>
 * </ul>
 */
public class ProvisionActivity extends Activity {

    public static final String EXTRA_ADDRESS = "address";
    public static final String EXTRA_NAME = "name";

    private static final String TAG = "Dusty";
    private static final int REQ_IMPORT = 1;
    private static final long RESCAN_AFTER_PROVISION_TIMEOUT_MS = 60_000;

    private String address;
    private String cameraName;
    private BluetoothAdapter adapter;
    private Prefs prefs;
    private DustyLink link;

    private final Handler main = new Handler(Looper.getMainLooper());

    private TextView status;
    private TextView log;
    private ScrollView logScroll;
    private EditText deviceIdInput;
    private Button btnImport;
    private Button btnProvision;

    /** The imported dusty_phone.json, kept only in memory here; Prefs is the durable copy. Never logged verbatim (has secrets). */
    private JSONObject importedProfile;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        address = getIntent().getStringExtra(EXTRA_ADDRESS);
        cameraName = getIntent().getStringExtra(EXTRA_NAME);
        prefs = new Prefs(this);

        BluetoothManager bm = (BluetoothManager) getSystemService(BLUETOOTH_SERVICE);
        adapter = bm.getAdapter();

        buildUi();

        if (address == null) {
            appendLog("no camera pre-selected; import a profile, then enter a device id");
        } else {
            appendLog("target: " + cameraName + " (" + address + ")");
        }

        if (prefs.hasImportedProfile()) {
            try {
                importedProfile = new JSONObject(prefs.importedProfileJson());
                status.setText("profile already imported (" + prefs.importedCameraCount() + " camera id(s) on file)");
                btnProvision.setEnabled(address != null);
            } catch (JSONException e) {
                appendLog("stored profile is corrupt: " + e);
            }
        }
    }

    @Override
    protected void onDestroy() {
        super.onDestroy();
        if (link != null) link.disconnect();
    }

    // ---- UI ----

    private void buildUi() {
        LinearLayout root = new LinearLayout(this);
        root.setOrientation(LinearLayout.VERTICAL);
        root.addView(Brand.buildHeader(this, getString(R.string.kicker_provision)));

        status = new TextView(this);
        status.setPadding(dp(24), dp(16), dp(24), dp(8));
        status.setTextColor(getColor(R.color.dc_ink));
        status.setText("Import dusty_phone.json to provision a camera.");
        root.addView(status);

        btnImport = new Button(this);
        btnImport.setText("Import profile…");
        btnImport.setOnClickListener(v -> pickProfile());
        Brand.styleButton(this, btnImport);
        LinearLayout.LayoutParams importLp = new LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.WRAP_CONTENT, LinearLayout.LayoutParams.WRAP_CONTENT);
        importLp.setMargins(dp(24), dp(8), dp(24), dp(8));
        root.addView(btnImport, importLp);

        deviceIdInput = new EditText(this);
        deviceIdInput.setHint("device id (e.g. xiaocam1)");
        deviceIdInput.setTextColor(getColor(R.color.dc_ink));
        deviceIdInput.setHintTextColor(getColor(R.color.dc_muted));
        deviceIdInput.setPadding(dp(24), dp(8), dp(24), dp(8));
        root.addView(deviceIdInput);

        btnProvision = new Button(this);
        btnProvision.setText("Provision");
        btnProvision.setEnabled(false);
        btnProvision.setOnClickListener(v -> startProvisioning());
        Brand.styleButton(this, btnProvision);
        LinearLayout.LayoutParams provisionLp = new LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.WRAP_CONTENT, LinearLayout.LayoutParams.WRAP_CONTENT);
        provisionLp.setMargins(dp(24), dp(8), dp(24), dp(8));
        root.addView(btnProvision, provisionLp);

        log = new TextView(this);
        log.setTextSize(TypedValue.COMPLEX_UNIT_SP, 12);
        log.setTypeface(android.graphics.Typeface.MONOSPACE);
        log.setTextColor(getColor(R.color.dc_ink));
        log.setPadding(dp(12), dp(8), dp(12), dp(8));
        log.setMovementMethod(new ScrollingMovementMethod());
        logScroll = new ScrollView(this);
        // Background lives on the scroll view, not the TextView: see
        // CameraActivity's identical fix for why.
        logScroll.setBackgroundColor(getColor(R.color.dc_paper));
        logScroll.addView(log, new ScrollView.LayoutParams(
                ScrollView.LayoutParams.MATCH_PARENT, ScrollView.LayoutParams.WRAP_CONTENT));
        root.addView(logScroll, new LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.MATCH_PARENT, 0, 1f));

        setContentView(root);
    }

    private int dp(int v) { return Math.round(v * getResources().getDisplayMetrics().density); }

    private void appendLog(String line) {
        Log.i(TAG, line);
        main.post(() -> {
            log.append(line + "\n");
            logScroll.post(() -> logScroll.fullScroll(View.FOCUS_DOWN));
        });
    }

    // ---- import ----

    private void pickProfile() {
        Intent i = new Intent(Intent.ACTION_OPEN_DOCUMENT);
        i.addCategory(Intent.CATEGORY_OPENABLE);
        i.setType("application/json");
        try {
            startActivityForResult(i, REQ_IMPORT);
        } catch (Exception e) {
            appendLog("no file picker available: " + e);
        }
    }

    @Override
    protected void onActivityResult(int requestCode, int resultCode, Intent data) {
        super.onActivityResult(requestCode, resultCode, data);
        if (requestCode != REQ_IMPORT || resultCode != RESULT_OK || data == null) return;
        Uri uri = data.getData();
        if (uri == null) return;
        try {
            importProfile(new JSONObject(readAll(uri)));
        } catch (Exception e) {
            appendLog("import failed: " + e);
        }
    }

    private String readAll(Uri uri) throws Exception {
        ContentResolver cr = getContentResolver();
        try (InputStream is = cr.openInputStream(uri)) {
            if (is == null) throw new IllegalStateException("could not open " + uri);
            BufferedReader r = new BufferedReader(new InputStreamReader(is, StandardCharsets.UTF_8));
            StringBuilder sb = new StringBuilder();
            String line;
            while ((line = r.readLine()) != null) sb.append(line).append('\n');
            return sb.toString();
        }
    }

    /**
     * {@code {"v":1,"server":{host,port,tls,token},"hotspot":{ssid,pass},
     * "ble_key":"<hex>","cameras":[{id}...]}}. Secrets (token, pass, ble_key)
     * go straight into private {@link Prefs} and are never logged; only
     * structural facts (host name, camera count, key length) are.
     */
    private void importProfile(JSONObject profile) throws JSONException {
        int v = profile.optInt("v", -1);
        if (v != 1) {
            appendLog("import failed: unknown profile version " + v);
            return;
        }
        String bleKeyHex = profile.optString("ble_key", null);
        if (bleKeyHex == null || bleKeyHex.isEmpty()) {
            appendLog("import failed: profile has no ble_key");
            return;
        }
        JSONObject server = profile.optJSONObject("server");
        JSONObject hotspot = profile.optJSONObject("hotspot");
        JSONArray cameras = profile.optJSONArray("cameras");

        importedProfile = profile;
        prefs.setBleKeyHex(bleKeyHex);
        prefs.setImportedProfile(profile.toString());

        List<String> ids = new ArrayList<>();
        if (cameras != null) {
            for (int i = 0; i < cameras.length(); i++) {
                JSONObject c = cameras.optJSONObject(i);
                if (c != null && c.has("id")) ids.add(c.optString("id"));
            }
        }
        if (ids.size() == 1) deviceIdInput.setText(ids.get(0));

        appendLog("imported profile: host=" + (server != null ? server.optString("host", "?") : "?")
                + " hotspot_ssid=" + (hotspot != null ? hotspot.optString("ssid", "?") : "?")
                + " ble_key=" + (bleKeyHex.length() / 2) + " bytes"
                + " cameras=" + ids.size());
        status.setText("profile imported (" + ids.size() + " camera id(s))");
        btnProvision.setEnabled(address != null);
    }

    // ---- provisioning ----

    private void startProvisioning() {
        String deviceId = deviceIdInput.getText().toString().trim();
        if (deviceId.isEmpty()) {
            appendLog("enter a device id first");
            return;
        }
        if (importedProfile == null) {
            appendLog("import a profile first");
            return;
        }
        if (address == null) {
            appendLog("no camera address — go back and tap an unprovisioned entry");
            return;
        }
        btnProvision.setEnabled(false);
        appendLog("connecting to read info… (no auth yet — we don't know if this camera has our key)");
        link = new DustyLink(this, Crypto.fromHex(prefs.bleKeyHex()), infoOnlyListener);
        link.connectForInfo(adapter, address);
    }

    private final DustyLink.Listener infoOnlyListener = new DustyLink.Listener() {
        @Override public void onStateChanged(DustyLink.State s) {
            appendLog("link state=" + s);
            if (s == DustyLink.State.INFO_ONLY) {
                JSONObject info = link.getInfo();
                int prov = info != null ? info.optInt("prov", 1) : 1;
                if (prov == 0) {
                    appendLog("camera reports prov:0 (unprovisioned, presence window open) "
                            + "— sending plaintext prov.set");
                    sendPlaintextProvSet();
                } else {
                    appendLog("camera reports prov:1 (already provisioned) "
                            + "— re-authenticating to send an encrypted prov.set");
                    reauthThenSendEnvelope();
                }
            } else if (s == DustyLink.State.FAILED || s == DustyLink.State.DISCONNECTED) {
                appendLog("provisioning link failed/disconnected before info was read");
                btnProvision.setEnabled(true);
            }
        }
        @Override public void onEvent(JSONObject evt) { appendLog("evt: " + evt); }
        @Override public void onInfo(JSONObject info) { appendLog("info: " + info); }
    };

    private void sendPlaintextProvSet() {
        try {
            JSONObject args = provArgs(deviceIdInput.getText().toString().trim());
            link.request("prov.set", args, provCallback());
        } catch (JSONException e) {
            appendLog("prov.set build failed: " + e);
        }
    }

    private void reauthThenSendEnvelope() {
        // connectForInfo() deliberately skipped hello/auth; a full session
        // needs a fresh connect (DustyLink doesn't support resuming mid-session).
        link.disconnect();
        link = new DustyLink(this, Crypto.fromHex(prefs.bleKeyHex()), new DustyLink.Listener() {
            @Override public void onStateChanged(DustyLink.State s) {
                appendLog("link state=" + s);
                if (s == DustyLink.State.READY) {
                    sendEncryptedProvSet();
                } else if (s == DustyLink.State.FAILED || s == DustyLink.State.DISCONNECTED) {
                    appendLog("auth failed — wrong owner key for this already-provisioned camera?");
                    btnProvision.setEnabled(true);
                }
            }
            @Override public void onEvent(JSONObject evt) { appendLog("evt: " + evt); }
            @Override public void onInfo(JSONObject info) { appendLog("info: " + info); }
        });
        link.connect(adapter, address);
    }

    private void sendEncryptedProvSet() {
        try {
            JSONObject plain = provArgs(deviceIdInput.getText().toString().trim());
            byte[] sk = link.sessionKey();
            if (sk == null) {
                appendLog("no session key available — not actually authenticated?");
                return;
            }
            byte[] envelope = Crypto.aesGcmEncrypt(sk, plain.toString().getBytes(StandardCharsets.UTF_8));
            JSONObject args = new JSONObject();
            args.put("env", Crypto.toBase64(envelope));
            appendLog("prov.set (encrypted envelope, " + envelope.length + " B)");
            link.request("prov.set", args, provCallback());
        } catch (JSONException e) {
            appendLog("prov.set (encrypted) build failed: " + e);
        }
    }

    /**
     * {@code {device,ssid,pass,host,port,tls,token,ble_key}} (§2 {@code
     * prov.set}). Built fresh per call — never stashed as a field — so the
     * plaintext identity object doesn't linger in memory longer than it has to.
     */
    private JSONObject provArgs(String deviceId) throws JSONException {
        JSONObject server = importedProfile.optJSONObject("server");
        JSONObject hotspot = importedProfile.optJSONObject("hotspot");
        JSONObject args = new JSONObject();
        args.put("device", deviceId);
        args.put("ssid", hotspot != null ? hotspot.optString("ssid", "") : "");
        args.put("pass", hotspot != null ? hotspot.optString("pass", "") : "");
        args.put("host", server != null ? server.optString("host", "") : "");
        args.put("port", server != null ? server.optInt("port", 0) : 0);
        args.put("tls", server != null && server.optBoolean("tls", false));
        args.put("token", server != null ? server.optString("token", "") : "");
        args.put("ble_key", prefs.bleKeyHex());
        return args;
    }

    private DustyLink.OpCallback provCallback() {
        return new DustyLink.OpCallback() {
            @Override public void onResponse(JSONObject rsp) {
                String device = rsp.optString("device", deviceIdInput.getText().toString().trim());
                appendLog("prov.set ok: " + rsp + " — camera is restarting as " + device);
                status.setText("provisioned — waiting for dc-" + device + " to re-advertise…");
                rescanForProvisionedDevice(device);
            }
            @Override public void onError(String err) {
                appendLog("prov.set error: " + err);
                btnProvision.setEnabled(true);
            }
        };
    }

    /** After prov.set the camera reboots and re-advertises as `dc-<device>`; rescan by name and hand off to CameraActivity. */
    private void rescanForProvisionedDevice(String deviceId) {
        String expectedName = "dc-" + deviceId;
        BluetoothLeScanner scanner = adapter.getBluetoothLeScanner();
        if (scanner == null) {
            appendLog("no BLE scanner available to rescan for " + expectedName);
            return;
        }
        ScanSettings settings = new ScanSettings.Builder()
                .setScanMode(ScanSettings.SCAN_MODE_LOW_LATENCY)
                .build();
        ScanCallback cb = new ScanCallback() {
            @Override public void onScanResult(int callbackType, ScanResult result) {
                String name = result.getScanRecord() != null ? result.getScanRecord().getDeviceName() : null;
                if (!expectedName.equals(name)) return;
                try { scanner.stopScan(this); } catch (SecurityException ignored) {}
                String foundAddress = result.getDevice().getAddress();
                appendLog("found " + expectedName + " at " + foundAddress + ", connecting…");
                main.post(() -> {
                    Intent i = new Intent(ProvisionActivity.this, CameraActivity.class);
                    i.putExtra(CameraActivity.EXTRA_ADDRESS, foundAddress);
                    i.putExtra(CameraActivity.EXTRA_NAME, expectedName);
                    startActivity(i);
                    finish();
                });
            }
            @Override public void onScanFailed(int errorCode) { appendLog("rescan failed code=" + errorCode); }
        };
        try {
            scanner.startScan(cb);
            appendLog("scanning for " + expectedName + "…");
        } catch (SecurityException e) {
            appendLog("scan permission denied");
            return;
        }
        main.postDelayed(() -> {
            try { scanner.stopScan(cb); } catch (SecurityException ignored) {}
        }, RESCAN_AFTER_PROVISION_TIMEOUT_MS);
    }
}
