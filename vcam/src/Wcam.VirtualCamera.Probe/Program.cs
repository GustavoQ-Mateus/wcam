namespace Wcam.VirtualCamera.Probe;

internal static class Program
{
    private const string DllOption = "--dll";
    private const string PatternOption = "--pattern";
    private const string PatchesOption = "--patches";
    private const string Usage = "usage: Wcam.VirtualCamera.Probe [--dll <path>] [--pattern | --patches]";

    private static int Main(string[] args)
    {
        if (!TryParse(args, out string? dllPath, out FrameRenderer? render))
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
        using (PatternPublisher? publisher = render is null ? null : new PatternPublisher(library, render))
        {
            Console.WriteLine("camera \"WCam\" is running; press Enter to stop");
            Console.ReadLine();
        }
        status = library.Stop();
        Console.WriteLine($"WcamCameraStop: 0x{status:X8}");
        return status < 0 ? 1 : 0;
    }

    private static bool TryParse(string[] args, out string? dllPath, out FrameRenderer? render)
    {
        dllPath = null;
        render = null;
        for (int index = 0; index < args.Length; index++)
        {
            switch (args[index])
            {
                case PatternOption when render is null:
                    render = new TestPattern().Render;
                    break;
                case PatchesOption when render is null:
                    render = (frame, _) => PatchGrid.Render(frame);
                    break;
                case DllOption when index + 1 < args.Length:
                    dllPath = Path.GetFullPath(args[++index]);
                    break;
                default:
                    return false;
            }
        }
        return true;
    }
}
