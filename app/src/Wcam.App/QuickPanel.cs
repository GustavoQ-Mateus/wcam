using Microsoft.UI;
using Microsoft.UI.Dispatching;
using Microsoft.UI.Windowing;
using Microsoft.UI.Xaml;
using Microsoft.UI.Xaml.Controls;
using Microsoft.UI.Xaml.Input;
using Microsoft.UI.Xaml.Media;
using Microsoft.UI.Xaml.Media.Animation;
using Windows.Graphics;
using VirtualKey = Windows.System.VirtualKey;
using Windows.UI;
using Windows.Win32;
using Windows.Win32.Foundation;
using Windows.Win32.UI.WindowsAndMessaging;

namespace Wcam.App;

internal sealed class QuickPanel
{
    public const double Width = 248;
    private const double Padding = 8;
    private const double RowHeight = 36;
    private const double Gap = 8;
    private const double Shift = 4;
    private static readonly TimeSpan OpenDuration = TimeSpan.FromMilliseconds(120);
    private static readonly TimeSpan CloseDuration = TimeSpan.FromMilliseconds(90);
    private static readonly TimeSpan LeavePoll = TimeSpan.FromMilliseconds(100);
    private static readonly TimeSpan LeaveGrace = TimeSpan.FromMilliseconds(400);
    private static readonly Color Surface = Color.FromArgb(255, 0x11, 0x11, 0x11);
    private static readonly Color Raised = Color.FromArgb(255, 0x2a, 0x2a, 0x2a);
    private static readonly Color RaisedHover = Color.FromArgb(255, 0x35, 0x35, 0x35);
    private static readonly Color Divider = Color.FromArgb(255, 0x22, 0x22, 0x22);
    private static readonly Color Ink = Color.FromArgb(255, 0xff, 0xff, 0xff);
    private static readonly Color Muted = Color.FromArgb(255, 0xb4, 0xb4, 0xb4);
    private static readonly Color Faint = Color.FromArgb(255, 0x94, 0x94, 0x94);

    private readonly Window _window;
    private readonly HWND _handle;
    private readonly StackPanel _root;
    private readonly TranslateTransform _offset = new();
    private readonly DispatcherQueueTimer _leaveTimer;
    private IReadOnlyList<MenuEntry> _entries = [];
    private Func<(int X, int Y, int Size)> _anchor = () => (0, 0, 0);
    private HWND _previousForeground;
    private bool _keyboard;
    private bool _open;
    private TimeSpan _outside;

    public QuickPanel(string title)
    {
        _root = new StackPanel
        {
            Background = new SolidColorBrush(Surface),
            Padding = new Thickness(Padding),
            RenderTransform = _offset,
            XYFocusKeyboardNavigation = XYFocusKeyboardNavigationMode.Enabled,
            TabFocusNavigation = KeyboardNavigationMode.Cycle,
            RequestedTheme = ElementTheme.Dark,
        };
        StyleButtons(_root.Resources);
        _root.KeyDown += OnKeyDown;
        _window = new Window { Title = title, Content = _root };
        _handle = new HWND(Win32Interop.GetWindowFromWindowId(_window.AppWindow.Id));
        ConfigureWindow();
        _window.Activated += OnActivated;
        _leaveTimer = _window.DispatcherQueue.CreateTimer();
        _leaveTimer.Interval = LeavePoll;
        _leaveTimer.Tick += (_, _) => CloseWhenPointerLeft();
    }

    public event Action<TrayAction>? Selected;

    public bool IsOpen => _open;

    public void Update(string header, IReadOnlyList<MenuEntry> entries, IReadOnlyList<string> texts, IReadOnlyList<string> footer)
    {
        _entries = entries;
        int focused = FocusedIndex();
        _root.Children.Clear();
        _root.Children.Add(Label(header, Muted, new Thickness(Gap, Gap / 2, Gap, Gap)));
        for (int index = 0; index < entries.Count; index++)
        {
            _root.Children.Add(entries[index].Action == TrayAction.Separator ? Rule() : Row(entries[index], texts[index], index));
        }
        _root.Children.Add(Rule());
        foreach (string line in footer)
        {
            _root.Children.Add(Label(line, Faint, new Thickness(Gap, Gap / 2, Gap, 0)));
        }
        if (_keyboard && _open)
        {
            Focus(focused);
        }
        if (_open)
        {
            Resize();
        }
    }

    public void Open(Func<(int X, int Y, int Size)> anchor, bool keyboard)
    {
        _anchor = anchor;
        _keyboard = keyboard;
        _outside = TimeSpan.Zero;
        SetActivatable(keyboard);
        Resize();
        if (keyboard)
        {
            _previousForeground = PInvoke.GetForegroundWindow();
            _window.AppWindow.Show(true);
            _window.Activate();
            Focus(0);
        }
        else
        {
            _window.AppWindow.Show(false);
            _leaveTimer.Start();
        }
        _open = true;
        Animate(opening: true, () => { });
    }

    public void Close(bool restoreFocus)
    {
        if (!_open)
        {
            return;
        }
        _open = false;
        _leaveTimer.Stop();
        Animate(opening: false, () =>
        {
            if (!_open)
            {
                _window.AppWindow.Hide();
            }
        });
        if (restoreFocus && !_previousForeground.IsNull)
        {
            PInvoke.SetForegroundWindow(_previousForeground);
        }
        _previousForeground = HWND.Null;
    }

    private void ConfigureWindow()
    {
        var presenter = OverlappedPresenter.Create();
        presenter.SetBorderAndTitleBar(false, false);
        presenter.IsResizable = false;
        presenter.IsMaximizable = false;
        presenter.IsMinimizable = false;
        presenter.IsAlwaysOnTop = true;
        _window.AppWindow.SetPresenter(presenter);
        _window.AppWindow.IsShownInSwitchers = false;
        ScreenCapture.Exclude(_handle);
    }

    private void SetActivatable(bool activatable)
    {
        nint style = PInvoke.GetWindowLongPtr(_handle, WINDOW_LONG_PTR_INDEX.GWL_EXSTYLE);
        nint flags = (nint)(WINDOW_EX_STYLE.WS_EX_NOACTIVATE | WINDOW_EX_STYLE.WS_EX_TOOLWINDOW);
        style = activatable ? (style & ~(nint)WINDOW_EX_STYLE.WS_EX_NOACTIVATE) | (nint)WINDOW_EX_STYLE.WS_EX_TOOLWINDOW
            : style | flags;
        PInvoke.SetWindowLongPtr(_handle, WINDOW_LONG_PTR_INDEX.GWL_EXSTYLE, style);
    }

    private void Resize()
    {
        (int iconX, int iconY, int iconSize) = _anchor();
        double scale = Monitors.ScaleAt(iconX, iconY);
        _root.Measure(new Windows.Foundation.Size(Width, double.PositiveInfinity));
        int width = (int)Math.Round(Width * scale);
        int height = (int)Math.Round(_root.DesiredSize.Height * scale);
        (int x, int y) = PanelPlacement.Beside(Monitors.All(), iconX, iconY, iconSize, width, height, (int)Math.Round(Gap * scale));
        _window.AppWindow.MoveAndResize(new RectInt32(x, y, width, height));
    }

    private void Animate(bool opening, Action completed)
    {
        if (!Motion.Enabled)
        {
            _root.Opacity = opening ? 1 : 0;
            _offset.X = 0;
            completed();
            return;
        }
        var storyboard = new Storyboard();
        Duration duration = opening ? OpenDuration : CloseDuration;
        EasingFunctionBase easing = new CubicEase { EasingMode = opening ? EasingMode.EaseOut : EasingMode.EaseIn };
        double from = opening ? 0 : 1;
        AddAnimation(storyboard, _root, "Opacity", from, 1 - from, duration, easing);
        AddAnimation(storyboard, _offset, "X", opening ? -Shift * Direction() : 0, opening ? 0 : -Shift * Direction(), duration, easing);
        storyboard.Completed += (_, _) => completed();
        storyboard.Begin();
    }

    private int Direction()
    {
        (int iconX, _, _) = _anchor();
        return _window.AppWindow.Position.X >= iconX ? 1 : -1;
    }

    private static void AddAnimation(
        Storyboard storyboard,
        DependencyObject target,
        string property,
        double from,
        double to,
        Duration duration,
        EasingFunctionBase easing)
    {
        var animation = new DoubleAnimation { From = from, To = to, Duration = duration, EasingFunction = easing };
        Storyboard.SetTarget(animation, target);
        Storyboard.SetTargetProperty(animation, property);
        storyboard.Children.Add(animation);
    }

    private void CloseWhenPointerLeft()
    {
        PInvoke.GetCursorPos(out System.Drawing.Point cursor);
        (int iconX, int iconY, int iconSize) = _anchor();
        PointInt32 position = _window.AppWindow.Position;
        SizeInt32 size = _window.AppWindow.Size;
        bool overPanel = cursor.X >= position.X && cursor.X < position.X + size.Width
            && cursor.Y >= position.Y && cursor.Y < position.Y + size.Height;
        bool overIcon = cursor.X >= iconX && cursor.X < iconX + iconSize && cursor.Y >= iconY && cursor.Y < iconY + iconSize;
        _outside = overPanel || overIcon ? TimeSpan.Zero : _outside + LeavePoll;
        if (_outside >= LeaveGrace)
        {
            Close(restoreFocus: false);
        }
    }

    private void OnActivated(object sender, WindowActivatedEventArgs args)
    {
        if (_keyboard && _open && args.WindowActivationState == WindowActivationState.Deactivated)
        {
            Close(restoreFocus: false);
        }
    }

    private void OnKeyDown(object sender, KeyRoutedEventArgs args)
    {
        if (args.Key != VirtualKey.Escape)
        {
            return;
        }
        args.Handled = true;
        Close(restoreFocus: true);
    }

    private Button Row(MenuEntry entry, string text, int index)
    {
        var button = new Button
        {
            Content = text,
            IsEnabled = entry.Enabled,
            HorizontalAlignment = HorizontalAlignment.Stretch,
            HorizontalContentAlignment = HorizontalAlignment.Left,
            MinHeight = RowHeight,
            Padding = new Thickness(Gap, 0, Gap, 0),
            Tag = index,
        };
        AutomationName(button, text);
        button.Click += (_, _) => OnRowClicked(entry.Action);
        return button;
    }

    private void OnRowClicked(TrayAction action)
    {
        Selected?.Invoke(action);
        if (_keyboard)
        {
            Close(restoreFocus: true);
        }
    }

    private static TextBlock Label(string text, Color color, Thickness margin) => new()
    {
        Text = text,
        Foreground = new SolidColorBrush(color),
        Margin = margin,
        TextWrapping = TextWrapping.Wrap,
        FontSize = 12,
    };

    private static Border Rule() => new()
    {
        Height = 1,
        Background = new SolidColorBrush(Divider),
        Margin = new Thickness(0, Gap / 2, 0, Gap / 2),
    };

    private int FocusedIndex()
    {
        object? focused = _root.XamlRoot is null ? null : FocusManager.GetFocusedElement(_root.XamlRoot);
        return focused is Button { Tag: int index } ? index : 0;
    }

    private void Focus(int index)
    {
        Button? target = _root.Children.OfType<Button>().FirstOrDefault(button => button.IsEnabled && (int)button.Tag! >= index)
            ?? _root.Children.OfType<Button>().FirstOrDefault(button => button.IsEnabled);
        target?.Focus(FocusState.Keyboard);
    }

    private static void AutomationName(Button button, string text) =>
        Microsoft.UI.Xaml.Automation.AutomationProperties.SetName(button, text);

    private static void StyleButtons(ResourceDictionary resources)
    {
        resources["ButtonBackground"] = new SolidColorBrush(Colors.Transparent);
        resources["ButtonBackgroundPointerOver"] = new SolidColorBrush(Raised);
        resources["ButtonBackgroundPressed"] = new SolidColorBrush(RaisedHover);
        resources["ButtonBackgroundDisabled"] = new SolidColorBrush(Colors.Transparent);
        resources["ButtonForeground"] = new SolidColorBrush(Ink);
        resources["ButtonForegroundPointerOver"] = new SolidColorBrush(Ink);
        resources["ButtonForegroundPressed"] = new SolidColorBrush(Ink);
        resources["ButtonForegroundDisabled"] = new SolidColorBrush(Faint);
        resources["ButtonBorderBrush"] = new SolidColorBrush(Colors.Transparent);
        resources["ButtonBorderBrushPointerOver"] = new SolidColorBrush(Colors.Transparent);
        resources["ButtonBorderBrushPressed"] = new SolidColorBrush(Colors.Transparent);
        resources["ButtonBorderBrushDisabled"] = new SolidColorBrush(Colors.Transparent);
    }
}
