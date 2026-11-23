namespace Wcam.App.Tests;

public class TrayMenuTests
{
    private static readonly Controls Normal = new(false, false, false, Facing.Environment);
    private static readonly AgentStatus Live = new(true, "phone", "live", Normal, false, false);
    private static readonly TrayPreferences Preferences = new(true, false);

    [Fact]
    public void RestartingAgent_ShowsProblemWithRestartingText()
    {
        Assert.Equal((TrayState.Problem, "tray.agent_restarting"), TrayMenu.State(AgentLifecycle.Restarting, Live));
    }

    [Fact]
    public void StoppedAgent_ShowsProblemWithStoppedText()
    {
        Assert.Equal((TrayState.Problem, "tray.agent_stopped"), TrayMenu.State(AgentLifecycle.Stopped, Live));
    }

    [Fact]
    public void AgentWithoutNetwork_ShowsTheNetworkText()
    {
        Assert.Equal((TrayState.Problem, "tray.agent_no_network"), TrayMenu.State(AgentLifecycle.NoNetwork, Live));
    }

    [Fact]
    public void AgentWithBusyPort_ShowsThePortText()
    {
        Assert.Equal((TrayState.Problem, "tray.agent_port_busy"), TrayMenu.State(AgentLifecycle.PortBusy, Live));
    }

    [Fact]
    public void LivePhone_ShowsLive()
    {
        Assert.Equal((TrayState.Live, "state.live"), TrayMenu.State(AgentLifecycle.Running, Live));
    }

    [Fact]
    public void NoSession_ShowsWaiting()
    {
        AgentStatus status = Live with { SessionState = null };

        Assert.Equal((TrayState.Waiting, "state.waiting"), TrayMenu.State(AgentLifecycle.Running, status));
    }

    [Fact]
    public void SessionAwaitingConfirmation_ShowsConfirming()
    {
        AgentStatus status = Live with { SessionState = "awaiting_confirmation" };

        Assert.Equal((TrayState.Waiting, "state.confirming"), TrayMenu.State(AgentLifecycle.Running, status));
    }

    [Fact]
    public void FrozenImage_ShowsFrozen()
    {
        AgentStatus status = Live with { Controls = Normal with { Frozen = true } };

        Assert.Equal((TrayState.Frozen, "state.frozen"), TrayMenu.State(AgentLifecycle.Running, status));
    }

    [Fact]
    public void CameraOff_ShowsCameraOff()
    {
        AgentStatus status = Live with { Controls = Normal with { CameraOff = true } };

        Assert.Equal((TrayState.CameraOff, "state.camera_off"), TrayMenu.State(AgentLifecycle.Running, status));
    }

    [Fact]
    public void VideoActive_ShowsVideo()
    {
        AgentStatus status = Live with { VideoActive = true };

        Assert.Equal((TrayState.Video, "state.video"), TrayMenu.State(AgentLifecycle.Running, status));
    }

    [Fact]
    public void LiveWithoutPhoneFrames_ShowsLost()
    {
        AgentStatus status = Live with { CameraSource = "frozen" };

        Assert.Equal((TrayState.Problem, "state.lost"), TrayMenu.State(AgentLifecycle.Running, status));
    }

    [Fact]
    public void CameraUnavailable_ShowsProblem()
    {
        AgentStatus status = Live with { CameraActive = false };

        Assert.Equal((TrayState.Problem, "state.problem"), TrayMenu.State(AgentLifecycle.Running, status));
    }

    [Fact]
    public void NoPhone_DisablesPhoneControls()
    {
        AgentStatus status = Live with { SessionState = null };

        IReadOnlyList<MenuEntry> controls = TrayMenu.ControlEntries(status);

        Assert.All(
            controls.Where(entry => entry.Action != TrayAction.ToggleMirror),
            entry => Assert.False(entry.Enabled));
    }

    [Fact]
    public void FrozenImage_OffersUnfreeze()
    {
        AgentStatus status = Live with { Controls = Normal with { Frozen = true } };

        MenuEntry freeze = TrayMenu.ControlEntries(status).Single(entry => entry.Action == TrayAction.ToggleFreeze);

        Assert.Equal("controls.unfreeze", freeze.TextKey);
    }

    [Fact]
    public void ActiveVideo_OffersBackToPhone()
    {
        AgentStatus status = Live with { VideoActive = true, TimelineHasClips = true };

        MenuEntry video = TrayMenu.ControlEntries(status).Single(entry => entry.Action == TrayAction.ToggleVideo);

        Assert.Equal("controls.back_to_phone", video.TextKey);
        Assert.True(video.Checked);
    }

    [Fact]
    public void LiveWithoutClips_DisablesUseVideo()
    {
        MenuEntry video = TrayMenu.ControlEntries(Live).Single(entry => entry.Action == TrayAction.ToggleVideo);

        Assert.False(video.Enabled);
    }

    [Fact]
    public void StoppedAgent_KeepsOnlyAppEntries()
    {
        IReadOnlyList<MenuEntry> entries = TrayMenu.Entries(AgentLifecycle.Stopped, Live, Preferences);

        Assert.DoesNotContain(entries, entry => entry.Action == TrayAction.ToggleFreeze);
        Assert.Contains(entries, entry => entry.Action == TrayAction.Quit);
    }

    [Fact]
    public void Preferences_AreCheckedInTheMenu()
    {
        IReadOnlyList<MenuEntry> entries = TrayMenu.Entries(AgentLifecycle.Running, Live, new TrayPreferences(false, true));

        Assert.False(entries.Single(entry => entry.Action == TrayAction.ToggleOverlay).Checked);
        Assert.True(entries.Single(entry => entry.Action == TrayAction.ToggleStartWithWindows).Checked);
    }

[Fact]
    public void Panel_FollowsTheStatusOfTheControls()
    {
        AgentStatus status = Live with { Controls = Normal with { CameraOff = true } };

        IReadOnlyList<MenuEntry> entries = TrayMenu.PanelEntries(AgentLifecycle.Running, status, false);

        Assert.Equal("controls.camera_on", entries.Single(entry => entry.Action == TrayAction.ToggleCamera).TextKey);
        Assert.False(entries.Single(entry => entry.Action == TrayAction.ToggleFreeze).Enabled);
        Assert.DoesNotContain(entries, entry => entry.Action == TrayAction.ToggleMirror);
    }

    [Fact]
    public void Panel_OffersToHideAShownFloatingPreview()
    {
        IReadOnlyList<MenuEntry> entries = TrayMenu.PanelEntries(AgentLifecycle.Running, Live, true);

        MenuEntry preview = entries.Single(entry => entry.Action == TrayAction.ToggleFloatingPreview);
        Assert.Equal("overlay.preview_off", preview.TextKey);
    }

    [Fact]
    public void PanelWithAgentStopped_KeepsOnlyTheAppActions()
    {
        IReadOnlyList<MenuEntry> entries = TrayMenu.PanelEntries(AgentLifecycle.Stopped, Live, false);

        Assert.Equal(
            [TrayAction.ToggleFloatingPreview, TrayAction.OpenConsole, TrayAction.HideOverlay],
            entries.Select(entry => entry.Action));
    }

    [Fact]
    public void LiveFrontCamera_ShowsFrontCamera()
    {
        AgentStatus status = Live with { Controls = Normal with { Facing = Facing.User } };

        Assert.Equal("camera.front", TrayMenu.CameraTextKey(status));
    }
}
