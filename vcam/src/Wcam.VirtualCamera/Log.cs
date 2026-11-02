using Windows.Win32;

namespace Wcam.VirtualCamera;

internal static class Log
{
    private static readonly Lock Gate = new();
    private static readonly string FilePath = Path.Combine(
        Environment.GetFolderPath(Environment.SpecialFolder.CommonApplicationData),
        "WCam",
        "logs",
        "vcam.log");

    public static void Info(string message) => Write("info", message);

    public static void Error(string message, Exception exception) => Write("error", $"{message}: {exception}");

    private static void Write(string level, string message)
    {
        string line = $"{DateTime.UtcNow:O} pid={Environment.ProcessId} tid={Environment.CurrentManagedThreadId} {level} {message}";
        PInvoke.OutputDebugString($"WCam {line}\n");
        try
        {
            lock (Gate)
            {
                File.AppendAllText(FilePath, line + Environment.NewLine);
            }
        }
        catch (IOException)
        {
        }
        catch (UnauthorizedAccessException)
        {
        }
    }
}
