using Windows.Win32;

namespace Wcam.VirtualCamera;

internal sealed class SessionFrameReader : IDisposable
{
    private const long RetryMilliseconds = 1000;
    private const int ReadAttempts = 3;
    private const byte BlackLuma = 16;
    private const byte NeutralChroma = 128;
    private const int LumaSize = VideoFormat.Width * VideoFormat.Height;

    private MappedFrameChannel? _channel;
    private long _nextOpenAttempt;
    private string? _lastOpenError;
    private bool _hasOpened;
    private bool _showingPublished;

    public static void FillBlack(Span<byte> frame)
    {
        frame[..LumaSize].Fill(BlackLuma);
        frame[LumaSize..].Fill(NeutralChroma);
    }

    public void Fill(Span<byte> frame)
    {
        bool published = TryReadFresh(frame);
        if (!published)
        {
            FillBlack(frame);
        }
        if (published != _showingPublished)
        {
            Log.Info(published ? "showing published frames" : "showing black: no frame in the last second");
            _showingPublished = published;
        }
    }

    public void Dispose() => _channel?.Dispose();

    private bool TryReadFresh(Span<byte> frame)
    {
        MappedFrameChannel? channel = OpenWhenDue();
        if (channel is null)
        {
            return false;
        }
        for (int attempt = 0; attempt < ReadAttempts; attempt++)
        {
            if (channel.Channel.TryReadLatest(frame, out _, out long timestampTicks))
            {
                if (FrameTransport.IsFresh(timestampTicks, DateTime.UtcNow.Ticks))
                {
                    return true;
                }
                break;
            }
        }
        CloseUntilNextAttempt();
        return false;
    }

    private MappedFrameChannel? OpenWhenDue()
    {
        if (_channel is not null || Environment.TickCount64 < _nextOpenAttempt)
        {
            return _channel;
        }
        _nextOpenAttempt = Environment.TickCount64 + RetryMilliseconds;
        string name = FrameTransport.SessionSectionName(PInvoke.WTSGetActiveConsoleSessionId());
        try
        {
            _channel = MappedFrameChannel.OpenSection(name, writable: false);
            if (_lastOpenError is not null || !_hasOpened)
            {
                Log.Info($"opened {name} for reading");
            }
            _hasOpened = true;
            _lastOpenError = null;
        }
        catch (Exception exception) when (exception is IOException or UnauthorizedAccessException)
        {
            LogOpenErrorOnce(name, exception);
        }
        return _channel;
    }

    private void CloseUntilNextAttempt()
    {
        _channel?.Dispose();
        _channel = null;
        _nextOpenAttempt = Environment.TickCount64 + RetryMilliseconds;
    }

    private void LogOpenErrorOnce(string name, Exception exception)
    {
        string error = $"{exception.GetType().Name}: {exception.Message}";
        if (error == _lastOpenError)
        {
            return;
        }
        _lastOpenError = error;
        Log.Info($"{name} unavailable: {error}");
    }
}
