package com.dustycam.phone;

import android.app.Activity;
import android.app.AlertDialog;
import android.bluetooth.BluetoothAdapter;
import android.bluetooth.BluetoothManager;
import android.bluetooth.le.BluetoothLeScanner;
import android.bluetooth.le.ScanCallback;
import android.bluetooth.le.ScanResult;
import android.bluetooth.le.ScanSettings;
import android.graphics.Bitmap;
import android.graphics.BitmapFactory;
import android.os.Bundle;
import android.os.Handler;
import android.os.Looper;
import android.text.method.ScrollingMovementMethod;
import android.util.Log;
import android.util.TypedValue;
import android.view.Gravity;
import android.view.View;
import android.widget.Button;
import android.widget.HorizontalScrollView;
import android.widget.ImageView;
import android.widget.LinearLayout;
import android.widget.ScrollView;
import android.widget.TextView;

import com.dustycam.phone.ble.DustyLink;
import com.dustycam.phone.net.Beacon;
import com.dustycam.phone.net.CamHttp;
import com.dustycam.phone.ui.Brand;
import com.dustycam.phone.ui.SettingsForm;

import org.json.JSONArray;
import org.json.JSONException;
import org.json.JSONObject;

import java.text.SimpleDateFormat;
import java.util.Locale;
import java.util.TimeZone;

/**
 * P0 test bench (docs/phone_app_plan.md §4, §6 P0 row): one screen exercising
 * every P0 op, the BLE&lt;-&gt;Wi-Fi handoff, and the reconnect-by-address path.
 * This is deliberately a raw control panel, not the polished P2 UI (schema
 * form, frame grid, etc.) — a log line per action plus a handful of buttons
 * is what proves the protocol and the radio state machine.
 */
public class CameraActivity extends Activity {

    public static final String EXTRA_ADDRESS = "address";
    public static final String EXTRA_NAME = "name";

    private static final String TAG = "Dusty";
    private static final long RESCAN_TIMEOUT_MS = 30_000;
    private static final long GATT_RELEASE_DELAY_MS = 60_000;
    // Camera's hotspot_join_s is 90 (plan §4.1); wait 10s past that for its
    // beacon before giving up (review finding #6).
    private static final int WIFI_POLL_TIMEOUT_S = 100;

    private final Session session = new Session();
    private final Handler main = new Handler(Looper.getMainLooper());
    private final SimpleDateFormat timeFmt = new SimpleDateFormat("HH:mm:ss.SSS", Locale.US);

    private String address;
    private String cameraName;
    private BluetoothAdapter adapter;
    private DustyLink link;
    private CamHttp camHttp;
    private Prefs prefs;

    private TextView banner;
    private TextView log;
    private ScrollView logScroll;
    private ImageView image;
    private LinearLayout contentStack; // image + logScroll, swapped out for the Settings panel
    private Button btnStatus, btnPreview, btnThumb, btnShoot, btnViewWifi, btnLive;
    private Button btnWifiScan, btnProvGet, btnContact, btnSettingsToggle;
    private Button btnBringBack;
    private Button btnReconnect;

    // Settings panel (docs/phone_app_plan.md §4 ui/SettingsForm.java).
    private SettingsForm settingsForm;
    private View settingsPanelView;
    private TextView settingsBadge;
    private TextView settingsBanner;
    private Button btnSettingsSave;
    private boolean settingsOpen = false;

    /** From the connected camera's `info` (§2); used to match beacons to it. */
    private String cameraDeviceId;
    /** Reason from the last `evt bye` (§2: "handoff"|"window"|"live"), consumed by onLinkLost(). */
    private String lastByeReason;
    private Beacon beacon;
    private Runnable wifiStatusPoller;
    private static final long WIFI_STATUS_POLL_MS = 3000;

    private Runnable rescanTimeoutRunnable;
    private BluetoothLeScanner rescanScanner;
    private boolean rescanning = false;
    private Runnable releaseGattRunnable;

    // Cycle x10 driver (gate P0.1b).
    private int cyclesRemaining = 0;
    private long cycleWifiStartMs;
    private long cycleBleStartMs;

    /** Set in onDestroy so async callbacks (rescan, poll, link events) become no-ops. */
    private boolean closed = false;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        address = getIntent().getStringExtra(EXTRA_ADDRESS);
        cameraName = getIntent().getStringExtra(EXTRA_NAME);
        prefs = new Prefs(this);
        prefs.setLastCameraAddress(address);
        session.setCameraAddress(address);
        session.setLastIp(prefs.lastIp());

        BluetoothManager bm = (BluetoothManager) getSystemService(BLUETOOTH_SERVICE);
        adapter = bm.getAdapter();
        camHttp = new CamHttp(this);

        buildUi();
        session.addListener(s -> main.post(() -> {
            refreshBanner();
            updateButtonStates();
        }));
        refreshBanner();
        updateButtonStates();

        appendLog("connecting to " + cameraName + " (" + address + ")"
                + (prefs.isDevKey() ? " [DEV key]" : ""));
        connectLink();
    }

    @Override
    protected void onStart() {
        super.onStart();
        if (releaseGattRunnable != null) {
            main.removeCallbacks(releaseGattRunnable);
            releaseGattRunnable = null;
        }
    }

    @Override
    protected void onStop() {
        super.onStop();
        // Bench finding #1: stop listening for the camera's Wi-Fi beacon
        // whenever the activity isn't visible — no point polling in the
        // background, and it's one less socket to worry about across a
        // configuration/visibility change.
        stopBeaconListener();
        stopWifiStatusPolling();
        // §4 "Foreground rules": GATT held while an activity is started,
        // released 60 s after onStop.
        releaseGattRunnable = () -> {
            appendLog("60s in background: releasing GATT");
            if (link != null) link.disconnect();
        };
        main.postDelayed(releaseGattRunnable, GATT_RELEASE_DELAY_MS);
    }

    @Override
    protected void onDestroy() {
        super.onDestroy();
        // Set before disconnect(): that call synchronously flips DustyLink to
        // DISCONNECTED, which would otherwise route through onLinkLost() and
        // kick off a rescan (and further UI updates) on a dying activity
        // (review finding #6).
        closed = true;
        stopRescan();
        stopBeaconListener();
        stopWifiStatusPolling();
        if (link != null) link.disconnect();
        camHttp.release();
    }

    // ---- UI ----

    private void buildUi() {
        LinearLayout root = new LinearLayout(this);
        root.setOrientation(LinearLayout.VERTICAL);
        root.addView(Brand.buildHeader(this, getString(R.string.kicker_camera)));

        banner = new TextView(this);
        banner.setTextSize(TypedValue.COMPLEX_UNIT_SP, 16);
        banner.setGravity(Gravity.CENTER);
        banner.setPadding(dp(16), dp(12), dp(16), dp(12));
        banner.setBackgroundColor(getColor(R.color.dc_clay_deep));
        banner.setTextColor(getColor(R.color.dc_paper));
        root.addView(banner, new LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.MATCH_PARENT, LinearLayout.LayoutParams.WRAP_CONTENT));

        image = new ImageView(this);
        image.setAdjustViewBounds(true);
        image.setBackgroundColor(getColor(R.color.dc_line));

        log = new TextView(this);
        log.setTextSize(TypedValue.COMPLEX_UNIT_SP, 12);
        log.setTypeface(android.graphics.Typeface.MONOSPACE);
        log.setTextColor(getColor(R.color.dc_ink));
        log.setPadding(dp(12), dp(8), dp(12), dp(8));
        log.setMovementMethod(new ScrollingMovementMethod());
        logScroll = new ScrollView(this);
        // Background lives on the scroll view, not the TextView: the TextView
        // is only as tall as the log text, so a background on it grew a
        // paper patch line-by-line against the bone window while the log was
        // shorter than the viewport.
        logScroll.setBackgroundColor(getColor(R.color.dc_paper));
        logScroll.addView(log, new ScrollView.LayoutParams(
                ScrollView.LayoutParams.MATCH_PARENT, ScrollView.LayoutParams.WRAP_CONTENT));

        // image + logScroll live in one swappable stack so the Settings panel
        // (a "tab", per the plan) can occupy the same middle area instead.
        contentStack = new LinearLayout(this);
        contentStack.setOrientation(LinearLayout.VERTICAL);
        contentStack.addView(image, new LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.MATCH_PARENT, dp(200)));
        contentStack.addView(logScroll, new LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.MATCH_PARENT, 0, 1f));
        root.addView(contentStack, new LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.MATCH_PARENT, 0, 1f));

        settingsPanelView = buildSettingsPanel();
        settingsPanelView.setVisibility(View.GONE);
        root.addView(settingsPanelView, new LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.MATCH_PARENT, 0, 1f));

        HorizontalScrollView buttonScroll = new HorizontalScrollView(this);
        LinearLayout buttons = new LinearLayout(this);
        buttons.setOrientation(LinearLayout.HORIZONTAL);
        buttons.setPadding(dp(8), dp(8), dp(8), dp(8));

        btnReconnect = makeButton("Reconnect", this::onReconnectButton);
        buttons.addView(btnReconnect);
        btnStatus = makeButton("Status", this::onStatus);
        buttons.addView(btnStatus);
        btnPreview = makeButton("Preview", this::onPreview);
        buttons.addView(btnPreview);
        btnThumb = makeButton("Thumb", this::onThumb);
        buttons.addView(btnThumb);
        btnShoot = makeButton("Shoot", this::onShoot);
        buttons.addView(btnShoot);
        btnWifiScan = makeButton("Wifi Scan", this::onWifiScan);
        buttons.addView(btnWifiScan);
        btnProvGet = makeButton("Prov Get", this::onProvGet);
        buttons.addView(btnProvGet);
        btnViewWifi = makeButton("View over Wi-Fi", () -> onViewOverWifi(null));
        buttons.addView(btnViewWifi);
        btnContact = makeButton("Contact", () -> onContact(null));
        buttons.addView(btnContact);
        btnBringBack = makeButton("Bring back to Bluetooth", () -> onBringBack(null));
        buttons.addView(btnBringBack);
        btnLive = makeButton("Live", this::onLive);
        buttons.addView(btnLive);
        btnSettingsToggle = makeButton("Settings", this::onSettingsToggle);
        buttons.addView(btnSettingsToggle);
        buttons.addView(makeButton("Cycle ×10", this::onCycle10));

        buttonScroll.addView(buttons);
        root.addView(buttonScroll, new LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.MATCH_PARENT, LinearLayout.LayoutParams.WRAP_CONTENT));

        setContentView(root);
    }

    private Button makeButton(String text, Runnable onClick) {
        Button b = new Button(this);
        b.setText(text);
        b.setOnClickListener(v -> onClick.run());
        Brand.styleButton(this, b);
        LinearLayout.LayoutParams lp = new LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.WRAP_CONTENT, LinearLayout.LayoutParams.WRAP_CONTENT);
        lp.setMargins(dp(6), dp(4), dp(6), dp(4));
        b.setLayoutParams(lp);
        return b;
    }

    private int dp(int v) {
        return Math.round(v * getResources().getDisplayMetrics().density);
    }

    /** Settings tab/panel (docs/phone_app_plan.md §4): schema-driven form + save/badge chrome around it. */
    private View buildSettingsPanel() {
        LinearLayout col = new LinearLayout(this);
        col.setOrientation(LinearLayout.VERTICAL);

        settingsBanner = new TextView(this);
        settingsBanner.setPadding(dp(16), dp(8), dp(16), dp(4));
        settingsBanner.setTextColor(getColor(R.color.dc_ink));
        settingsBanner.setText("Settings — open while READY to load cfg.schema / cfg.get");
        col.addView(settingsBanner);

        settingsBadge = new TextView(this);
        settingsBadge.setPadding(dp(16), 0, dp(16), dp(8));
        settingsBadge.setTextColor(getColor(R.color.dc_muted));
        settingsBadge.setText("cfg_src: ?");
        col.addView(settingsBadge);

        settingsForm = new SettingsForm(this);
        col.addView(settingsForm.getView(), new LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.MATCH_PARENT, 0, 1f));

        btnSettingsSave = new Button(this);
        btnSettingsSave.setText("Save");
        btnSettingsSave.setOnClickListener(v -> onSettingsSave());
        Brand.styleButton(this, btnSettingsSave);
        LinearLayout.LayoutParams saveLp = new LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.WRAP_CONTENT, LinearLayout.LayoutParams.WRAP_CONTENT);
        saveLp.setMargins(dp(16), dp(8), dp(16), dp(12));
        col.addView(btnSettingsSave, saveLp);

        return col;
    }

    private void refreshBanner() {
        banner.setText(session.banner());
        banner.setBackgroundColor(Brand.bannerColor(this, session.getState()));
    }

    /**
     * Bench finding #3: the op buttons used to fire straight into the void
     * while disconnected (e.g. a stray `preview` tap while LOST); gate them on
     * DustyLink actually being READY, and only offer Reconnect while LOST.
     */
    private void updateButtonStates() {
        boolean ready = link != null && link.getState() == DustyLink.State.READY;
        btnStatus.setEnabled(ready);
        btnPreview.setEnabled(ready);
        btnThumb.setEnabled(ready);
        btnShoot.setEnabled(ready);
        btnWifiScan.setEnabled(ready);
        btnProvGet.setEnabled(ready);
        btnViewWifi.setEnabled(ready);
        btnContact.setEnabled(ready);
        btnLive.setEnabled(ready);
        btnSettingsToggle.setEnabled(ready || settingsOpen); // allow closing the panel even if the link dropped
        btnReconnect.setEnabled(session.getState() == Session.State.LOST);
        if (settingsForm != null) settingsForm.setEnabled(ready);
        if (btnSettingsSave != null) btnSettingsSave.setEnabled(ready);
    }

    private void appendLog(String line) {
        String stamped = timeFmt.format(new java.util.Date()) + "  " + line;
        Log.i(TAG, stamped);
        if (closed) return; // avoid touching views after onDestroy (review finding #6)
        main.post(() -> {
            if (closed) return;
            log.append(stamped + "\n");
            logScroll.post(() -> logScroll.fullScroll(View.FOCUS_DOWN));
        });
    }

    // ---- BLE link ----

    private void connectLink() {
        link = new DustyLink(this, com.dustycam.phone.ble.Crypto.fromHex(prefs.bleKeyHex()), linkListener);
        link.connect(adapter, address);
    }

    private final DustyLink.Listener linkListener = new DustyLink.Listener() {
        @Override public void onStateChanged(DustyLink.State s) {
            appendLog("link state=" + s);
            updateButtonStates();
            if (s == DustyLink.State.READY) {
                directReconnectFallback = null;
                session.setState(Session.State.BLE);
                prefs.setLastCameraAddress(address);
                syncTime();
                if (pendingBleReachedCallback != null) {
                    Runnable cb = pendingBleReachedCallback;
                    pendingBleReachedCallback = null;
                    cb.run();
                }
            } else if (s == DustyLink.State.DISCONNECTED || s == DustyLink.State.FAILED) {
                if (session.getState() == Session.State.RETURNING && directReconnectFallback != null) {
                    Runnable fb = directReconnectFallback;
                    directReconnectFallback = null;
                    fb.run();
                    return;
                }
                onLinkLost();
            }
        }

        @Override public void onEvent(JSONObject evt) {
            appendLog("evt: " + evt);
            String ev = evt.optString("ev", "");
            if ("bye".equals(ev)) {
                String reason = evt.optString("reason", "");
                lastByeReason = reason; // consumed by onLinkLost() below
                if ("handoff".equals(reason)) {
                    // Belt-and-suspenders: startHandoff() already set HANDOFF the
                    // moment it sent the request, precisely so the GATT disconnect
                    // that follows this event can never race onLinkLost() into
                    // treating a handoff as an unexpected loss (bench finding).
                    session.setState(Session.State.HANDOFF);
                } else {
                    session.setState(Session.State.LOST);
                }
            }
        }

        @Override public void onInfo(JSONObject info) {
            appendLog("info: " + info);
            cameraDeviceId = info.optString("device", cameraDeviceId);
        }
    };

    /** Unexpected disconnect while we still expect to be on BLE: rescan by address. */
    private void onLinkLost() {
        if (closed) return;
        String byeReason = lastByeReason;
        lastByeReason = null;
        Session.State s = session.getState();
        if (s == Session.State.HANDOFF || s == Session.State.WIFI || s == Session.State.RETURNING) {
            // Expected: the camera tore its GATT down for the Wi-Fi phase.
            // (startHandoff() sets HANDOFF synchronously when it sends the
            // request, before any disconnect can land, so this is reliable.)
            return;
        }
        session.setState(Session.State.LOST);
        stopBeaconListener();
        if ("live".equals(byeReason) || "window".equals(byeReason)) {
            // A deliberate disconnect the camera told us about ahead of time
            // (§2 evt bye: "live" = the `live` op just ended the window and
            // the camera is sleeping; "window" = ble_adv_s ran out with no
            // link): not a loss, and a 30s BLE rescan would just spin against
            // a camera that is intentionally not advertising — skip it.
            appendLog("camera ended the window (" + byeReason + ") and is asleep — press its button to reconnect");
            return;
        }
        appendLog("link lost unexpectedly");
        beginReconnectRescan();
    }

    /** Manual "Reconnect" button (only enabled while LOST). */
    private void onReconnectButton() {
        if (session.getState() != Session.State.LOST) return;
        beginReconnectRescan();
    }

    /** Rescans for the camera's BLE address and reconnects once found. Shared by every LOST path. */
    private void beginReconnectRescan() {
        appendLog("rescanning for " + RESCAN_TIMEOUT_MS / 1000 + "s");
        rescanForAddress(RESCAN_TIMEOUT_MS, () -> {
            appendLog("found camera again by address, reconnecting");
            reconnectAfterRescan();
        }, () -> appendLog("rescan timed out; press the camera's button"));
    }

    /**
     * Every "found the camera again by address, reconnect" path funnels
     * through here so the previous {@link DustyLink} (and the BluetoothGatt it
     * holds) is always torn down first — creating a second one on top of it
     * leaks a GATT client, and Android caps ~32 per process (review finding
     * #4).
     */
    private void reconnectAfterRescan() {
        if (closed) return;
        if (link != null) {
            // Detach first: the old link's DISCONNECTED must not trigger the
            // direct-reconnect fallback meant for the new one.
            DustyLink old = link;
            link = null;
            old.detach();
            old.disconnect();
        }
        connectLink();
    }

    /** Address-filtered rescan (no service-UUID filter needed: we already know the MAC). */
    private void rescanForAddress(long timeoutMs, Runnable onFound, Runnable onTimeout) {
        if (closed || rescanning) return;
        rescanScanner = adapter.getBluetoothLeScanner();
        if (rescanScanner == null) {
            onTimeout.run();
            return;
        }
        rescanning = true;
        ScanSettings settings = new ScanSettings.Builder()
                .setScanMode(ScanSettings.SCAN_MODE_LOW_LATENCY)
                .build();
        ScanCallback cb = new ScanCallback() {
            @Override public void onScanResult(int callbackType, ScanResult result) {
                if (address.equals(result.getDevice().getAddress())) {
                    stopRescan();
                    onFound.run();
                }
            }
            @Override public void onScanFailed(int errorCode) {
                appendLog("rescan failed code=" + errorCode);
            }
        };
        try {
            rescanScanner.startScan(cb);
        } catch (SecurityException e) {
            rescanning = false;
            onTimeout.run();
            return;
        }
        rescanTimeoutRunnable = () -> {
            if (!rescanning) return;
            try { rescanScanner.stopScan(cb); } catch (SecurityException ignored) {}
            rescanning = false;
            onTimeout.run();
        };
        main.postDelayed(rescanTimeoutRunnable, timeoutMs);
        // Remember the callback so stopRescan() (found path) can also stop it.
        this.activeRescanCallback = cb;
    }

    private ScanCallback activeRescanCallback;

    private void stopRescan() {
        if (rescanTimeoutRunnable != null) {
            main.removeCallbacks(rescanTimeoutRunnable);
            rescanTimeoutRunnable = null;
        }
        if (rescanning && rescanScanner != null && activeRescanCallback != null) {
            try { rescanScanner.stopScan(activeRescanCallback); } catch (SecurityException ignored) {}
        }
        rescanning = false;
    }

    // ---- button actions ----

    private void onStatus() {
        link.request("status", null, new DustyLink.OpCallback() {
            @Override public void onResponse(JSONObject rsp) {
                appendLog("status: " + rsp.toString());
            }
            @Override public void onError(String err) {
                appendLog("status error: " + err);
            }
        });
    }

    private void onPreview() {
        link.request("preview", null, new DustyLink.OpCallback() {
            @Override public void onData(byte[] data, double kbPerSec) {
                appendLog("preview: " + data.length + " B, " + String.format("%.1f", kbPerSec) + " KB/s");
                showImage(data);
            }
            @Override public void onResponse(JSONObject rsp) {
                appendLog("preview stats: focus=" + rsp.opt("focus") + " lum=" + rsp.opt("lum"));
            }
            @Override public void onError(String err) {
                appendLog("preview error: " + err);
            }
        });
    }

    private void onThumb() {
        JSONObject args = new JSONObject();
        try { args.put("tier", "spool"); args.put("n", 1); } catch (JSONException ignored) {}
        link.request("spool.list", args, new DustyLink.OpCallback() {
            @Override public void onResponse(JSONObject rsp) {
                JSONArray items = rsp.optJSONArray("items");
                if (items == null || items.length() == 0) {
                    appendLog("thumb: spool is empty");
                    return;
                }
                JSONObject item = items.optJSONObject(0);
                appendLog("thumb: first item " + item);
                JSONObject thumbArgs = new JSONObject();
                try {
                    thumbArgs.put("boot", item.optInt("boot"));
                    thumbArgs.put("seq", item.optInt("seq"));
                } catch (JSONException ignored) {}
                link.request("thumb", thumbArgs, new DustyLink.OpCallback() {
                    @Override public void onData(byte[] data, double kbPerSec) {
                        appendLog("thumb: " + data.length + " B, " + String.format("%.1f", kbPerSec) + " KB/s");
                        showImage(data);
                    }
                    @Override public void onError(String err) {
                        appendLog("thumb error: " + err);
                    }
                });
            }
            @Override public void onError(String err) {
                appendLog("spool.list error: " + err);
            }
        });
    }

    private void onShoot() {
        link.request("shoot", null, new DustyLink.OpCallback() {
            @Override public void onResponse(JSONObject rsp) {
                appendLog("shoot: " + rsp);
            }
            @Override public void onError(String err) {
                appendLog("shoot error: " + err);
            }
        });
    }

    private void onLive() {
        link.request("live", null, new DustyLink.OpCallback() {
            @Override public void onResponse(JSONObject rsp) {
                appendLog("live: " + rsp);
            }
            @Override public void onError(String err) {
                appendLog("live error: " + err);
            }
        });
    }

    private void onWifiScan() {
        link.request("wifi.scan", null, new DustyLink.OpCallback() {
            @Override public void onResponse(JSONObject rsp) {
                appendLog("wifi.scan: " + rsp.optJSONArray("aps"));
            }
            @Override public void onError(String err) {
                appendLog("wifi.scan error: " + err);
            }
        });
    }

    private void onProvGet() {
        link.request("prov.get", null, new DustyLink.OpCallback() {
            @Override public void onResponse(JSONObject rsp) {
                appendLog("prov.get: " + rsp);
            }
            @Override public void onError(String err) {
                appendLog("prov.get error: " + err);
            }
        });
    }

    /** {@code time.set} on every READY (§2 "Ops"); phone clock is assumed correct. */
    private void syncTime() {
        JSONObject args = new JSONObject();
        try {
            args.put("ts", System.currentTimeMillis() / 1000L);
            args.put("tz_min", TimeZone.getDefault().getOffset(System.currentTimeMillis()) / 60000);
        } catch (JSONException ignored) {}
        link.request("time.set", args, new DustyLink.OpCallback() {
            @Override public void onResponse(JSONObject rsp) {
                appendLog("time.set: " + rsp);
            }
            @Override public void onError(String err) {
                appendLog("time.set error: " + err);
            }
        });
    }

    /** onWifiReached (nullable) fires once the camera's beacon (or a lucky expect_ip hit) lands — used by Cycle x10. */
    private void onViewOverWifi(Runnable onWifiReached) {
        showHandoffDialog("wifi.up", onWifiReached);
    }

    /** Same handoff UX as View over Wi-Fi, but `mode:contact` (full contact sequence, §2 `contact` op). */
    private void onContact(Runnable onWifiReached) {
        showHandoffDialog("contact", onWifiReached);
    }

    private void showHandoffDialog(String op, Runnable onWifiReached) {
        boolean contact = "contact".equals(op);
        new AlertDialog.Builder(this)
                .setTitle(contact ? "Contact sensorhub" : "Switch camera to Wi-Fi")
                .setMessage("Make sure your phone's hotspot is on (2.4 GHz / \"extend compatibility\"). "
                        + "The camera will join it and announce itself.")
                .setPositiveButton(contact ? "Contact" : "Switch", (d, w) -> startHandoff(op, onWifiReached))
                .setNegativeButton("Cancel", null)
                .show();
    }

    private void startHandoff(String op, Runnable onWifiReached) {
        // Set HANDOFF now, synchronously, rather than waiting for the rsp: the
        // camera's disconnect can otherwise land before the app processes the
        // handoff rsp/evt, which used to make onLinkLost() see state==BLE and
        // log a spurious "link lost unexpectedly" (bench finding).
        session.setState(Session.State.HANDOFF);
        JSONObject args = new JSONObject();
        link.request(op, args, new DustyLink.OpCallback() {
            @Override public void onResponse(JSONObject rsp) {
                appendLog(op + " handoff: " + rsp);
                String hintIp = rsp.optString("expect_ip", null);
                if (hintIp != null && hintIp.isEmpty()) hintIp = null;
                cycleWifiStartMs = android.os.SystemClock.elapsedRealtime();
                beginWifiDiscovery(hintIp, onWifiReached);
            }
            @Override public void onError(String err) {
                appendLog(op + " error: " + err);
                if (session.getState() == Session.State.HANDOFF) session.setState(Session.State.BLE);
                if (cyclesRemaining > 0) { appendLog("cycle aborted: " + op + " failed"); cyclesRemaining = 0; }
            }
        });
    }

    /**
     * Bench finding #1: never ask the user to type an IP. The camera
     * broadcasts a UDP beacon (device/ip/port) once per second while its
     * Wi-Fi control plane is up; that's the only IP source. {@code hintIp}
     * (the handoff rsp's {@code expect_ip}) is an optional, best-effort fast
     * path only — it is polled once, unbound, and never surfaced to the user.
     */
    private void beginWifiDiscovery(String hintIp, Runnable onWifiReached) {
        final boolean[] resolved = {false};

        startBeaconListener((device, ip, port) -> {
            if (resolved[0] || closed) return;
            resolved[0] = true;
            appendLog("beacon: " + device + " @ " + ip + ":" + port);
            onWifiIpFound(ip, port, onWifiReached);
        });

        if (hintIp != null) {
            camHttp.getStatus(hintIp, new CamHttp.Callback() {
                @Override public void onResult(int code, String body) {
                    if (resolved[0] || closed) return;
                    if (code == 200) {
                        resolved[0] = true;
                        appendLog("expect_ip hint " + hintIp + " answered directly: " + body);
                        onWifiIpFound(hintIp, 8266, onWifiReached);
                    }
                    // else: keep waiting for the beacon, which is authoritative.
                }
                @Override public void onError(Exception e) { /* beacon remains authoritative */ }
            });
        }

        main.postDelayed(() -> {
            if (resolved[0] || closed) return;
            resolved[0] = true;
            stopBeaconListener();
            appendLog("no camera beacon within " + WIFI_POLL_TIMEOUT_S + "s");
            session.setState(Session.State.LOST);
            if (cyclesRemaining > 0) {
                appendLog("=== Cycle x10 aborted: camera never reached Wi-Fi ===");
                cyclesRemaining = 0;
            }
            beginReconnectRescan();
        }, (long) WIFI_POLL_TIMEOUT_S * 1000);
    }

    private void onWifiIpFound(String ip, int port, Runnable onWifiReached) {
        stopBeaconListener();
        session.setLastIp(ip);
        prefs.setLastIp(ip);
        session.setState(Session.State.WIFI);
        appendLog("Wi-Fi up: camera at " + ip + ":" + port);
        camHttp.getStatus(ip, new CamHttp.Callback() {
            @Override public void onResult(int code, String body) { appendLog("/status -> " + code + " " + body); }
            @Override public void onError(Exception e) { appendLog("/status check failed: " + e); }
        });
        startWifiStatusPolling(ip);
        if (onWifiReached != null) onWifiReached.run();
    }

    /**
     * Bench housekeeping: while WIFI, periodically re-poll `/status` and
     * surface its `drain` and `ble_back_in_s` fields (§2 "HTTP additions") —
     * the two things that tell the bench operator whether the drain is
     * progressing and how long is left before the camera re-advertises BLE
     * on its own.
     */
    private void startWifiStatusPolling(String ip) {
        stopWifiStatusPolling();
        wifiStatusPoller = () -> {
            if (closed || session.getState() != Session.State.WIFI) return;
            camHttp.getStatus(ip, new CamHttp.Callback() {
                @Override public void onResult(int code, String body) {
                    if (code == 200) {
                        try {
                            JSONObject st = new JSONObject(body);
                            appendLog("/status drain=" + st.opt("drain")
                                    + " ble_back_in_s=" + st.opt("ble_back_in_s")
                                    + " win_left_s=" + st.opt("win_left_s"));
                        } catch (JSONException e) {
                            appendLog("/status parse error: " + e);
                        }
                    }
                    if (session.getState() == Session.State.WIFI && wifiStatusPoller != null) {
                        main.postDelayed(wifiStatusPoller, WIFI_STATUS_POLL_MS);
                    }
                }
                @Override public void onError(Exception e) {
                    if (session.getState() == Session.State.WIFI && wifiStatusPoller != null) {
                        main.postDelayed(wifiStatusPoller, WIFI_STATUS_POLL_MS);
                    }
                }
            });
        };
        main.postDelayed(wifiStatusPoller, WIFI_STATUS_POLL_MS);
    }

    private void stopWifiStatusPolling() {
        if (wifiStatusPoller != null) {
            main.removeCallbacks(wifiStatusPoller);
            wifiStatusPoller = null;
        }
    }

    private void startBeaconListener(BeaconMatch onMatch) {
        stopBeaconListener();
        beacon = new Beacon((device, ip, port) -> {
            if (cameraDeviceId != null && !cameraDeviceId.equals(device)) {
                appendLog("beacon from a different camera (" + device + "), ignoring");
                return;
            }
            onMatch.onMatch(device, ip, port);
        });
        beacon.start();
        appendLog("listening for the camera's Wi-Fi beacon (udp/" + Beacon.PORT + ")");
    }

    private void stopBeaconListener() {
        if (beacon != null) {
            beacon.stop();
            beacon = null;
        }
    }

    private interface BeaconMatch {
        void onMatch(String device, String ip, int port);
    }

    /** onBleReached (nullable) fires once BLE is READY again — used by Cycle x10. */
    private void onBringBack(Runnable onBleReached) {
        String ip = session.getLastIp();
        if (ip == null) {
            appendLog("bring-back: no known IP");
            return;
        }
        stopBeaconListener(); // stop listening on POST /ble (bench finding #1)
        stopWifiStatusPolling();
        session.setState(Session.State.RETURNING);
        cycleBleStartMs = android.os.SystemClock.elapsedRealtime();
        camHttp.postBle(ip, new CamHttp.Callback() {
            @Override public void onResult(int code, String body) {
                appendLog("POST /ble -> " + code + " " + body);
                camHttp.release();
                // Connect DIRECTLY to the known address instead of scanning:
                // Android silently suppresses results after 5 startScan()
                // calls in 30 s, which killed cycle 9 of the first Cycle x10
                // run (bench 2026-09-15). The camera re-advertises ~0.5 s
                // after answering POST /ble; connectGatt() uses the stack's
                // own initiator scan, which is not throttled. Fall back to
                // an address-filtered rescan only if the direct attempt
                // fails.
                pendingBleReachedCallback = onBleReached;
                main.postDelayed(() -> {
                    if (closed) return;
                    appendLog("direct reconnect to " + address);
                    directReconnectFallback = () -> {
                        appendLog("direct reconnect failed, rescanning by address");
                        rescanForAddress(RESCAN_TIMEOUT_MS, () -> {
                            appendLog("found camera again by address, reconnecting");
                            reconnectAfterRescan();
                        }, () -> appendLog("rescan timed out after bring-back"));
                    };
                    reconnectAfterRescan();
                }, 1500);
            }
            @Override public void onError(Exception e) {
                appendLog("POST /ble failed: " + e);
            }
        });
    }

    private Runnable pendingBleReachedCallback;
    /** Set while a post-/ble direct connect is in flight; run if it fails. */
    private Runnable directReconnectFallback;

    private void onCycle10() {
        if (cyclesRemaining > 0) {
            // A second tap cancels: the loop checks cyclesRemaining before
            // every step, so this stops it at the next boundary.
            cyclesRemaining = 0;
            appendLog("cycle cancelled");
            return;
        }
        if (link == null || link.getState() != DustyLink.State.READY) {
            appendLog("cycle needs a live Bluetooth link first (Reconnect / Bring back to Bluetooth)");
            return;
        }
        cyclesRemaining = 10;
        appendLog("=== Cycle x10 starting (gate P0.1b) ===");
        runNextCycle();
    }

    private void runNextCycle() {
        if (cyclesRemaining <= 0) {
            appendLog("=== Cycle x10 done ===");
            return;
        }
        int n = 11 - cyclesRemaining;
        if (link == null || link.getState() != DustyLink.State.READY) {
            appendLog("cycle " + n + ": no Bluetooth link, aborting");
            cyclesRemaining = 0;
            return;
        }
        appendLog("--- cycle " + n + "/10: wifi.up ---");
        long t0 = android.os.SystemClock.elapsedRealtime();
        startHandoff("wifi.up", () -> {
            if (cyclesRemaining <= 0) return; // cancelled mid-cycle
            long wifiMs = android.os.SystemClock.elapsedRealtime() - t0;
            appendLog("cycle " + n + ": reached WIFI in " + wifiMs + " ms");
            long t1 = android.os.SystemClock.elapsedRealtime();
            onBringBack(() -> {
                long bleMs = android.os.SystemClock.elapsedRealtime() - t1;
                appendLog("cycle " + n + ": reached BLE in " + bleMs + " ms");
                cyclesRemaining--;
                main.postDelayed(this::runNextCycle, 1000);
            });
        });
    }

    private void showImage(byte[] jpeg) {
        Bitmap bmp = BitmapFactory.decodeByteArray(jpeg, 0, jpeg.length);
        if (bmp != null) main.post(() -> image.setImageBitmap(bmp));
    }

    // ---- settings panel (docs/phone_app_plan.md §4 SettingsForm) ----

    private void onSettingsToggle() {
        if (settingsOpen) {
            settingsOpen = false;
            settingsPanelView.setVisibility(View.GONE);
            contentStack.setVisibility(View.VISIBLE);
            return;
        }
        if (link == null || link.getState() != DustyLink.State.READY) {
            appendLog("settings needs a live Bluetooth link first");
            return;
        }
        settingsOpen = true;
        contentStack.setVisibility(View.GONE);
        settingsPanelView.setVisibility(View.VISIBLE);
        loadSettings();
    }

    private void loadSettings() {
        settingsBanner.setText("loading cfg.schema…");
        appendLog("cfg.schema");
        link.request("cfg.schema", null, new DustyLink.OpCallback() {
            @Override public void onResponse(JSONObject schema) {
                appendLog("cfg.schema: " + schema);
                settingsBanner.setText("loading cfg.get…");
                appendLog("cfg.get");
                link.request("cfg.get", null, new DustyLink.OpCallback() {
                    @Override public void onResponse(JSONObject values) {
                        appendLog("cfg.get: " + values);
                        settingsForm.render(schema, values);
                        settingsForm.setEnabled(link.getState() == DustyLink.State.READY);
                        settingsBanner.setText("cfg " + values.opt("cfg") + " loaded");
                        refreshCfgSrcBadge();
                    }
                    @Override public void onError(String err) {
                        appendLog("cfg.get error: " + err);
                        settingsBanner.setText("cfg.get failed: " + err);
                    }
                });
            }
            @Override public void onError(String err) {
                appendLog("cfg.schema error: " + err);
                settingsBanner.setText("cfg.schema failed: " + err);
            }
        });
    }

    private void refreshCfgSrcBadge() {
        link.request("status", null, new DustyLink.OpCallback() {
            @Override public void onResponse(JSONObject rsp) {
                settingsBadge.setText("cfg_src: " + rsp.optString("cfg_src", "?"));
            }
            @Override public void onError(String err) {
                // leave the badge as-is; not fatal to the form
            }
        });
    }

    private void onSettingsSave() {
        if (link == null || link.getState() != DustyLink.State.READY) {
            appendLog("settings: not connected");
            return;
        }
        JSONObject changed = settingsForm.collectChangedCfg();
        if (changed.length() == 0) {
            appendLog("settings: nothing changed");
            settingsBanner.setText("nothing changed");
            return;
        }
        JSONObject args = new JSONObject();
        try {
            args.put("cfg", changed);
        } catch (JSONException e) {
            appendLog("cfg.set build failed: " + e);
            return;
        }
        appendLog("cfg.set " + changed);
        link.request("cfg.set", args, new DustyLink.OpCallback() {
            @Override public void onResponse(JSONObject rsp) {
                int cfgN = rsp.optInt("cfg", -1);
                appendLog("cfg.set ok: cfg=" + cfgN);
                settingsBanner.setText("cfg " + cfgN + " — syncs to sensorhub at next contact");
                settingsBadge.setText("cfg_src: ble");
                loadSettings(); // refresh so the diff baseline matches the new cfg
            }
            @Override public void onError(String err) {
                appendLog("cfg.set error: " + err);
                settingsBanner.setText("cfg.set failed: " + err);
            }
        });
    }
}
