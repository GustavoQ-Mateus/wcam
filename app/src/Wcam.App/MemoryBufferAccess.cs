using System.Runtime.InteropServices;
using System.Runtime.InteropServices.Marshalling;
using Windows.Foundation;

namespace Wcam.App;

[GeneratedComInterface]
[Guid("5b0d3235-4dba-4d44-865e-8f1d0e4fd04d")]
internal unsafe partial interface IMemoryBufferByteAccess
{
    void GetBuffer(out byte* value, out uint capacity);
}

internal static unsafe class MemoryBufferAccess
{
    private static readonly StrategyBasedComWrappers Wrappers = new();

    public static byte* Pointer(IMemoryBufferReference reference)
    {
        nint unknown = WinRT.MarshalInterface<IMemoryBufferReference>.FromManaged(reference);
        try
        {
            var access = (IMemoryBufferByteAccess)Wrappers.GetOrCreateObjectForComInstance(unknown, CreateObjectFlags.None);
            access.GetBuffer(out byte* value, out _);
            return value;
        }
        finally
        {
            Marshal.Release(unknown);
        }
    }
}
