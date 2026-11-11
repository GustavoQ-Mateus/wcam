namespace Wcam.VirtualCamera.Tests;

public class SessionFrameReaderTests
{
    private const int LumaSize = VideoFormat.Width * VideoFormat.Height;

    [Fact]
    public void FillBlack_AnyFrame_WritesLimitedRangeBlack()
    {
        byte[] frame = new byte[VideoFormat.FrameSize];
        new Random(9).NextBytes(frame);
        SessionFrameReader.FillBlack(frame, FrameFormat.Default);
        Assert.All(frame[..LumaSize], value => Assert.Equal(16, value));
        Assert.All(frame[LumaSize..], value => Assert.Equal(128, value));
    }
}
