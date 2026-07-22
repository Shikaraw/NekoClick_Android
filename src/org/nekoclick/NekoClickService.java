package org.nekoclick;

import android.accessibilityservice.AccessibilityService;
import android.accessibilityservice.GestureDescription;
import android.content.Intent;
import android.graphics.Path;
import android.os.Build;
import android.os.Handler;
import android.os.Looper;
import android.util.Log;
import android.view.accessibility.AccessibilityEvent;

/**
 * NekoClick 无障碍服务
 * 通过 Android AccessibilityService 的 dispatchGesture API 实现模拟点击/滑动
 */
public class NekoClickService extends AccessibilityService {

    private static final String TAG = "NekoClickService";
    private static NekoClickService instance = null;
    private static boolean running = false;
    private final Handler handler = new Handler(Looper.getMainLooper());

    @Override
    public void onCreate() {
        super.onCreate();
        instance = this;
        running = true;
        Log.i(TAG, "无障碍服务已启动");
    }

    @Override
    public void onDestroy() {
        instance = null;
        running = false;
        Log.i(TAG, "无障碍服务已停止");
        super.onDestroy();
    }

    @Override
    public void onAccessibilityEvent(AccessibilityEvent event) {
        // 不需要处理事件
    }

    @Override
    public void onInterrupt() {
        Log.w(TAG, "服务被中断");
    }

    // ──────────────── Python 层调用的静态方法 ────────────────

    /** 检查服务是否正在运行 */
    public static boolean isServiceRunning() {
        return instance != null && running;
    }

    /** 单击 */
    public static boolean tap(final int x, final int y) {
        if (instance == null) return false;
        if (Build.VERSION.SDK_INT < 24) return false; // 需要 Android 7.0+

        Path path = new Path();
        path.moveTo(x, y);
        GestureDescription.Builder builder = new GestureDescription.Builder();
        builder.addStroke(new GestureDescription.StrokeDescription(path, 0, 80)); // 80ms 触摸时长

        return instance.dispatchGesture(builder.build(), null, null);
    }

    /** 双击 */
    public static boolean doubleTap(final int x, final int y) {
        if (instance == null) return false;
        if (Build.VERSION.SDK_INT < 24) return false;

        // 第一次点击
        Path path1 = new Path();
        path1.moveTo(x, y);
        GestureDescription.StrokeDescription stroke1 =
                new GestureDescription.StrokeDescription(path1, 0, 80);

        // 第二次点击（间隔 100ms 后开始）
        Path path2 = new Path();
        path2.moveTo(x, y);
        GestureDescription.StrokeDescription stroke2 =
                new GestureDescription.StrokeDescription(path2, 180, 80);

        GestureDescription.Builder builder = new GestureDescription.Builder();
        builder.addStroke(stroke1);
        builder.addStroke(stroke2);

        return instance.dispatchGesture(builder.build(), null, null);
    }

    /** 长按 */
    public static boolean longPress(final int x, final int y, final int durationMs) {
        if (instance == null) return false;
        if (Build.VERSION.SDK_INT < 24) return false;

        Path path = new Path();
        path.moveTo(x, y);
        GestureDescription.Builder builder = new GestureDescription.Builder();
        builder.addStroke(new GestureDescription.StrokeDescription(path, 0, durationMs));

        return instance.dispatchGesture(builder.build(), null, null);
    }

    /** 滑动 */
    public static boolean swipe(final int x1, final int y1,
                                 final int x2, final int y2,
                                 final int durationMs) {
        if (instance == null) return false;
        if (Build.VERSION.SDK_INT < 24) return false;

        Path path = new Path();
        path.moveTo(x1, y1);
        path.lineTo(x2, y2);
        GestureDescription.Builder builder = new GestureDescription.Builder();
        builder.addStroke(new GestureDescription.StrokeDescription(path, 0, durationMs));

        return instance.dispatchGesture(builder.build(), null, null);
    }
}
