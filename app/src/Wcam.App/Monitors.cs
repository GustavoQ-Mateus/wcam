using System.Runtime.CompilerServices;
using System.Runtime.InteropServices;
using Windows.Win32;
using Windows.Win32.Foundation;
using Windows.Win32.Graphics.Gdi;
using Windows.Win32.UI.HiDpi;

namespace Wcam.App;

internal static unsafe class Monitors
{
    private const uint PrimaryFlag = 1;
    private const int DefaultDpi = 96;

    [ThreadStatic]
    private static List<Monitor>? _collecting;

    public static IReadOnlyList<Monitor> All()
    {
        _collecting = [];
        PInvoke.EnumDisplayMonitors(HDC.Null, null, &Collect, default);
        List<Monitor> monitors = _collecting;
        _collecting = null;
        return monitors;
    }

    public static double ScaleAt(int x, int y)
    {
        HMONITOR monitor = PInvoke.MonitorFromPoint(new System.Drawing.Point(x, y), MONITOR_FROM_FLAGS.MONITOR_DEFAULTTOPRIMARY);
        PInvoke.GetDpiForMonitor(monitor, MONITOR_DPI_TYPE.MDT_EFFECTIVE_DPI, out uint dpiX, out _);
        return (double)dpiX / DefaultDpi;
    }

    [UnmanagedCallersOnly(CallConvs = [typeof(CallConvStdcall)])]
    private static BOOL Collect(HMONITOR monitor, HDC context, RECT* bounds, LPARAM data)
    {
        var info = new MONITORINFOEXW();
        info.monitorInfo.cbSize = (uint)sizeof(MONITORINFOEXW);
        if (PInvoke.GetMonitorInfo(monitor, (MONITORINFO*)&info))
        {
            RECT work = info.monitorInfo.rcWork;
            _collecting!.Add(new Monitor(
                info.szDevice.ToString(),
                new ScreenRect(work.left, work.top, work.right, work.bottom),
                (info.monitorInfo.dwFlags & PrimaryFlag) != 0));
        }
        return true;
    }
}
