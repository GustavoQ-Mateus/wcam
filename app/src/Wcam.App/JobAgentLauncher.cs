using System.ComponentModel;
using System.Diagnostics;
using Windows.Win32;
using Windows.Win32.Foundation;
using Windows.Win32.System.JobObjects;

namespace Wcam.App;

internal sealed unsafe class JobAgentLauncher : IAgentLauncher, IDisposable
{
    private readonly AgentCommand _command;
    private readonly HANDLE _job;

    public JobAgentLauncher(AgentCommand command)
    {
        _command = command;
        _job = PInvoke.CreateJobObject(null, (PCWSTR)null);
        if (_job.IsNull)
        {
            throw new Win32Exception();
        }
        var limits = new JOBOBJECT_EXTENDED_LIMIT_INFORMATION();
        limits.BasicLimitInformation.LimitFlags = JOB_OBJECT_LIMIT.JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE;
        if (!PInvoke.SetInformationJobObject(
            _job,
            JOBOBJECTINFOCLASS.JobObjectExtendedLimitInformation,
            &limits,
            (uint)sizeof(JOBOBJECT_EXTENDED_LIMIT_INFORMATION)))
        {
            throw new Win32Exception();
        }
    }

    public IAgentProcess Start()
    {
        var start = new ProcessStartInfo(_command.Executable)
        {
            UseShellExecute = false,
            CreateNoWindow = true,
            RedirectStandardInput = true,
            WorkingDirectory = _command.WorkingDirectory,
        };
        foreach (string argument in _command.Arguments)
        {
            start.ArgumentList.Add(argument);
        }
        Process process = Process.Start(start) ?? throw new InvalidOperationException(_command.Executable);
        PInvoke.AssignProcessToJobObject(_job, (HANDLE)process.Handle);
        return new JobAgentProcess(process, _job);
    }

    public void Dispose() => PInvoke.CloseHandle(_job);

    private sealed class JobAgentProcess : IAgentProcess
    {
        private const uint KilledExitCode = 1;

        private readonly Process _process;
        private readonly HANDLE _job;

        public JobAgentProcess(Process process, HANDLE job)
        {
            _process = process;
            _job = job;
            Exited = process.WaitForExitAsync();
        }

        public Task Exited { get; }

        public int ExitCode => _process.ExitCode;

        public void RequestStop()
        {
            try
            {
                _process.StandardInput.Close();
            }
            catch (IOException)
            {
            }
        }

        public void Kill() => PInvoke.TerminateJobObject(_job, KilledExitCode);

        public void Dispose() => _process.Dispose();
    }
}

internal sealed record AgentCommand(string Executable, IReadOnlyList<string> Arguments, string WorkingDirectory);
