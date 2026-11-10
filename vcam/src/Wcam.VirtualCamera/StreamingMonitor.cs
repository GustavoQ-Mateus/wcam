using System.Runtime.InteropServices.Marshalling;
using Windows.Win32;
using Windows.Win32.Foundation;
using Windows.Win32.Media.MediaFoundation;

namespace Wcam.VirtualCamera;

[GeneratedComClass]
internal sealed unsafe partial class StreamingMonitor : IMFSensorActivitiesReportCallback, IDisposable
{
    private const int NameCapacity = 512;
    private const string LocalizedSuffixStart = " (";

    private readonly Action<int> _onStreamingAppsChanged;
    private readonly IMFSensorActivityMonitor _monitor;
    private int _lastCount = -1;

    private StreamingMonitor(Action<int> onStreamingAppsChanged)
    {
        _onStreamingAppsChanged = onStreamingAppsChanged;
        PInvoke.MFCreateSensorActivityMonitor(this, out _monitor).ThrowOnFailure();
    }

    public static StreamingMonitor Start(Action<int> onStreamingAppsChanged)
    {
        var monitor = new StreamingMonitor(onStreamingAppsChanged);
        monitor._monitor.Start();
        Log.Info("sensor activity monitor started");
        return monitor;
    }

    public static bool IsWcamDevice(string friendlyName) =>
        friendlyName == CameraIdentity.FriendlyName
        || friendlyName.StartsWith(CameraIdentity.FriendlyName + LocalizedSuffixStart, StringComparison.Ordinal);

    public void OnActivitiesReport(IMFSensorActivitiesReport sensorActivitiesReport)
    {
        try
        {
            int count = CountStreamingApps(sensorActivitiesReport);
            if (count == _lastCount)
            {
                return;
            }
            _lastCount = count;
            Log.Info($"apps receiving video from WCam: {count}");
            _onStreamingAppsChanged(count);
        }
        catch (Exception exception)
        {
            Log.Error("sensor activity report failed", exception);
        }
    }

    public void Dispose()
    {
        _monitor.Stop();
        ComObjects.Release(_monitor);
        Log.Info("sensor activity monitor stopped");
    }

    private static int CountStreamingApps(IMFSensorActivitiesReport report)
    {
        report.GetCount(out uint devices);
        var processes = new HashSet<uint>();
        for (uint index = 0; index < devices; index++)
        {
            report.GetActivityReport(index, out IMFSensorActivityReport device);
            if (IsWcamDevice(FriendlyName(device)))
            {
                AddStreamingProcesses(device, processes);
            }
        }
        return processes.Count;
    }

    private static void AddStreamingProcesses(IMFSensorActivityReport device, HashSet<uint> processes)
    {
        device.GetProcessCount(out uint count);
        for (uint index = 0; index < count; index++)
        {
            device.GetProcessActivity(index, out IMFSensorProcessActivity activity);
            BOOL streaming;
            activity.GetStreamingState(&streaming);
            if (streaming)
            {
                activity.GetProcessId(out uint processId);
                processes.Add(processId);
            }
        }
    }

    private static string FriendlyName(IMFSensorActivityReport device)
    {
        char* buffer = stackalloc char[NameCapacity];
        device.GetFriendlyName(new PWSTR(buffer), NameCapacity, out _);
        return new string(buffer);
    }
}
