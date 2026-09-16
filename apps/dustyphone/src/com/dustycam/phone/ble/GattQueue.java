package com.dustycam.phone.ble;

import android.bluetooth.BluetoothDevice;
import android.bluetooth.BluetoothGatt;
import android.bluetooth.BluetoothGattCallback;
import android.bluetooth.BluetoothGattCharacteristic;
import android.bluetooth.BluetoothGattDescriptor;
import android.bluetooth.BluetoothProfile;
import android.bluetooth.BluetoothStatusCodes;
import android.content.Context;
import android.os.Build;
import android.os.Handler;
import android.os.Looper;
import android.util.Log;

import java.util.ArrayDeque;
import java.util.UUID;

/**
 * Serialises Android BLE GATT operations on one connection.
 *
 * <p>{@link BluetoothGatt} allows only one outstanding op (write, read,
 * descriptor write, MTU/priority request) at a time per connection — issuing
 * a second before the first's callback fires is undefined (frequently
 * silently dropped). This queues ops and drains one at a time, driven by its
 * own {@link BluetoothGattCallback}.
 *
 * <p>Also implements the well-known status-133 workaround: on a GATT_ERROR
 * (133) at connect time, {@code close()} the GATT, wait 500 ms, and retry
 * {@code connectGatt} up to 3 times before giving up.
 */
public class GattQueue {

    private static final String TAG = "Dusty";
    private static final UUID CCCD = UUID.fromString("00002902-0000-1000-8000-00805f9b34fb");
    private static final int MAX_133_RETRIES = 3;
    private static final long RETRY_DELAY_MS = 500;

    public interface Listener {
        void onConnected();
        void onDisconnected();
        void onServicesDiscovered(BluetoothGatt gatt);
        void onNotification(UUID characteristic, byte[] value);
        void onMtuChanged(int mtu);
        void onGattFailure(String op, int status);
    }

    public interface OpCallback {
        void onSuccess(byte[] value);
        void onFailure(int status);
    }

    private final Context ctx;
    private final BluetoothDevice device;
    private final Listener listener;
    private final Handler main = new Handler(Looper.getMainLooper());

    private volatile BluetoothGatt gatt;
    private int retries133 = 0;

    private enum OpType { WRITE, READ, ENABLE_NOTIFY, REQUEST_MTU, CONN_PRIORITY }

    private static final class Op {
        OpType type;
        BluetoothGattCharacteristic ch;
        byte[] value;
        int writeType;
        int mtu;
        int priority;
        OpCallback cb;
    }

    private final ArrayDeque<Op> queue = new ArrayDeque<>();
    private Op inFlight;

    public GattQueue(Context ctx, BluetoothDevice device, Listener listener) {
        this.ctx = ctx.getApplicationContext();
        this.device = device;
        this.listener = listener;
    }

    public void connect() {
        Log.i(TAG, "GattQueue: connecting to " + device.getAddress());
        gatt = device.connectGatt(ctx, false, callback, BluetoothDevice.TRANSPORT_LE);
    }

    public synchronized void close() {
        queue.clear();
        inFlight = null;
        if (gatt != null) {
            gatt.close();
            gatt = null;
        }
    }

    public BluetoothGatt gatt() { return gatt; }

    // ---- enqueue API ----

    public synchronized void writeCharacteristic(BluetoothGattCharacteristic ch, byte[] value,
                                                  int writeType, OpCallback cb) {
        Op op = new Op();
        op.type = OpType.WRITE;
        op.ch = ch;
        op.value = value;
        op.writeType = writeType;
        op.cb = cb;
        enqueue(op);
    }

    public synchronized void readCharacteristic(BluetoothGattCharacteristic ch, OpCallback cb) {
        Op op = new Op();
        op.type = OpType.READ;
        op.ch = ch;
        op.cb = cb;
        enqueue(op);
    }

    /** {@code setCharacteristicNotification(true)} + write the CCCD (0x2902) descriptor. */
    public synchronized void enableNotify(BluetoothGattCharacteristic ch, OpCallback cb) {
        Op op = new Op();
        op.type = OpType.ENABLE_NOTIFY;
        op.ch = ch;
        op.cb = cb;
        enqueue(op);
    }

    public synchronized void requestMtu(int mtu, OpCallback cb) {
        Op op = new Op();
        op.type = OpType.REQUEST_MTU;
        op.mtu = mtu;
        op.cb = cb;
        enqueue(op);
    }

    public synchronized void requestConnectionPriority(int priority, OpCallback cb) {
        Op op = new Op();
        op.type = OpType.CONN_PRIORITY;
        op.priority = priority;
        op.cb = cb;
        enqueue(op);
    }

    private void enqueue(Op op) {
        queue.add(op);
        drain();
    }

    private synchronized void drain() {
        if (inFlight != null || gatt == null) return;
        Op op = queue.poll();
        if (op == null) return;
        inFlight = op;
        boolean ok = start(op);
        if (!ok) {
            Log.w(TAG, "GattQueue: failed to start op " + op.type);
            finishInFlight(false, -1, null);
        } else if (op.type == OpType.CONN_PRIORITY) {
            // requestConnectionPriority has no reliable public completion signal
            // (onConnectionUpdated is unreliable/hidden on many stacks) — treat it
            // as fire-and-forget so it never blocks the queue behind it (review
            // finding #1: this previously wedged every connection in HANDSHAKE
            // because the read of `info` was queued right after it).
            finishInFlight(true, BluetoothGatt.GATT_SUCCESS, null);
        }
        // NOTE: WRITE_TYPE_NO_RESPONSE writes are NOT finished early here — on
        // API 33+ a second writeCharacteristic() before onCharacteristicWrite
        // fires for the previous one returns ERROR_GATT_WRITE_REQUEST_BUSY, which
        // would silently drop cmd fragments 2..n (review finding #3). Android
        // does deliver onCharacteristicWrite for no-response writes, so we always
        // wait for it — that also paces multi-fragment writes correctly.
    }

    @SuppressWarnings("deprecation")
    private boolean start(Op op) {
        switch (op.type) {
            case WRITE:
                if (Build.VERSION.SDK_INT >= 33) {
                    return gatt.writeCharacteristic(op.ch, op.value, op.writeType)
                            == BluetoothStatusCodes.SUCCESS;
                } else {
                    op.ch.setWriteType(op.writeType);
                    op.ch.setValue(op.value);
                    return gatt.writeCharacteristic(op.ch);
                }
            case READ:
                return gatt.readCharacteristic(op.ch);
            case ENABLE_NOTIFY: {
                if (!gatt.setCharacteristicNotification(op.ch, true)) return false;
                BluetoothGattDescriptor cccd = op.ch.getDescriptor(CCCD);
                if (cccd == null) return false;
                if (Build.VERSION.SDK_INT >= 33) {
                    return gatt.writeDescriptor(cccd, BluetoothGattDescriptor.ENABLE_NOTIFICATION_VALUE)
                            == BluetoothStatusCodes.SUCCESS;
                } else {
                    cccd.setValue(BluetoothGattDescriptor.ENABLE_NOTIFICATION_VALUE);
                    return gatt.writeDescriptor(cccd);
                }
            }
            case REQUEST_MTU:
                return gatt.requestMtu(op.mtu);
            case CONN_PRIORITY:
                return gatt.requestConnectionPriority(op.priority);
        }
        return false;
    }

    private synchronized void finishInFlight(boolean ok, int status, byte[] value) {
        Op done = inFlight;
        inFlight = null;
        if (done != null && done.cb != null) {
            if (ok) main.post(() -> done.cb.onSuccess(value));
            else main.post(() -> done.cb.onFailure(status));
        }
        drain();
    }

    private final BluetoothGattCallback callback = new BluetoothGattCallback() {
        @Override
        public void onConnectionStateChange(BluetoothGatt g, int status, int newState) {
            if (newState == BluetoothProfile.STATE_CONNECTED) {
                retries133 = 0;
                Log.i(TAG, "GattQueue: connected, discovering services");
                g.discoverServices();
            } else if (newState == BluetoothProfile.STATE_DISCONNECTED) {
                Log.i(TAG, "GattQueue: disconnected status=" + status);
                if (status == 133 && retries133 < MAX_133_RETRIES) {
                    retries133++;
                    Log.w(TAG, "GattQueue: GATT 133, retry " + retries133 + "/" + MAX_133_RETRIES);
                    g.close();
                    main.postDelayed(() -> {
                        gatt = device.connectGatt(ctx, false, callback, BluetoothDevice.TRANSPORT_LE);
                    }, RETRY_DELAY_MS);
                    return;
                }
                synchronized (GattQueue.this) {
                    queue.clear();
                    inFlight = null;
                    // Final (non-retry) disconnect: release the platform's GATT
                    // client now, not just on our own explicit close() — otherwise
                    // every reconnect (e.g. Cycle x10 / bring-back) leaks one
                    // BluetoothGatt, and Android caps ~32 of these per process
                    // (review finding #4).
                    g.close();
                    if (gatt == g) gatt = null;
                }
                main.post(listener::onDisconnected);
            }
        }

        @Override
        public void onServicesDiscovered(BluetoothGatt g, int status) {
            if (status == BluetoothGatt.GATT_SUCCESS) {
                main.post(() -> {
                    listener.onServicesDiscovered(g);
                    listener.onConnected();
                });
            } else {
                main.post(() -> listener.onGattFailure("discoverServices", status));
            }
        }

        @Override
        public void onCharacteristicWrite(BluetoothGatt g, BluetoothGattCharacteristic ch, int status) {
            finishInFlight(status == BluetoothGatt.GATT_SUCCESS, status, null);
        }

        @Override
        @SuppressWarnings("deprecation")
        public void onCharacteristicRead(BluetoothGatt g, BluetoothGattCharacteristic ch, int status) {
            // Pre-API-33 path; the byte[]-carrying overload below fires instead on 33+.
            finishInFlight(status == BluetoothGatt.GATT_SUCCESS, status, ch.getValue());
        }

        @Override
        public void onCharacteristicRead(BluetoothGatt g, BluetoothGattCharacteristic ch, byte[] value, int status) {
            finishInFlight(status == BluetoothGatt.GATT_SUCCESS, status, value);
        }

        @Override
        public void onDescriptorWrite(BluetoothGatt g, BluetoothGattDescriptor d, int status) {
            finishInFlight(status == BluetoothGatt.GATT_SUCCESS, status, null);
        }

        @Override
        public void onMtuChanged(BluetoothGatt g, int mtu, int status) {
            if (status == BluetoothGatt.GATT_SUCCESS) {
                main.post(() -> listener.onMtuChanged(mtu));
            }
            finishInFlight(status == BluetoothGatt.GATT_SUCCESS, status, null);
        }

        @Override
        @SuppressWarnings("deprecation")
        public void onCharacteristicChanged(BluetoothGatt g, BluetoothGattCharacteristic ch) {
            // Pre-API-33 path; the byte[]-carrying overload below fires instead on 33+.
            main.post(() -> listener.onNotification(ch.getUuid(), ch.getValue()));
        }

        @Override
        public void onCharacteristicChanged(BluetoothGatt g, BluetoothGattCharacteristic ch, byte[] value) {
            main.post(() -> listener.onNotification(ch.getUuid(), value));
        }
    };
}
