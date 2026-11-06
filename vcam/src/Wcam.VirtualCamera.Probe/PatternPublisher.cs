namespace Wcam.VirtualCamera.Probe;

internal sealed class PatternPublisher : IDisposable
{
    private const int ReportEveryFrames = VideoFormat.FramesPerSecond * 10;
    private static readonly TimeSpan FrameInterval = TimeSpan.FromTicks(VideoFormat.FrameDurationTicks);

    private readonly CameraLibrary _library;
    private readonly FrameRenderer _render;
    private readonly byte[] _frame = new byte[VideoFormat.FrameSize];
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
        for (long frameNumber = 0; !_stopping; frameNumber++)
        {
            _render(_frame, frameNumber);
            int status = _library.Publish(_frame);
            if (status != 0 || frameNumber % ReportEveryFrames == 0)
            {
                Console.WriteLine($"pattern: frame {frameNumber}, WcamFramePublish 0x{status:X8}");
            }
            Thread.Sleep(FrameInterval);
        }
    }
}
