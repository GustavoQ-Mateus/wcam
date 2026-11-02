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

    public static MappedFrameChannel CreateFile(string path)
    {
        Directory.CreateDirectory(Path.GetDirectoryName(path)!);
        var stream = new FileStream(path, FileMode.OpenOrCreate, FileAccess.ReadWrite, FileShare.ReadWrite | FileShare.Delete);
        MemoryMappedFile file = MemoryMappedFile.CreateFromFile(
            stream,
            null,
            FrameChannel.Capacity,
            MemoryMappedFileAccess.ReadWrite,
            HandleInheritability.None,
            leaveOpen: false);
        var mapped = new MappedFrameChannel(file, MemoryMappedFileAccess.ReadWrite);
        mapped.Channel.InitializeHeader();
        return mapped;
    }

    public static MappedFrameChannel OpenFile(string path)
    {
        var stream = new FileStream(path, FileMode.Open, FileAccess.Read, FileShare.ReadWrite | FileShare.Delete);
        MemoryMappedFile file = MemoryMappedFile.CreateFromFile(
            stream,
            null,
            0,
            MemoryMappedFileAccess.Read,
            HandleInheritability.None,
            leaveOpen: false);
        return new MappedFrameChannel(file, MemoryMappedFileAccess.Read);
    }

    public static MappedFrameChannel OpenSection(string name, bool writable)
    {
        MemoryMappedFileRights rights = writable ? MemoryMappedFileRights.ReadWrite : MemoryMappedFileRights.Read;
        MemoryMappedFileAccess access = writable ? MemoryMappedFileAccess.ReadWrite : MemoryMappedFileAccess.Read;
        return new MappedFrameChannel(MemoryMappedFile.OpenExisting(name, rights), access);
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
