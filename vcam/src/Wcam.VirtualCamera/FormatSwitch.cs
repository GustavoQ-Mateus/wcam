namespace Wcam.VirtualCamera;

internal enum FormatRequestOutcome
{
    Applied,
    RestartCamera,
    Pending,
}

internal sealed class FormatSwitch
{
    public const long IdleBeforeApplyMilliseconds = 1000;

    private long? _idleSince;

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

    public bool UpdateStreamingApps(int count, long nowMilliseconds)
    {
        if (count > 0)
        {
            _idleSince = null;
        }
        else if (StreamingApps > 0 || _idleSince is null)
        {
            _idleSince = nowMilliseconds;
        }
        StreamingApps = count;
        return count == 0 && IsPending;
    }

    public long? MillisecondsUntilPendingApplies(long nowMilliseconds)
    {
        if (!IsPending || StreamingApps > 0 || _idleSince is not long idleSince)
        {
            return null;
        }
        return Math.Max(0, IdleBeforeApplyMilliseconds - (nowMilliseconds - idleSince));
    }

    public void Announce(FrameFormat format) => Announced = format;
}
