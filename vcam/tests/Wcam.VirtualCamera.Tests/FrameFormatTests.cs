namespace Wcam.VirtualCamera.Tests;

public class FrameFormatTests
{
    [Theory]
    [InlineData(1280, 720, 30)]
    [InlineData(1280, 720, 60)]
    [InlineData(1920, 1080, 30)]
    [InlineData(2560, 1440, 30)]
    [InlineData(3840, 2160, 30)]
    public void IsSupported_FormatOfTheContractTable_IsTrue(int width, int height, int framesPerSecond)
    {
        Assert.True(new FrameFormat(width, height, framesPerSecond).IsSupported);
    }

    [Theory]
    [InlineData(1920, 1080, 60)]
    [InlineData(2560, 1440, 60)]
    [InlineData(3840, 2160, 60)]
    [InlineData(1080, 1920, 30)]
    [InlineData(1920, 1080, 25)]
    [InlineData(1600, 900, 30)]
    [InlineData(0, 0, 0)]
    public void IsSupported_FormatOutsideTheTable_IsFalse(int width, int height, int framesPerSecond)
    {
        Assert.False(new FrameFormat(width, height, framesPerSecond).IsSupported);
    }

    [Fact]
    public void Default_IsFullHdAt30Fps()
    {
        Assert.Equal(new FrameFormat(1920, 1080, 30), FrameFormat.Default);
    }

    [Fact]
    public void FrameSize_Of2160p_IsNv12Size()
    {
        Assert.Equal(3840 * 2160 * 3 / 2, new FrameFormat(3840, 2160, 30).FrameSize);
    }
}
