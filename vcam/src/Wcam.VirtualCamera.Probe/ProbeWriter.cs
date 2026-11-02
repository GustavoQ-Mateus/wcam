namespace Wcam.VirtualCamera.Probe;

internal sealed class ProbeWriter : IDisposable
{
    private const byte LumaFloor = 16;
    private const int LumaRange = 220;
    private const byte ChromaBlue = 170;
    private const byte ChromaRed = 200;
    private const int GradientStep = 8;
    private const int ReportEveryFrames = VideoFormat.FramesPerSecond * 10;
    private static readonly TimeSpan FrameInterval = TimeSpan.FromTicks(VideoFormat.FrameDurationTicks);
    private static readonly TimeSpan ConnectRetry = TimeSpan.FromSeconds(1);

    private readonly ProbeTransport _transport;
    private readonly Thread _thread;
    private readonly byte[] _frame = new byte[VideoFormat.FrameSize];
    private volatile bool _stopping;

    public ProbeWriter(ProbeTransport transport)
    {
        _transport = transport;
        _thread = new Thread(Run) { IsBackground = true, Name = "WCam probe writer" };
        _thread.Start();
    }

    public void Dispose()
    {
        _stopping = true;
        _thread.Join();
    }

    private void Run()
    {
        using MappedFrameChannel? mapped = Connect();
        if (mapped is null)
        {
            return;
        }
        Console.WriteLine($"writer: connected to {_transport}");
        long frameNumber = 0;
        while (!_stopping)
        {
            RenderFrame(frameNumber);
            ulong published = mapped.Channel.Publish(_frame, DateTime.UtcNow.Ticks);
            if (published % ReportEveryFrames == 0)
            {
                Console.WriteLine($"writer: published frame {published}");
            }
            frameNumber++;
            Thread.Sleep(FrameInterval);
        }
    }

    private MappedFrameChannel? Connect()
    {
        string? lastError = null;
        while (!_stopping)
        {
            try
            {
                return _transport == ProbeTransport.File ? MappedFrameChannel.CreateFile(FrameTransport.FilePath) : OpenSection();
            }
            catch (Exception exception) when (exception is IOException or UnauthorizedAccessException)
            {
                string error = $"{exception.GetType().Name}: {exception.Message}";
                if (error != lastError)
                {
                    Console.WriteLine($"writer: {_transport} unavailable, retrying: {error}");
                    lastError = error;
                }
                Thread.Sleep(ConnectRetry);
            }
        }
        return null;
    }

    private static MappedFrameChannel OpenSection()
    {
        MappedFrameChannel mapped = MappedFrameChannel.OpenSection(FrameTransport.SectionName, writable: true);
        mapped.Channel.InitializeHeader();
        return mapped;
    }

    private void RenderFrame(long frameNumber)
    {
        Span<byte> luma = _frame.AsSpan(0, VideoFormat.Width * VideoFormat.Height);
        Span<byte> chroma = _frame.AsSpan(VideoFormat.Width * VideoFormat.Height);
        Span<byte> row = luma[..VideoFormat.Width];
        int offset = (int)(frameNumber * GradientStep % LumaRange);
        for (int column = 0; column < VideoFormat.Width; column++)
        {
            row[column] = (byte)(LumaFloor + (column + offset) % LumaRange);
        }
        for (int line = 1; line < VideoFormat.Height; line++)
        {
            row.CopyTo(luma.Slice(line * VideoFormat.Width, VideoFormat.Width));
        }
        for (int index = 0; index < chroma.Length; index += 2)
        {
            chroma[index] = ChromaBlue;
            chroma[index + 1] = ChromaRed;
        }
    }
}
