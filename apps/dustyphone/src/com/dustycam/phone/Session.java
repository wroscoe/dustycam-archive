package com.dustycam.phone;

import java.util.ArrayList;
import java.util.List;

/**
 * App-side radio state (docs/phone_app_plan.md §4): one source of truth for
 * the {@code CameraActivity} status banner. Distinct from the camera's own
 * {@code radio} field in {@code /status}/{@code info} — this tracks what the
 * *phone* is doing (which link it holds, or is trying to regain), and drives
 * the UI regardless of which characteristic or HTTP call is in flight.
 */
public class Session {

    public enum State { BLE, HANDOFF, WIFI, RETURNING, LOST }

    public interface Listener {
        void onSessionStateChanged(State state);
    }

    private State state = State.LOST;
    private String cameraAddress;
    private String lastIp;
    private final List<Listener> listeners = new ArrayList<>();

    public synchronized State getState() { return state; }

    public synchronized void setState(State s) {
        if (state == s) return;
        state = s;
        for (Listener l : new ArrayList<>(listeners)) l.onSessionStateChanged(s);
    }

    public void addListener(Listener l) { listeners.add(l); }
    public void removeListener(Listener l) { listeners.remove(l); }

    public String getCameraAddress() { return cameraAddress; }
    public void setCameraAddress(String a) { cameraAddress = a; }

    public String getLastIp() { return lastIp; }
    public void setLastIp(String ip) { lastIp = ip; }

    /** Text for the status banner (§4 "Handoff UX"). */
    public String banner() {
        switch (state) {
            case BLE: return "Bluetooth linked";
            case HANDOFF: return "Switching to Wi-Fi…";
            case WIFI: return "Wi-Fi " + (lastIp != null ? lastIp : "(no ip)");
            case RETURNING: return "Returning to Bluetooth…";
            case LOST:
            default: return "Lost — press the camera's button";
        }
    }
}
