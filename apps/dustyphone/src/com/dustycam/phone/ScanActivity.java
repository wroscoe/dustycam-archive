package com.dustycam.phone;

import android.Manifest;
import android.app.Activity;
import android.bluetooth.BluetoothAdapter;
import android.bluetooth.BluetoothManager;
import android.bluetooth.le.BluetoothLeScanner;
import android.bluetooth.le.ScanCallback;
import android.bluetooth.le.ScanResult;
import android.bluetooth.le.ScanSettings;
import android.content.pm.PackageManager;
import android.content.Intent;
import android.os.Build;
import android.os.Bundle;
import android.os.ParcelUuid;
import android.util.SparseArray;
import android.util.TypedValue;
import android.view.Gravity;
import android.view.Menu;
import android.view.MenuItem;
import android.view.View;
import android.view.ViewGroup;
import android.widget.BaseAdapter;
import android.widget.LinearLayout;
import android.widget.ListView;
import android.widget.TextView;

import com.dustycam.phone.ble.DustyLink;

import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/**
 * Launcher screen: scans for {@code dc-*} camera advertisers and lists them
 * (name, address, rssi, provisioned flag). Tapping one opens
 * {@link CameraActivity} (docs/phone_app_plan.md §4).
 *
 * <p>No camera advertises until one is flashed with the BLE spike (P1), so an
 * empty list here is the expected P0 state — this screen exists to prove
 * permissions, scanning, and the hand-off into {@code CameraActivity} work.
 */
public class ScanActivity extends Activity {

    private static final String TAG = "Dusty";
    private static final int REQ_PERMISSIONS = 1;

    /**
     * On the wire the manufacturer-data AD structure starts with the 2-byte
     * company id, little-endian: {@code [0xDC 0x0A]} -&gt; 0x0ADC
     * (docs/phone_app_plan.md §2 "Advertising"). Android's
     * getManufacturerSpecificData() keys its SparseArray by that same
     * little-endian-interpreted int.
     */
    private static final int MANUFACTURER_ID = 0x0ADC;
    private static final String NAME_PREFIX = "dc-";

    private BluetoothAdapter adapter;
    private BluetoothLeScanner scanner;
    private TextView status;
    private ScanAdapter listAdapter;
    private final Map<String, Entry> found = new LinkedHashMap<>();
    private boolean scanning = false;

    private static final class Entry {
        String name;
        String address;
        int rssi;
        boolean provisioned;
        boolean provFieldKnown;
    }

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);

        LinearLayout root = new LinearLayout(this);
        root.setOrientation(LinearLayout.VERTICAL);

        status = new TextView(this);
        status.setGravity(Gravity.CENTER);
        status.setTextSize(TypedValue.COMPLEX_UNIT_SP, 16);
        status.setPadding(dp(24), dp(24), dp(24), dp(16));
        status.setText("Press the camera's button, then scan.");
        root.addView(status);

        ListView list = new ListView(this);
        listAdapter = new ScanAdapter();
        list.setAdapter(listAdapter);
        list.setOnItemClickListener((parent, view, pos, id) -> {
            Entry e = listAdapter.getItem(pos);
            // Unprovisioned (dc-new-…, mfg flags bit0==0) -> provisioning, not the
            // bench control panel: there's no owner session to authenticate yet.
            if (e.provFieldKnown && !e.provisioned) {
                Intent i = new Intent(this, ProvisionActivity.class);
                i.putExtra(ProvisionActivity.EXTRA_ADDRESS, e.address);
                i.putExtra(ProvisionActivity.EXTRA_NAME, e.name);
                startActivity(i);
                return;
            }
            Intent i = new Intent(this, CameraActivity.class);
            i.putExtra(CameraActivity.EXTRA_ADDRESS, e.address);
            i.putExtra(CameraActivity.EXTRA_NAME, e.name);
            startActivity(i);
        });
        root.addView(list, new LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.MATCH_PARENT, 0, 1f));

        setContentView(root);

        BluetoothManager bm = (BluetoothManager) getSystemService(BLUETOOTH_SERVICE);
        adapter = bm.getAdapter();

        ensurePermissions();
    }

    @Override
    protected void onResume() {
        super.onResume();
        if (hasPermissions() && adapter != null && adapter.isEnabled()) startScan();
    }

    @Override
    protected void onPause() {
        super.onPause();
        stopScan();
    }

    // ---- permissions ----

    private String[] neededPermissions() {
        if (Build.VERSION.SDK_INT >= 31) {
            return new String[]{Manifest.permission.BLUETOOTH_SCAN, Manifest.permission.BLUETOOTH_CONNECT};
        }
        return new String[]{Manifest.permission.ACCESS_FINE_LOCATION};
    }

    private boolean hasPermissions() {
        for (String p : neededPermissions()) {
            if (checkSelfPermission(p) != PackageManager.PERMISSION_GRANTED) return false;
        }
        return true;
    }

    private void ensurePermissions() {
        if (!hasPermissions()) {
            requestPermissions(neededPermissions(), REQ_PERMISSIONS);
            return;
        }
        if (adapter == null) {
            status.setText("This device has no Bluetooth adapter.");
        } else if (!adapter.isEnabled()) {
            status.setText("Turn on Bluetooth, then reopen Dusty.");
        }
    }

    @Override
    public void onRequestPermissionsResult(int req, String[] perms, int[] results) {
        if (req != REQ_PERMISSIONS) return;
        boolean allGranted = results.length > 0;
        for (int r : results) if (r != PackageManager.PERMISSION_GRANTED) allGranted = false;
        if (allGranted) {
            status.setText("Press the camera's button, then scan.");
            if (adapter != null && adapter.isEnabled()) startScan();
        } else {
            status.setText("Dusty needs Bluetooth permission to find cameras.\n"
                    + "Grant it in Settings → Apps → Dusty → Permissions.");
        }
    }

    // ---- menu ----

    private static final int MENU_PROVISION = 1;

    @Override
    public boolean onCreateOptionsMenu(Menu menu) {
        menu.add(0, MENU_PROVISION, 0, "Provision a camera");
        return true;
    }

    @Override
    public boolean onOptionsItemSelected(MenuItem item) {
        if (item.getItemId() == MENU_PROVISION) {
            openProvisionFromMenu();
            return true;
        }
        return super.onOptionsItemSelected(item);
    }

    /** Alternate entry point to ProvisionActivity (besides tapping an unprovisioned row directly). */
    private void openProvisionFromMenu() {
        List<Entry> unprovisioned = new ArrayList<>();
        for (Entry e : found.values()) {
            if (e.provFieldKnown && !e.provisioned) unprovisioned.add(e);
        }
        Intent i = new Intent(this, ProvisionActivity.class);
        if (unprovisioned.isEmpty()) {
            // Still open it: importing the owner profile (dusty_phone.json)
            // is needed before talking to ANY camera built with the real key,
            // provisioned or not. ProvisionActivity handles a null address.
            status.setText("No unprovisioned camera in view — you can still import a profile.");
            startActivity(i);
            return;
        }
        Entry pick = unprovisioned.get(0);
        if (unprovisioned.size() > 1) {
            status.setText("Multiple unprovisioned cameras found; opening " + pick.name
                    + " (tap a specific row instead to pick another).");
        }
        i.putExtra(ProvisionActivity.EXTRA_ADDRESS, pick.address);
        i.putExtra(ProvisionActivity.EXTRA_NAME, pick.name);
        startActivity(i);
    }

    // ---- scanning ----

    private void startScan() {
        if (scanning || adapter == null) return;
        scanner = adapter.getBluetoothLeScanner();
        if (scanner == null) return;

        found.clear();
        listAdapter.notifyDataSetChanged();

        // No OS-level ScanFilter: some stacks are flaky about surfacing 128-bit
        // service UUIDs through the filter path, so filtering (by service UUID,
        // falling back to the `dc-` name prefix) happens in the callback instead
        // (docs/phone_app_plan.md §4 ScanActivity).
        ScanSettings settings = new ScanSettings.Builder()
                .setScanMode(ScanSettings.SCAN_MODE_LOW_LATENCY)
                .build();

        try {
            scanner.startScan(null, settings, scanCallback);
            scanning = true;
            status.setText("Scanning… press the camera's button.");
        } catch (SecurityException e) {
            status.setText("Bluetooth permission was denied.");
        }
    }

    private void stopScan() {
        if (!scanning || scanner == null) return;
        try {
            scanner.stopScan(scanCallback);
        } catch (SecurityException ignored) {}
        scanning = false;
    }

    private final ScanCallback scanCallback = new ScanCallback() {
        @Override
        public void onScanResult(int callbackType, ScanResult result) {
            // The BluetoothDevice name cache can be null on first sight of an
            // address; the advertisement's own scan record (Local Name AD
            // structure) is available immediately and doesn't need it (review
            // finding #7).
            String name = result.getScanRecord() != null ? result.getScanRecord().getDeviceName() : null;
            if (name == null) {
                try {
                    name = result.getDevice().getName();
                } catch (SecurityException e) {
                    name = null;
                }
            }
            boolean byService = result.getScanRecord() != null
                    && result.getScanRecord().getServiceUuids() != null
                    && result.getScanRecord().getServiceUuids()
                            .contains(ParcelUuid.fromString(DustyLink.SVC_UUID.toString()));
            boolean byName = name != null && name.startsWith(NAME_PREFIX);
            android.util.Log.d("Dusty", "scan " + result.getDevice().getAddress() + " rssi=" + result.getRssi()
                    + " name=" + name + " svc=" + byService);
            if (!byService && !byName) return;

            Entry e = new Entry();
            e.name = name != null ? name : "(unnamed)";
            e.address = result.getDevice().getAddress();
            e.rssi = result.getRssi();

            if (result.getScanRecord() != null) {
                SparseArray<byte[]> mfg = result.getScanRecord().getManufacturerSpecificData();
                byte[] payload = mfg != null ? mfg.get(MANUFACTURER_ID) : null;
                if (payload != null && payload.length >= 2) {
                    // [proto u8][flags u8]; bit0 of flags = provisioned.
                    e.provisioned = (payload[1] & 0x01) != 0;
                    e.provFieldKnown = true;
                }
            }

            found.put(e.address, e);
            runOnUiThread(listAdapter::notifyDataSetChanged);
        }

        @Override
        public void onScanFailed(int errorCode) {
            runOnUiThread(() -> status.setText("Scan failed (code " + errorCode + ")."));
        }
    };

    private int dp(int v) {
        return Math.round(v * getResources().getDisplayMetrics().density);
    }

    private class ScanAdapter extends BaseAdapter {
        @Override public int getCount() { return found.size(); }
        @Override public Entry getItem(int pos) { return new ArrayList<>(found.values()).get(pos); }
        @Override public long getItemId(int pos) { return pos; }

        @Override
        public View getView(int pos, View convert, ViewGroup parent) {
            TextView tv = convert instanceof TextView ? (TextView) convert : new TextView(ScanActivity.this);
            tv.setPadding(dp(24), dp(16), dp(24), dp(16));
            tv.setTextSize(TypedValue.COMPLEX_UNIT_SP, 16);
            Entry e = getItem(pos);
            String provStr = e.provFieldKnown ? (e.provisioned ? "provisioned" : "UNPROVISIONED") : "prov?";
            tv.setText(e.name + "\n" + e.address + "   " + e.rssi + " dBm   " + provStr);
            return tv;
        }
    }
}
