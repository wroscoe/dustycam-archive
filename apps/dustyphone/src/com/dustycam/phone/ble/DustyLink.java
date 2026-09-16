package com.dustycam.phone.ble;

import android.bluetooth.BluetoothAdapter;
import android.bluetooth.BluetoothDevice;
import android.bluetooth.BluetoothGatt;
import android.bluetooth.BluetoothGattCharacteristic;
import android.bluetooth.BluetoothGattService;
import android.content.Context;
import android.os.Build;
import android.os.Handler;
import android.os.Looper;
import android.os.SystemClock;
import android.util.Log;

import org.json.JSONException;
import org.json.JSONObject;

import java.nio.charset.StandardCharsets;
import java.util.ArrayDeque;
import java.util.Arrays;
import java.util.HashMap;
import java.util.HashSet;
import java.util.Iterator;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.UUID;

/**
 * One GATT session with a camera (docs/phone_app_plan.md §2):
 * connect -&gt; discover services -&gt; enable notifications on rsp/data/evt -&gt;
 * MTU 517 (+ high connection priority) -&gt; read {@code info} -&gt; {@code hello}/
 * {@code auth} -&gt; READY. Once ready, {@link #request} sends a JSON op on
 * {@code cmd} and correlates its {@code rsp}/{@code data} replies by id;
 * {@code evt} notifications are dispatched to the {@link Listener}
 * independently (id 0, never correlated to a request).
 */
public class DustyLink {

    private static final String TAG = "Dusty";
    private static final String BASE_FMT = "7d1e00%02x-dc0a-4c9b-8f6e-2e9a0c5d1b00";

    public static final UUID SVC_UUID  = uuid(0x01);
    public static final UUID INFO_UUID = uuid(0x02);
    public static final UUID CMD_UUID  = uuid(0x03);
    public static final UUID RSP_UUID  = uuid(0x04);
    public static final UUID DATA_UUID = uuid(0x05);
    public static final UUID EVT_UUID  = uuid(0x06);

    private static UUID uuid(int xx) { return UUID.fromString(String.format(BASE_FMT, xx)); }

    /**
     * INFO_ONLY is reached only via {@link #connectForInfo}: connected and
     * {@code info} has been read, but hello/auth was deliberately skipped —
     * used by provisioning to inspect {@code info.prov} before deciding
     * whether a plaintext {@code prov.set} (unprovisioned, no key to auth
     * with) or a full authenticated session (already provisioned) is needed.
     */
    public enum State { CONNECTING, DISCOVERING, HANDSHAKE, INFO_ONLY, READY, DISCONNECTED, FAILED }

    public interface OpCallback {
        default void onResponse(JSONObject rsp) {}
        default void onData(byte[] data, double kbPerSec) {}
        default void onError(String err) {}
    }

    public interface Listener {
        void onStateChanged(State s);
        void onEvent(JSONObject evt);
        void onInfo(JSONObject info);
    }

    private final Context ctx;
    private final byte[] bleKey;
    private Listener listener;
    /** Stop delivering callbacks (a superseded link's teardown must not
     *  be mistaken for the new link failing). */
    public void detach() { listener = null; }
    private final Handler main = new Handler(Looper.getMainLooper());

    private GattQueue queue;
    private BluetoothGattCharacteristic cmdChar, rspChar, dataChar, evtChar;
    private volatile int mtu = 23;
    private volatile State state = State.DISCONNECTED;
    private String address;

    private final Framer.Reassembler rspReasm = new Framer.Reassembler();
    private final Framer.Reassembler dataReasm = new Framer.Reassembler();
    private final Framer.Reassembler evtReasm = new Framer.Reassembler();

    /**
     * `preview`'s reply is a `data` JPEG followed by a `rsp` {focus,lum} for the
     * same id — the rsp is what's terminal here. `thumb`/`frame` send only
     * `data`, no rsp at all, so they stay retired-on-data (review finding #5).
     */
    private static final Set<String> RSP_AFTER_DATA_OPS = new HashSet<>(Arrays.asList("preview"));

    private static final class Pending {
        final String op;
        final OpCallback cb;
        Pending(String op, OpCallback cb) { this.op = op; this.cb = cb; }
    }

    private final Map<Integer, Pending> pending = new HashMap<>();
    private final Map<Integer, Long> reqStartMs = new HashMap<>();
    private final Map<Integer, Long> dataStartMs = new HashMap<>();
    private final Map<Integer, Runnable> timeouts = new HashMap<>();
    private int nextId = 1;

    /**
     * A dropped/never-answered rsp or data notification (lost BLE
     * notification, firmware hiccup) must never wedge the one-outstanding
     * -request queue forever — every subsequent op would then silently queue
     * with no `-> op=...` log line and no visible effect at all (bench
     * finding: a request appeared to vanish with no trace). Any request
     * without a reply within this window is treated as a timeout error and
     * the queue unblocks itself.
     */
    private static final long REQUEST_TIMEOUT_MS = 8000;

    /**
     * The camera only ever has one op outstanding at a time and answers a
     * second with `err:"busy"` (plan §2, firmware note from review) — so
     * DustyLink queues requests itself and only has one `id` in flight on
     * `cmd` at once, instead of relying on callers to serialise.
     */
    private static final class QueuedRequest {
        final String op;
        final JSONObject args;
        final OpCallback cb;
        QueuedRequest(String op, JSONObject args, OpCallback cb) { this.op = op; this.args = args; this.cb = cb; }
    }

    private final ArrayDeque<QueuedRequest> requestQueue = new ArrayDeque<>();
    private boolean sending = false;

    private JSONObject infoJson;
    private byte[] phoneNonce;
    private byte[] camNonce;
    /** Set only by {@link #connectForInfo}: stop after reading `info`, skip hello/auth. */
    private boolean skipHandshake = false;

    public DustyLink(Context ctx, byte[] bleKey, Listener listener) {
        this.ctx = ctx.getApplicationContext();
        this.bleKey = bleKey;
        this.listener = listener;
    }

    public State getState() { return state; }
    public String getAddress() { return address; }
    public JSONObject getInfo() { return infoJson; }
    public int getMtu() { return mtu; }

    /**
     * The {@code prov.set} envelope key (§2 "Session"): {@code sk =
     * HMAC(ble_key, "sk"||cam_nonce||phone_nonce)}. Only meaningful once
     * READY (full hello/auth completed, not the {@link State#INFO_ONLY}
     * path) — returns null otherwise.
     */
    public byte[] sessionKey() {
        return (state == State.READY && camNonce != null) ? Crypto.sessionKey(bleKey, camNonce, phoneNonce) : null;
    }

    private void setState(State s) {
        state = s;
        Log.i(TAG, "DustyLink: state=" + s);
        main.post(() -> { if (listener != null) listener.onStateChanged(s); });
    }

    // ---- connect / handshake ----

    public void connect(BluetoothAdapter adapter, String address) {
        this.address = address;
        // The camera advertises a fixed static-random address (plan §2
        // "Advertising"); getRemoteDevice() assumes a public address and
        // relies on the scan cache to paper over that. getRemoteLeDevice()
        // (API 33+) states the address type explicitly (review finding #7).
        BluetoothDevice device = Build.VERSION.SDK_INT >= 33
                ? adapter.getRemoteLeDevice(address, BluetoothDevice.ADDRESS_TYPE_RANDOM)
                : adapter.getRemoteDevice(address);
        setState(State.CONNECTING);
        queue = new GattQueue(ctx, device, gattListener);
        Log.i(TAG, "DustyLink: connect(" + address + ")");
        queue.connect();
    }

    /**
     * Provisioning entry point: connect and read {@code info} only, then stop
     * at {@link State#INFO_ONLY} — no {@code hello}/{@code auth}. An
     * unprovisioned camera (`info.prov==0`) has no {@code ble_key} to
     * authenticate with yet, and the protocol exempts `prov.set` from auth
     * during its presence window, so there is nothing to skip *to*; the
     * caller decides from {@code info.prov} whether to send a plaintext
     * {@code prov.set} here or reconnect with {@link #connect} for a full
     * authenticated session (already-provisioned re-provisioning).
     */
    public void connectForInfo(BluetoothAdapter adapter, String address) {
        this.skipHandshake = true;
        connect(adapter, address);
    }

    public void disconnect() {
        if (queue != null) queue.close();
        pending.clear();
        reqStartMs.clear();
        dataStartMs.clear();
        for (Runnable r : timeouts.values()) main.removeCallbacks(r);
        timeouts.clear();
        synchronized (requestQueue) {
            requestQueue.clear();
            sending = false;
        }
        setState(State.DISCONNECTED);
    }

    private final GattQueue.Listener gattListener = new GattQueue.Listener() {
        @Override public void onConnected() {
            Log.i(TAG, "DustyLink: GATT connected");
        }

        @Override public void onDisconnected() {
            setState(State.DISCONNECTED);
        }

        @Override public void onServicesDiscovered(BluetoothGatt gatt) {
            setState(State.DISCOVERING);
            BluetoothGattService svc = gatt.getService(SVC_UUID);
            if (svc == null) {
                Log.e(TAG, "DustyLink: service " + SVC_UUID + " not found");
                setState(State.FAILED);
                return;
            }
            cmdChar = svc.getCharacteristic(CMD_UUID);
            rspChar = svc.getCharacteristic(RSP_UUID);
            dataChar = svc.getCharacteristic(DATA_UUID);
            evtChar = svc.getCharacteristic(EVT_UUID);
            final BluetoothGattCharacteristic infoChar = svc.getCharacteristic(INFO_UUID);

            queue.enableNotify(rspChar, notifyCb("rsp"));
            queue.enableNotify(dataChar, notifyCb("data"));
            queue.enableNotify(evtChar, notifyCb("evt"));
            queue.requestMtu(517, new GattQueue.OpCallback() {
                @Override public void onSuccess(byte[] value) {
                    queue.requestConnectionPriority(BluetoothGatt.CONNECTION_PRIORITY_HIGH, noop());
                    readInfoAndHandshake(infoChar);
                }
                @Override public void onFailure(int status) {
                    Log.w(TAG, "DustyLink: requestMtu failed status=" + status + ", staying at " + mtu);
                    readInfoAndHandshake(infoChar);
                }
            });
        }

        @Override public void onNotification(UUID characteristic, byte[] value) {
            dispatchNotification(characteristic, value);
        }

        @Override public void onMtuChanged(int newMtu) {
            mtu = newMtu;
            Log.i(TAG, "DustyLink: MTU=" + newMtu);
        }

        @Override public void onGattFailure(String op, int status) {
            Log.e(TAG, "DustyLink: GATT failure op=" + op + " status=" + status);
            setState(State.FAILED);
        }
    };

    private GattQueue.OpCallback notifyCb(String name) {
        return new GattQueue.OpCallback() {
            @Override public void onSuccess(byte[] value) {}
            @Override public void onFailure(int status) {
                Log.w(TAG, "DustyLink: enableNotify(" + name + ") failed status=" + status);
            }
        };
    }

    private GattQueue.OpCallback noop() {
        return new GattQueue.OpCallback() {
            @Override public void onSuccess(byte[] value) {}
            @Override public void onFailure(int status) {}
        };
    }

    private void readInfoAndHandshake(BluetoothGattCharacteristic infoChar) {
        setState(State.HANDSHAKE);
        if (infoChar == null) {
            Log.e(TAG, "DustyLink: info characteristic missing");
            setState(State.FAILED);
            return;
        }
        queue.readCharacteristic(infoChar, new GattQueue.OpCallback() {
            @Override public void onSuccess(byte[] value) {
                try {
                    infoJson = new JSONObject(new String(value, StandardCharsets.UTF_8));
                } catch (JSONException e) {
                    Log.e(TAG, "DustyLink: bad info JSON", e);
                    setState(State.FAILED);
                    return;
                }
                Log.i(TAG, "DustyLink: info=" + infoJson);
                main.post(() -> { if (listener != null) listener.onInfo(infoJson); });
                int proto = infoJson.optInt("proto", -1);
                if (proto != 1) {
                    Log.e(TAG, "DustyLink: refusing unsupported proto=" + proto);
                    setState(State.FAILED);
                    return;
                }
                if (skipHandshake) {
                    setState(State.INFO_ONLY);
                    return;
                }
                doHello();
            }
            @Override public void onFailure(int status) {
                Log.e(TAG, "DustyLink: read info failed status=" + status);
                setState(State.FAILED);
            }
        });
    }

    private void doHello() {
        phoneNonce = Crypto.randomNonce16();
        JSONObject args = new JSONObject();
        try {
            args.put("pn", Crypto.toHex(phoneNonce));
        } catch (JSONException ignored) {}
        request("hello", args, new OpCallback() {
            @Override public void onResponse(JSONObject rsp) {
                String camNonceHex = rsp.optString("nonce", null);
                if (camNonceHex == null) {
                    Log.e(TAG, "DustyLink: hello response missing nonce");
                    setState(State.FAILED);
                    return;
                }
                doAuth(Crypto.fromHex(camNonceHex));
            }
            @Override public void onError(String err) {
                Log.e(TAG, "DustyLink: hello failed: " + err);
                setState(State.FAILED);
            }
        });
    }

    private void doAuth(byte[] camNonce) {
        this.camNonce = camNonce; // kept for sessionKey() (prov.set's encrypted envelope)
        String mac = Crypto.authMac(bleKey, camNonce, phoneNonce);
        JSONObject args = new JSONObject();
        try {
            args.put("mac", mac);
        } catch (JSONException ignored) {}
        request("auth", args, new OpCallback() {
            @Override public void onResponse(JSONObject rsp) {
                if (rsp.optBoolean("ok", false)) {
                    Log.i(TAG, "DustyLink: auth ok");
                    setState(State.READY);
                } else {
                    Log.e(TAG, "DustyLink: auth rejected: " + rsp);
                    setState(State.FAILED);
                }
            }
            @Override public void onError(String err) {
                Log.e(TAG, "DustyLink: auth failed: " + err);
                setState(State.FAILED);
            }
        });
    }

    // ---- request/response ----

    /** ids roll 1..255 (0 is reserved for unsolicited events). */
    private synchronized int allocId() {
        int id = nextId;
        nextId = (nextId % 255) + 1;
        return id;
    }

    /**
     * Send {@code op} on {@code cmd} (merging {@code args}' keys straight into
     * the request body alongside {@code id}/{@code op}), correlated by id;
     * {@code cb} receives whichever of the {@code rsp} JSON / {@code data}
     * bytes come back tagged with that id (some ops send both, e.g. {@code
     * preview}: a {@code data} JPEG plus a {@code rsp} with focus/lum).
     *
     * <p>The camera only ever processes one op at a time and answers a second
     * with {@code err:"busy"} — so this just queues the request; only one is
     * ever in flight on {@code cmd} (review finding #8).
     */
    public void request(String op, JSONObject args, OpCallback cb) {
        if (queue == null || cmdChar == null) {
            cb.onError("not connected");
            return;
        }
        synchronized (requestQueue) {
            requestQueue.add(new QueuedRequest(op, args, cb));
        }
        pumpRequestQueue();
    }

    private void pumpRequestQueue() {
        QueuedRequest next;
        synchronized (requestQueue) {
            if (sending) return;
            next = requestQueue.poll();
            if (next == null) return;
            sending = true;
        }
        sendNow(next.op, next.args, next.cb);
    }

    /** Marks the in-flight request finished and lets the next queued one go. */
    private void requestDone() {
        synchronized (requestQueue) {
            sending = false;
        }
        pumpRequestQueue();
    }

    private void sendNow(String op, JSONObject args, OpCallback cb) {
        int id = allocId();
        JSONObject body = new JSONObject();
        try {
            body.put("id", id);
            body.put("op", op);
            if (args != null) {
                Iterator<String> it = args.keys();
                while (it.hasNext()) {
                    String k = it.next();
                    body.put(k, args.get(k));
                }
            }
        } catch (JSONException e) {
            cb.onError("bad request json: " + e);
            requestDone();
            return;
        }
        byte[] payload = body.toString().getBytes(StandardCharsets.UTF_8);
        if (payload.length > Framer.REQ_MAX) {
            cb.onError("request too large: " + payload.length);
            requestDone();
            return;
        }
        pending.put(id, new Pending(op, cb));
        reqStartMs.put(id, SystemClock.elapsedRealtime());
        scheduleTimeout(id, op, cb);
        Log.i(TAG, "DustyLink: -> id=" + id + " op=" + op + " (" + payload.length + " B)");
        // Cap the fragmentation size at 247 even when the negotiated MTU is
        // larger (517): a handful of BLE stacks are unreliable with ATT
        // writes above ~244 B despite advertising a bigger MTU, and prov.set's
        // encrypted envelope (~430 B) would otherwise be the first request on
        // this link ever to cross that size — cheap insurance, same cap the
        // firmware side applies to its own notify fragments.
        int fragMtu = Math.min(mtu, 247);
        List<byte[]> frames = Framer.fragment(id, 0, payload, fragMtu);
        final boolean[] aborted = {false};
        for (byte[] frame : frames) {
            queue.writeCharacteristic(cmdChar, frame, BluetoothGattCharacteristic.WRITE_TYPE_NO_RESPONSE,
                    new GattQueue.OpCallback() {
                        @Override public void onSuccess(byte[] value) {}
                        @Override public void onFailure(int status) {
                            Log.w(TAG, "DustyLink: cmd write failed id=" + id + " status=" + status);
                            synchronized (aborted) {
                                if (aborted[0]) return;
                                aborted[0] = true;
                            }
                            // A dropped fragment write means no rsp/data for this id will
                            // ever complete it — abort now so the queue isn't stuck
                            // waiting forever behind a lost request.
                            if (pending.remove(id) != null) {
                                reqStartMs.remove(id);
                                cancelTimeout(id);
                                cb.onError("cmd write failed status=" + status);
                                requestDone();
                            }
                        }
                    });
        }
    }

    private void scheduleTimeout(int id, String op, OpCallback cb) {
        Runnable timeout = () -> {
            timeouts.remove(id);
            if (pending.remove(id) != null) {
                reqStartMs.remove(id);
                Log.w(TAG, "DustyLink: id=" + id + " op=" + op + " timed out after " + REQUEST_TIMEOUT_MS + "ms");
                cb.onError("timeout");
                requestDone();
            }
        };
        timeouts.put(id, timeout);
        main.postDelayed(timeout, REQUEST_TIMEOUT_MS);
    }

    private void cancelTimeout(int id) {
        Runnable r = timeouts.remove(id);
        if (r != null) main.removeCallbacks(r);
    }

    private void dispatchNotification(UUID characteristic, byte[] value) {
        try {
            if (RSP_UUID.equals(characteristic)) {
                Framer.Message msg = rspReasm.accept(value);
                if (msg != null) handleRsp(msg);
            } else if (DATA_UUID.equals(characteristic)) {
                // Per-fragment logging removed (bench feedback: too noisy at
                // INFO/D — handleData()'s transfer summary below is the useful line).
                Framer.Frame f = Framer.parse(value);
                if (f.idx == 0) dataStartMs.putIfAbsent(f.id, SystemClock.elapsedRealtime());
                Framer.Message msg = dataReasm.accept(value);
                if (msg != null) handleData(msg);
            } else if (EVT_UUID.equals(characteristic)) {
                Framer.Message msg = evtReasm.accept(value);
                if (msg != null) handleEvt(msg);
            }
        } catch (Framer.FramingException e) {
            Log.e(TAG, "DustyLink: framing error on " + characteristic + ": " + e.getMessage());
        }
    }

    private void handleRsp(Framer.Message msg) {
        JSONObject rsp;
        try {
            rsp = new JSONObject(new String(msg.data, StandardCharsets.UTF_8));
        } catch (JSONException e) {
            Log.e(TAG, "DustyLink: bad rsp JSON id=" + msg.id, e);
            return;
        }
        long elapsed = elapsedSinceRequest(msg.id);
        Log.i(TAG, "DustyLink: <- id=" + msg.id + " rsp=" + rsp + " (" + elapsed + " ms)");
        // A `rsp` is always terminal for whichever request it answers: for a
        // plain op it's the only reply; for `preview` it's the focus/lum
        // follow-up after its `data` JPEG; and if it carries an error it is
        // terminal even when the matching `data` transfer never arrived at all
        // (firmware sends `err:"busy"` for a request it can't service) — review
        // finding #5.
        Pending p = pending.remove(msg.id);
        reqStartMs.remove(msg.id);
        cancelTimeout(msg.id);
        if (p == null) return;
        boolean ok = rsp.optBoolean("ok", true);
        if (!ok || msg.err) {
            p.cb.onError(rsp.optString("err", "error") + ": " + rsp.optString("msg", ""));
        } else {
            p.cb.onResponse(rsp);
        }
        requestDone();
    }

    private void handleData(Framer.Message msg) {
        Long startedBoxed = dataStartMs.remove(msg.id);
        double kbPerSec = 0.0;
        if (startedBoxed != null) {
            long elapsedMs = Math.max(1, SystemClock.elapsedRealtime() - startedBoxed);
            kbPerSec = (msg.data.length / 1024.0) / (elapsedMs / 1000.0);
        }
        Log.i(TAG, "DustyLink: <- id=" + msg.id + " data=" + msg.data.length + " B, "
                + String.format("%.1f", kbPerSec) + " KB/s (" + elapsedSinceRequest(msg.id) + " ms total)");
        Pending p = pending.get(msg.id);
        if (p != null) p.cb.onData(msg.data, kbPerSec);
        if (p != null && RSP_AFTER_DATA_OPS.contains(p.op)) {
            // `preview`: a `rsp` with focus/lum still follows — handleRsp retires it.
            return;
        }
        pending.remove(msg.id);
        reqStartMs.remove(msg.id);
        cancelTimeout(msg.id);
        requestDone();
    }

    private void handleEvt(Framer.Message msg) {
        JSONObject evt;
        try {
            evt = new JSONObject(new String(msg.data, StandardCharsets.UTF_8));
        } catch (JSONException e) {
            Log.e(TAG, "DustyLink: bad evt JSON", e);
            return;
        }
        Log.i(TAG, "DustyLink: evt=" + evt);
        main.post(() -> { if (listener != null) listener.onEvent(evt); });
    }

    private long elapsedSinceRequest(int id) {
        Long t0 = reqStartMs.get(id);
        return t0 == null ? -1 : SystemClock.elapsedRealtime() - t0;
    }
}
