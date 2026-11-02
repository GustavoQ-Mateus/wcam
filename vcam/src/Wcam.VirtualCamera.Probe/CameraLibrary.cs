using System.Runtime.InteropServices;
using Microsoft.Win32;

namespace Wcam.VirtualCamera.Probe;

internal sealed unsafe class CameraLibrary
{
    private const string InprocServerKey = "InprocServer32";

    private readonly delegate* unmanaged<int> _start;
    private readonly delegate* unmanaged<int> _stop;

    public CameraLibrary(string path)
    {
        nint library = NativeLibrary.Load(path);
        _start = (delegate* unmanaged<int>)NativeLibrary.GetExport(library, "WcamCameraStart");
        _stop = (delegate* unmanaged<int>)NativeLibrary.GetExport(library, "WcamCameraStop");
    }

    public int Start() => _start();

    public int Stop() => _stop();

    public static string? RegisteredPath()
    {
        using RegistryKey? key = Registry.LocalMachine.OpenSubKey($@"{CameraIdentity.SourceClassKey}\{InprocServerKey}");
        return key?.GetValue(null) as string;
    }
}
