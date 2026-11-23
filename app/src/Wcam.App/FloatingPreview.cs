using Wcam.VirtualCamera;
using Windows.Win32;
using Windows.Win32.Foundation;
using Windows.Win32.UI.Input.KeyboardAndMouse;
using Windows.Win32.UI.WindowsAndMessaging;

namespace Wcam.App;

internal sealed unsafe class FloatingPreview : NativeWindow
{
    public const int BaseWidth = 320;
    public const int BaseHeight = 180;
    public const int MinimumBaseWidth = 160;
    public const int MaximumBaseWidth = 960;
    private const int BaseResizeBorder = 6;
    private static readonly TimeSpan FramePoll = TimeSpan.FromMilliseconds(3);
    private static readonly TimeSpan IdlePoll = TimeSpan.FromMilliseconds(250);

    private readonly CancellationTokenSource _stop = new();
    private readonly CloseButton _close;
    private readonly double _scale;
    private Thread? _renderer;
    private int _width;
    private int _height;
    private bool _hovering;

    public FloatingPreview(WindowBounds bounds, double scale, string closeLabel)
    {
        _scale = scale;
        Create(
            WINDOW_EX_STYLE.WS_EX_TOPMOST | WINDOW_EX_STYLE.WS_EX_NOACTIVATE | WINDOW_EX_STYLE.WS_EX_TOOLWINDOW,
            WINDOW_STYLE.WS_POPUP | WINDOW_STYLE.WS_THICKFRAME,
            HWND.Null);
        ScreenCapture.Exclude(Handle);
        fixed (char* title = closeLabel)
        {
            PInvoke.SetWindowText(Handle, title);
        }
        _close = new CloseButton(Handle, (int)Math.Round(CloseButton.BaseSize * scale));
        _close.Clicked += () => Closed?.Invoke();
        _close.Left += HideCloseUnlessOverPreview;
        _width = bounds.Width;
        _height = bounds.Height;
        PInvoke.SetWindowPos(
            Handle, HWND.HWND_TOPMOST, bounds.X, bounds.Y, bounds.Width, bounds.Height,
            SET_WINDOW_POS_FLAGS.SWP_NOACTIVATE | SET_WINDOW_POS_FLAGS.SWP_SHOWWINDOW | SET_WINDOW_POS_FLAGS.SWP_FRAMECHANGED);
        _renderer = new Thread(Render) { IsBackground = true, Name = "WCam floating preview" };
        _renderer.Start();
    }

    public event Action? Closed;

    public event Action<WindowBounds>? BoundsChanged;

    public void Close()
    {
        _stop.Cancel();
        _renderer?.Join();
        _renderer = null;
        _close.Dispose();
        Dispose();
    }
    protected override LRESULT OnMessage(uint message, WPARAM wParam, LPARAM lParam)
    {
        switch (message)
        {
            case PInvoke.WM_NCCALCSIZE when wParam.Value != 0:
                return new LRESULT(0);
            case PInvoke.WM_NCHITTEST:
                return new LRESULT((nint)HitTest(lParam));
            case PInvoke.WM_NCMOUSEMOVE:
                ShowClose();
                break;
            case PInvoke.WM_NCMOUSELEAVE:
                HideCloseUnlessOver();
                break;
            case PInvoke.WM_SIZING:
                KeepAspect((RECT*)lParam.Value, (uint)wParam.Value);
                return new LRESULT(1);
            case PInvoke.WM_SIZE:
                _width = (int)(lParam.Value & 0xFFFF);
                _height = (int)((lParam.Value >> 16) & 0xFFFF);
                PlaceClose();
                break;
            case PInvoke.WM_MOVE:
                PlaceClose();
                break;
            case PInvoke.WM_EXITSIZEMOVE:
                BoundsChanged?.Invoke(CurrentBounds());
                break;
            case PInvoke.WM_MOUSEACTIVATE:
                return new LRESULT((nint)PInvoke.MA_NOACTIVATE);
        }
        return base.OnMessage(message, wParam, lParam);
    }


    private void Render()
    {
        using var presenter = new VideoPresenter(Handle, Math.Max(1, _width), Math.Max(1, _height));
        using var reader = new PublishedFrameReader(AppPaths.FramesSection, TimeProvider.System);
        using var timer = new PollTimer();
        byte[] frame = [];
        bool showingBlack = false;
        while (!_stop.IsCancellationRequested)
        {
            presenter.Resize(_width, _height);
            TimeSpan wait = FramePoll;
            if (!reader.TryReadFormat(out FrameFormat format))
            {
                showingBlack = ShowBlack(presenter, showingBlack);
                wait = IdlePoll;
            }
            else
            {
                if (frame.Length != format.FrameSize)
                {
                    frame = new byte[format.FrameSize];
                }
                FrameRead read = reader.ReadLatest(frame, format, out _);
                if (read == FrameRead.New)
                {
                    presenter.Present(frame, format.Width, format.Height);
                    showingBlack = false;
                }
                else if (read == FrameRead.Idle)
                {
                    showingBlack = ShowBlack(presenter, showingBlack);
                    wait = IdlePoll;
                }
            }
            timer.Wait(wait, _stop.Token.WaitHandle);
        }
    }

    private static bool ShowBlack(VideoPresenter presenter, bool showingBlack)
    {
        if (!showingBlack)
        {
            presenter.PresentBlack();
        }
        return true;
    }

    private HitTestResult HitTest(LPARAM lParam)
    {
        PInvoke.GetWindowRect(Handle, out RECT window);
        int x = (short)(lParam.Value & 0xFFFF);
        int y = (short)((lParam.Value >> 16) & 0xFFFF);
        int border = (int)Math.Round(BaseResizeBorder * _scale);
        bool left = x < window.left + border;
        bool right = x >= window.right - border;
        bool top = y < window.top + border;
        bool bottom = y >= window.bottom - border;
        return (left, right, top, bottom) switch
        {
            (true, _, true, _) => HitTestResult.TopLeft,
            (_, true, true, _) => HitTestResult.TopRight,
            (true, _, _, true) => HitTestResult.BottomLeft,
            (_, true, _, true) => HitTestResult.BottomRight,
            (true, _, _, _) => HitTestResult.Left,
            (_, true, _, _) => HitTestResult.Right,
            (_, _, true, _) => HitTestResult.Top,
            (_, _, _, true) => HitTestResult.Bottom,
            _ => HitTestResult.Caption,
        };
    }

    private void KeepAspect(RECT* rect, uint edge)
    {
        int minimum = (int)Math.Round(MinimumBaseWidth * _scale);
        int maximum = (int)Math.Round(MaximumBaseWidth * _scale);
        bool vertical = edge is (uint)ResizeEdge.Top or (uint)ResizeEdge.Bottom;
        int width = vertical ? (rect->bottom - rect->top) * 16 / 9 : rect->right - rect->left;
        width = Math.Clamp(width, minimum, maximum);
        int height = width * 9 / 16;
        if (edge is (uint)ResizeEdge.Left or (uint)ResizeEdge.TopLeft or (uint)ResizeEdge.BottomLeft)
        {
            rect->left = rect->right - width;
        }
        else
        {
            rect->right = rect->left + width;
        }
        if (edge is (uint)ResizeEdge.Top or (uint)ResizeEdge.TopLeft or (uint)ResizeEdge.TopRight)
        {
            rect->top = rect->bottom - height;
        }
        else
        {
            rect->bottom = rect->top + height;
        }
    }

    private void ShowClose()
    {
        if (_hovering)
        {
            return;
        }
        _hovering = true;
        var track = new TRACKMOUSEEVENT
        {
            cbSize = (uint)sizeof(TRACKMOUSEEVENT),
            dwFlags = TRACKMOUSEEVENT_FLAGS.TME_LEAVE | TRACKMOUSEEVENT_FLAGS.TME_NONCLIENT,
            hwndTrack = Handle,
        };
        PInvoke.TrackMouseEvent(ref track);
        PlaceClose();
        _close.Show();
    }

    private void HideCloseUnlessOver()
    {
        _hovering = false;
        if (!_close.ContainsCursor())
        {
            _close.Hide();
        }
    }

    private void HideCloseUnlessOverPreview()
    {
        PInvoke.GetCursorPos(out System.Drawing.Point cursor);
        PInvoke.GetWindowRect(Handle, out RECT window);
        bool over = cursor.X >= window.left && cursor.X < window.right && cursor.Y >= window.top && cursor.Y < window.bottom;
        if (!over)
        {
            _close.Hide();
        }
    }

    private void PlaceClose()
    {
        PInvoke.GetWindowRect(Handle, out RECT window);
        _close.MoveTo(window.right - _close.Size, window.top);
    }

    private WindowBounds CurrentBounds()
    {
        PInvoke.GetWindowRect(Handle, out RECT window);
        return new WindowBounds(window.left, window.top, window.right - window.left, window.bottom - window.top);
    }

    private enum HitTestResult
    {
        Caption = 2,
        Left = 10,
        Right = 11,
        Top = 12,
        TopLeft = 13,
        TopRight = 14,
        Bottom = 15,
        BottomLeft = 16,
        BottomRight = 17,
    }

    private enum ResizeEdge : uint
    {
        Left = 1,
        Right = 2,
        Top = 3,
        TopLeft = 4,
        TopRight = 5,
        Bottom = 6,
        BottomLeft = 7,
        BottomRight = 8,
    }
}
