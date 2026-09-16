package com.dustycam.phone.net;

import android.os.Handler;
import android.os.Looper;
import android.util.Log;

import org.json.JSONException;
import org.json.JSONObject;

import java.io.IOException;
import java.net.DatagramPacket;
import java.net.DatagramSocket;
import java.net.InetSocketAddress;
import java.net.SocketException;
import java.net.SocketTimeoutException;
import java.nio.charset.StandardCharsets;

/**
 * Listens for the camera's Wi-Fi-phase UDP beacon (bench finding #1: never
 * ask the user to type an IP). While its control plane is up, the camera
 * broadcasts once per second to UDP port 8267:
 * {@code {"dc":1,"device":"xiaocam1","ip":"10.231.180.44","port":8266,"radio":"wifi"}}.
 *
 * <p>Runs its own background thread with a 1 s socket-read timeout so {@link
 * #stop} can take effect within a second without needing interrupts to land
 * mid-{@code receive()}.
 */
public class Beacon {

    private static final String TAG = "Dusty";
    public static final int PORT = 8267;
    private static final int BUF_SIZE = 1024;
    private static final int SOCKET_TIMEOUT_MS = 1000;

    public interface Listener {
        /** Called on the main thread for each beacon carrying {@code dc:1} + a device/ip/port. */
        void onBeacon(String device, String ip, int port);
    }

    private final Listener listener;
    private final Handler main = new Handler(Looper.getMainLooper());
    private volatile boolean running = false;
    private Thread thread;
    private DatagramSocket socket;

    public Beacon(Listener listener) {
        this.listener = listener;
    }

    public synchronized void start() {
        if (running) return;
        running = true;
        thread = new Thread(this::loop, "DustyBeacon");
        thread.start();
    }

    public synchronized void stop() {
        running = false;
        DatagramSocket s = socket;
        socket = null;
        if (s != null) s.close(); // unblocks a receive() promptly if one is outstanding
        thread = null;
    }

    public boolean isRunning() { return running; }

    private void loop() {
        DatagramSocket s;
        try {
            s = new DatagramSocket(null);
            s.setReuseAddress(true);
            s.setBroadcast(true);
            s.bind(new InetSocketAddress(PORT));
            s.setSoTimeout(SOCKET_TIMEOUT_MS);
        } catch (IOException e) {
            Log.e(TAG, "Beacon: bind to udp/" + PORT + " failed: " + e);
            running = false;
            return;
        }
        socket = s;
        Log.i(TAG, "Beacon: listening on udp/" + PORT);

        byte[] buf = new byte[BUF_SIZE];
        while (running) {
            DatagramPacket packet = new DatagramPacket(buf, buf.length);
            try {
                s.receive(packet);
            } catch (SocketTimeoutException e) {
                continue;
            } catch (SocketException e) {
                break; // stop() closed the socket
            } catch (IOException e) {
                if (running) Log.w(TAG, "Beacon: receive() failed: " + e);
                break;
            }
            handlePacket(packet);
        }

        s.close();
        Log.i(TAG, "Beacon: stopped");
    }

    private void handlePacket(DatagramPacket packet) {
        String text = new String(packet.getData(), packet.getOffset(), packet.getLength(), StandardCharsets.UTF_8);
        try {
            JSONObject json = new JSONObject(text);
            if (json.optInt("dc", 0) != 1) return;
            String device = json.optString("device", null);
            String ip = json.optString("ip", null);
            int port = json.optInt("port", 0);
            if (device == null || ip == null || port == 0) {
                Log.w(TAG, "Beacon: incomplete beacon from " + packet.getAddress() + ": " + text);
                return;
            }
            Log.d(TAG, "Beacon: " + text);
            main.post(() -> listener.onBeacon(device, ip, port));
        } catch (JSONException e) {
            Log.w(TAG, "Beacon: bad JSON from " + packet.getAddress() + ": " + text);
        }
    }
}
