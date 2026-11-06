using Windows.Win32;
using Windows.Win32.Media.MediaFoundation;

namespace Wcam.VirtualCamera;

internal static class CaptureMediaType
{
    public const MFNominalRange NominalRange = MFNominalRange.MFNominalRange_16_235;
    public const MFVideoTransferMatrix YuvMatrix = MFVideoTransferMatrix.MFVideoTransferMatrix_BT709;
    public const MFVideoPrimaries Primaries = MFVideoPrimaries.MFVideoPrimaries_BT709;
    public const MFVideoTransferFunction TransferFunction = MFVideoTransferFunction.MFVideoTransFunc_709;

    public static IMFMediaType Create()
    {
        PInvoke.MFCreateMediaType(out IMFMediaType mediaType).ThrowOnFailure();
        mediaType.SetGuid(PInvoke.MF_MT_MAJOR_TYPE, PInvoke.MFMediaType_Video);
        mediaType.SetGuid(PInvoke.MF_MT_SUBTYPE, PInvoke.MFVideoFormat_NV12);
        mediaType.SetUInt64(PInvoke.MF_MT_FRAME_SIZE, VideoFormat.Width, VideoFormat.Height);
        mediaType.SetUInt64(PInvoke.MF_MT_FRAME_RATE, VideoFormat.FramesPerSecond, 1);
        mediaType.SetUInt64(PInvoke.MF_MT_PIXEL_ASPECT_RATIO, 1, 1);
        mediaType.SetUInt32(PInvoke.MF_MT_INTERLACE_MODE, (uint)MFVideoInterlaceMode.MFVideoInterlace_Progressive);
        mediaType.SetUInt32(PInvoke.MF_MT_ALL_SAMPLES_INDEPENDENT, 1);
        mediaType.SetUInt32(PInvoke.MF_MT_FIXED_SIZE_SAMPLES, 1);
        mediaType.SetUInt32(PInvoke.MF_MT_SAMPLE_SIZE, VideoFormat.FrameSize);
        mediaType.SetUInt32(PInvoke.MF_MT_DEFAULT_STRIDE, VideoFormat.Width);
        SetColor(mediaType);
        return mediaType;
    }

    private static void SetColor(IMFMediaType mediaType)
    {
        mediaType.SetUInt32(PInvoke.MF_MT_VIDEO_NOMINAL_RANGE, (uint)NominalRange);
        mediaType.SetUInt32(PInvoke.MF_MT_YUV_MATRIX, (uint)YuvMatrix);
        mediaType.SetUInt32(PInvoke.MF_MT_VIDEO_PRIMARIES, (uint)Primaries);
        mediaType.SetUInt32(PInvoke.MF_MT_TRANSFER_FUNCTION, (uint)TransferFunction);
    }
}
