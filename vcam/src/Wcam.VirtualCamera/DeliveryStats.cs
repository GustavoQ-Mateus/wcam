using System.Diagnostics;

namespace Wcam.VirtualCamera;

internal sealed class DeliveryStats
{
    private static readonly long ReportInterval = Stopwatch.Frequency * 10;

    private long _requests;
    private long _delivered;
    private long _idleTicks;
    private long _buildTicks;
    private long _windowStart = Stopwatch.GetTimestamp();

    public void CountRequest() => Interlocked.Increment(ref _requests);

    public void CountIdleTick()
    {
        _idleTicks++;
        ReportWhenDue();
    }

    public void CountDelivery(long buildStarted)
    {
        _buildTicks += Stopwatch.GetTimestamp() - buildStarted;
        _delivered++;
        ReportWhenDue();
    }

    private void ReportWhenDue()
    {
        long now = Stopwatch.GetTimestamp();
        long elapsed = now - _windowStart;
        if (elapsed < ReportInterval)
        {
            return;
        }
        double seconds = (double)elapsed / Stopwatch.Frequency;
        double buildMilliseconds = _delivered == 0 ? 0 : _buildTicks * 1000.0 / Stopwatch.Frequency / _delivered;
        Log.Info(
            $"delivery: {_delivered / seconds:F1} fps, {Interlocked.Exchange(ref _requests, 0) / seconds:F1} requests/s, "
            + $"{_idleTicks} idle ticks, {buildMilliseconds:F2} ms per sample");
        _delivered = 0;
        _idleTicks = 0;
        _buildTicks = 0;
        _windowStart = now;
    }
}
