namespace Wcam.VirtualCamera.Tests;

public class FormatSwitchTests
{
    private static readonly FrameFormat Hd = new(1280, 720, 30);
    private static readonly FrameFormat UltraHd = new(3840, 2160, 30);

    [Fact]
    public void Request_BeforeCameraStarts_AppliesWithoutRestart()
    {
        var formats = new FormatSwitch(FrameFormat.Default);
        Assert.Equal(FormatRequestOutcome.Applied, formats.Request(Hd, cameraStarted: false));
        Assert.Equal(Hd, formats.Announced);
        Assert.False(formats.IsPending);
    }

    [Fact]
    public void Request_WithNoAppReceivingVideo_RestartsCameraBeforeReturning()
    {
        var formats = new FormatSwitch(FrameFormat.Default);
        Assert.Equal(FormatRequestOutcome.RestartCamera, formats.Request(Hd, cameraStarted: true));
        Assert.Equal(Hd, formats.Requested);
    }

    [Fact]
    public void Request_WhileAnAppReceivesVideo_StaysPendingInAnnouncedFormat()
    {
        var formats = new FormatSwitch(FrameFormat.Default);
        formats.UpdateStreamingApps(1, 0);
        Assert.Equal(FormatRequestOutcome.Pending, formats.Request(Hd, cameraStarted: true));
        Assert.Equal(FrameFormat.Default, formats.Announced);
        Assert.True(formats.IsPending);
    }

    [Fact]
    public void UpdateStreamingApps_LastAppStopsWithPendingFormat_AsksToApply()
    {
        var formats = new FormatSwitch(FrameFormat.Default);
        formats.UpdateStreamingApps(2, 0);
        formats.Request(Hd, cameraStarted: true);
        Assert.False(formats.UpdateStreamingApps(1, 0));
        Assert.True(formats.UpdateStreamingApps(0, 0));
    }

    [Fact]
    public void UpdateStreamingApps_LastAppStopsWithoutPendingFormat_DoesNotAskToApply()
    {
        var formats = new FormatSwitch(FrameFormat.Default);
        formats.UpdateStreamingApps(1, 0);
        Assert.False(formats.UpdateStreamingApps(0, 0));
    }

    [Fact]
    public void Request_AnnouncedFormatWhilePending_CancelsPendingChange()
    {
        var formats = new FormatSwitch(FrameFormat.Default);
        formats.UpdateStreamingApps(1, 0);
        formats.Request(Hd, cameraStarted: true);
        Assert.Equal(FormatRequestOutcome.Applied, formats.Request(FrameFormat.Default, cameraStarted: true));
        Assert.False(formats.IsPending);
        Assert.False(formats.UpdateStreamingApps(0, 0));
    }

    [Fact]
    public void Request_OtherFormatWhilePending_KeepsOnlyTheLatestRequest()
    {
        var formats = new FormatSwitch(FrameFormat.Default);
        formats.UpdateStreamingApps(1, 0);
        formats.Request(Hd, cameraStarted: true);
        formats.Request(UltraHd, cameraStarted: true);
        Assert.Equal(UltraHd, formats.Requested);
        Assert.Equal(FrameFormat.Default, formats.Announced);
    }

    [Fact]
    public void MillisecondsUntilPendingApplies_LastAppStopped_WaitsOneSecondWithNoApp()
    {
        FormatSwitch formats = PendingWithOneApp();
        formats.UpdateStreamingApps(0, 10_000);
        Assert.Equal(FormatSwitch.IdleBeforeApplyMilliseconds, formats.MillisecondsUntilPendingApplies(10_000));
        Assert.Equal(500, formats.MillisecondsUntilPendingApplies(10_500));
        Assert.Equal(0, formats.MillisecondsUntilPendingApplies(10_000 + FormatSwitch.IdleBeforeApplyMilliseconds));
    }

    [Fact]
    public void MillisecondsUntilPendingApplies_AppReturnsWithinOneSecond_StaysPending()
    {
        FormatSwitch formats = PendingWithOneApp();
        formats.UpdateStreamingApps(0, 10_000);
        formats.UpdateStreamingApps(1, 10_300);
        Assert.Null(formats.MillisecondsUntilPendingApplies(11_000));
        Assert.True(formats.IsPending);
    }

    [Fact]
    public void MillisecondsUntilPendingApplies_AppStopsAgain_CountsFromTheLastStop()
    {
        FormatSwitch formats = PendingWithOneApp();
        formats.UpdateStreamingApps(0, 10_000);
        formats.UpdateStreamingApps(1, 10_300);
        formats.UpdateStreamingApps(0, 10_600);
        Assert.Equal(600, formats.MillisecondsUntilPendingApplies(11_000));
    }

    [Fact]
    public void MillisecondsUntilPendingApplies_RepeatedReportWithNoApp_KeepsTheFirstStop()
    {
        FormatSwitch formats = PendingWithOneApp();
        formats.UpdateStreamingApps(0, 10_000);
        formats.UpdateStreamingApps(0, 10_800);
        Assert.Equal(0, formats.MillisecondsUntilPendingApplies(11_000));
    }

    [Fact]
    public void MillisecondsUntilPendingApplies_WithoutPendingFormat_IsNull()
    {
        var formats = new FormatSwitch(FrameFormat.Default);
        formats.UpdateStreamingApps(0, 10_000);
        Assert.Null(formats.MillisecondsUntilPendingApplies(20_000));
    }

    [Fact]
    public void Announce_AfterRestart_ClearsPending()
    {
        var formats = new FormatSwitch(FrameFormat.Default);
        formats.Request(Hd, cameraStarted: true);
        formats.Announce(Hd);
        Assert.False(formats.IsPending);
    }

    private static FormatSwitch PendingWithOneApp()
    {
        var formats = new FormatSwitch(FrameFormat.Default);
        formats.UpdateStreamingApps(1, 0);
        formats.Request(Hd, cameraStarted: true);
        return formats;
    }
}
