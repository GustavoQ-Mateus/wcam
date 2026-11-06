using System.Diagnostics;
using System.Runtime.InteropServices.Marshalling;
using Windows.Win32;
using Windows.Win32.Foundation;
using Windows.Win32.Media.KernelStreaming;
using Windows.Win32.Media.MediaFoundation;
using Windows.Win32.System.Com.StructuredStorage;
using MediaEvent = Windows.Win32.Media.MediaFoundation.__MIDL___MIDL_itf_mfobjects_0000_0013_0001;

namespace Wcam.VirtualCamera;

[GeneratedComClass]
internal sealed unsafe partial class MediaStream : IMFMediaStream2, IKsControl
{
    public const uint StreamId = 0;
    private static readonly Guid VideoCapturePinCategory = new("FB6C4281-0353-11D1-905F-0000C0CC16BA");

    private readonly Lock _lock = new();
    private readonly MediaSource _source;
    private readonly IMFMediaEventQueue _events;
    private readonly Queue<object?> _pendingTokens = new();
    private readonly SessionFrameReader _reader = new();
    private readonly DeliveryStats _stats = new();
    private FramePacer? _pacer;
    private MF_STREAM_STATE _state = MF_STREAM_STATE.MF_STREAM_STATE_STOPPED;
    private bool _isShutdown;

    public MediaStream(MediaSource source)
    {
        _source = source;
        PInvoke.MFCreateEventQueue(out _events).ThrowOnFailure();
        Attributes = CreateAttributes();
        Descriptor = CreateDescriptor(Attributes);
    }

    public IMFAttributes Attributes { get; }

    public IMFStreamDescriptor Descriptor { get; }

    public void Start(in PROPVARIANT startPosition)
    {
        lock (_lock)
        {
            ThrowIfShutdown();
            BeginDelivery();
        }
        QueueEvent(MediaEvent.MEStreamStarted, in startPosition);
    }

    public void Stop()
    {
        EndDelivery(MF_STREAM_STATE.MF_STREAM_STATE_STOPPED);
        PROPVARIANT empty = default;
        QueueEvent(MediaEvent.MEStreamStopped, in empty);
    }

    public void Shutdown()
    {
        FramePacer? pacer;
        lock (_lock)
        {
            if (_isShutdown)
            {
                return;
            }
            _isShutdown = true;
            pacer = TakePacer();
        }
        pacer?.Dispose();
        _reader.Dispose();
        _events.Shutdown();
    }

    public void GetEvent(MEDIA_EVENT_GENERATOR_GET_EVENT_FLAGS dwFlags, out IMFMediaEvent ppEvent) =>
        _events.GetEvent((uint)dwFlags, out ppEvent);

    public void BeginGetEvent(IMFAsyncCallback pCallback, object punkState) => _events.BeginGetEvent(pCallback, punkState);

    public void EndGetEvent(IMFAsyncResult pResult, out IMFMediaEvent ppEvent) => _events.EndGetEvent(pResult, out ppEvent);

    public void QueueEvent(uint met, Guid* guidExtendedType, HRESULT hrStatus, in PROPVARIANT pvValue) =>
        _events.QueueEventParamVar(met, guidExtendedType, hrStatus, in pvValue);

    public void GetMediaSource(out IMFMediaSource ppMediaSource)
    {
        lock (_lock)
        {
            ThrowIfShutdown();
        }
        ppMediaSource = _source;
    }

    public void GetStreamDescriptor(out IMFStreamDescriptor ppStreamDescriptor)
    {
        lock (_lock)
        {
            ThrowIfShutdown();
        }
        ppStreamDescriptor = Descriptor;
    }

    public void RequestSample(object pToken)
    {
        lock (_lock)
        {
            ThrowIfShutdown();
            if (_state != MF_STREAM_STATE.MF_STREAM_STATE_RUNNING)
            {
                throw ComObjects.Error(HRESULT.MF_E_INVALIDREQUEST);
            }
            _pendingTokens.Enqueue(pToken);
            _stats.CountRequest();
        }
    }

    public void SetStreamState(MF_STREAM_STATE value)
    {
        Log.Info($"stream state set to {value}");
        if (value != MF_STREAM_STATE.MF_STREAM_STATE_RUNNING)
        {
            EndDelivery(value);
            return;
        }
        lock (_lock)
        {
            ThrowIfShutdown();
            BeginDelivery();
        }
    }

    public void GetStreamState(MF_STREAM_STATE* value)
    {
        lock (_lock)
        {
            ThrowIfShutdown();
            *value = _state;
        }
    }

    public HRESULT KsProperty(KSIDENTIFIER* Property, uint PropertyLength, void* PropertyData, uint DataLength, out uint BytesReturned) =>
        KernelStreaming.NotSupported(out BytesReturned);

    public HRESULT KsMethod(KSIDENTIFIER* Method, uint MethodLength, void* MethodData, uint DataLength, out uint BytesReturned) =>
        KernelStreaming.NotSupported(out BytesReturned);

    public HRESULT KsEvent(KSIDENTIFIER* Event, uint EventLength, void* EventData, uint DataLength, out uint BytesReturned) =>
        KernelStreaming.NotSupported(out BytesReturned);

    private void BeginDelivery()
    {
        _state = MF_STREAM_STATE.MF_STREAM_STATE_RUNNING;
        _pacer ??= new FramePacer(DeliverPendingSample);
    }

    private void EndDelivery(MF_STREAM_STATE state)
    {
        FramePacer? pacer;
        lock (_lock)
        {
            ThrowIfShutdown();
            _state = state;
            _pendingTokens.Clear();
            pacer = TakePacer();
        }
        pacer?.Dispose();
    }

    private FramePacer? TakePacer()
    {
        FramePacer? pacer = _pacer;
        _pacer = null;
        return pacer;
    }

    private void DeliverPendingSample()
    {
        object? token;
        lock (_lock)
        {
            if (_isShutdown || _state != MF_STREAM_STATE.MF_STREAM_STATE_RUNNING || _pendingTokens.Count == 0)
            {
                _stats.CountIdleTick();
                return;
            }
            token = _pendingTokens.Dequeue();
        }
        long buildStarted = Stopwatch.GetTimestamp();
        IMFSample sample = CreateSample(token);
        _stats.CountDelivery(buildStarted);
        try
        {
            Guid none = Guid.Empty;
            _events.QueueEventParamUnk((uint)MediaEvent.MEMediaSample, &none, HRESULT.S_OK, sample);
        }
        finally
        {
            ComObjects.Release(sample);
        }
    }

    private IMFSample CreateSample(object? token)
    {
        PInvoke.MFCreateMemoryBuffer(VideoFormat.FrameSize, out IMFMediaBuffer buffer).ThrowOnFailure();
        try
        {
            FillBuffer(buffer);
            PInvoke.MFCreateSample(out IMFSample sample).ThrowOnFailure();
            sample.AddBuffer(buffer);
            sample.SetSampleTime(PInvoke.MFGetSystemTime());
            sample.SetSampleDuration(VideoFormat.FrameDurationTicks);
            if (token is not null)
            {
                sample.SetObject(PInvoke.MFSampleExtension_Token, token);
            }
            return sample;
        }
        finally
        {
            ComObjects.Release(buffer);
        }
    }

    private void FillBuffer(IMFMediaBuffer buffer)
    {
        byte* data;
        buffer.Lock(&data, null, null);
        try
        {
            _reader.Fill(new Span<byte>(data, VideoFormat.FrameSize));
        }
        finally
        {
            buffer.Unlock();
        }
        buffer.SetCurrentLength(VideoFormat.FrameSize);
    }

    private void QueueEvent(MediaEvent type, in PROPVARIANT value)
    {
        Guid none = Guid.Empty;
        _events.QueueEventParamVar((uint)type, &none, HRESULT.S_OK, in value);
    }

    private void ThrowIfShutdown()
    {
        if (_isShutdown)
        {
            throw ComObjects.Error(HRESULT.MF_E_SHUTDOWN);
        }
    }

    private static IMFAttributes CreateAttributes()
    {
        PInvoke.MFCreateAttributes(out IMFAttributes attributes, 4).ThrowOnFailure();
        attributes.SetGuid(PInvoke.MF_DEVICESTREAM_STREAM_CATEGORY, VideoCapturePinCategory);
        attributes.SetUInt32(PInvoke.MF_DEVICESTREAM_STREAM_ID, StreamId);
        attributes.SetUInt32(PInvoke.MF_DEVICESTREAM_FRAMESERVER_SHARED, 1);
        attributes.SetUInt32(
            PInvoke.MF_DEVICESTREAM_ATTRIBUTE_FRAMESOURCE_TYPES,
            (uint)MFFrameSourceTypes.MFFrameSourceTypes_Color);
        return attributes;
    }

    private static IMFStreamDescriptor CreateDescriptor(IMFAttributes attributes)
    {
        IMFMediaType mediaType = CreateMediaType();
        PInvoke.MFCreateStreamDescriptor(StreamId, [mediaType], out IMFStreamDescriptor descriptor).ThrowOnFailure();
        descriptor.GetMediaTypeHandler(out IMFMediaTypeHandler handler);
        handler.SetCurrentMediaType(mediaType);
        attributes.CopyAllItems(descriptor);
        return descriptor;
    }

    private static IMFMediaType CreateMediaType()
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
        return mediaType;
    }
}
