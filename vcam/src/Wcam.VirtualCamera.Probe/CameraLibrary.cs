using System.Runtime.InteropServices;
using Microsoft.Win32;

namespace Wcam.VirtualCamera.Probe;

internal sealed unsafe class CameraLibrary
{
    private const string InprocServerKey = "InprocServer32";

    private readonly delegate* unmanaged<int> _start;
    private readonly delegate* unmanaged<int> _stop;
    private readonly delegate* unmanaged<byte*, uint, uint, uint, int> _publish;

    public CameraLibrary(string path)
    {
        nint library = NativeLibrary.Load(path);
        _start = (delegate* unmanaged<int>)NativeLibrary.GetExport(library, "WcamCameraStart");
        _stop = (delegate* unmanaged<int>)NativeLibrary.GetExport(library, "WcamCameraStop");
        _publish = (delegate* unmanaged<byte*, uint, uint, uint, int>)NativeLibrary.GetExport(library, "WcamFramePublish");
    }

    public int Start() => _start();

    public int Stop() => _stop();

    public int Publish(ReadOnlySpan<byte> frame)
    {
        fixed (byte* data = frame)
        {
            return _publish(data, (uint)frame.Length, VideoFormat.Width, VideoFormat.Height);
        }
    }

    public static string? RegisteredPath()
    {
        using RegistryKey? key = Registry.LocalMachine.OpenSubKey($@"{CameraIdentity.SourceClassKey}\{InprocServerKey}");
        return key?.GetValue(null) as string;
    }
}
