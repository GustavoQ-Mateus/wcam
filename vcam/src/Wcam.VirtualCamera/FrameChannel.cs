using System.Runtime.CompilerServices;

namespace Wcam.VirtualCamera;

internal sealed unsafe class FrameChannel
{
    public const uint Magic = 0x4D414357;
    public const uint LayoutVersion = 1;
    public const int SlotCount = 3;
    public const int HeaderSize = 64;
    public const int MagicOffset = 0;
    public const int VersionOffset = 4;
    public const int WidthOffset = 8;
    public const int HeightOffset = 12;
    public const int FourCcOffset = 16;
    public const int SlotCountOffset = 20;
    public const int FrameIndexOffset = 24;
    public const int TimestampOffset = 32;
    public const int SlotSequenceOffset = 40;
    public const long Capacity = HeaderSize + (long)SlotCount * VideoFormat.FrameSize;

    private readonly byte* _base;

    public FrameChannel(byte* basePointer)
    {
        _base = basePointer;
    }

    public bool HasValidHeader =>
        Volatile.Read(ref Field<uint>(MagicOffset)) == Magic
        && Field<uint>(VersionOffset) == LayoutVersion
        && Field<uint>(WidthOffset) == VideoFormat.Width
        && Field<uint>(HeightOffset) == VideoFormat.Height
        && Field<uint>(FourCcOffset) == VideoFormat.Nv12FourCc
        && Field<uint>(SlotCountOffset) == SlotCount;

    public void InitializeHeader()
    {
        new Span<byte>(_base, HeaderSize).Clear();
        Field<uint>(VersionOffset) = LayoutVersion;
        Field<uint>(WidthOffset) = VideoFormat.Width;
        Field<uint>(HeightOffset) = VideoFormat.Height;
        Field<uint>(FourCcOffset) = VideoFormat.Nv12FourCc;
        Field<uint>(SlotCountOffset) = SlotCount;
        Volatile.Write(ref Field<uint>(MagicOffset), Magic);
    }

    public ulong Publish(ReadOnlySpan<byte> frame, long timestampTicks)
    {
        ulong frameIndex = Field<ulong>(FrameIndexOffset) + 1;
        ref ulong sequence = ref SlotSequence(frameIndex);
        Volatile.Write(ref sequence, sequence + 1);
        Interlocked.MemoryBarrier();
        frame.CopyTo(Slot(frameIndex));
        Volatile.Write(ref sequence, sequence + 1);
        Volatile.Write(ref Field<long>(TimestampOffset), timestampTicks);
        Volatile.Write(ref Field<ulong>(FrameIndexOffset), frameIndex);
        return frameIndex;
    }

    public bool TryReadLatest(Span<byte> destination, out ulong frameIndex, out long timestampTicks)
    {
        frameIndex = 0;
        timestampTicks = 0;
        if (!HasValidHeader)
        {
            return false;
        }
        ulong latest = Volatile.Read(ref Field<ulong>(FrameIndexOffset));
        if (latest == 0)
        {
            return false;
        }
        ref ulong sequence = ref SlotSequence(latest);
        ulong before = Volatile.Read(ref sequence);
        if (before % 2 != 0)
        {
            return false;
        }
        Slot(latest).CopyTo(destination);
        Interlocked.MemoryBarrier();
        if (Volatile.Read(ref sequence) != before)
        {
            return false;
        }
        frameIndex = latest;
        timestampTicks = Volatile.Read(ref Field<long>(TimestampOffset));
        return true;
    }

    private ref T Field<T>(int offset) where T : unmanaged => ref Unsafe.AsRef<T>(_base + offset);

    private ref ulong SlotSequence(ulong frameIndex) =>
        ref Field<ulong>(SlotSequenceOffset + SlotIndex(frameIndex) * sizeof(ulong));

    private Span<byte> Slot(ulong frameIndex) =>
        new(_base + HeaderSize + (long)SlotIndex(frameIndex) * VideoFormat.FrameSize, VideoFormat.FrameSize);

    private static int SlotIndex(ulong frameIndex) => (int)(frameIndex % SlotCount);
}
