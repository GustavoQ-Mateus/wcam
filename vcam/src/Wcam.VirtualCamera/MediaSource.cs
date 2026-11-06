using System.Runtime.InteropServices.Marshalling;
using Windows.Win32;
using Windows.Win32.Foundation;
using Windows.Win32.Media.KernelStreaming;
using Windows.Win32.Media.MediaFoundation;
using Windows.Win32.System.Com.StructuredStorage;
using MediaEvent = Windows.Win32.Media.MediaFoundation.__MIDL___MIDL_itf_mfobjects_0000_0013_0001;

namespace Wcam.VirtualCamera;

[GeneratedComClass]
internal sealed unsafe partial class MediaSource : IMFMediaSourceEx, IMFGetService, IKsControl
{
    private readonly Lock _lock = new();
    private readonly IMFMediaEventQueue _events;
    private readonly IMFAttributes _attributes;
    private readonly IMFPresentationDescriptor _presentation;
    private readonly MediaStream _stream;
    private bool _streamStarted;
    private bool _isShutdown;

    public MediaSource()
    {
        PInvoke.MFCreateEventQueue(out _events).ThrowOnFailure();
        PInvoke.MFCreateAttributes(out _attributes, 1).ThrowOnFailure();
        _stream = new MediaStream(this);
        PInvoke.MFCreatePresentationDescriptor([_stream.Descriptor], out _presentation).ThrowOnFailure();
        _presentation.SelectStream(0);
        Log.Info("media source created");
    }

    public void GetEvent(MEDIA_EVENT_GENERATOR_GET_EVENT_FLAGS dwFlags, out IMFMediaEvent ppEvent) =>
        _events.GetEvent((uint)dwFlags, out ppEvent);

    public void BeginGetEvent(IMFAsyncCallback pCallback, object punkState) => _events.BeginGetEvent(pCallback, punkState);

    public void EndGetEvent(IMFAsyncResult pResult, out IMFMediaEvent ppEvent) => _events.EndGetEvent(pResult, out ppEvent);

    public void QueueEvent(uint met, Guid* guidExtendedType, HRESULT hrStatus, in PROPVARIANT pvValue) =>
        _events.QueueEventParamVar(met, guidExtendedType, hrStatus, in pvValue);

    public void GetCharacteristics(out uint pdwCharacteristics)
    {
        lock (_lock)
        {
            ThrowIfShutdown();
        }
        pdwCharacteristics = (uint)MFMEDIASOURCE_CHARACTERISTICS.MFMEDIASOURCE_IS_LIVE;
    }

    public void CreatePresentationDescriptor(out IMFPresentationDescriptor ppPresentationDescriptor)
    {
        lock (_lock)
        {
            ThrowIfShutdown();
        }
        _presentation.Clone(out ppPresentationDescriptor);
    }

    public void Start(IMFPresentationDescriptor pPresentationDescriptor, Guid* pguidTimeFormat, in PROPVARIANT pvarStartPosition)
    {
        try
        {
            lock (_lock)
            {
                ThrowIfShutdown();
                if (pguidTimeFormat != null && *pguidTimeFormat != Guid.Empty)
                {
                    throw ComObjects.Error(HRESULT.MF_E_UNSUPPORTED_TIME_FORMAT);
                }
                StartStream(IsStreamSelected(pPresentationDescriptor), in pvarStartPosition);
                QueueEvent(MediaEvent.MESourceStarted, in pvarStartPosition);
            }
            Log.Info("media source started");
        }
        catch (Exception exception)
        {
            Log.Error("media source start failed", exception);
            throw;
        }
    }

    public void Stop()
    {
        lock (_lock)
        {
            ThrowIfShutdown();
            if (_streamStarted)
            {
                _stream.Stop();
            }
            PROPVARIANT empty = default;
            QueueEvent(MediaEvent.MESourceStopped, in empty);
        }
        Log.Info("media source stopped");
    }

    public void Pause() => throw ComObjects.Error(HRESULT.MF_E_INVALID_STATE_TRANSITION);

    public void Shutdown()
    {
        lock (_lock)
        {
            if (_isShutdown)
            {
                return;
            }
            _isShutdown = true;
        }
        _stream.Shutdown();
        _events.Shutdown();
        Log.Info("media source shut down");
    }

    public void GetSourceAttributes(out IMFAttributes ppAttributes)
    {
        lock (_lock)
        {
            ThrowIfShutdown();
        }
        ppAttributes = _attributes;
    }

    public void GetStreamAttributes(uint dwStreamIdentifier, out IMFAttributes ppAttributes)
    {
        lock (_lock)
        {
            ThrowIfShutdown();
        }
        if (dwStreamIdentifier != MediaStream.StreamId)
        {
            throw ComObjects.Error(HRESULT.MF_E_INVALIDSTREAMNUMBER);
        }
        ppAttributes = _stream.Attributes;
    }

    public void SetD3DManager(object pManager)
    {
    }

    public HRESULT GetService(Guid* guidService, Guid* riid, out void* ppvObject)
    {
        ppvObject = null;
        return HRESULT.MF_E_UNSUPPORTED_SERVICE;
    }

    public HRESULT KsProperty(KSIDENTIFIER* Property, uint PropertyLength, void* PropertyData, uint DataLength, out uint BytesReturned) =>
        KernelStreaming.NotSupported(out BytesReturned);

    public HRESULT KsMethod(KSIDENTIFIER* Method, uint MethodLength, void* MethodData, uint DataLength, out uint BytesReturned) =>
        KernelStreaming.NotSupported(out BytesReturned);

    public HRESULT KsEvent(KSIDENTIFIER* Event, uint EventLength, void* EventData, uint DataLength, out uint BytesReturned) =>
        KernelStreaming.NotSupported(out BytesReturned);

    private void StartStream(bool selected, in PROPVARIANT startPosition)
    {
        if (!selected)
        {
            if (_streamStarted)
            {
                _stream.Stop();
            }
            return;
        }
        Guid none = Guid.Empty;
        MediaEvent streamEvent = _streamStarted ? MediaEvent.MEUpdatedStream : MediaEvent.MENewStream;
        _events.QueueEventParamUnk((uint)streamEvent, &none, HRESULT.S_OK, _stream);
        _stream.Start(in startPosition);
        _streamStarted = true;
    }

    private static bool IsStreamSelected(IMFPresentationDescriptor presentation)
    {
        presentation.GetStreamDescriptorCount(out uint count);
        bool selected = false;
        for (uint index = 0; index < count; index++)
        {
            BOOL isSelected;
            presentation.GetStreamDescriptorByIndex(index, &isSelected, out IMFStreamDescriptor descriptor);
            descriptor.GetStreamIdentifier(out uint streamId);
            if (streamId != MediaStream.StreamId)
            {
                throw ComObjects.Error(HRESULT.MF_E_INVALIDSTREAMNUMBER);
            }
            selected |= isSelected;
        }
        return selected;
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
}
