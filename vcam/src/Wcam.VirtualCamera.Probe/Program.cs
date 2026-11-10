namespace Wcam.VirtualCamera.Probe;

internal static class Program
{
    private const string DllOption = "--dll";
    private const string PatternOption = "--pattern";
    private const string PatchesOption = "--patches";
    private const string MovingOption = "--moving";
    private const string FormatOption = "--format";
    private const string ModeOption = "--mode";
    private const string ControlOption = "--control";
    private const string FormatCommand = "format";
    private const string ModeCommand = "mode";
    private const string StopCommand = "stop";
    private const int ControlPollMilliseconds = 100;
    private const string Usage =
        "usage: Wcam.VirtualCamera.Probe [--dll <path>] [--pattern | --patches | --moving] [--format <w>x<h>@<fps>] " +
        "[--mode <n>] [--control <file with lines 'format <w>x<h>@<fps>', 'mode <n>', 'stop'>]";

    private static int Main(string[] args)
    {
        if (!TryParse(args, out ProbeOptions options))
        {
            Console.Error.WriteLine(Usage);
            return 2;
        }
        string? dllPath = options.DllPath ?? CameraLibrary.RegisteredPath();
        if (dllPath is null)
        {
            Console.Error.WriteLine("the WCam media source is not registered; run scripts/register-vcam.ps1 or pass --dll");
            return 1;
        }
        Console.WriteLine($"loading {dllPath}");
        var library = new CameraLibrary(dllPath);
        Console.WriteLine($"WcamFormatSet {options.Format}: 0x{library.SetFormat(options.Format):X8}");
        Console.WriteLine($"WcamSpikeFormatChangeMode {options.Mode}: 0x{library.SetChangeMode(options.Mode):X8}");
        int status = library.Start();
        Console.WriteLine($"WcamCameraStart: 0x{status:X8}");
        if (status < 0)
        {
            return 1;
        }
        using (PatternPublisher? publisher = options.Render is null ? null : new PatternPublisher(library, options.Render, options.Format))
        {
            if (options.ControlPath is null)
            {
                Console.WriteLine("camera \"WCam\" is running; press Enter to stop");
                Console.ReadLine();
            }
            else
            {
                Console.WriteLine($"camera \"WCam\" is running; commands from {options.ControlPath}");
                FollowControlFile(options.ControlPath, library, publisher);
            }
        }
        status = library.Stop();
        Console.WriteLine($"WcamCameraStop: 0x{status:X8}");
        return status < 0 ? 1 : 0;
    }

    private static void FollowControlFile(string path, CameraLibrary library, PatternPublisher? publisher)
    {
        int handled = 0;
        while (true)
        {
            string[] lines = ReadControlLines(path);
            for (; handled < lines.Length; handled++)
            {
                if (!Apply(lines[handled].Trim(), library, publisher))
                {
                    return;
                }
            }
            Thread.Sleep(ControlPollMilliseconds);
        }
    }

    private static string[] ReadControlLines(string path)
    {
        try
        {
            return File.Exists(path) ? File.ReadAllLines(path) : [];
        }
        catch (IOException)
        {
            return [];
        }
    }

    private static bool Apply(string command, CameraLibrary library, PatternPublisher? publisher)
    {
        string[] parts = command.Split(' ', 2, StringSplitOptions.RemoveEmptyEntries);
        if (parts.Length == 0)
        {
            return true;
        }
        if (parts[0] == StopCommand)
        {
            return false;
        }
        if (parts.Length == 2 && parts[0] == FormatCommand && TryParseFormat(parts[1], out FrameFormat format))
        {
            int status = library.SetFormat(format);
            if (status >= 0 && publisher is not null)
            {
                publisher.Format = format;
            }
            Console.WriteLine($"{DateTime.UtcNow:O} WcamFormatSet {format}: 0x{status:X8}");
            return true;
        }
        if (parts.Length == 2 && parts[0] == ModeCommand && uint.TryParse(parts[1], out uint mode))
        {
            Console.WriteLine($"{DateTime.UtcNow:O} WcamSpikeFormatChangeMode {mode}: 0x{library.SetChangeMode(mode):X8}");
            return true;
        }
        Console.WriteLine($"unknown command: {command}");
        return true;
    }

    private static bool TryParse(string[] args, out ProbeOptions options)
    {
        options = new ProbeOptions();
        for (int index = 0; index < args.Length; index++)
        {
            bool hasValue = index + 1 < args.Length;
            switch (args[index])
            {
                case PatternOption when options.Render is null:
                    options.Render = Fixed(new TestPattern().Render);
                    break;
                case PatchesOption when options.Render is null:
                    options.Render = Fixed((frame, _) => PatchGrid.Render(frame));
                    break;
                case MovingOption when options.Render is null:
                    options.Render = FormatPattern.Render;
                    break;
                case DllOption when hasValue:
                    options.DllPath = Path.GetFullPath(args[++index]);
                    break;
                case FormatOption when hasValue && TryParseFormat(args[++index], out FrameFormat format):
                    options.Format = format;
                    break;
                case ModeOption when hasValue && uint.TryParse(args[++index], out uint mode):
                    options.Mode = mode;
                    break;
                case ControlOption when hasValue:
                    options.ControlPath = Path.GetFullPath(args[++index]);
                    break;
                default:
                    return false;
            }
        }
        return true;
    }

    private static FrameRenderer Fixed(Action<Span<byte>, long> render) =>
        (frame, format, frameNumber) =>
        {
            if (format == FrameFormat.Default)
            {
                render(frame, frameNumber);
                return;
            }
            FormatPattern.Render(frame, format, frameNumber);
        };

    private static bool TryParseFormat(string text, out FrameFormat format)
    {
        format = default;
        string[] sizeAndRate = text.Split('@');
        string[] size = sizeAndRate[0].Split('x');
        if (sizeAndRate.Length != 2
            || size.Length != 2
            || !int.TryParse(size[0], out int width)
            || !int.TryParse(size[1], out int height)
            || !int.TryParse(sizeAndRate[1], out int framesPerSecond))
        {
            return false;
        }
        format = new FrameFormat(width, height, framesPerSecond);
        return true;
    }

    private sealed class ProbeOptions
    {
        public string? DllPath { get; set; }

        public FrameRenderer? Render { get; set; }

        public FrameFormat Format { get; set; } = FrameFormat.Default;

        public uint Mode { get; set; }

        public string? ControlPath { get; set; }
    }
}
