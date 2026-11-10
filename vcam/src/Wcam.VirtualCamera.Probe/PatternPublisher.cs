using System.Diagnostics;

namespace Wcam.VirtualCamera.Probe;

internal sealed class PatternPublisher : IDisposable
{
    private const int ReportEverySeconds = 10;
    private const int SleepThresholdMilliseconds = 3;

    private readonly CameraLibrary _library;
    private readonly FrameRenderer _render;
    private readonly Thread _thread;
    private volatile bool _stopping;

    public PatternPublisher(CameraLibrary library, FrameRenderer render)
    {
        _library = library;
        _render = render;
        _thread = new Thread(Run) { IsBackground = true, Name = "WCam probe pattern" };
        _thread.Start();
    }

    public void Dispose()
    {
        _stopping = true;
        _thread.Join();
    }

    private void Run()
    {
        byte[] frame = [];
        long deadline = Stopwatch.GetTimestamp();
        long reportAt = deadline;
        for (long frameNumber = 0; !_stopping; frameNumber++)
        {
            FrameFormat format = _library.AnnouncedFormat() ?? FrameFormat.Default;
            if (frame.Length != format.FrameSize)
            {
                frame = new byte[format.FrameSize];
            }
            _render(frame, format, frameNumber);
            int status = _library.Publish(frame, format);
            if (status != 0 || Stopwatch.GetTimestamp() >= reportAt)
            {
                Console.WriteLine($"pattern: frame {frameNumber} at {format}, WcamFramePublish 0x{status:X8}");
                reportAt = Stopwatch.GetTimestamp() + Stopwatch.Frequency * ReportEverySeconds;
            }
            deadline = Math.Max(deadline + Stopwatch.Frequency / format.FramesPerSecond, Stopwatch.GetTimestamp() - Stopwatch.Frequency);
            WaitUntil(deadline);
        }
    }

    private static void WaitUntil(long deadline)
    {
        long sleepThreshold = Stopwatch.Frequency * SleepThresholdMilliseconds / 1000;
        while (true)
        {
            long remaining = deadline - Stopwatch.GetTimestamp();
            if (remaining <= 0)
            {
                return;
            }
            if (remaining > sleepThreshold)
            {
                Thread.Sleep(1);
                continue;
            }
            Thread.SpinWait(100);
        }
    }
}
