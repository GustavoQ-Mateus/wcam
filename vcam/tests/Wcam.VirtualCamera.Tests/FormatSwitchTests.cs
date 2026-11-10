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
        formats.UpdateStreamingApps(1);
        Assert.Equal(FormatRequestOutcome.Pending, formats.Request(Hd, cameraStarted: true));
        Assert.Equal(FrameFormat.Default, formats.Announced);
        Assert.True(formats.IsPending);
    }

    [Fact]
    public void UpdateStreamingApps_LastAppStopsWithPendingFormat_AsksToApply()
    {
        var formats = new FormatSwitch(FrameFormat.Default);
        formats.UpdateStreamingApps(2);
        formats.Request(Hd, cameraStarted: true);
        Assert.False(formats.UpdateStreamingApps(1));
        Assert.True(formats.UpdateStreamingApps(0));
    }

    [Fact]
    public void UpdateStreamingApps_LastAppStopsWithoutPendingFormat_DoesNotAskToApply()
    {
        var formats = new FormatSwitch(FrameFormat.Default);
        formats.UpdateStreamingApps(1);
        Assert.False(formats.UpdateStreamingApps(0));
    }

    [Fact]
    public void Request_AnnouncedFormatWhilePending_CancelsPendingChange()
    {
        var formats = new FormatSwitch(FrameFormat.Default);
        formats.UpdateStreamingApps(1);
        formats.Request(Hd, cameraStarted: true);
        Assert.Equal(FormatRequestOutcome.Applied, formats.Request(FrameFormat.Default, cameraStarted: true));
        Assert.False(formats.IsPending);
        Assert.False(formats.UpdateStreamingApps(0));
    }

    [Fact]
    public void Request_OtherFormatWhilePending_KeepsOnlyTheLatestRequest()
    {
        var formats = new FormatSwitch(FrameFormat.Default);
        formats.UpdateStreamingApps(1);
        formats.Request(Hd, cameraStarted: true);
        formats.Request(UltraHd, cameraStarted: true);
        Assert.Equal(UltraHd, formats.Requested);
        Assert.Equal(FrameFormat.Default, formats.Announced);
    }

    [Fact]
    public void Announce_AfterRestart_ClearsPending()
    {
        var formats = new FormatSwitch(FrameFormat.Default);
        formats.Request(Hd, cameraStarted: true);
        formats.Announce(Hd);
        Assert.False(formats.IsPending);
    }
}
