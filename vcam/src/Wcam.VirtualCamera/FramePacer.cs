using System.ComponentModel;
using System.Diagnostics;
using Microsoft.Win32.SafeHandles;
using Windows.Win32;
using Windows.Win32.System.Threading;

namespace Wcam.VirtualCamera;

internal sealed class FramePacer : IDisposable
{
    private const uint InfiniteWait = uint.MaxValue;
    private static readonly long Interval = Stopwatch.Frequency / VideoFormat.FramesPerSecond;

    private readonly Action _tick;
    private readonly Thread _thread;
    private volatile bool _stopping;

    public FramePacer(Action tick)
    {
        _tick = tick;
        _thread = new Thread(Run) { IsBackground = true, Name = "WCam frame pacer" };
        _thread.Start();
    }

    public void Dispose()
    {
        _stopping = true;
        if (Thread.CurrentThread != _thread)
        {
            _thread.Join();
        }
    }

    private void Run()
    {
        try
        {
            using SafeFileHandle timer = CreateTimer();
            long deadline = Stopwatch.GetTimestamp();
            while (!_stopping)
            {
                deadline = NextDeadline(deadline);
                WaitUntil(timer, deadline);
                Tick();
            }
        }
        catch (Exception exception)
        {
            Log.Error("frame pacer stopped", exception);
        }
    }

    private void Tick()
    {
        try
        {
            _tick();
        }
        catch (Exception exception)
        {
            Log.Error("frame delivery failed", exception);
        }
    }

    private static long NextDeadline(long previous)
    {
        long next = previous + Interval;
        long now = Stopwatch.GetTimestamp();
        return next < now ? now : next;
    }

    private static SafeFileHandle CreateTimer()
    {
        SafeFileHandle timer = PInvoke.CreateWaitableTimerEx(
            null,
            null,
            PInvoke.CREATE_WAITABLE_TIMER_HIGH_RESOLUTION,
            (uint)SYNCHRONIZATION_ACCESS_RIGHTS.TIMER_ALL_ACCESS);
        if (timer.IsInvalid)
        {
            throw new Win32Exception();
        }
        return timer;
    }

    private static unsafe void WaitUntil(SafeFileHandle timer, long deadline)
    {
        long remaining = deadline - Stopwatch.GetTimestamp();
        if (remaining <= 0)
        {
            return;
        }
        long relativeDueTime = -(remaining * TimeSpan.TicksPerSecond / Stopwatch.Frequency);
        if (!PInvoke.SetWaitableTimer(timer, relativeDueTime, 0, null, null, false))
        {
            throw new Win32Exception();
        }
        PInvoke.WaitForSingleObject(timer, InfiniteWait);
    }
}
