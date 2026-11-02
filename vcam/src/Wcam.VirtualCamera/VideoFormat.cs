namespace Wcam.VirtualCamera;

internal static class VideoFormat
{
    public const int Width = 1920;
    public const int Height = 1080;
    public const int FramesPerSecond = 30;
    public const int FrameSize = Width * Height * 3 / 2;
    public const long FrameDurationTicks = TimeSpan.TicksPerSecond / FramesPerSecond;
    public const uint Nv12FourCc = 0x3231564E;
}
