using System.Runtime.InteropServices;
using System.Runtime.InteropServices.Marshalling;
using Windows.Win32.Foundation;

namespace Wcam.VirtualCamera;

internal static unsafe class ComObjects
{
    public static HRESULT QueryInterface<T>(T instance, Guid* interfaceId, out void* result) where T : class
    {
        void* unknown = ComInterfaceMarshaller<T>.ConvertToUnmanaged(instance);
        try
        {
            HRESULT status = (HRESULT)Marshal.QueryInterface((nint)unknown, in *interfaceId, out nint pointer);
            result = (void*)pointer;
            return status;
        }
        finally
        {
            ComInterfaceMarshaller<T>.Free(unknown);
        }
    }

    public static COMException Error(HRESULT status) => new(null, status.Value);

    public static void Release(object instance)
    {
        if (instance is ComObject wrapper)
        {
            wrapper.FinalRelease();
        }
    }
}
