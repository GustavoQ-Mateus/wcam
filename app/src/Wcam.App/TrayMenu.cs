namespace Wcam.App;

internal enum TrayState
{
    Live,
    Video,
    Frozen,
    CameraOff,
    Waiting,
    Problem,
}

internal enum TrayAction
{
    None,
    Separator,
    ToggleFreeze,
    ToggleCamera,
    SwitchCamera,
    ToggleMirror,
    ToggleVideo,
    OpenConsole,
    ShowQr,
    Disconnect,
    ToggleOverlay,
    ToggleStartWithWindows,
    Quit,
}

internal enum AgentLifecycle
{
    Starting,
    Running,
    Restarting,
    Stopped,
}

internal sealed record MenuEntry(string TextKey, TrayAction Action, bool Enabled = true, bool Checked = false)
{
    public static readonly MenuEntry Separator = new(string.Empty, TrayAction.Separator);
}

internal sealed record TrayPreferences(bool OverlayVisible, bool StartWithWindows);

internal static class TrayMenu
{
    public static (TrayState State, string TextKey) State(AgentLifecycle lifecycle, AgentStatus status)
    {
        if (lifecycle == AgentLifecycle.Restarting)
        {
            return (TrayState.Problem, "tray.agent_restarting");
        }
        if (lifecycle == AgentLifecycle.Stopped)
        {
            return (TrayState.Problem, "tray.agent_stopped");
        }
        if (lifecycle == AgentLifecycle.Starting)
        {
            return (TrayState.Waiting, "state.waiting");
        }
        return StatusState(status);
    }

    public static IReadOnlyList<MenuEntry> Entries(
        AgentLifecycle lifecycle,
        AgentStatus status,
        TrayPreferences preferences)
    {
        string stateKey = State(lifecycle, status).TextKey;
        var entries = new List<MenuEntry> { new(stateKey, TrayAction.None, Enabled: false) };
        if (lifecycle == AgentLifecycle.Running)
        {
            entries.Add(new MenuEntry(CameraTextKey(status), TrayAction.None, Enabled: false));
            entries.Add(MenuEntry.Separator);
            entries.AddRange(ControlEntries(status));
            entries.Add(MenuEntry.Separator);
            entries.Add(new MenuEntry("tray.open_console", TrayAction.OpenConsole));
            entries.Add(new MenuEntry("tray.show_qr", TrayAction.ShowQr));
            entries.Add(new MenuEntry("tray.disconnect", TrayAction.Disconnect, Enabled: status.Live));
        }
        entries.Add(MenuEntry.Separator);
        entries.Add(new MenuEntry("tray.show_overlay", TrayAction.ToggleOverlay, Checked: preferences.OverlayVisible));
        entries.Add(new MenuEntry(
            "tray.start_with_windows",
            TrayAction.ToggleStartWithWindows,
            Checked: preferences.StartWithWindows));
        entries.Add(MenuEntry.Separator);
        entries.Add(new MenuEntry("tray.quit", TrayAction.Quit));
        return entries;
    }

    public static IReadOnlyList<MenuEntry> ControlEntries(AgentStatus status)
    {
        Controls controls = status.Controls;
        bool phoneCamera = status.Live && !status.VideoActive;
        return
        [
            new(
                controls.Frozen ? "controls.unfreeze" : "controls.freeze",
                TrayAction.ToggleFreeze,
                Enabled: (status.Live || status.VideoActive) && !controls.CameraOff),
            new(
                controls.CameraOff ? "controls.camera_on" : "controls.camera_off",
                TrayAction.ToggleCamera,
                Enabled: phoneCamera),
            new("controls.switch_camera", TrayAction.SwitchCamera, Enabled: phoneCamera),
            new("controls.mirror", TrayAction.ToggleMirror, Checked: controls.Mirror),
            new(
                status.VideoActive ? "controls.back_to_phone" : "tray.use_video",
                TrayAction.ToggleVideo,
                Enabled: status.VideoActive || (status.Live && status.TimelineHasClips),
                Checked: status.VideoActive),
        ];
    }

    public static string CameraTextKey(AgentStatus status) => status.Live ? status.Controls.Facing switch
    {
        Facing.User => "camera.front",
        Facing.Environment => "camera.back",
        _ => "tray.no_phone",
    } : "tray.no_phone";

    private static (TrayState State, string TextKey) StatusState(AgentStatus status)
    {
        if (!status.CameraActive)
        {
            return (TrayState.Problem, "state.problem");
        }
        if (status.VideoActive)
        {
            return status.Controls.Frozen ? (TrayState.Frozen, "state.frozen") : (TrayState.Video, "state.video");
        }
        if (!status.HasSession)
        {
            return (TrayState.Waiting, "state.waiting");
        }
        if (!status.Live)
        {
            return (TrayState.Waiting, "state.confirming");
        }
        if (status.Controls.CameraOff)
        {
            return (TrayState.CameraOff, "state.camera_off");
        }
        if (status.Controls.Frozen)
        {
            return (TrayState.Frozen, "state.frozen");
        }
        if (status.CameraSource != AgentStatus.PhoneSource)
        {
            return (TrayState.Problem, "state.lost");
        }
        return (TrayState.Live, "state.live");
    }
}
