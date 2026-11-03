using System.ComponentModel;
using System.Security.Principal;
using Microsoft.Win32.SafeHandles;
using Windows.Win32;
using Windows.Win32.Foundation;
using Windows.Win32.Security;
using Windows.Win32.System.Memory;

namespace Wcam.VirtualCamera;

internal sealed unsafe class PublishedFrameSection : IDisposable
{
    private static readonly HANDLE PagingFile = new(-1);

    private readonly SafeFileHandle _section;
    private readonly MappedFrameChannel _writer;

    private PublishedFrameSection(SafeFileHandle section, MappedFrameChannel writer)
    {
        _section = section;
        _writer = writer;
    }

    public static PublishedFrameSection Create(string name)
    {
        string ownerSid = WindowsIdentity.GetCurrent().User!.Value;
        SafeFileHandle section = CreateSection(name, FrameTransport.AccessDescriptor(ownerSid));
        try
        {
            MappedFrameChannel writer = MappedFrameChannel.OpenSection(name, writable: true);
            writer.Channel.InitializeHeader();
            Log.Info($"created {name} for {ownerSid}");
            return new PublishedFrameSection(section, writer);
        }
        catch
        {
            section.Dispose();
            throw;
        }
    }

    public void Publish(ReadOnlySpan<byte> frame) => _writer.Channel.Publish(frame, DateTime.UtcNow.Ticks);

    public void Dispose()
    {
        _writer.Dispose();
        _section.Dispose();
    }

    private static SafeFileHandle CreateSection(string name, string accessDescriptor)
    {
        PSECURITY_DESCRIPTOR descriptor;
        if (!PInvoke.ConvertStringSecurityDescriptorToSecurityDescriptor(accessDescriptor, PInvoke.SDDL_REVISION_1, out descriptor))
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
            fixed (char* sectionName = name)
            {
                HANDLE section = PInvoke.CreateFileMapping(
                    PagingFile,
                    &attributes,
                    PAGE_PROTECTION_FLAGS.PAGE_READWRITE,
                    (uint)(FrameChannel.Capacity >> 32),
                    (uint)FrameChannel.Capacity,
                    sectionName);
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
