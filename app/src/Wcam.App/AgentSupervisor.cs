namespace Wcam.App;

internal interface IAgentProcess : IDisposable
{
    Task Exited { get; }

    int ExitCode { get; }

    void RequestStop();

    void Kill();
}

internal interface IAgentLauncher
{
    IAgentProcess Start();
}

internal interface IHealthProbe
{
    Task<bool> IsHealthyAsync(CancellationToken cancellation);
}

internal sealed record SupervisorTiming(
    TimeSpan HealthInterval,
    TimeSpan ReadyTimeout,
    int FailuresBeforeRestart,
    int MaximumRestarts,
    TimeSpan RestartWindow,
    TimeSpan StopTimeout)
{
    public static readonly SupervisorTiming Product = new(
        TimeSpan.FromSeconds(2),
        TimeSpan.FromSeconds(30),
        3,
        3,
        TimeSpan.FromMinutes(5),
        TimeSpan.FromSeconds(5));
}

internal sealed class AgentSupervisor
{
    public const int NoLocalNetworkExitCode = 2;
    public const int PortInUseExitCode = 3;

    private readonly IAgentLauncher _launcher;
    private readonly IHealthProbe _health;
    private readonly SupervisorTiming _timing;
    private readonly TimeProvider _time;
    private readonly RestartPolicy _restarts;

    public AgentSupervisor(IAgentLauncher launcher, IHealthProbe health, SupervisorTiming timing, TimeProvider time)
    {
        _launcher = launcher;
        _health = health;
        _timing = timing;
        _time = time;
        _restarts = new RestartPolicy(timing.MaximumRestarts, timing.RestartWindow);
    }

    public event Action<AgentLifecycle>? LifecycleChanged;

    public AgentLifecycle Lifecycle { get; private set; } = AgentLifecycle.Starting;

    public async Task RunAsync(CancellationToken stop)
    {
        while (!stop.IsCancellationRequested)
        {
            using IAgentProcess? process = TryStart();
            if (process is null)
            {
                SetLifecycle(AgentLifecycle.Stopped);
                return;
            }
            bool crashed = await WatchAsync(process, stop);
            if (!crashed)
            {
                await StopAsync(process);
                return;
            }
            AgentLifecycle? final = FinalLifecycle(process);
            process.Kill();
            if (final is not null || !_restarts.TryRestart(_time.GetUtcNow()))
            {
                SetLifecycle(final ?? AgentLifecycle.Stopped);
                return;
            }
            SetLifecycle(AgentLifecycle.Restarting);
        }
    }

    private IAgentProcess? TryStart()
    {
        try
        {
            return _launcher.Start();
        }
        catch (Exception exception) when (exception is System.ComponentModel.Win32Exception or InvalidOperationException)
        {
            return null;
        }
    }

    private static AgentLifecycle? FinalLifecycle(IAgentProcess process)
    {
        if (!process.Exited.IsCompleted)
        {
            return null;
        }
        return process.ExitCode switch
        {
            0 => AgentLifecycle.Stopped,
            NoLocalNetworkExitCode => AgentLifecycle.NoNetwork,
            PortInUseExitCode => AgentLifecycle.PortBusy,
            _ => null,
        };
    }

    private async Task<bool> WatchAsync(IAgentProcess process, CancellationToken stop)
    {
        DateTimeOffset readyDeadline = _time.GetUtcNow() + _timing.ReadyTimeout;
        int failures = 0;
        while (!stop.IsCancellationRequested)
        {
            if (process.Exited.IsCompleted)
            {
                return true;
            }
            bool healthy = await ProbeAsync(stop);
            if (stop.IsCancellationRequested)
            {
                return false;
            }
            if (healthy)
            {
                failures = 0;
                SetLifecycle(AgentLifecycle.Running);
            }
            else if (Lifecycle == AgentLifecycle.Running ? ++failures >= _timing.FailuresBeforeRestart
                : _time.GetUtcNow() >= readyDeadline)
            {
                return true;
            }
            await WaitAsync(process, stop);
        }
        return false;
    }

    private async Task<bool> ProbeAsync(CancellationToken stop)
    {
        try
        {
            return await _health.IsHealthyAsync(stop);
        }
        catch (Exception exception) when (exception is HttpRequestException or OperationCanceledException or IOException)
        {
            return false;
        }
    }

    private async Task WaitAsync(IAgentProcess process, CancellationToken stop)
    {
        Task delay = Task.Delay(_timing.HealthInterval, _time, stop);
        await Task.WhenAny(delay, process.Exited).ConfigureAwait(false);
    }

    private async Task StopAsync(IAgentProcess process)
    {
        process.RequestStop();
        Task timeout = Task.Delay(_timing.StopTimeout, _time);
        if (await Task.WhenAny(process.Exited, timeout).ConfigureAwait(false) != process.Exited)
        {
            process.Kill();
        }
    }

    private void SetLifecycle(AgentLifecycle lifecycle)
    {
        if (Lifecycle == lifecycle)
        {
            return;
        }
        Lifecycle = lifecycle;
        LifecycleChanged?.Invoke(lifecycle);
    }
}
