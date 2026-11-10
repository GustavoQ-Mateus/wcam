using System.Runtime.InteropServices;

namespace Wcam.VirtualCamera.Tests;

public class WcamFormatStateTests
{
    [Fact]
    public void Layout_IsNineConsecutiveUInt32()
    {
        Assert.Equal(9 * sizeof(uint), Marshal.SizeOf<WcamFormatState>());
        Assert.Equal(6 * sizeof(uint), (int)Marshal.OffsetOf<WcamFormatState>(nameof(WcamFormatState.Pending)));
        Assert.Equal(8 * sizeof(uint), (int)Marshal.OffsetOf<WcamFormatState>(nameof(WcamFormatState.Running)));
    }

    [Fact]
    public void From_PendingChange_ReportsAnnouncedRequestedAndApps()
    {
        var formats = new FormatSwitch(FrameFormat.Default);
        formats.UpdateStreamingApps(2, 0);
        formats.Request(new FrameFormat(1280, 720, 60), cameraStarted: true);
        WcamFormatState state = WcamFormatState.From(formats, running: true);
        Assert.Equal((1920u, 1080u, 30u), (state.Width, state.Height, state.FramesPerSecond));
        Assert.Equal((1280u, 720u, 60u), (state.RequestedWidth, state.RequestedHeight, state.RequestedFramesPerSecond));
        Assert.Equal((1u, 2u, 1u), (state.Pending, state.StreamingApps, state.Running));
    }

    [Fact]
    public void From_WhileRestarting_ReportsNotRunning()
    {
        WcamFormatState state = WcamFormatState.From(new FormatSwitch(FrameFormat.Default), running: false);
        Assert.Equal(0u, state.Running);
        Assert.Equal(0u, state.Pending);
    }
}
