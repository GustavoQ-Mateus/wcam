using System.IO.MemoryMappedFiles;
using Wcam.VirtualCamera;

namespace Wcam.App;

internal enum FrameRead
{
    New,
    Same,
    Idle,
}

internal sealed unsafe class PublishedFrameReader : IDisposable
{
    public const string SectionName = @"Local\" + FrameTransport.SectionName;
    private static readonly TimeSpan ReopenInterval = TimeSpan.FromSeconds(1);

    private readonly string _name;
    private readonly TimeProvider _time;
    private MemoryMappedFile? _file;
    private MemoryMappedViewAccessor? _view;
    private byte* _pointer;
    private FrameChannel? _channel;
    private DateTimeOffset _nextOpen;
    private ulong _lastIndex;

    public PublishedFrameReader(string name, TimeProvider time)
    {
        _name = name;
        _time = time;
    }

    public bool TryReadFormat(out FrameFormat format)
    {
        format = default;
        FrameChannel? channel = OpenWhenDue();
        return channel is not null && channel.TryReadFormat(out format);
    }

    public FrameRead ReadLatest(Span<byte> destination, FrameFormat format, out ulong frameIndex)
    {
        frameIndex = 0;
        FrameChannel? channel = OpenWhenDue();
        if (channel is null)
        {
            return FrameRead.Idle;
        }
        ulong latest = Volatile.Read(ref *(ulong*)(_pointer + FrameChannel.FrameIndexOffset));
        if (latest == _lastIndex && latest != 0)
        {
            return IsFresh() ? FrameRead.Same : CloseUntilNextOpen();
        }
        if (!channel.TryReadLatest(destination, format, out frameIndex, out long timestamp))
        {
            return FrameRead.Same;
        }
        if (!FrameTransport.IsFresh(timestamp, DateTime.UtcNow.Ticks))
        {
            return CloseUntilNextOpen();
        }
        _lastIndex = frameIndex;
        return FrameRead.New;
    }

    public void Dispose() => Close();

    private bool IsFresh()
    {
        long timestamp = Volatile.Read(ref *(long*)(_pointer + FrameChannel.TimestampOffset));
        return FrameTransport.IsFresh(timestamp, DateTime.UtcNow.Ticks);
    }

    private FrameRead CloseUntilNextOpen()
    {
        Close();
        _nextOpen = _time.GetUtcNow() + ReopenInterval;
        return FrameRead.Idle;
    }

    private FrameChannel? OpenWhenDue()
    {
        if (_channel is not null || _time.GetUtcNow() < _nextOpen)
        {
            return _channel;
        }
        _nextOpen = _time.GetUtcNow() + ReopenInterval;
        try
        {
            _file = MemoryMappedFile.OpenExisting(_name, MemoryMappedFileRights.Read);
            _view = _file.CreateViewAccessor(0, FrameChannel.Capacity, MemoryMappedFileAccess.Read);
            _view.SafeMemoryMappedViewHandle.AcquirePointer(ref _pointer);
            _pointer += _view.PointerOffset;
            _channel = new FrameChannel(_pointer);
            _lastIndex = 0;
        }
        catch (Exception exception) when (exception is IOException or UnauthorizedAccessException)
        {
            Close();
        }
        return _channel;
    }

    private void Close()
    {
        if (_pointer != null && _view is not null)
        {
            _view.SafeMemoryMappedViewHandle.ReleasePointer();
        }
        _pointer = null;
        _channel = null;
        _view?.Dispose();
        _file?.Dispose();
        _view = null;
        _file = null;
    }
}
