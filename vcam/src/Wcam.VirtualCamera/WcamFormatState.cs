using System.Runtime.InteropServices;

namespace Wcam.VirtualCamera;

[StructLayout(LayoutKind.Sequential)]
internal struct WcamFormatState
{
    public uint Width;
    public uint Height;
    public uint FramesPerSecond;
    public uint RequestedWidth;
    public uint RequestedHeight;
    public uint RequestedFramesPerSecond;
    public uint Pending;
    public uint StreamingApps;
    public uint Running;

    public static WcamFormatState From(FormatSwitch formats, bool running) => new()
    {
        Width = (uint)formats.Announced.Width,
        Height = (uint)formats.Announced.Height,
        FramesPerSecond = (uint)formats.Announced.FramesPerSecond,
        RequestedWidth = (uint)formats.Requested.Width,
        RequestedHeight = (uint)formats.Requested.Height,
        RequestedFramesPerSecond = (uint)formats.Requested.FramesPerSecond,
        Pending = formats.IsPending ? 1u : 0u,
        StreamingApps = (uint)formats.StreamingApps,
        Running = running ? 1u : 0u,
    };
}
