using Microsoft.UI;
using Microsoft.UI.Windowing;
using Microsoft.UI.Xaml;
using Microsoft.UI.Xaml.Controls;
using Microsoft.Web.WebView2.Core;
using Windows.Graphics;

namespace Wcam.App;

internal sealed class ConsoleWindow
{
    private const int DefaultWidth = 1280;
    private const int DefaultHeight = 820;

    private readonly Uri _address;
    private readonly Window _window;
    private readonly WebView2 _webView;
    private PreviewBridge? _preview;
    private bool _navigationFailed;

    public ConsoleWindow(Uri address, string title, WindowBounds? bounds, Microsoft.UI.IconId icon)
    {
        _address = address;
        _webView = new WebView2 { DefaultBackgroundColor = Colors.Black };
        _window = new Window { Title = title, Content = _webView };
        _window.AppWindow.SetIcon(icon);
        _window.AppWindow.Closing += OnClosing;
        Place(bounds);
        _webView.CoreWebView2Initialized += OnWebViewReady;
        _webView.NavigationCompleted += (_, args) => _navigationFailed = !args.IsSuccess;
        _webView.Source = address;
    }

    public event Action<WindowBounds>? BoundsChanged;

    public void Show()
    {
        _window.AppWindow.Show();
        if (_window.AppWindow.Presenter is OverlappedPresenter { State: OverlappedPresenterState.Minimized } presenter)
        {
            presenter.Restore();
        }
        _webView.Visibility = Visibility.Visible;
        _window.Activate();
    }

    public void ReloadIfFailed()
    {
        if (_navigationFailed)
        {
            _webView.Reload();
        }
    }

    public void Hide()
    {
        BoundsChanged?.Invoke(CurrentBounds());
        _webView.Visibility = Visibility.Collapsed;
        _window.AppWindow.Hide();
    }

    public void Close()
    {
        _preview?.Dispose();
        _window.AppWindow.Closing -= OnClosing;
        _window.Close();
    }

    private void OnClosing(AppWindow sender, AppWindowClosingEventArgs args)
    {
        args.Cancel = true;
        Hide();
    }

    private void OnWebViewReady(WebView2 sender, CoreWebView2InitializedEventArgs args)
    {
        CoreWebView2 core = sender.CoreWebView2;
        CoreWebView2Settings settings = core.Settings;
        settings.IsZoomControlEnabled = false;
#if !DEBUG
        settings.AreDefaultContextMenusEnabled = false;
        settings.AreDevToolsEnabled = false;
        settings.AreBrowserAcceleratorKeysEnabled = false;
#endif
        core.PermissionRequested += OnPermissionRequested;
        core.NewWindowRequested += OnNewWindowRequested;
        _preview = new PreviewBridge(core, _window.DispatcherQueue);
    }

    private void OnPermissionRequested(CoreWebView2 sender, CoreWebView2PermissionRequestedEventArgs args)
    {
        if (args.PermissionKind != CoreWebView2PermissionKind.Camera)
        {
            return;
        }
        bool console = Uri.TryCreate(args.Uri, UriKind.Absolute, out Uri? origin)
            && Uri.Compare(origin, _address, UriComponents.SchemeAndServer, UriFormat.Unescaped, StringComparison.OrdinalIgnoreCase) == 0;
        args.State = console ? CoreWebView2PermissionState.Allow : CoreWebView2PermissionState.Deny;
    }

    private static void OnNewWindowRequested(CoreWebView2 sender, CoreWebView2NewWindowRequestedEventArgs args)
    {
        args.Handled = true;
        if (Uri.TryCreate(args.Uri, UriKind.Absolute, out Uri? target))
        {
            _ = Windows.System.Launcher.LaunchUriAsync(target);
        }
    }

    private void Place(WindowBounds? bounds)
    {
        if (bounds is null || !IsOnScreen(bounds))
        {
            _window.AppWindow.Resize(new SizeInt32(DefaultWidth, DefaultHeight));
            return;
        }
        _window.AppWindow.MoveAndResize(new RectInt32(bounds.X, bounds.Y, bounds.Width, bounds.Height));
    }

    private static bool IsOnScreen(WindowBounds bounds)
    {
        var rect = new RectInt32(bounds.X, bounds.Y, bounds.Width, bounds.Height);
        RectInt32 area = DisplayArea.GetFromRect(rect, DisplayAreaFallback.None)?.WorkArea ?? default;
        return area.Width > 0 && bounds.X < area.X + area.Width && bounds.Y < area.Y + area.Height
            && bounds.X + bounds.Width > area.X && bounds.Y + bounds.Height > area.Y;
    }

    private WindowBounds CurrentBounds()
    {
        PointInt32 position = _window.AppWindow.Position;
        SizeInt32 size = _window.AppWindow.Size;
        return new WindowBounds(position.X, position.Y, size.Width, size.Height);
    }
}
