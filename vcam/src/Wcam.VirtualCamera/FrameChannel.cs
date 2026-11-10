using System.Runtime.CompilerServices;

namespace Wcam.VirtualCamera;

internal sealed unsafe class FrameChannel
{
    public const uint Magic = 0x4D414357;
    public const uint LayoutVersion = 2;
    public const int SlotCount = 3;
    public const int HeaderSize = 128;
    public const int MagicOffset = 0;
    public const int VersionOffset = 4;
    public const int WidthOffset = 8;
    public const int HeightOffset = 12;
    public const int FourCcOffset = 16;
    public const int SlotCountOffset = 20;
    public const int FrameIndexOffset = 24;
    public const int TimestampOffset = 32;
    public const int SlotSequenceOffset = 40;
    public const int FramesPerSecondOffset = 64;
    public const int FormatSequenceOffset = 72;
    public const long Capacity = HeaderSize + (long)SlotCount * FrameFormat.LargestFrameSize;

    private readonly byte* _base;

    public FrameChannel(byte* basePointer)
    {
        _base = basePointer;
    }

    public bool HasValidHeader =>
        Volatile.Read(ref Field<uint>(MagicOffset)) == Magic
        && Field<uint>(VersionOffset) == LayoutVersion
        && Field<uint>(FourCcOffset) == VideoFormat.Nv12FourCc
        && Field<uint>(SlotCountOffset) == SlotCount;

    public FrameFormat Format => new(Field<int>(WidthOffset), Field<int>(HeightOffset), Field<int>(FramesPerSecondOffset));

    public void InitializeHeader(FrameFormat format)
    {
        new Span<byte>(_base, HeaderSize).Clear();
        Field<uint>(VersionOffset) = LayoutVersion;
        WriteFormat(format);
        Field<uint>(FourCcOffset) = VideoFormat.Nv12FourCc;
        Field<uint>(SlotCountOffset) = SlotCount;
        Volatile.Write(ref Field<uint>(MagicOffset), Magic);
    }

    public void SetFormat(FrameFormat format)
    {
        ref ulong sequence = ref Field<ulong>(FormatSequenceOffset);
        Volatile.Write(ref sequence, sequence + 1);
        Interlocked.MemoryBarrier();
        Volatile.Write(ref Field<ulong>(FrameIndexOffset), 0UL);
        WriteFormat(format);
        Volatile.Write(ref sequence, sequence + 1);
    }

    public ulong Publish(ReadOnlySpan<byte> frame, long timestampTicks)
    {
        if (frame.Length != Format.FrameSize)
        {
            throw new ArgumentException($"frame of {frame.Length} bytes does not match {Format}", nameof(frame));
        }
        ulong frameIndex = Field<ulong>(FrameIndexOffset) + 1;
        ref ulong sequence = ref SlotSequence(frameIndex);
        Volatile.Write(ref sequence, sequence + 1);
        Interlocked.MemoryBarrier();
        frame.CopyTo(Slot(frameIndex, frame.Length));
        Volatile.Write(ref sequence, sequence + 1);
        Volatile.Write(ref Field<long>(TimestampOffset), timestampTicks);
        Volatile.Write(ref Field<ulong>(FrameIndexOffset), frameIndex);
        return frameIndex;
    }

    public bool TryReadFormat(out FrameFormat format)
    {
        format = default;
        if (!HasValidHeader)
        {
            return false;
        }
        ulong before = Volatile.Read(ref Field<ulong>(FormatSequenceOffset));
        if (before % 2 != 0)
        {
            return false;
        }
        format = Format;
        Interlocked.MemoryBarrier();
        return Volatile.Read(ref Field<ulong>(FormatSequenceOffset)) == before && format.IsSupported;
    }

    public bool TryReadLatest(Span<byte> destination, FrameFormat expected, out ulong frameIndex, out long timestampTicks)
    {
        frameIndex = 0;
        timestampTicks = 0;
        ulong formatBefore = Volatile.Read(ref Field<ulong>(FormatSequenceOffset));
        if (!TryReadFormat(out FrameFormat format) || format != expected || destination.Length != expected.FrameSize)
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
        Slot(latest, expected.FrameSize).CopyTo(destination);
        Interlocked.MemoryBarrier();
        if (Volatile.Read(ref sequence) != before || Volatile.Read(ref Field<ulong>(FormatSequenceOffset)) != formatBefore)
        {
            return false;
        }
        frameIndex = latest;
        timestampTicks = Volatile.Read(ref Field<long>(TimestampOffset));
        return true;
    }

    private void WriteFormat(FrameFormat format)
    {
        Field<int>(WidthOffset) = format.Width;
        Field<int>(HeightOffset) = format.Height;
        Field<int>(FramesPerSecondOffset) = format.FramesPerSecond;
    }

    private ref T Field<T>(int offset) where T : unmanaged => ref Unsafe.AsRef<T>(_base + offset);

    private ref ulong SlotSequence(ulong frameIndex) =>
        ref Field<ulong>(SlotSequenceOffset + SlotIndex(frameIndex) * sizeof(ulong));

    private Span<byte> Slot(ulong frameIndex, int length) =>
        new(_base + HeaderSize + (long)SlotIndex(frameIndex) * FrameFormat.LargestFrameSize, length);

    private static int SlotIndex(ulong frameIndex) => (int)(frameIndex % SlotCount);
}
