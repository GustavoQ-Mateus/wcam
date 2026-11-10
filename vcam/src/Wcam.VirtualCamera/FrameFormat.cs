namespace Wcam.VirtualCamera;

internal readonly record struct FrameFormat(int Width, int Height, int FramesPerSecond)
{
    public const int LargestWidth = 3840;
    public const int LargestHeight = 2160;
    public const int LargestFrameSize = LargestWidth * LargestHeight * 3 / 2;
    private const int AspectWidth = 16;
    private const int AspectHeight = 9;
    private static readonly int[] SupportedWidths = [1280, 1920, 2560, LargestWidth];
    private static readonly int[] SupportedRates = [30, 60];

    public static FrameFormat Default => new(VideoFormat.Width, VideoFormat.Height, VideoFormat.FramesPerSecond);

    public int FrameSize => Width * Height * 3 / 2;

    public int LumaSize => Width * Height;

    public long FrameDurationTicks => TimeSpan.TicksPerSecond / FramesPerSecond;

    public bool IsSupported =>
        SupportedWidths.Contains(Width)
        && Height * AspectWidth == Width * AspectHeight
        && SupportedRates.Contains(FramesPerSecond);

    public override string ToString() => $"{Width}x{Height}@{FramesPerSecond}";
}
