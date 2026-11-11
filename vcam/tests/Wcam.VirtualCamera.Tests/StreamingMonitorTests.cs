namespace Wcam.VirtualCamera.Tests;

public class StreamingMonitorTests
{
    [Theory]
    [InlineData("WCam")]
    [InlineData("WCam (Câmera Virtual do Windows)")]
    [InlineData("WCam (Windows Virtual Camera)")]
    public void IsWcamDevice_WcamWithOrWithoutLocalizedSuffix_IsTrue(string friendlyName)
    {
        Assert.True(StreamingMonitor.IsWcamDevice(friendlyName));
    }

    [Theory]
    [InlineData("Integrated Camera")]
    [InlineData("WCamera Pro")]
    [InlineData("OBS Virtual Camera")]
    [InlineData("")]
    public void IsWcamDevice_OtherCamera_IsFalse(string friendlyName)
    {
        Assert.False(StreamingMonitor.IsWcamDevice(friendlyName));
    }
}
