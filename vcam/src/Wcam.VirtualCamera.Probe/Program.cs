namespace Wcam.VirtualCamera.Probe;

internal static class Program
{
    private const string DllOption = "--dll";
    private const string WriteOption = "--write";
    private const string Usage = "usage: Wcam.VirtualCamera.Probe [--dll <path>] [--write file|section]";

    private static int Main(string[] args)
    {
        if (!TryParse(args, out string? dllPath, out ProbeTransport? transport))
        {
            Console.Error.WriteLine(Usage);
            return 2;
        }
        dllPath ??= CameraLibrary.RegisteredPath();
        if (dllPath is null)
        {
            Console.Error.WriteLine("the WCam media source is not registered; run scripts/register-vcam.ps1 or pass --dll");
            return 1;
        }
        Console.WriteLine($"loading {dllPath}");
        var library = new CameraLibrary(dllPath);
        int status = library.Start();
        Console.WriteLine($"WcamCameraStart: 0x{status:X8}");
        if (status < 0)
        {
            return 1;
        }
        using (ProbeWriter? writer = transport is null ? null : new ProbeWriter(transport.Value))
        {
            Console.WriteLine("camera \"WCam\" is running; press Enter to stop");
            Console.ReadLine();
        }
        status = library.Stop();
        Console.WriteLine($"WcamCameraStop: 0x{status:X8}");
        return status < 0 ? 1 : 0;
    }

    private static bool TryParse(string[] args, out string? dllPath, out ProbeTransport? transport)
    {
        dllPath = null;
        transport = null;
        for (int index = 0; index < args.Length; index += 2)
        {
            if (index + 1 >= args.Length)
            {
                return false;
            }
            string value = args[index + 1];
            switch (args[index])
            {
                case DllOption:
                    dllPath = Path.GetFullPath(value);
                    break;
                case WriteOption when Enum.TryParse(value, ignoreCase: true, out ProbeTransport parsed):
                    transport = parsed;
                    break;
                default:
                    return false;
            }
        }
        return true;
    }
}
