using System.Diagnostics;

namespace Wcam.VirtualCamera.Tests;

public sealed class PublishedFrameSectionTests : IDisposable
{
    private readonly string _name = $"WCamFramesTest{Guid.NewGuid():N}";
    private readonly PublishedFrameSection _section;

    public PublishedFrameSectionTests()
    {
        _section = PublishedFrameSection.Create($@"Local\{_name}");
    }

    public void Dispose() => _section.Dispose();

    [Fact]
    public void Publish_ThenOpenBySessionName_ReadsSameBytes()
    {
        byte[] frame = new byte[VideoFormat.FrameSize];
        new Random(5).NextBytes(frame);
        byte[] destination = new byte[VideoFormat.FrameSize];
        _section.Publish(frame);
        using MappedFrameChannel reader = MappedFrameChannel.OpenSection(SessionName(), writable: false);
        Assert.True(reader.Channel.TryReadLatest(destination, out ulong frameIndex, out long timestamp));
        Assert.Equal(frame, destination);
        Assert.Equal(1UL, frameIndex);
        Assert.True(FrameTransport.IsFresh(timestamp, DateTime.UtcNow.Ticks));
    }

    [Fact]
    public void Create_BeforeAnyPublish_HasValidHeaderAndNoFrame()
    {
        using MappedFrameChannel reader = MappedFrameChannel.OpenSection($@"Local\{_name}", writable: false);
        Assert.True(reader.Channel.HasValidHeader);
        Assert.False(reader.Channel.TryReadLatest(new byte[VideoFormat.FrameSize], out _, out _));
    }

    private string SessionName() => $@"Session\{Process.GetCurrentProcess().SessionId}\{_name}";
}
