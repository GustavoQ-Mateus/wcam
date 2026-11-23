namespace Wcam.App;

internal sealed class OverlayController : IDisposable
{
    private const int PreviewGap = 8;
    private const int IconInset = 6;

    private readonly Localization _texts;
    private readonly Func<AppSettings> _settings;
    private readonly Action<AppSettings> _save;
    private readonly OverlayIcon _icon;
    private readonly QuickPanel _panel;
    private FloatingPreview? _preview;
    private AgentLifecycle _lifecycle = AgentLifecycle.Starting;
    private AgentStatus _status = AgentStatus.Unknown;

    public OverlayController(Localization texts, Func<AppSettings> settings, Action<AppSettings> save)
    {
        _texts = texts;
        _settings = settings;
        _save = save;
        _icon = new OverlayIcon();
        _icon.OpenRequested += () => OpenPanel(keyboard: false);
        _icon.Dropped += OnDropped;
        _icon.DisplayChanged += Apply;
        _panel = new QuickPanel(texts.Text("overlay.panel"));
        _panel.Selected += action => Selected?.Invoke(action);
    }

    public event Action<TrayAction>? Selected;

    public void Apply()
    {
        AppSettings settings = _settings();
        if (!settings.OverlayVisible)
        {
            _panel.Close(restoreFocus: false);
            _icon.Hide();
        }
        else
        {
            PlaceIcon(animate: false);
            _icon.Show();
        }
        ShowPreview(settings.FloatingPreviewVisible);
    }

    public void Update(AgentLifecycle lifecycle, AgentStatus status)
    {
        _lifecycle = lifecycle;
        _status = status;
        _icon.SetState(TrayMenu.State(lifecycle, status).State);
        RefreshPanel();
    }

    public void OpenPanel(bool keyboard)
    {
        if (_panel.IsOpen && !keyboard)
        {
            return;
        }
        RefreshPanel();
        _panel.Open(Anchor, keyboard);
    }

    public void ToggleFloatingPreview()
    {
        AppSettings settings = _settings() with { FloatingPreviewVisible = !_settings().FloatingPreviewVisible };
        _save(settings);
        ShowPreview(settings.FloatingPreviewVisible);
        RefreshPanel();
    }

    public void Dispose()
    {
        _preview?.Close();
        _icon.Dispose();
    }

    private (int X, int Y, int Size) Anchor()
    {
        (int x, int y) = _icon.Position;
        return (x, y, _icon.Size);
    }

    private void PlaceIcon(bool animate)
    {
        IReadOnlyList<Monitor> monitors = Monitors.All();
        Monitor primary = monitors.FirstOrDefault(monitor => monitor.IsPrimary) ?? monitors[0];
        EdgePlacement placement = _settings().OverlayPlacement ?? EdgePlacement.Default(primary);
        int size = ScaledIconSize(placement, monitors);
        int inset = (int)Math.Round(IconInset * (double)size / OverlayIcon.BaseSize);
        (int x, int y) = placement.Position(monitors, size, inset);
        _icon.Place(x, y, size, animate);
    }

    private static int ScaledIconSize(EdgePlacement placement, IReadOnlyList<Monitor> monitors)
    {
        Monitor monitor = monitors.FirstOrDefault(candidate => candidate.Id == placement.MonitorId) ?? monitors[0];
        ScreenRect area = monitor.WorkArea;
        return (int)Math.Round(OverlayIcon.BaseSize * Monitors.ScaleAt(area.Left, area.Top));
    }

    private void OnDropped(int centerX, int centerY)
    {
        EdgePlacement placement = EdgePlacement.Snap(Monitors.All(), centerX, centerY);
        _save(_settings() with { OverlayPlacement = placement });
        PlaceIcon(animate: true);
    }

    private void ShowPreview(bool visible)
    {
        if (!visible)
        {
            _preview?.Close();
            _preview = null;
            return;
        }
        if (_preview is not null)
        {
            return;
        }
        _preview = new FloatingPreview(PreviewBounds(), PreviewScale(), _texts.Text("overlay.preview_close"));
        _preview.Closed += ToggleFloatingPreview;
        _preview.BoundsChanged += bounds => _save(_settings() with { FloatingPreview = bounds });
    }

    private WindowBounds PreviewBounds()
    {
        if (_settings().FloatingPreview is { } saved && IsOnScreen(saved))
        {
            return saved;
        }
        double scale = PreviewScale();
        int width = (int)Math.Round(FloatingPreview.BaseWidth * scale);
        int height = (int)Math.Round(FloatingPreview.BaseHeight * scale);
        (int iconX, int iconY, int iconSize) = Anchor();
        (int x, int y) = PanelPlacement.Beside(
            Monitors.All(), iconX, iconY, iconSize, width, height, (int)Math.Round(PreviewGap * scale));
        return new WindowBounds(x, y, width, height);
    }

    private double PreviewScale()
    {
        (int x, int y) = _icon.Position;
        return Monitors.ScaleAt(x, y);
    }

    private static bool IsOnScreen(WindowBounds bounds) =>
        Monitors.All().Any(monitor => monitor.WorkArea.Contains(bounds.X + bounds.Width / 2, bounds.Y + bounds.Height / 2));

    private void RefreshPanel()
    {
        (_, string stateKey) = TrayMenu.State(_lifecycle, _status);
        string header = _status.Live && _lifecycle == AgentLifecycle.Running
            ? $"{_texts.Text(stateKey)} Â· {_texts.Text(TrayMenu.CameraTextKey(_status))}"
            : _texts.Text(stateKey);
        IReadOnlyList<MenuEntry> entries = TrayMenu.PanelEntries(_lifecycle, _status, _settings().FloatingPreviewVisible);
        string[] texts = entries.Select(entry => entry.TextKey.Length == 0 ? string.Empty : _texts.Text(entry.TextKey)).ToArray();
        string[] footer =
        [
            _texts.Text("overlay.drag_hint"),
            _texts.Text("overlay.hotkey", "keys", _settings().Hotkey),
        ];
        _panel.Update(header, entries, texts, footer);
    }
}
