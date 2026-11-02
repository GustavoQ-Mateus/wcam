namespace Wcam.VirtualCamera;

internal sealed class FrameProducer : IDisposable
{
    private const string TestPatternName = "test pattern";
    private const string SectionTransportName = "global section";
    private const string FileTransportName = "mapped file";
    private const long FileRetryMilliseconds = 1000;
    private static readonly long FreshnessTicks = TimeSpan.FromSeconds(1).Ticks;

    private readonly TestPattern _pattern = new();
    private readonly GlobalFrameSection? _section = TryCreateSection();
    private MappedFrameChannel? _file;
    private long _nextFileAttempt;
    private string? _lastFileError;
    private string _activeSource = TestPatternName;
    private long _frameNumber;

    public void Fill(Span<byte> frame)
    {
        string source = TryReadPublished(frame) ?? TestPatternName;
        if (source == TestPatternName)
        {
            _pattern.Render(frame, _frameNumber);
        }
        if (source != _activeSource)
        {
            Log.Info($"frame source changed from {_activeSource} to {source} at frame {_frameNumber}");
            _activeSource = source;
        }
        _frameNumber++;
    }

    public void Dispose()
    {
        _section?.Dispose();
        _file?.Dispose();
    }

    private string? TryReadPublished(Span<byte> frame)
    {
        if (_section is not null && TryReadFresh(_section.Reader.Channel, frame))
        {
            return SectionTransportName;
        }
        MappedFrameChannel? file = OpenFileWhenAvailable();
        if (file is not null && TryReadFresh(file.Channel, frame))
        {
            return FileTransportName;
        }
        return null;
    }

    private static bool TryReadFresh(FrameChannel channel, Span<byte> frame) =>
        channel.TryReadLatest(frame, out _, out long timestampTicks)
        && DateTime.UtcNow.Ticks - timestampTicks < FreshnessTicks;

    private MappedFrameChannel? OpenFileWhenAvailable()
    {
        if (_file is not null || Environment.TickCount64 < _nextFileAttempt)
        {
            return _file;
        }
        _nextFileAttempt = Environment.TickCount64 + FileRetryMilliseconds;
        try
        {
            _file = MappedFrameChannel.OpenFile(FrameTransport.FilePath);
            Log.Info($"opened {FileTransportName} {FrameTransport.FilePath}");
        }
        catch (Exception exception) when (exception is IOException or UnauthorizedAccessException)
        {
            LogFileErrorOnce(exception);
        }
        return _file;
    }

    private void LogFileErrorOnce(Exception exception)
    {
        string error = $"{exception.GetType().Name}: {exception.Message}";
        if (error == _lastFileError)
        {
            return;
        }
        _lastFileError = error;
        Log.Info($"{FileTransportName} unavailable: {error}");
    }

    private static GlobalFrameSection? TryCreateSection()
    {
        try
        {
            GlobalFrameSection section = GlobalFrameSection.Create();
            Log.Info($"created {SectionTransportName} {FrameTransport.SectionName}");
            return section;
        }
        catch (Exception exception)
        {
            Log.Error($"could not create {SectionTransportName} {FrameTransport.SectionName}", exception);
            return null;
        }
    }
}
