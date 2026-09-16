package com.dustycam.phone;

import android.content.Context;
import android.content.SharedPreferences;

import org.json.JSONArray;
import org.json.JSONObject;

/**
 * App-private settings (docs/phone_app_plan.md §4). Holds the BLE owner key,
 * the last camera the app talked to, and — once {@code ProvisionActivity}
 * imports one — the full {@code dusty_phone.json} profile (server host/port/
 * tls/token, hotspot ssid/pass, ble_key, known camera ids). Everything here
 * is app-private {@link SharedPreferences} (MODE_PRIVATE); callers must never
 * log the secret fields (token, pass, ble_key) — only structural facts about
 * them (lengths, presence, host names).
 */
public class Prefs {

    private static final String FILE = "dustyphone_prefs";
    private static final String KEY_BLE_KEY = "ble_key_hex";
    private static final String KEY_LAST_ADDRESS = "last_camera_address";
    private static final String KEY_LAST_IP = "last_camera_ip";
    private static final String KEY_IMPORTED_PROFILE = "imported_profile_json";

    /**
     * DEV ONLY bench key, compiled into the firmware spike (plan §1 decision
     * 5, §6 P0 row). PUBLIC, NOT A SECRET: it is SHA-256 of the string
     * "dustycam public bench BLE key - NOT A SECRET", so anyone can derive it;
     * it only ever unlocks a bench build of ble_spike. Real cameras use the
     * owner key from ~/.dusty/secrets.toml, imported via dusty_phone.json. Replace by importing a real {@code dusty_phone.json} once
     * {@code ProvisionActivity} exists (P2) — the UI labels this key "DEV".
     */
    public static final String DEV_BLE_KEY_HEX =
            "d2759966293ad602e12d68ec8a712703141a998ca2abf18e447fd11dc9630139";

    private final SharedPreferences sp;

    public Prefs(Context ctx) {
        sp = ctx.getApplicationContext().getSharedPreferences(FILE, Context.MODE_PRIVATE);
    }

    public String bleKeyHex() {
        return sp.getString(KEY_BLE_KEY, DEV_BLE_KEY_HEX);
    }

    public void setBleKeyHex(String hex) {
        sp.edit().putString(KEY_BLE_KEY, hex).apply();
    }

    public boolean isDevKey() {
        return DEV_BLE_KEY_HEX.equals(bleKeyHex());
    }

    public String lastCameraAddress() {
        return sp.getString(KEY_LAST_ADDRESS, null);
    }

    public void setLastCameraAddress(String address) {
        sp.edit().putString(KEY_LAST_ADDRESS, address).apply();
    }

    public String lastIp() {
        return sp.getString(KEY_LAST_IP, null);
    }

    public void setLastIp(String ip) {
        sp.edit().putString(KEY_LAST_IP, ip).apply();
    }

    // ---- imported dusty_phone.json profile (ProvisionActivity) ----

    public boolean hasImportedProfile() {
        return sp.contains(KEY_IMPORTED_PROFILE);
    }

    /** Stores the raw profile JSON verbatim; callers set ble_key separately via {@link #setBleKeyHex}. */
    public void setImportedProfile(String profileJson) {
        sp.edit().putString(KEY_IMPORTED_PROFILE, profileJson).apply();
    }

    public String importedProfileJson() {
        return sp.getString(KEY_IMPORTED_PROFILE, null);
    }

    /** For a status line only ("N camera id(s) imported") — never the ids' surrounding secrets. */
    public int importedCameraCount() {
        String json = importedProfileJson();
        if (json == null) return 0;
        try {
            JSONObject profile = new JSONObject(json);
            JSONArray cameras = profile.optJSONArray("cameras");
            return cameras != null ? cameras.length() : 0;
        } catch (Exception e) {
            return 0;
        }
    }
}
