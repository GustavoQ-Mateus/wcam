using Windows.Win32.Media.MediaFoundation;

namespace Wcam.VirtualCamera;

internal static unsafe class AttributeExtensions
{
    public static void SetUInt32(this IMFAttributes attributes, Guid key, uint value) => attributes.SetUINT32(&key, value);

    public static void SetUInt64(this IMFAttributes attributes, Guid key, ulong value) => attributes.SetUINT64(&key, value);

    public static void SetUInt64(this IMFAttributes attributes, Guid key, uint high, uint low) =>
        attributes.SetUINT64(&key, (ulong)high << 32 | low);

    public static void SetGuid(this IMFAttributes attributes, Guid key, Guid value) => attributes.SetGUID(&key, &value);

    public static void SetObject(this IMFAttributes attributes, Guid key, object value) => attributes.SetUnknown(&key, value);
}
