using System.Drawing;
using Windows.Win32;
using Windows.Win32.Foundation;
using Windows.Win32.Graphics.Gdi;
using Windows.Win32.UI.WindowsAndMessaging;

namespace Wcam.App;

internal abstract unsafe class LayeredWindow : NativeWindow
{
    private const byte Opaque = 255;
    private const byte AlphaFormat = 1;

    protected void CreateLayered(HWND owner)
    {
        Create(
            WINDOW_EX_STYLE.WS_EX_LAYERED | WINDOW_EX_STYLE.WS_EX_TOPMOST | WINDOW_EX_STYLE.WS_EX_NOACTIVATE
                | WINDOW_EX_STYLE.WS_EX_TOOLWINDOW,
            WINDOW_STYLE.WS_POPUP,
            owner);
        ScreenCapture.Exclude(Handle);
    }

    protected void Paint(uint[] premultipliedPixels, int size, int x, int y)
    {
        HDC screen = PInvoke.GetDC(HWND.Null);
        HDC memory = PInvoke.CreateCompatibleDC(screen);
        HBITMAP bitmap = IconFactory.CreateBitmap(premultipliedPixels, size);
        HGDIOBJ previous = PInvoke.SelectObject(memory, bitmap);
        var position = new Point(x, y);
        var dimensions = new SIZE(size, size);
        var source = new Point(0, 0);
        var blend = new BLENDFUNCTION { BlendOp = 0, SourceConstantAlpha = Opaque, AlphaFormat = AlphaFormat };
        PInvoke.UpdateLayeredWindow(
            Handle, screen, &position, &dimensions, memory, &source, new COLORREF(0), &blend, UPDATE_LAYERED_WINDOW_FLAGS.ULW_ALPHA);
        PInvoke.SelectObject(memory, previous);
        PInvoke.DeleteObject(bitmap);
        PInvoke.DeleteDC(memory);
        PInvoke.ReleaseDC(HWND.Null, screen);
    }

    public void Show() => PInvoke.ShowWindow(Handle, SHOW_WINDOW_CMD.SW_SHOWNOACTIVATE);

    public void Hide() => PInvoke.ShowWindow(Handle, SHOW_WINDOW_CMD.SW_HIDE);
}

internal static class ScreenCapture
{
    private const string InspectionVariable = "WCAM_CAPTURE_OVERLAY";
    private static readonly bool Inspecting = Environment.GetEnvironmentVariable(InspectionVariable) == "1";

    public static void Exclude(HWND window)
    {
        if (!Inspecting)
        {
            PInvoke.SetWindowDisplayAffinity(window, WINDOW_DISPLAY_AFFINITY.WDA_EXCLUDEFROMCAPTURE);
        }
    }
}
