using System.ComponentModel;
using System.IO.MemoryMappedFiles;
using System.Security.Principal;
using System.Text;
using Microsoft.Win32.SafeHandles;
using Windows.Win32;
using Windows.Win32.Foundation;
using Windows.Win32.Security;
using Windows.Win32.System.Memory;

namespace Wcam.VirtualCamera;

internal static unsafe class SessionChannelSpike
{
    private const string ObjectName = "WCamOwnerSpike";
    private const int Capacity = 4096;
    private static readonly HANDLE PagingFile = new(-1);
    private static SafeFileHandle? _section;

    public static void Create()
    {
        try
        {
            string sid = WindowsIdentity.GetCurrent().User!.Value;
            _section = CreateSection($@"Local\{ObjectName}", $"D:(A;;GA;;;SY)(A;;GA;;;{sid})(A;;GR;;;LS)");
            using MemoryMappedFile file = MemoryMappedFile.OpenExisting($@"Local\{ObjectName}", MemoryMappedFileRights.ReadWrite);
            using MemoryMappedViewAccessor view = file.CreateViewAccessor(0, Capacity);
            byte[] marker = Encoding.UTF8.GetBytes($"owner {sid} pid {Environment.ProcessId}\0");
            view.WriteArray(0, marker, 0, marker.Length);
            PInvoke.ProcessIdToSessionId(PInvoke.GetCurrentProcessId(), out uint session);
            Log.Info($"spike: created Local\\{ObjectName} in session {session} for {sid}");
        }
        catch (Exception exception)
        {
            Log.Error("spike: could not create session section", exception);
        }
    }

    public static void Probe()
    {
        PInvoke.ProcessIdToSessionId(PInvoke.GetCurrentProcessId(), out uint ownSession);
        uint consoleSession = PInvoke.WTSGetActiveConsoleSessionId();
        string name = $@"Session\{consoleSession}\{ObjectName}";
        Log.Info($"spike: source in session {ownSession}, console session {consoleSession}, opening {name}");
        try
        {
            using MemoryMappedFile file = MemoryMappedFile.OpenExisting(name, MemoryMappedFileRights.Read);
            using MemoryMappedViewAccessor view = file.CreateViewAccessor(0, Capacity, MemoryMappedFileAccess.Read);
            byte[] marker = new byte[256];
            view.ReadArray(0, marker, 0, marker.Length);
            Log.Info($"spike: read marker \"{Encoding.UTF8.GetString(marker).TrimEnd('\0')}\"");
        }
        catch (Exception exception)
        {
            Log.Info($"spike: read open failed {exception.GetType().Name} 0x{exception.HResult:X8} {exception.Message}");
        }
        try
        {
            using MemoryMappedFile file = MemoryMappedFile.OpenExisting(name, MemoryMappedFileRights.ReadWrite);
            Log.Info("spike: write open succeeded (unexpected)");
        }
        catch (Exception exception)
        {
            Log.Info($"spike: write open refused as expected {exception.GetType().Name} 0x{exception.HResult:X8}");
        }
    }

    private static SafeFileHandle CreateSection(string name, string descriptorText)
    {
        PSECURITY_DESCRIPTOR descriptor;
        if (!PInvoke.ConvertStringSecurityDescriptorToSecurityDescriptor(descriptorText, PInvoke.SDDL_REVISION_1, out descriptor))
        {
            throw new Win32Exception();
        }
        try
        {
            var attributes = new SECURITY_ATTRIBUTES
            {
                nLength = (uint)sizeof(SECURITY_ATTRIBUTES),
                lpSecurityDescriptor = descriptor,
            };
            fixed (char* objectName = name)
            {
                HANDLE section = PInvoke.CreateFileMapping(
                    PagingFile,
                    &attributes,
                    PAGE_PROTECTION_FLAGS.PAGE_READWRITE,
                    0,
                    Capacity,
                    objectName);
                if (section.IsNull)
                {
                    throw new Win32Exception();
                }
                return new SafeFileHandle(section, ownsHandle: true);
            }
        }
        finally
        {
            PInvoke.LocalFree((HLOCAL)descriptor.Value);
        }
    }
}
