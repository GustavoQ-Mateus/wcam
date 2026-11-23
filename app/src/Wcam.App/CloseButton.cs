using Windows.Win32;
using Windows.Win32.Foundation;
using Windows.Win32.UI.Input.KeyboardAndMouse;
using Windows.Win32.UI.WindowsAndMessaging;

namespace Wcam.App;

internal sealed unsafe class CloseButton : LayeredWindow
{
    public const int BaseSize = 28;
    private const uint ScrimPremultiplied = 0x99000000;
    private const double CrossHalfLength = 0.18;
    private const double CrossHalfWidth = 0.035;
    private const int Supersample = 4;

    private readonly uint[] _pixels;
    private int _x;
    private int _y;

    public CloseButton(HWND owner, int size)
    {
        Size = size;
        _pixels = Draw(size);
        CreateLayered(owner);
    }

    public event Action? Clicked;

    public event Action? Left;

    public int Size { get; }

    public void MoveTo(int x, int y)
    {
        _x = x;
        _y = y;
        Paint(_pixels, Size, x, y);
    }

    public bool ContainsCursor()
    {
        PInvoke.GetCursorPos(out System.Drawing.Point cursor);
        return cursor.X >= _x && cursor.X < _x + Size && cursor.Y >= _y && cursor.Y < _y + Size;
    }

    protected override LRESULT OnMessage(uint message, WPARAM wParam, LPARAM lParam)
    {
        switch (message)
        {
            case PInvoke.WM_MOUSEMOVE:
                TrackLeave();
                return new LRESULT(0);
            case PInvoke.WM_MOUSELEAVE:
                Left?.Invoke();
                return new LRESULT(0);
            case PInvoke.WM_LBUTTONUP:
                Clicked?.Invoke();
                return new LRESULT(0);
            case PInvoke.WM_MOUSEACTIVATE:
                return new LRESULT((nint)PInvoke.MA_NOACTIVATE);
        }
        return base.OnMessage(message, wParam, lParam);
    }

    private void TrackLeave()
    {
        var track = new TRACKMOUSEEVENT
        {
            cbSize = (uint)sizeof(TRACKMOUSEEVENT),
            dwFlags = TRACKMOUSEEVENT_FLAGS.TME_LEAVE,
            hwndTrack = Handle,
        };
        PInvoke.TrackMouseEvent(ref track);
    }

    private static uint[] Draw(int size)
    {
        var pixels = new uint[size * size];
        for (int y = 0; y < size; y++)
        {
            for (int x = 0; x < size; x++)
            {
                pixels[y * size + x] = Pixel(x, y, size);
            }
        }
        return pixels;
    }

    private static uint Pixel(int x, int y, int size)
    {
        int cross = 0;
        int background = 0;
        for (int sampleY = 0; sampleY < Supersample; sampleY++)
        {
            for (int sampleX = 0; sampleX < Supersample; sampleX++)
            {
                double u = (x + (sampleX + 0.5) / Supersample) / size - 0.5;
                double v = (y + (sampleY + 0.5) / Supersample) / size - 0.5;
                if (u * u + v * v > 0.25)
                {
                    continue;
                }
                background++;
                bool onDiagonal = Math.Abs(u - v) / Math.Sqrt(2) <= CrossHalfWidth;
                bool onAntiDiagonal = Math.Abs(u + v) / Math.Sqrt(2) <= CrossHalfWidth;
                bool inLength = Math.Abs(u) <= CrossHalfLength && Math.Abs(v) <= CrossHalfLength;
                cross += inLength && (onDiagonal || onAntiDiagonal) ? 1 : 0;
            }
        }
        const double samples = Supersample * Supersample;
        double crossCoverage = cross / samples;
        double scrimCoverage = (background - cross) / samples;
        double scrimAlpha = (ScrimPremultiplied >> 24) / 255.0;
        double alpha = crossCoverage + scrimCoverage * scrimAlpha;
        uint channel = (uint)Math.Round(crossCoverage * 255);
        return (uint)Math.Round(alpha * 255) << 24 | channel << 16 | channel << 8 | channel;
    }
}
