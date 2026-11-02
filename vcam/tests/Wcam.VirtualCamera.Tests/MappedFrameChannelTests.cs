namespace Wcam.VirtualCamera.Tests;

public sealed class MappedFrameChannelTests : IDisposable
{
    private const long Timestamp = 638_000_000_000_000_000;

    private readonly string _path = Path.Combine(Path.GetTempPath(), $"wcam-frames-{Guid.NewGuid():N}.bin");

    public void Dispose() => File.Delete(_path);

    [Fact]
    public void OpenFile_WhileWriterPublishes_ReadsFrameWrittenThroughOtherMapping()
    {
        byte[] frame = new byte[VideoFormat.FrameSize];
        new Random(11).NextBytes(frame);
        byte[] destination = new byte[VideoFormat.FrameSize];
        using MappedFrameChannel writer = MappedFrameChannel.CreateFile(_path);
        using MappedFrameChannel reader = MappedFrameChannel.OpenFile(_path);
        writer.Channel.Publish(frame, Timestamp);
        Assert.True(reader.Channel.TryReadLatest(destination, out ulong frameIndex, out _));
        Assert.Equal(frame, destination);
        Assert.Equal(1UL, frameIndex);
    }

    [Fact]
    public void CreateFile_OnNewPath_SizesFileForHeaderAndThreeSlots()
    {
        using (MappedFrameChannel.CreateFile(_path))
        {
        }
        Assert.Equal(FrameChannel.Capacity, new FileInfo(_path).Length);
    }
}
