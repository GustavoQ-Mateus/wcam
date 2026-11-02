using Windows.Win32;
using Windows.Win32.Foundation;
using Windows.Win32.Media.MediaFoundation;

namespace Wcam.VirtualCamera;

internal static unsafe class AttributeLog
{
    public static void Write(string owner, IMFAttributes attributes)
    {
        attributes.GetCount(out uint count);
        Log.Info($"{owner} has {count} attributes");
        for (uint index = 0; index < count; index++)
        {
            Guid key;
            attributes.GetItemByIndex(index, &key, null);
            Log.Info($"{owner} attribute {key:B} = {Describe(attributes, key)}");
        }
    }

    private static string Describe(IMFAttributes attributes, Guid key)
    {
        MF_ATTRIBUTE_TYPE type;
        attributes.GetItemType(&key, &type);
        switch (type)
        {
            case MF_ATTRIBUTE_TYPE.MF_ATTRIBUTE_UINT32:
                attributes.GetUINT32(&key, out uint number);
                return $"uint32 {number}";
            case MF_ATTRIBUTE_TYPE.MF_ATTRIBUTE_UINT64:
                attributes.GetUINT64(&key, out ulong wide);
                return $"uint64 {wide}";
            case MF_ATTRIBUTE_TYPE.MF_ATTRIBUTE_GUID:
                Guid value;
                attributes.GetGUID(&key, &value);
                return $"guid {value:B}";
            case MF_ATTRIBUTE_TYPE.MF_ATTRIBUTE_STRING:
                PWSTR text;
                attributes.GetAllocatedString(&key, &text, out _);
                string result = $"string {text}";
                PInvoke.CoTaskMemFree(text);
                return result;
            default:
                return type.ToString();
        }
    }
}
