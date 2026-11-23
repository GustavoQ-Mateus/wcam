namespace Wcam.App.Tests;

public class AgentSupervisorTests
{
    private static readonly SupervisorTiming Fast = new(
        TimeSpan.FromMilliseconds(10),
        TimeSpan.FromMilliseconds(200),
        3,
        2,
        TimeSpan.FromMinutes(5),
        TimeSpan.FromMilliseconds(100));

    [Fact]
    public async Task HealthyAgent_BecomesRunning()
    {
        var launcher = new FakeLauncher();
        var supervisor = new AgentSupervisor(launcher, new FakeHealth(() => true), Fast, TimeProvider.System);
        using var stop = new CancellationTokenSource();
        Task run = supervisor.RunAsync(stop.Token);

        await WaitUntil(() => supervisor.Lifecycle == AgentLifecycle.Running);
        stop.Cancel();
        await run;

        Assert.Single(launcher.Started);
    }

    [Fact]
    public async Task CrashedAgent_IsStartedAgain()
    {
        var launcher = new FakeLauncher();
        var supervisor = new AgentSupervisor(launcher, new FakeHealth(() => true), Fast, TimeProvider.System);
        using var stop = new CancellationTokenSource();
        Task run = supervisor.RunAsync(stop.Token);
        await WaitUntil(() => supervisor.Lifecycle == AgentLifecycle.Running);

        launcher.Started[0].Crash();
        await WaitUntil(() => launcher.Started.Count == 2 && supervisor.Lifecycle == AgentLifecycle.Running);
        stop.Cancel();
        await run;

        Assert.True(launcher.Started[0].Killed);
    }

    [Fact]
    public async Task AgentThatStopsAnswering_IsStartedAgain()
    {
        bool healthy = true;
        var launcher = new FakeLauncher();
        var supervisor = new AgentSupervisor(launcher, new FakeHealth(() => healthy), Fast, TimeProvider.System);
        using var stop = new CancellationTokenSource();
        Task run = supervisor.RunAsync(stop.Token);
        await WaitUntil(() => supervisor.Lifecycle == AgentLifecycle.Running);

        healthy = false;
        await WaitUntil(() => launcher.Started.Count == 2);
        stop.Cancel();
        await run;

        Assert.True(launcher.Started[0].Killed);
    }

    [Fact]
    public async Task AgentCrashingPastTheLimit_EndsStopped()
    {
        var launcher = new FakeLauncher { CrashOnStart = true };
        var supervisor = new AgentSupervisor(launcher, new FakeHealth(() => false), Fast, TimeProvider.System);

        await supervisor.RunAsync(CancellationToken.None).WaitAsync(TimeSpan.FromSeconds(5));

        Assert.Equal(AgentLifecycle.Stopped, supervisor.Lifecycle);
        Assert.Equal(Fast.MaximumRestarts + 1, launcher.Started.Count);
    }

    [Fact]
    public async Task AgentNeverReady_IsStartedAgainAfterTheReadyTimeout()
    {
        var launcher = new FakeLauncher();
        var supervisor = new AgentSupervisor(launcher, new FakeHealth(() => false), Fast, TimeProvider.System);

        await supervisor.RunAsync(CancellationToken.None).WaitAsync(TimeSpan.FromSeconds(5));

        Assert.Equal(AgentLifecycle.Stopped, supervisor.Lifecycle);
        Assert.All(launcher.Started, process => Assert.True(process.Killed));
    }

    [Fact]
    public async Task Stop_AsksTheAgentToEndCleanly()
    {
        var launcher = new FakeLauncher();
        var supervisor = new AgentSupervisor(launcher, new FakeHealth(() => true), Fast, TimeProvider.System);
        using var stop = new CancellationTokenSource();
        Task run = supervisor.RunAsync(stop.Token);
        await WaitUntil(() => supervisor.Lifecycle == AgentLifecycle.Running);

        stop.Cancel();
        await run;

        Assert.True(launcher.Started[0].StopRequested);
        Assert.False(launcher.Started[0].Killed);
    }

    [Fact]
    public async Task Stop_KillsAnAgentThatDoesNotEndInTime()
    {
        var launcher = new FakeLauncher { IgnoreStop = true };
        var supervisor = new AgentSupervisor(launcher, new FakeHealth(() => true), Fast, TimeProvider.System);
        using var stop = new CancellationTokenSource();
        Task run = supervisor.RunAsync(stop.Token);
        await WaitUntil(() => supervisor.Lifecycle == AgentLifecycle.Running);

        stop.Cancel();
        await run;

        Assert.True(launcher.Started[0].Killed);
    }

    [Fact]
    public async Task AgentWithoutLocalNetwork_EndsWithNoNetworkAndIsNotStartedAgain()
    {
        await AssertFinalExit(AgentSupervisor.NoLocalNetworkExitCode, AgentLifecycle.NoNetwork);
    }

    [Fact]
    public async Task AgentWithBusyPort_EndsWithPortBusyAndIsNotStartedAgain()
    {
        await AssertFinalExit(AgentSupervisor.PortInUseExitCode, AgentLifecycle.PortBusy);
    }

    [Fact]
    public async Task AgentEndingOnItsOwnWithZero_EndsStoppedAndIsNotStartedAgain()
    {
        await AssertFinalExit(0, AgentLifecycle.Stopped);
    }

    [Fact]
    public async Task MissingAgentExecutable_EndsStopped()
    {
        var supervisor = new AgentSupervisor(new MissingLauncher(), new FakeHealth(() => true), Fast, TimeProvider.System);

        await supervisor.RunAsync(CancellationToken.None).WaitAsync(TimeSpan.FromSeconds(5));

        Assert.Equal(AgentLifecycle.Stopped, supervisor.Lifecycle);
    }

    private static async Task AssertFinalExit(int exitCode, AgentLifecycle expected)
    {
        var launcher = new FakeLauncher();
        var supervisor = new AgentSupervisor(launcher, new FakeHealth(() => true), Fast, TimeProvider.System);
        Task run = supervisor.RunAsync(CancellationToken.None);
        await WaitUntil(() => supervisor.Lifecycle == AgentLifecycle.Running);

        launcher.Started[0].Crash(exitCode);
        await run.WaitAsync(TimeSpan.FromSeconds(5));

        Assert.Equal(expected, supervisor.Lifecycle);
        Assert.Single(launcher.Started);
    }

    private static async Task WaitUntil(Func<bool> condition)
    {
        DateTime deadline = DateTime.UtcNow.AddSeconds(5);
        while (!condition())
        {
            Assert.True(DateTime.UtcNow < deadline, "condition not reached in 5 s");
            await Task.Delay(5);
        }
    }

    private sealed class FakeLauncher : IAgentLauncher
    {
        public bool CrashOnStart { get; init; }

        public bool IgnoreStop { get; init; }

        public List<FakeProcess> Started { get; } = [];

        public IAgentProcess Start()
        {
            var process = new FakeProcess(IgnoreStop);
            Started.Add(process);
            if (CrashOnStart)
            {
                process.Crash();
            }
            return process;
        }
    }

    private sealed class FakeProcess(bool ignoreStop) : IAgentProcess
    {
        private readonly TaskCompletionSource _exited = new(TaskCreationOptions.RunContinuationsAsynchronously);

        public Task Exited => _exited.Task;

        public int ExitCode { get; private set; } = 1;

        public bool StopRequested { get; private set; }

        public bool Killed { get; private set; }

        public void Crash(int exitCode = 1)
        {
            ExitCode = exitCode;
            _exited.TrySetResult();
        }

        public void RequestStop()
        {
            StopRequested = true;
            if (!ignoreStop)
            {
                ExitCode = 0;
                _exited.TrySetResult();
            }
        }

        public void Kill()
        {
            Killed = true;
            _exited.TrySetResult();
        }

        public void Dispose()
        {
        }
    }

private sealed class MissingLauncher : IAgentLauncher
    {
        public IAgentProcess Start() => throw new System.ComponentModel.Win32Exception(2);
    }

    private sealed class FakeHealth(Func<bool> healthy) : IHealthProbe
    {
        public Task<bool> IsHealthyAsync(CancellationToken cancellation) => Task.FromResult(healthy());
    }
}
