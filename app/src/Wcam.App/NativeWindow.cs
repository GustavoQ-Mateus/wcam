using System.ComponentModel;
using System.Runtime.CompilerServices;
using System.Runtime.InteropServices;
using Windows.Win32;
using Windows.Win32.Foundation;
using Windows.Win32.UI.WindowsAndMessaging;

namespace Wcam.App;

internal abstract unsafe class NativeWindow : IDisposable
{
    private const string ClassName = "WCam.NativeWindow";
    private static readonly Dictionary<nint, NativeWindow> Windows = [];
    private static bool _registered;
    [ThreadStatic]
    private static NativeWindow? _creating;

    protected HWND Handle { get; private set; }

    public void Dispose()
    {
        if (Handle.IsNull)
        {
            return;
        }
        PInvoke.DestroyWindow(Handle);
        GC.SuppressFinalize(this);
    }

    protected void Create(WINDOW_EX_STYLE extendedStyle, WINDOW_STYLE style, HWND parent)
    {
        Register();
        fixed (char* className = ClassName)
        {
            _creating = this;
            HWND handle = PInvoke.CreateWindowEx(
                extendedStyle, className, (PCWSTR)null, style, 0, 0, 0, 0, parent, HMENU.Null, HINSTANCE.Null, null);
            _creating = null;
            if (handle.IsNull)
            {
                throw new Win32Exception();
            }
            Handle = handle;
        }
    }

    protected virtual LRESULT OnMessage(uint message, WPARAM wParam, LPARAM lParam) =>
        PInvoke.DefWindowProc(Handle, message, wParam, lParam);

    protected virtual void OnDestroyed()
    {
    }

    private static void Register()
    {
        if (_registered)
        {
            return;
        }
        fixed (char* className = ClassName)
        {
            var windowClass = new WNDCLASSEXW
            {
                cbSize = (uint)sizeof(WNDCLASSEXW),
                lpfnWndProc = &WindowProcedure,
                lpszClassName = className,
                hCursor = PInvoke.LoadCursor(HINSTANCE.Null, PInvoke.IDC_ARROW),
            };
            if (PInvoke.RegisterClassEx(&windowClass) == 0)
            {
                throw new Win32Exception();
            }
        }
        _registered = true;
    }

    [UnmanagedCallersOnly(CallConvs = [typeof(CallConvStdcall)])]
    private static LRESULT WindowProcedure(HWND hwnd, uint message, WPARAM wParam, LPARAM lParam)
    {
        if (!Windows.TryGetValue(hwnd, out NativeWindow? window))
        {
            if (_creating is null)
            {
                return PInvoke.DefWindowProc(hwnd, message, wParam, lParam);
            }
            window = _creating;
            window.Handle = hwnd;
            Windows[hwnd] = window;
        }
        if (message == PInvoke.WM_NCDESTROY)
        {
            Windows.Remove(hwnd);
            window.Handle = HWND.Null;
            window.OnDestroyed();
            return PInvoke.DefWindowProc(hwnd, message, wParam, lParam);
        }
        try
        {
            return window.OnMessage(message, wParam, lParam);
        }
        catch (Exception exception)
        {
            Environment.FailFast(exception.Message, exception);
            return new LRESULT(0);
        }
    }
}
