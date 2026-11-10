using System.Diagnostics;
using System.Runtime.InteropServices.Marshalling;
using Windows.Win32;
using Windows.Win32.Foundation;
using Windows.Win32.Media.MediaFoundation;
using Windows.Win32.System.Com;

namespace Wcam.SensorActivity;

internal static class Program
{
    private const int DefaultSeconds = 60;

    private static int Main(string[] args)
    {
        int seconds = args.Length > 0 && int.TryParse(args[0], out int parsed) ? parsed : DefaultSeconds;
        PInvoke.CoInitializeEx(COINIT.COINIT_MULTITHREADED).ThrowOnFailure();
        PInvoke.MFStartup(PInvoke.MF_VERSION, PInvoke.MFSTARTUP_FULL).ThrowOnFailure();
        PInvoke.MFCreateSensorActivityMonitor(new ReportPrinter(), out IMFSensorActivityMonitor monitor).ThrowOnFailure();
        monitor.Start();
        Console.WriteLine($"{DateTime.Now:HH:mm:ss.fff} sensor activity monitor started for {seconds} s");
        Thread.Sleep(TimeSpan.FromSeconds(seconds));
        monitor.Stop();
        PInvoke.MFShutdown();
        return 0;
    }
}

[GeneratedComClass]
internal sealed unsafe partial class ReportPrinter : IMFSensorActivitiesReportCallback
{
    private const int NameCapacity = 512;

    public void OnActivitiesReport(IMFSensorActivitiesReport sensorActivitiesReport)
    {
        try
        {
            sensorActivitiesReport.GetCount(out uint count);
            Console.WriteLine($"{DateTime.Now:HH:mm:ss.fff} report with {count} devices");
            for (uint index = 0; index < count; index++)
            {
                sensorActivitiesReport.GetActivityReport(index, out IMFSensorActivityReport report);
                PrintDevice(report);
            }
        }
        catch (Exception exception)
        {
            Console.WriteLine($"report failed: {exception.Message}");
        }
    }

    private static void PrintDevice(IMFSensorActivityReport report)
    {
        Console.WriteLine($"  device {ReadName(report, true)} | {ReadName(report, false)}");
        report.GetProcessCount(out uint processes);
        for (uint index = 0; index < processes; index++)
        {
            report.GetProcessActivity(index, out IMFSensorProcessActivity activity);
            activity.GetProcessId(out uint processId);
            BOOL streaming;
            activity.GetStreamingState(&streaming);
            MFSensorDeviceMode mode;
            activity.GetStreamingMode(&mode);
            Console.WriteLine($"    pid {processId} ({ProcessName(processId)}) streaming {(bool)streaming} mode {mode}");
        }
    }

    private static string ReadName(IMFSensorActivityReport report, bool friendly)
    {
        char* buffer = stackalloc char[NameCapacity];
        uint written = 0;
        try
        {
            if (friendly)
            {
                report.GetFriendlyName(new PWSTR(buffer), NameCapacity, out written);
            }
            else
            {
                report.GetSymbolicLink(new PWSTR(buffer), NameCapacity, out written);
            }
            return new string(buffer).TrimEnd('\0');
        }
        catch (Exception exception)
        {
            return $"<{exception.Message}>";
        }
    }

    private static string ProcessName(uint processId)
    {
        try
        {
            return Process.GetProcessById((int)processId).ProcessName;
        }
        catch (ArgumentException)
        {
            return "?";
        }
    }
}
