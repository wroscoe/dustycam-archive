package com.dustycam.phone.ui;

import android.content.Context;
import android.content.res.ColorStateList;
import android.graphics.Typeface;
import android.graphics.drawable.Drawable;
import android.graphics.drawable.GradientDrawable;
import android.graphics.drawable.LayerDrawable;
import android.graphics.drawable.StateListDrawable;
import android.util.TypedValue;
import android.view.Gravity;
import android.view.View;
import android.widget.Button;
import android.widget.ImageView;
import android.widget.LinearLayout;
import android.widget.TextView;

import com.dustycam.phone.R;
import com.dustycam.phone.Session;

/**
 * DustyCam presentation helpers shared by {@code ScanActivity},
 * {@code CameraActivity} and {@code ProvisionActivity}: the in-app brand
 * header (mark + wordmark + per-screen kicker, styled like
 * dustycamsplash/index.html's masthead) and the button/banner styling that
 * carries the site's palette onto framework widgets. Presentation only — no
 * BLE/GATT/HTTP/crypto references here.
 *
 * <p>All colors come from res/values/colors.xml (the same hex values as
 * dustycamsplash/index.html's {@code :root}); the camera glyph is
 * res/drawable/ic_camera_mark.xml, the same path as the site's
 * {@code .brand-mark} svg.
 */
public final class Brand {

    private Brand() {}

    private static int dp(Context ctx, float v) {
        return Math.round(v * ctx.getResources().getDisplayMetrics().density);
    }

    private static int color(Context ctx, int resId) {
        return ctx.getColor(resId);
    }

    /**
     * The clay square + ink border + paper camera-glyph mark
     * (dustycamsplash .brand-mark), sized {@code sizeDp} square. The glyph
     * inset matches the site's 19px-glyph-in-28px-square ratio so it scales
     * cleanly at any header size.
     */
    private static View buildMark(Context ctx, int sizeDp) {
        int sizePx = dp(ctx, sizeDp);
        int strokePx = Math.max(1, dp(ctx, 2));
        int paddingPx = Math.round(sizePx * (1f - 19f / 28f) / 2f);

        GradientDrawable bg = new GradientDrawable();
        bg.setShape(GradientDrawable.RECTANGLE);
        bg.setColor(color(ctx, R.color.dc_clay));
        bg.setStroke(strokePx, color(ctx, R.color.dc_ink));

        ImageView iv = new ImageView(ctx);
        iv.setBackground(bg);
        iv.setImageResource(R.drawable.ic_camera_mark);
        iv.setScaleType(ImageView.ScaleType.CENTER_INSIDE);
        iv.setPadding(paddingPx, paddingPx, paddingPx, paddingPx);
        iv.setLayoutParams(new LinearLayout.LayoutParams(sizePx, sizePx));
        return iv;
    }

    /**
     * The shared masthead: mark + "dustycam" wordmark, an uppercase
     * letterspaced kicker ("SCAN"/"CAMERA"/"PROVISION") led by a short clay
     * rule, and an ink bottom rule — the same shape as the site's
     * {@code .site-header}/{@code .brand}/{@code .kicker}. Callers add this
     * as the first child of their root layout.
     */
    public static View buildHeader(Context ctx, String kickerText) {
        LinearLayout header = new LinearLayout(ctx);
        header.setOrientation(LinearLayout.VERTICAL);
        header.setPadding(dp(ctx, 16), dp(ctx, 10), dp(ctx, 16), 0);

        LinearLayout row1 = new LinearLayout(ctx);
        row1.setOrientation(LinearLayout.HORIZONTAL);
        row1.setGravity(Gravity.CENTER_VERTICAL);
        row1.addView(buildMark(ctx, 30));

        TextView wordmark = new TextView(ctx);
        wordmark.setText(R.string.app_name);
        wordmark.setTypeface(Typeface.MONOSPACE, Typeface.BOLD);
        wordmark.setTextColor(color(ctx, R.color.dc_ink));
        wordmark.setTextSize(TypedValue.COMPLEX_UNIT_SP, 20);
        wordmark.setLetterSpacing(-0.04f);
        LinearLayout.LayoutParams wmLp = new LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.WRAP_CONTENT, LinearLayout.LayoutParams.WRAP_CONTENT);
        wmLp.setMarginStart(dp(ctx, 10));
        row1.addView(wordmark, wmLp);
        header.addView(row1);

        LinearLayout row2 = new LinearLayout(ctx);
        row2.setOrientation(LinearLayout.HORIZONTAL);
        row2.setGravity(Gravity.CENTER_VERTICAL);
        row2.setPadding(0, dp(ctx, 6), 0, dp(ctx, 10));

        View rule = new View(ctx);
        rule.setBackgroundColor(color(ctx, R.color.dc_clay));
        row2.addView(rule, new LinearLayout.LayoutParams(dp(ctx, 22), dp(ctx, 2)));

        TextView kicker = new TextView(ctx);
        kicker.setText(kickerText);
        kicker.setAllCaps(true);
        kicker.setTypeface(Typeface.MONOSPACE, Typeface.BOLD);
        kicker.setTextColor(color(ctx, R.color.dc_muted));
        kicker.setTextSize(TypedValue.COMPLEX_UNIT_SP, 11);
        kicker.setLetterSpacing(0.14f);
        LinearLayout.LayoutParams kLp = new LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.WRAP_CONTENT, LinearLayout.LayoutParams.WRAP_CONTENT);
        kLp.setMarginStart(dp(ctx, 8));
        row2.addView(kicker, kLp);
        header.addView(row2);

        View bottomRule = new View(ctx);
        bottomRule.setBackgroundColor(color(ctx, R.color.dc_ink));
        header.addView(bottomRule, new LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.MATCH_PARENT, dp(ctx, 2)));

        return header;
    }

    /**
     * Site-style button: clay fill, 2px ink border, a hard offset ink
     * "shadow" ({@code box-shadow: 3px 3px 0 var(--ink)} on the site),
     * uppercase monospace paper text. Disabled state falls back to a flat
     * bone/line outline with muted text rather than just dimming, since
     * several buttons here are enabled/disabled per radio state
     * (CameraActivity#updateButtonStates) and that transition needs to read
     * clearly on a bench screen. Pressed state mirrors the site's
     * {@code .button:hover} (clay-deep fill, shadow shrunk from 3px to 1px
     * as if the face translated 2px toward it); the framework's default
     * elevation/stateListAnimator is turned off so it doesn't add its own
     * translationZ shadow on top of this hand-drawn one.
     */
    public static void styleButton(Context ctx, Button b) {
        int stroke = Math.max(1, dp(ctx, 2));
        int shadowOffset = dp(ctx, 3);
        int pressedShadowOffset = dp(ctx, 1);
        float radius = dp(ctx, 2);

        GradientDrawable shadow = new GradientDrawable();
        shadow.setShape(GradientDrawable.RECTANGLE);
        shadow.setCornerRadius(radius);
        shadow.setColor(color(ctx, R.color.dc_ink));

        GradientDrawable face = new GradientDrawable();
        face.setShape(GradientDrawable.RECTANGLE);
        face.setCornerRadius(radius);
        face.setColor(color(ctx, R.color.dc_clay));
        face.setStroke(stroke, color(ctx, R.color.dc_ink));

        LayerDrawable enabledBg = new LayerDrawable(new Drawable[]{shadow, face});
        enabledBg.setLayerInset(0, shadowOffset, shadowOffset, 0, 0);
        enabledBg.setLayerInset(1, 0, 0, shadowOffset, shadowOffset);

        GradientDrawable pressedShadow = new GradientDrawable();
        pressedShadow.setShape(GradientDrawable.RECTANGLE);
        pressedShadow.setCornerRadius(radius);
        pressedShadow.setColor(color(ctx, R.color.dc_ink));

        GradientDrawable pressedFace = new GradientDrawable();
        pressedFace.setShape(GradientDrawable.RECTANGLE);
        pressedFace.setCornerRadius(radius);
        pressedFace.setColor(color(ctx, R.color.dc_clay_deep));
        pressedFace.setStroke(stroke, color(ctx, R.color.dc_ink));

        LayerDrawable pressedBg = new LayerDrawable(new Drawable[]{pressedShadow, pressedFace});
        pressedBg.setLayerInset(0, pressedShadowOffset, pressedShadowOffset, 0, 0);
        pressedBg.setLayerInset(1, 0, 0, pressedShadowOffset, pressedShadowOffset);

        GradientDrawable disabledBg = new GradientDrawable();
        disabledBg.setShape(GradientDrawable.RECTANGLE);
        disabledBg.setCornerRadius(radius);
        disabledBg.setColor(color(ctx, R.color.dc_bone));
        disabledBg.setStroke(stroke, color(ctx, R.color.dc_line));

        StateListDrawable bg = new StateListDrawable();
        bg.addState(new int[]{-android.R.attr.state_enabled}, disabledBg);
        bg.addState(new int[]{android.R.attr.state_pressed}, pressedBg);
        bg.addState(new int[]{}, enabledBg);
        b.setBackground(bg);
        b.setStateListAnimator(null);
        b.setElevation(0f);

        ColorStateList textColors = new ColorStateList(
                new int[][]{new int[]{-android.R.attr.state_enabled}, new int[]{}},
                new int[]{color(ctx, R.color.dc_muted), color(ctx, R.color.dc_paper)});
        b.setTextColor(textColors);
        b.setTypeface(Typeface.MONOSPACE, Typeface.BOLD);
        b.setAllCaps(true);
        b.setLetterSpacing(0.02f);
        // Symmetric padding would center text in the full (shadow-inclusive)
        // bounds, leaving it visibly off-center on the face; add the shadow
        // offset to the right/bottom padding to compensate.
        b.setPadding(dp(ctx, 14), dp(ctx, 10), dp(ctx, 14) + shadowOffset, dp(ctx, 10) + shadowOffset);
    }

    /**
     * Session radio-state -> banner background (clay for transitions/attention,
     * sage for a good link, clay-deep for lost). {@code state} is unreachable
     * as null today (Session always reports a real enum value), but the
     * switch itself would NPE on one, so guard it explicitly.
     */
    public static int bannerColor(Context ctx, Session.State state) {
        if (state == null) return color(ctx, R.color.dc_clay_deep);
        switch (state) {
            case BLE: return color(ctx, R.color.dc_sage_deep);
            case WIFI: return color(ctx, R.color.dc_sage);
            case HANDOFF:
            case RETURNING: return color(ctx, R.color.dc_clay);
            case LOST:
            default: return color(ctx, R.color.dc_clay_deep);
        }
    }
}
