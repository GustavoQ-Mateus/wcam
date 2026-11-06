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

    private static uint ReadUInt32(Guid key)
    {
        IMFMediaType mediaType = CaptureMediaType.Create();
        mediaType.GetUINT32(&key, out uint value);
        return value;
    }

    private static ulong ReadUInt64(Guid key)
    {
        IMFMediaType mediaType = CaptureMediaType.Create();
        mediaType.GetUINT64(&key, out ulong value);
        return value;
    }

    private static Guid ReadGuid(Guid key)
    {
        IMFMediaType mediaType = CaptureMediaType.Create();
        Guid value;
        mediaType.GetGUID(&key, &value);
        return value;
    }
}
