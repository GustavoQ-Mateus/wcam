using System.Security.Principal;
using System.Text;
using Microsoft.Win32;
using Microsoft.Win32.SafeHandles;
using Windows.Win32;
using Windows.Win32.Devices.DeviceAndDriverInstallation;
using Windows.Win32.Devices.Properties;
using Windows.Win32.Foundation;
using Windows.Win32.Media.MediaFoundation;
using Windows.Win32.System.Registry;

namespace Wcam.VirtualCamera;

internal static unsafe class CameraOwner
{
    public const string RegistryValueName = "WcamOwnerSid";
    private const string RegistrySubkey = "Wcam";
    private const uint OwnerPropertyId = 2;
    private const int PropertyBufferCapacity = 512;
    private static readonly Guid OwnerPropertySet = new("A606633F-DC4C-439E-8251-88D603D749A4");

    public static void Record(IMFVirtualCamera camera)
    {
        string sid = WindowsIdentity.GetCurrent().User!.Value;
        byte[] data = Encoding.Unicode.GetBytes(sid + '\0');
        Attempt("AddProperty", () => AddProperty(camera, data));
        Attempt("AddRegistryEntry", () => AddRegistryEntry(camera, data, null));
        Attempt("AddRegistryEntry with subkey", () => AddRegistryEntry(camera, data, RegistrySubkey));
        Log.Info($"camera owner to record: {sid}");
    }

    public static void TryRead(IMFAttributes activateAttributes)
    {
        string? symbolicLink = TryGetSymbolicLink(activateAttributes);
        if (symbolicLink is null)
        {
            Log.Info("camera owner unknown: activate has no symbolic link");
            return;
        }
        Log.Info($"camera owner lookup for {symbolicLink}");
        Attempt("read property", () => Log.Info($"property owner: {ReadProperty(symbolicLink) ?? "missing"}"));
        Attempt("read registry", () => Log.Info($"registry owner: {ReadRegistry(symbolicLink) ?? "missing"}"));
    }

    private static void Attempt(string name, Action action)
    {
        try
        {
            action();
            Log.Info($"{name}: ok");
        }
        catch (Exception exception)
        {
            Log.Info($"{name}: failed 0x{exception.HResult:X8} {exception.Message}");
        }
    }

    private static void AddProperty(IMFVirtualCamera camera, byte[] data)
    {
        var key = new DEVPROPKEY { fmtid = OwnerPropertySet, pid = OwnerPropertyId };
        camera.AddProperty(&key, DEVPROPTYPE.DEVPROP_TYPE_STRING, in data[0], (uint)data.Length);
    }

    private static void AddRegistryEntry(IMFVirtualCamera camera, byte[] data, string? subkey)
    {
        fixed (char* name = RegistryValueName)
        fixed (char* subkeyName = subkey)
        {
            camera.AddRegistryEntry(name, subkeyName, (uint)REG_VALUE_TYPE.REG_SZ, in data[0], (uint)data.Length);
        }
    }

    private static string? ReadProperty(string symbolicLink)
    {
        var key = new DEVPROPKEY { fmtid = OwnerPropertySet, pid = OwnerPropertyId };
        Span<byte> buffer = stackalloc byte[PropertyBufferCapacity];
        uint size = PropertyBufferCapacity;
        CONFIGRET status = PInvoke.CM_Get_Device_Interface_Property(symbolicLink, in key, out _, buffer, ref size, 0);
        if (status != CONFIGRET.CR_SUCCESS)
        {
            Log.Info($"CM_Get_Device_Interface_Property returned {status}");
            return null;
        }
        return Encoding.Unicode.GetString(buffer[..(int)size]).TrimEnd('\0');
    }

    private static string? ReadRegistry(string symbolicLink)
    {
        CONFIGRET status = PInvoke.CM_Open_Device_Interface_Key(
            symbolicLink,
            (uint)REG_SAM_FLAGS.KEY_READ,
            PInvoke.RegDisposition_OpenExisting,
            out SafeRegistryHandle handle,
            0);
        if (status != CONFIGRET.CR_SUCCESS)
        {
            Log.Info($"CM_Open_Device_Interface_Key returned {status}");
            return null;
        }
        using RegistryKey key = RegistryKey.FromHandle(handle);
        using RegistryKey? subkey = key.OpenSubKey(RegistrySubkey);
        return (key.GetValue(RegistryValueName) ?? subkey?.GetValue(RegistryValueName)) as string;
    }

    private static string? TryGetSymbolicLink(IMFAttributes attributes)
    {
        Guid key = PInvoke.MF_DEVSOURCE_ATTRIBUTE_SOURCE_TYPE_VIDCAP_SYMBOLIC_LINK;
        PWSTR value;
        try
        {
            attributes.GetAllocatedString(&key, &value, out _);
        }
        catch (Exception exception) when (exception.HResult < 0)
        {
            return null;
        }
        try
        {
            return value.ToString();
        }
        finally
        {
            PInvoke.CoTaskMemFree(value);
        }
    }
}
