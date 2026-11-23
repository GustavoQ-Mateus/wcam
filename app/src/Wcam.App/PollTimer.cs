using System.ComponentModel;
using Microsoft.Win32.SafeHandles;
using Windows.Win32;
using Windows.Win32.Foundation;
using Windows.Win32.System.Threading;

namespace Wcam.App;

internal sealed unsafe class PollTimer : WaitHandle
{
    private const uint AllAccess = 0x1F0003;

    public PollTimer()
    {
        HANDLE timer = PInvoke.CreateWaitableTimerEx(
            null, (PCWSTR)null, PInvoke.CREATE_WAITABLE_TIMER_HIGH_RESOLUTION, AllAccess);
        if (timer.IsNull)
        {
            throw new Win32Exception();
        }
        SafeWaitHandle = new SafeWaitHandle(timer, ownsHandle: true);
    }

    public bool Wait(TimeSpan delay, WaitHandle stop)
    {
        long dueTime = -delay.Ticks;
        if (!PInvoke.SetWaitableTimer((HANDLE)SafeWaitHandle.DangerousGetHandle(), &dueTime, 0, null, null, false))
        {
            throw new Win32Exception();
        }
        return WaitAny([this, stop]) == 0;
    }
}
