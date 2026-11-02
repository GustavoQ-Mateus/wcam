namespace Wcam.VirtualCamera;

internal static class FrameTransport
{
    public const string SectionName = @"Global\WCamFrames";
    public static readonly string FilePath = Path.Combine(
        Environment.GetFolderPath(Environment.SpecialFolder.CommonApplicationData),
        "WCam",
        "frames.bin");
}
