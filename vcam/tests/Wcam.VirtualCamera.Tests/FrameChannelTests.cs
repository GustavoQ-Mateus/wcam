using System.Runtime.InteropServices;

namespace Wcam.VirtualCamera.Tests;

public sealed unsafe class FrameChannelTests : IDisposable
{
    private const long Timestamp = 638_000_000_000_000_000;

    private readonly byte* _memory = (byte*)NativeMemory.AllocZeroed((nuint)FrameChannel.Capacity);
    private readonly byte[] _destination = new byte[VideoFormat.FrameSize];

    public void Dispose() => NativeMemory.Free(_memory);

    [Fact]
    public void TryReadLatest_WithUninitializedHeader_ReturnsFalse()
    {
        Assert.False(new FrameChannel(_memory).TryReadLatest(_destination, FrameFormat.Default, out _, out _));
    }

    [Fact]
    public void TryReadLatest_BeforeFirstPublish_ReturnsFalse()
    {
        FrameChannel channel = InitializedChannel();
        Assert.False(channel.TryReadLatest(_destination, FrameFormat.Default, out _, out _));
    }

    [Fact]
    public void TryReadLatest_AfterPublish_ReturnsSameBytesIndexAndTimestamp()
    {
        FrameChannel channel = InitializedChannel();
        byte[] frame = Frame(seed: 3);
        channel.Publish(frame, Timestamp);
        Assert.True(channel.TryReadLatest(_destination, FrameFormat.Default, out ulong frameIndex, out long timestamp));
        Assert.Equal(frame, _destination);
        Assert.Equal(1UL, frameIndex);
        Assert.Equal(Timestamp, timestamp);
    }

    [Fact]
    public void TryReadLatest_AfterSeveralPublishes_ReturnsMostRecentFrame()
    {
        FrameChannel channel = InitializedChannel();
        for (int seed = 1; seed <= 5; seed++)
        {
            channel.Publish(Frame(seed), Timestamp + seed);
        }
        Assert.True(channel.TryReadLatest(_destination, FrameFormat.Default, out ulong frameIndex, out _));
        Assert.Equal(Frame(5), _destination);
        Assert.Equal(5UL, frameIndex);
    }

    [Fact]
    public void TryReadLatest_WhileLatestSlotIsBeingWritten_ReturnsFalse()
    {
        FrameChannel channel = InitializedChannel();
        channel.Publish(Frame(1), Timestamp);
        ulong* latestSlotSequence = (ulong*)(_memory + FrameChannel.SlotSequenceOffset) + 1;
        (*latestSlotSequence)++;
        Assert.False(channel.TryReadLatest(_destination, FrameFormat.Default, out _, out _));
    }

    [Fact]
    public void TryReadLatest_WithOtherFrameSize_ReturnsFalse()
    {
        FrameChannel channel = InitializedChannel();
        channel.Publish(Frame(1), Timestamp);
        *(uint*)(_memory + FrameChannel.WidthOffset) = 1280;
        Assert.False(channel.TryReadLatest(_destination, FrameFormat.Default, out _, out _));
    }

    [Fact]
    public void Publish_FrameWithEdgeValues_KeepsBytesUnchanged()
    {
        FrameChannel channel = InitializedChannel();
        byte[] frame = new byte[VideoFormat.FrameSize];
        byte[] edges = [0, 16, 128, 235, 255];
        for (int index = 0; index < frame.Length; index++)
        {
            frame[index] = edges[index % edges.Length];
        }
        channel.Publish(frame, Timestamp);
        Assert.True(channel.TryReadLatest(_destination, FrameFormat.Default, out _, out _));
        Assert.Equal(frame, _destination);
    }

    [Fact]
    public void Capacity_HoldsThreeFramesOfLargestFormat()
    {
        Assert.Equal(FrameChannel.HeaderSize + 3L * 3840 * 2160 * 3 / 2, FrameChannel.Capacity);
    }

    [Fact]
    public void TryReadFormat_AfterInitialize_ReturnsInitialFormat()
    {
        FrameChannel channel = InitializedChannel();
        Assert.True(channel.TryReadFormat(out FrameFormat format));
        Assert.Equal(FrameFormat.Default, format);
    }

    [Fact]
    public void TryReadLatest_AfterSetFormatAndPublish_ReturnsFrameInNewFormat()
    {
        FrameChannel channel = InitializedChannel();
        channel.Publish(Frame(1), Timestamp);
        channel.SetFormat(Largest);
        byte[] frame = Frame(2, Largest);
        channel.Publish(frame, Timestamp);
        byte[] destination = new byte[Largest.FrameSize];
        Assert.True(channel.TryReadLatest(destination, Largest, out _, out _));
        Assert.Equal(frame, destination);
    }

    [Fact]
    public void TryReadLatest_AfterSetFormatBeforePublish_ReturnsFalse()
    {
        FrameChannel channel = InitializedChannel();
        channel.Publish(Frame(1), Timestamp);
        channel.SetFormat(Largest);
        Assert.False(channel.TryReadLatest(new byte[Largest.FrameSize], Largest, out _, out _));
    }

    [Fact]
    public void TryReadLatest_ExpectingPreviousFormat_ReturnsFalse()
    {
        FrameChannel channel = InitializedChannel();
        channel.SetFormat(Largest);
        channel.Publish(Frame(1, Largest), Timestamp);
        Assert.False(channel.TryReadLatest(_destination, FrameFormat.Default, out _, out _));
    }

    [Fact]
    public void TryReadFormat_WhileFormatIsBeingWritten_ReturnsFalse()
    {
        FrameChannel channel = InitializedChannel();
        (*(ulong*)(_memory + FrameChannel.FormatSequenceOffset))++;
        Assert.False(channel.TryReadFormat(out _));
    }

    [Fact]
    public void Publish_FrameOfOtherFormat_IsRejected()
    {
        FrameChannel channel = InitializedChannel();
        Assert.Throws<ArgumentException>(() => channel.Publish(Frame(1, Largest), Timestamp));
    }

    private static FrameFormat Largest => new(3840, 2160, 30);

    private FrameChannel InitializedChannel()
    {
        var channel = new FrameChannel(_memory);
        channel.InitializeHeader(FrameFormat.Default);
        return channel;
    }

    private static byte[] Frame(int seed) => Frame(seed, FrameFormat.Default);

    private static byte[] Frame(int seed, FrameFormat format)
    {
        byte[] frame = new byte[format.FrameSize];
        new Random(seed).NextBytes(frame);
        return frame;
    }
}
