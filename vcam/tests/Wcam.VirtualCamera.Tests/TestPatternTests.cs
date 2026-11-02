namespace Wcam.VirtualCamera.Tests;

public class TestPatternTests
{
    private const int ChromaPlaneOffset = VideoFormat.Width * VideoFormat.Height;

    [Fact]
    public void Render_BarsArea_HasEachBarColorInLumaAndChroma()
    {
        byte[] frame = Render(0);
        int row = TestPattern.BarsHeight / 2;
        for (int bar = 0; bar < TestPattern.BarCount; bar++)
        {
            int column = bar * TestPattern.BarWidth + TestPattern.BarWidth / 2;
            (byte y, byte u, byte v) = TestPattern.BarColor(bar);
            int chroma = ChromaPlaneOffset + row / 2 * VideoFormat.Width + column / 2 * 2;
            Assert.Equal(y, frame[row * VideoFormat.Width + column]);
            Assert.Equal(u, frame[chroma]);
            Assert.Equal(v, frame[chroma + 1]);
        }
    }

    [Fact]
    public void Render_SameFrameNumber_ProducesIdenticalFrames()
    {
        Assert.Equal(Render(42), Render(42));
    }

    [Fact]
    public void Render_NextFrameNumber_ChangesOnlyAreaBelowBars()
    {
        byte[] first = Render(1);
        byte[] second = Render(2);
        int barsLuma = TestPattern.BarsHeight * VideoFormat.Width;
        Assert.Equal(first[..barsLuma], second[..barsLuma]);
        Assert.NotEqual(first[barsLuma..ChromaPlaneOffset], second[barsLuma..ChromaPlaneOffset]);
    }

    [Fact]
    public void Render_SweepBlock_MovesWithFrameNumber()
    {
        byte[] frame = Render(10);
        int row = TestPattern.SweepTop + TestPattern.SweepHeight / 2;
        int left = TestPattern.SweepLeft(10);
        Assert.Equal(TestPattern.ForegroundLuma, frame[row * VideoFormat.Width + left]);
        Assert.Equal(TestPattern.BackgroundLuma, frame[row * VideoFormat.Width + left + TestPattern.SweepWidth]);
    }

    [Fact]
    public void Render_AreaBelowBars_HasNeutralChroma()
    {
        byte[] frame = Render(7);
        int firstChromaRowBelowBars = ChromaPlaneOffset + TestPattern.BarsHeight / 2 * VideoFormat.Width;
        Assert.All(frame[firstChromaRowBelowBars..], value => Assert.Equal(TestPattern.NeutralChroma, value));
    }

    private static byte[] Render(long frameNumber)
    {
        byte[] frame = new byte[VideoFormat.FrameSize];
        new TestPattern().Render(frame, frameNumber);
        return frame;
    }
}
