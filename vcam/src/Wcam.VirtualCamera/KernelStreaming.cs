using Windows.Win32.Foundation;

namespace Wcam.VirtualCamera;

internal static class KernelStreaming
{
    private static readonly HRESULT SetNotFound = (HRESULT)unchecked((int)(0x80070000 | (uint)WIN32_ERROR.ERROR_SET_NOT_FOUND));

    public static HRESULT NotSupported(out uint bytesReturned)
    {
        bytesReturned = 0;
        return SetNotFound;
    }
}
