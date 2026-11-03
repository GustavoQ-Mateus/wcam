using System.IO.MemoryMappedFiles;

namespace Wcam.VirtualCamera;

internal sealed unsafe class MappedFrameChannel : IDisposable
{
    private readonly MemoryMappedFile _file;
    private readonly MemoryMappedViewAccessor _view;
    private byte* _pointer;

    private MappedFrameChannel(MemoryMappedFile file, MemoryMappedFileAccess access)
    {
        _file = file;
        _view = file.CreateViewAccessor(0, FrameChannel.Capacity, access);
        _view.SafeMemoryMappedViewHandle.AcquirePointer(ref _pointer);
        Channel = new FrameChannel(_pointer + _view.PointerOffset);
    }

    public FrameChannel Channel { get; }

    public static MappedFrameChannel OpenSection(string name, bool writable)
    {
        MemoryMappedFileRights rights = writable ? MemoryMappedFileRights.ReadWrite : MemoryMappedFileRights.Read;
        MemoryMappedFileAccess access = writable ? MemoryMappedFileAccess.ReadWrite : MemoryMappedFileAccess.Read;
        MemoryMappedFile file = MemoryMappedFile.OpenExisting(name, rights);
        try
        {
            return new MappedFrameChannel(file, access);
        }
        catch
        {
            file.Dispose();
            throw;
        }
    }

    public void Dispose()
    {
        if (_pointer != null)
        {
            _view.SafeMemoryMappedViewHandle.ReleasePointer();
            _pointer = null;
        }
        _view.Dispose();
        _file.Dispose();
    }
}
