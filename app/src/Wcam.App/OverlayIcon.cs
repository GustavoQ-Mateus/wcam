using Windows.Win32;
using Windows.Win32.Foundation;
using Windows.Win32.UI.Input.KeyboardAndMouse;
using Windows.Win32.UI.WindowsAndMessaging;

namespace Wcam.App;

internal sealed unsafe class OverlayIcon : LayeredWindow
{
    public const int BaseSize = 36;
    private const int ControlKey = 0x11;
    private const ushort KeyDownBit = 0x8000;
    private const uint HoverTimer = 1;
    private const uint HoverIntervalMilliseconds = 50;
    private const uint SnapTimer = 2;
    private const uint SnapIntervalMilliseconds = 10;
    private static readonly TimeSpan SnapDuration = TimeSpan.FromMilliseconds(160);

    private TrayState _state = TrayState.Waiting;
    private int _size;
    private int _x;
    private int _y;
    private bool _hovering;
    private bool _dragging;
    private (int X, int Y) _grabOffset;
    private (int X, int Y) _snapFrom;
    private (int X, int Y) _snapTo;
    private long _snapStart;

    public OverlayIcon()
    {
        CreateLayered(HWND.Null);
    }

    public event Action? OpenRequested;

    public event Action<int, int>? Dropped;

    public event Action? DisplayChanged;

    public int Size => _size;

    public (int X, int Y) Position => (_x, _y);

    public bool Dragging => _dragging;

    public void Place(int x, int y, int size, bool animate)
    {
        _size = size;
        if (!animate || !Motion.Enabled)
        {
            MoveTo(x, y);
            return;
        }
        _snapFrom = (_x, _y);
        _snapTo = (x, y);
        _snapStart = Environment.TickCount64;
        PInvoke.SetTimer(Handle, SnapTimer, SnapIntervalMilliseconds, null);
    }

    public void SetState(TrayState state)
    {
        if (state == _state && _size > 0)
        {
            return;
        }
        _state = state;
        Repaint();
    }

    protected override LRESULT OnMessage(uint message, WPARAM wParam, LPARAM lParam)
    {
        switch (message)
        {
            case PInvoke.WM_MOUSEMOVE:
                OnMouseMove();
                return new LRESULT(0);
            case PInvoke.WM_MOUSELEAVE:
                _hovering = false;
                PInvoke.KillTimer(Handle, HoverTimer);
                return new LRESULT(0);
            case PInvoke.WM_LBUTTONDOWN:
                OnButtonDown();
                return new LRESULT(0);
            case PInvoke.WM_LBUTTONUP:
                OnButtonUp();
                return new LRESULT(0);
            case PInvoke.WM_TIMER when wParam.Value == HoverTimer:
                OpenIfControlHeld();
                return new LRESULT(0);
            case PInvoke.WM_TIMER when wParam.Value == SnapTimer:
                StepSnap();
                return new LRESULT(0);
            case PInvoke.WM_MOUSEACTIVATE:
                return new LRESULT((nint)PInvoke.MA_NOACTIVATE);
            case PInvoke.WM_DISPLAYCHANGE or PInvoke.WM_DPICHANGED or PInvoke.WM_SETTINGCHANGE when !_dragging:
                DisplayChanged?.Invoke();
                break;
        }
        return base.OnMessage(message, wParam, lParam);
    }

    private void OnMouseMove()
    {
        if (_dragging)
        {
            PInvoke.GetCursorPos(out System.Drawing.Point cursor);
            MoveTo(cursor.X - _grabOffset.X, cursor.Y - _grabOffset.Y);
            return;
        }
        if (!_hovering)
        {
            _hovering = true;
            TrackLeave();
            PInvoke.SetTimer(Handle, HoverTimer, HoverIntervalMilliseconds, null);
        }
        OpenIfControlHeld();
    }

    private void OnButtonDown()
    {
        if (!ControlHeld())
        {
            OpenRequested?.Invoke();
            return;
        }
        PInvoke.GetCursorPos(out System.Drawing.Point cursor);
        _grabOffset = (cursor.X - _x, cursor.Y - _y);
        _dragging = true;
        PInvoke.KillTimer(Handle, SnapTimer);
        PInvoke.SetCapture(Handle);
    }

    private void OnButtonUp()
    {
        if (!_dragging)
        {
            return;
        }
        _dragging = false;
        PInvoke.ReleaseCapture();
        Dropped?.Invoke(_x + _size / 2, _y + _size / 2);
    }

    private void OpenIfControlHeld()
    {
        if (_hovering && !_dragging && ControlHeld() && !MouseButtonHeld())
        {
            OpenRequested?.Invoke();
        }
    }

    private void StepSnap()
    {
        double progress = Math.Min(1, (Environment.TickCount64 - _snapStart) / SnapDuration.TotalMilliseconds);
        double eased = 1 - Math.Pow(1 - progress, 3);
        MoveTo(
            _snapFrom.X + (int)Math.Round((_snapTo.X - _snapFrom.X) * eased),
            _snapFrom.Y + (int)Math.Round((_snapTo.Y - _snapFrom.Y) * eased));
        if (progress >= 1)
        {
            PInvoke.KillTimer(Handle, SnapTimer);
        }
    }

    private void MoveTo(int x, int y)
    {
        _x = x;
        _y = y;
        Repaint();
    }

    private void Repaint()
    {
        if (_size > 0)
        {
            Paint(IconPainter.PaintOverlay(_state, _size), _size, _x, _y);
        }
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

    private static bool ControlHeld() => (PInvoke.GetAsyncKeyState(ControlKey) & KeyDownBit) != 0;

    private static bool MouseButtonHeld() => (PInvoke.GetAsyncKeyState((int)VIRTUAL_KEY.VK_LBUTTON) & KeyDownBit) != 0;
}

internal static unsafe class Motion
{
    public static bool Enabled
    {
        get
        {
            BOOL enabled = true;
            PInvoke.SystemParametersInfo(SYSTEM_PARAMETERS_INFO_ACTION.SPI_GETCLIENTAREAANIMATION, 0, &enabled, 0);
            return enabled;
        }
    }
}
