using System.Runtime.InteropServices;
using Microsoft.Win32;

namespace Wcam.VirtualCamera.Probe;

internal sealed unsafe class CameraLibrary
{
    private const string InprocServerKey = "InprocServer32";
    private const int FormatStateFields = 9;

    private readonly delegate* unmanaged<int> _start;
    private readonly delegate* unmanaged<int> _stop;
    private readonly delegate* unmanaged<byte*, uint, uint, uint, int> _publish;
    private readonly delegate* unmanaged<uint, uint, uint, int> _setFormat;
    private readonly delegate* unmanaged<uint*, int> _getFormat;

    public CameraLibrary(string path)
    {
        nint library = NativeLibrary.Load(path);
        _start = (delegate* unmanaged<int>)NativeLibrary.GetExport(library, "WcamCameraStart");
        _stop = (delegate* unmanaged<int>)NativeLibrary.GetExport(library, "WcamCameraStop");
        _publish = (delegate* unmanaged<byte*, uint, uint, uint, int>)NativeLibrary.GetExport(library, "WcamFramePublish");
        _setFormat = (delegate* unmanaged<uint, uint, uint, int>)NativeLibrary.GetExport(library, "WcamFormatSet");
        _getFormat = (delegate* unmanaged<uint*, int>)NativeLibrary.GetExport(library, "WcamFormatGet");
    }

    public int Start() => _start();

    public int Stop() => _stop();

    public int SetFormat(FrameFormat format) => _setFormat((uint)format.Width, (uint)format.Height, (uint)format.FramesPerSecond);

    public FrameFormat? AnnouncedFormat()
    {
        uint* state = stackalloc uint[FormatStateFields];
        if (_getFormat(state) != 0)
        {
            return null;
        }
        return new FrameFormat((int)state[0], (int)state[1], (int)state[2]);
    }

    public string FormatState()
    {
        uint* state = stackalloc uint[FormatStateFields];
        int status = _getFormat(state);
        return $"WcamFormatGet 0x{status:X8}: announced {state[0]}x{state[1]}@{state[2]}, "
            + $"requested {state[3]}x{state[4]}@{state[5]}, pending {state[6]}, streaming apps {state[7]}, running {state[8]}";
    }

    public int Publish(ReadOnlySpan<byte> frame, FrameFormat format)
    {
        fixed (byte* data = frame)
        {
            return _publish(data, (uint)frame.Length, (uint)format.Width, (uint)format.Height);
        }
    }

    public static string? RegisteredPath()
    {
        using RegistryKey? key = Registry.LocalMachine.OpenSubKey($@"{CameraIdentity.SourceClassKey}\{InprocServerKey}");
        return key?.GetValue(null) as string;
    }
}
