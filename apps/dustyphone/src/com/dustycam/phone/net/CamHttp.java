package com.dustycam.phone.net;

import android.content.Context;
import android.net.ConnectivityManager;
import android.net.LinkAddress;
import android.net.LinkProperties;
import android.net.Network;
import android.os.Handler;
import android.os.Looper;
import android.util.Log;

import java.io.ByteArrayOutputStream;
import java.io.IOException;
import java.io.InputStream;
import java.io.OutputStream;
import java.net.HttpURLConnection;
import java.net.InetAddress;
import java.net.URL;
import java.nio.charset.StandardCharsets;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;

/**
 * HTTP calls to the camera's {@code :8266} control plane during the WIFI
 * phase (docs/phone_app_plan.md §2 "HTTP additions", §4 net/CamHttp.java).
 *
 * <p>Bench finding #2: the phone can simultaneously be a Wi-Fi *client* on
 * one subnet (e.g. the home LAN, 192.168.86.0/24) and a hotspot *AP* on
 * another (e.g. 10.231.180.0/24, the camera's subnet) — both show up as
 * {@code TRANSPORT_WIFI}, so blindly requesting/binding "a" Wi-Fi network
 * bound every request to the wrong one and the tether subnet was
 * unreachable. Fix: default to a plain, unbound {@code url.openConnection()}
 * (which already routes to the tether subnet directly — no binding needed),
 * and only bind to a specific {@link Network} when that network's {@link
 * LinkProperties} actually contains a link address whose prefix covers the
 * target IP.
 */
public class CamHttp {

    private static final String TAG = "Dusty";

    public interface Callback {
        void onResult(int code, String body);
        void onError(Exception e);
    }

    private final ConnectivityManager cm;
    private final ExecutorService pool = Executors.newCachedThreadPool();
    private final Handler main = new Handler(Looper.getMainLooper());

    public CamHttp(Context ctx) {
        Context app = ctx.getApplicationContext();
        this.cm = (ConnectivityManager) app.getSystemService(Context.CONNECTIVITY_SERVICE);
    }

    /**
     * No persistent network binding is held anymore (see class doc) — kept as
     * a no-op so existing call sites (activity teardown, handoff transitions)
     * don't need to change.
     */
    public void release() {}

    /** {@code GET http://<ip>:8266/status}, 2 s timeout (§2 "Re-finding the camera after WIFI"). */
    public void getStatus(String ip, Callback cb) {
        get("http://" + ip + ":8266/status", 2000, cb);
    }

    /** {@code POST http://<ip>:8266/ble} — ends the Wi-Fi phase now. */
    public void postBle(String ip, Callback cb) {
        post("http://" + ip + ":8266/ble", 3000, cb);
    }

    public void get(String url, int timeoutMs, Callback cb) {
        pool.execute(() -> doRequest(url, "GET", null, timeoutMs, cb));
    }

    public void post(String url, int timeoutMs, Callback cb) {
        pool.execute(() -> doRequest(url, "POST", "", timeoutMs, cb));
    }

    private void doRequest(String urlStr, String method, String body, int timeoutMs, Callback cb) {
        HttpURLConnection conn = null;
        try {
            URL url = new URL(urlStr);
            Network net = networkCovering(url.getHost());
            Log.i(TAG, "CamHttp: " + method + " " + urlStr + " via "
                    + (net != null ? "bound network " + net + " (subnet match)" : "unbound/default route"));
            conn = (HttpURLConnection) (net != null ? net.openConnection(url) : url.openConnection());
            conn.setRequestMethod(method);
            conn.setConnectTimeout(timeoutMs);
            conn.setReadTimeout(timeoutMs);
            if (body != null && "POST".equals(method)) {
                conn.setDoOutput(true);
                byte[] b = body.getBytes(StandardCharsets.UTF_8);
                conn.setFixedLengthStreamingMode(b.length);
                try (OutputStream os = conn.getOutputStream()) {
                    os.write(b);
                }
            }
            int code = conn.getResponseCode();
            InputStream is = (code >= 200 && code < 400) ? conn.getInputStream() : conn.getErrorStream();
            String text = readAll(is);
            final int fc = code;
            final String ft = text;
            Log.i(TAG, "CamHttp: " + method + " " + urlStr + " -> " + fc);
            main.post(() -> cb.onResult(fc, ft));
        } catch (Exception e) {
            Log.w(TAG, "CamHttp: " + method + " " + urlStr + " failed: " + e);
            main.post(() -> cb.onError(e));
        } finally {
            if (conn != null) conn.disconnect();
        }
    }

    /**
     * The active network (if any) whose link address prefix actually covers
     * {@code host} — not just "some" network with a matching transport type.
     * Returns null (meaning: use the default/unbound route) when no active
     * network's subnet contains the address, which is normal and expected
     * when {@code host} is on the phone's own hotspot subnet: the hotspot
     * uplink is reachable over the default route without binding at all.
     */
    @SuppressWarnings("deprecation")
    private Network networkCovering(String host) {
        try {
            InetAddress target = InetAddress.getByName(host);
            // getAllNetworks() is deprecated in favor of a registered
            // NetworkCallback, but this needs only a one-shot snapshot at
            // request time — reintroducing a persistent callback is exactly
            // the lifecycle complexity review finding #2 removed.
            Network[] networks = cm.getAllNetworks();
            for (Network net : networks) {
                LinkProperties lp = cm.getLinkProperties(net);
                if (lp == null) continue;
                for (LinkAddress la : lp.getLinkAddresses()) {
                    if (sharesPrefix(target, la)) return net;
                }
            }
        } catch (Exception e) {
            Log.w(TAG, "CamHttp: networkCovering(" + host + ") failed: " + e);
        }
        return null;
    }

    private boolean sharesPrefix(InetAddress target, LinkAddress la) {
        byte[] a = target.getAddress();
        byte[] b = la.getAddress().getAddress();
        if (a.length != b.length) return false; // IPv4 vs IPv6 link address
        int prefixBits = la.getPrefixLength();
        int fullBytes = prefixBits / 8;
        int remBits = prefixBits % 8;
        for (int i = 0; i < fullBytes && i < a.length; i++) {
            if (a[i] != b[i]) return false;
        }
        if (remBits > 0 && fullBytes < a.length) {
            int mask = (0xFF00 >> remBits) & 0xFF;
            if ((a[fullBytes] & mask) != (b[fullBytes] & mask)) return false;
        }
        return true;
    }

    private String readAll(InputStream is) throws IOException {
        if (is == null) return "";
        ByteArrayOutputStream bos = new ByteArrayOutputStream();
        byte[] buf = new byte[4096];
        int n;
        while ((n = is.read(buf)) != -1) bos.write(buf, 0, n);
        return bos.toString("UTF-8");
    }
}
