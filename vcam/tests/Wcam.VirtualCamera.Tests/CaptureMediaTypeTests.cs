using Windows.Win32;
using Windows.Win32.Media.MediaFoundation;

namespace Wcam.VirtualCamera.Tests;

public unsafe class CaptureMediaTypeTests
{
    [Fact]
    public void Create_DeclaresLimitedNominalRange()
    {
        Assert.Equal((uint)MFNominalRange.MFNominalRange_16_235, ReadUInt32(PInvoke.MF_MT_VIDEO_NOMINAL_RANGE));
    }

    [Fact]
    public void Create_DeclaresChosenYuvMatrix()
    {
        Assert.Equal((uint)CaptureMediaType.YuvMatrix, ReadUInt32(PInvoke.MF_MT_YUV_MATRIX));
    }

    [Fact]
    public void Create_DeclaresBt709Primaries()
    {
        Assert.Equal((uint)MFVideoPrimaries.MFVideoPrimaries_BT709, ReadUInt32(PInvoke.MF_MT_VIDEO_PRIMARIES));
    }

    [Fact]
    public void Create_DeclaresBt709TransferFunction()
    {
        Assert.Equal((uint)MFVideoTransferFunction.MFVideoTransFunc_709, ReadUInt32(PInvoke.MF_MT_TRANSFER_FUNCTION));
    }

    [Fact]
    public void Create_KeepsFullHdNv12At30Fps()
    {
        Assert.Equal((ulong)VideoFormat.Width << 32 | VideoFormat.Height, ReadUInt64(PInvoke.MF_MT_FRAME_SIZE));
        Assert.Equal((ulong)VideoFormat.FramesPerSecond << 32 | 1, ReadUInt64(PInvoke.MF_MT_FRAME_RATE));
        Assert.Equal(PInvoke.MFVideoFormat_NV12, ReadGuid(PInvoke.MF_MT_SUBTYPE));
    }

    [Fact]
    public void Create_For2160p60_DeclaresThatSizeRateAndSampleSize()
    {
        var format = new FrameFormat(3840, 2160, 60);
        IMFMediaType mediaType = CaptureMediaType.Create(format);
        Guid frameSize = PInvoke.MF_MT_FRAME_SIZE;
        Guid frameRate = PInvoke.MF_MT_FRAME_RATE;
        Guid sampleSize = PInvoke.MF_MT_SAMPLE_SIZE;
        mediaType.GetUINT64(&frameSize, out ulong size);
        mediaType.GetUINT64(&frameRate, out ulong rate);
        mediaType.GetUINT32(&sampleSize, out uint bytes);
        Assert.Equal(3840UL << 32 | 2160, size);
        Assert.Equal(60UL << 32 | 1, rate);
        Assert.Equal((uint)format.FrameSize, bytes);
    }

    private static uint ReadUInt32(Guid key)
    {
        IMFMediaType mediaType = CaptureMediaType.Create(FrameFormat.Default);
        mediaType.GetUINT32(&key, out uint value);
        return value;
    }

    private static ulong ReadUInt64(Guid key)
    {
        IMFMediaType mediaType = CaptureMediaType.Create(FrameFormat.Default);
        mediaType.GetUINT64(&key, out ulong value);
        return value;
    }

    private static Guid ReadGuid(Guid key)
    {
        IMFMediaType mediaType = CaptureMediaType.Create(FrameFormat.Default);
        Guid value;
        mediaType.GetGUID(&key, &value);
        return value;
    }
}
