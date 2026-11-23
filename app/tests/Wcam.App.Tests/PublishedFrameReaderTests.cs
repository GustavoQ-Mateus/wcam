using System.IO.MemoryMappedFiles;
using Wcam.VirtualCamera;

namespace Wcam.App.Tests;

public unsafe class PublishedFrameReaderTests : IDisposable
{
    private static readonly FrameFormat Format = FrameFormat.Default;

    private readonly string _name = $@"Local\WCamFrames.Tests.{Guid.NewGuid()}";
    private readonly MemoryMappedFile _file;
    private readonly MemoryMappedViewAccessor _view;
    private readonly FrameChannel _writer;
    private readonly byte[] _frame = new byte[Format.FrameSize];

    public PublishedFrameReaderTests()
    {
        _file = MemoryMappedFile.CreateNew(_name, FrameChannel.Capacity);
        _view = _file.CreateViewAccessor();
        byte* pointer = null;
        _view.SafeMemoryMappedViewHandle.AcquirePointer(ref pointer);
        _writer = new FrameChannel(pointer + _view.PointerOffset);
        _writer.InitializeHeader(Format);
    }

    [Fact]
    public void PublishedFrame_IsReadAsNew()
    {
        using var reader = new PublishedFrameReader(_name, TimeProvider.System);
        _frame[0] = 42;
        _writer.Publish(_frame, DateTime.UtcNow.Ticks);
        var destination = new byte[Format.FrameSize];

        Assert.True(reader.TryReadFormat(out FrameFormat format));
        Assert.Equal(FrameRead.New, reader.ReadLatest(destination, format, out ulong index));
        Assert.Equal(1UL, index);
        Assert.Equal(42, destination[0]);
    }

    [Fact]
    public void SameFrameTwice_IsReadAsSame()
    {
        using var reader = new PublishedFrameReader(_name, TimeProvider.System);
        _writer.Publish(_frame, DateTime.UtcNow.Ticks);
        var destination = new byte[Format.FrameSize];
        reader.ReadLatest(destination, Format, out _);

        Assert.Equal(FrameRead.Same, reader.ReadLatest(destination, Format, out _));
    }

    [Fact]
    public void OldFrame_IsReadAsIdle()
    {
        using var reader = new PublishedFrameReader(_name, TimeProvider.System);
        _writer.Publish(_frame, DateTime.UtcNow.AddSeconds(-5).Ticks);

        Assert.Equal(FrameRead.Idle, reader.ReadLatest(new byte[Format.FrameSize], Format, out _));
    }

    [Fact]
    public void MissingSection_IsReadAsIdle()
    {
        using var reader = new PublishedFrameReader($@"Local\WCamFrames.Missing.{Guid.NewGuid()}", TimeProvider.System);

        Assert.False(reader.TryReadFormat(out _));
        Assert.Equal(FrameRead.Idle, reader.ReadLatest(new byte[Format.FrameSize], Format, out _));
    }

    public void Dispose()
    {
        _view.SafeMemoryMappedViewHandle.ReleasePointer();
        _view.Dispose();
        _file.Dispose();
    }
}
