namespace Wcam.VirtualCamera;

internal readonly record struct FrameFormat(int Width, int Height, int FramesPerSecond)
{
    public const int LargestWidth = 3840;
    public const int LargestHeight = 2160;
    public const int LargestFrameSize = LargestWidth * LargestHeight * 3 / 2;
    private static readonly FrameFormat[] Supported =
    [
        new(1280, 720, 30),
        new(1280, 720, 60),
        new(VideoFormat.Width, VideoFormat.Height, VideoFormat.FramesPerSecond),
        new(2560, 1440, 30),
        new(LargestWidth, LargestHeight, 30),
    ];

    public static FrameFormat Default => new(VideoFormat.Width, VideoFormat.Height, VideoFormat.FramesPerSecond);

    public int FrameSize => Width * Height * 3 / 2;

    public int LumaSize => Width * Height;

    public long FrameDurationTicks => TimeSpan.TicksPerSecond / FramesPerSecond;

    public bool IsSupported => Supported.Contains(this);

    public override string ToString() => $"{Width}x{Height}@{FramesPerSecond}";
}
