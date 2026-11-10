namespace Wcam.VirtualCamera;

internal static class FrameTransport
{
    public const string SectionName = "WCamFrames";
    public const string LocalSectionName = @"Local\" + SectionName;
    public static readonly long FreshnessTicks = TimeSpan.FromSeconds(1).Ticks;

    public static string SessionSectionName(uint sessionId) => $@"Session\{sessionId}\{SectionName}";

    public static string AccessDescriptor(string ownerSid) => $"D:(A;;GA;;;SY)(A;;GA;;;{ownerSid})(A;;GR;;;LS)";

    public static bool IsFresh(long publishedTicks, long nowTicks) => Math.Abs(nowTicks - publishedTicks) < FreshnessTicks;

    public static bool AcceptsFrame(uint length, uint width, uint height, FrameFormat format) =>
        width == format.Width && height == format.Height && length == format.FrameSize;
}
