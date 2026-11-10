namespace Wcam.VirtualCamera;

internal enum FormatRequestOutcome
{
    Applied,
    RestartCamera,
    Pending,
}

internal sealed class FormatSwitch
{
    public FormatSwitch(FrameFormat initial)
    {
        Announced = initial;
        Requested = initial;
    }

    public FrameFormat Announced { get; private set; }

    public FrameFormat Requested { get; private set; }

    public int StreamingApps { get; private set; }

    public bool IsPending => Requested != Announced;

    public FormatRequestOutcome Request(FrameFormat format, bool cameraStarted)
    {
        Requested = format;
        if (!cameraStarted || format == Announced)
        {
            Announced = format;
            return FormatRequestOutcome.Applied;
        }
        return StreamingApps > 0 ? FormatRequestOutcome.Pending : FormatRequestOutcome.RestartCamera;
    }

    public bool UpdateStreamingApps(int count)
    {
        StreamingApps = count;
        return count == 0 && IsPending;
    }

    public void Announce(FrameFormat format) => Announced = format;
}
