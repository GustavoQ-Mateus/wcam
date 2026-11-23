namespace Wcam.App;

internal sealed class SingleInstance : IDisposable
{
    public const string ProductName = @"Local\WCam.App";

    private readonly Mutex _mutex;
    private readonly EventWaitHandle _show;

    private SingleInstance(Mutex mutex, EventWaitHandle show)
    {
        _mutex = mutex;
        _show = show;
    }

    public WaitHandle ShowRequested => _show;

    public static SingleInstance? TryAcquire(string name)
    {
        var mutex = new Mutex(initiallyOwned: true, name, out bool createdNew);
        var show = new EventWaitHandle(false, EventResetMode.AutoReset, name + ".Show");
        if (createdNew)
        {
            return new SingleInstance(mutex, show);
        }
        show.Set();
        show.Dispose();
        mutex.Dispose();
        return null;
    }

    public void Dispose()
    {
        _mutex.ReleaseMutex();
        _mutex.Dispose();
        _show.Dispose();
    }
}
