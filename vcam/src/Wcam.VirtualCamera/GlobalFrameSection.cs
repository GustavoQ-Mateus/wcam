using System.ComponentModel;
using Microsoft.Win32.SafeHandles;
using Windows.Win32;
using Windows.Win32.Foundation;
using Windows.Win32.Security;
using Windows.Win32.System.Memory;

namespace Wcam.VirtualCamera;

internal sealed unsafe class GlobalFrameSection : IDisposable
{
    private const string AccessDescriptor = "D:(A;;GA;;;SY)(A;;GA;;;LS)(A;;GA;;;BA)(A;;GRGW;;;IU)";
    private static readonly HANDLE PagingFile = new(-1);

    private readonly SafeFileHandle _section;

    private GlobalFrameSection(SafeFileHandle section, MappedFrameChannel reader)
    {
        _section = section;
        Reader = reader;
    }

    public MappedFrameChannel Reader { get; }

    public static GlobalFrameSection Create()
    {
        SafeFileHandle section = CreateSection();
        try
        {
            return new GlobalFrameSection(section, MappedFrameChannel.OpenSection(FrameTransport.SectionName, writable: false));
        }
        catch
        {
            section.Dispose();
            throw;
        }
    }

    public void Dispose()
    {
        Reader.Dispose();
        _section.Dispose();
    }

    private static SafeFileHandle CreateSection()
    {
        PSECURITY_DESCRIPTOR descriptor;
        if (!PInvoke.ConvertStringSecurityDescriptorToSecurityDescriptor(AccessDescriptor, PInvoke.SDDL_REVISION_1, out descriptor))
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
            fixed (char* name = FrameTransport.SectionName)
            {
                HANDLE section = PInvoke.CreateFileMapping(
                    PagingFile,
                    &attributes,
                    PAGE_PROTECTION_FLAGS.PAGE_READWRITE,
                    (uint)(FrameChannel.Capacity >> 32),
                    (uint)FrameChannel.Capacity,
                    name);
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
