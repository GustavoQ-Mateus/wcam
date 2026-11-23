using System.Globalization;
using Microsoft.UI.Dispatching;
using Microsoft.UI.Xaml;

namespace Wcam.App;

public sealed partial class App : Application
{
    private readonly SingleInstance _instance;
    private readonly bool _startup;
    private readonly CancellationTokenSource _stop = new();
    private Localization _texts = null!;
    private AppSettings _settings = new();
    private StartupRegistration _startupRegistration = null!;
    private ConsoleClient _client = null!;
    private TrayIcon _tray = null!;
    private JobAgentLauncher _launcher = null!;
    private AgentSupervisor _supervisor = null!;
    private DispatcherQueue _ui = null!;
    private ConsoleWindow? _console;
    private AgentStatus _status = AgentStatus.Unknown;
    private Task _agent = Task.CompletedTask;
    private RegisteredWaitHandle? _showWait;

    internal App(SingleInstance instance, bool startup)
    {
        _instance = instance;
        _startup = startup;
        InitializeComponent();
    }

    protected override void OnLaunched(LaunchActivatedEventArgs args)
    {
        _ui = DispatcherQueue.GetForCurrentThread();
        _texts = Localization.Load(AppPaths.Locales, Localization.ResolveLanguage(CultureInfo.CurrentUICulture.Name));
        _settings = AppSettings.Load(AppPaths.Settings);
        _startupRegistration = new StartupRegistration(StartupRegistration.RunKey, AppPaths.Executable);
        _client = new ConsoleClient();
        _tray = new TrayIcon();
        _tray.Selected += OnTrayAction;
        _tray.Activated += ShowConsole;
        _launcher = new JobAgentLauncher(AppPaths.Agent());
        _supervisor = new AgentSupervisor(_launcher, _client, SupervisorTiming.Product, TimeProvider.System);
        _supervisor.LifecycleChanged += _ => _ui.TryEnqueue(OnLifecycleChanged);
        _agent = _supervisor.RunAsync(_stop.Token);
        _ = _client.WatchStatusAsync(status => _ui.TryEnqueue(() => OnStatus(status)), _stop.Token);
        _showWait = ThreadPool.RegisterWaitForSingleObject(
            _instance.ShowRequested, (_, _) => _ui.TryEnqueue(ShowConsole), null, Timeout.Infinite, executeOnlyOnce: false);
        Refresh();
        if (!_startup)
        {
            ShowConsole();
        }
    }

    private void OnStatus(AgentStatus status)
    {
        _status = status;
        Refresh();
    }

    private void OnLifecycleChanged()
    {
        if (_supervisor.Lifecycle == AgentLifecycle.Running)
        {
            _console?.ReloadIfFailed();
        }
        Refresh();
    }

    private void Refresh()
    {
        AgentLifecycle lifecycle = _supervisor.Lifecycle;
        (TrayState state, string textKey) = TrayMenu.State(lifecycle, _status);
        var preferences = new TrayPreferences(_settings.OverlayVisible, _startupRegistration.IsEnabled);
        IReadOnlyList<MenuEntry> entries = TrayMenu.Entries(lifecycle, _status, preferences);
        string[] texts = entries.Select(entry => entry.TextKey.Length == 0 ? string.Empty : _texts.Text(entry.TextKey)).ToArray();
        _tray.Update(state, _texts.Text("tray.tooltip", "state", _texts.Text(textKey)), entries, texts);
    }

    private void ShowConsole()
    {
        _console ??= CreateConsole();
        _console.Show();
    }

    private ConsoleWindow CreateConsole()
    {
        var window = new ConsoleWindow(_client.BaseAddress, _texts.Text("app.name"), _settings.ConsoleWindow, AppIcon.Id);
        window.BoundsChanged += bounds => SaveSettings(_settings with { ConsoleWindow = bounds });
        return window;
    }

    private void OnTrayAction(TrayAction action)
    {
        Controls controls = _status.Controls;
        switch (action)
        {
            case TrayAction.OpenConsole or TrayAction.ShowQr:
                ShowConsole();
                break;
            case TrayAction.ToggleFreeze:
                _ = _client.ChangeControlsAsync("frozen", ConsoleClient.Json(!controls.Frozen));
                break;
            case TrayAction.ToggleCamera:
                _ = _client.ChangeControlsAsync("cameraOff", ConsoleClient.Json(!controls.CameraOff));
                break;
            case TrayAction.ToggleMirror:
                _ = _client.ChangeControlsAsync("mirror", ConsoleClient.Json(!controls.Mirror));
                break;
            case TrayAction.SwitchCamera when controls.Facing != Facing.None:
                _ = _client.ChangeControlsAsync("facing", controls.Facing == Facing.User ? "\"environment\"" : "\"user\"");
                break;
            case TrayAction.ToggleVideo:
                _ = _client.SetVideoSourceAsync(!_status.VideoActive);
                break;
            case TrayAction.Disconnect:
                _ = _client.DisconnectAsync();
                break;
            case TrayAction.ToggleOverlay:
                SaveSettings(_settings with { OverlayVisible = !_settings.OverlayVisible });
                break;
            case TrayAction.ToggleStartWithWindows:
                _startupRegistration.Set(!_startupRegistration.IsEnabled);
                break;
            case TrayAction.Quit:
                _ = QuitAsync();
                return;
        }
        Refresh();
    }

    private void SaveSettings(AppSettings settings)
    {
        _settings = settings;
        settings.Save(AppPaths.Settings);
    }

    private async Task QuitAsync()
    {
        _console?.Hide();
        _stop.Cancel();
        _showWait?.Unregister(null);
        await _agent;
        _console?.Close();
        _tray.Dispose();
        _launcher.Dispose();
        _client.Dispose();
        Exit();
    }
}
