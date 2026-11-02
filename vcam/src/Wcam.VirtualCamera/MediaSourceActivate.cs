using System.Runtime.InteropServices.Marshalling;
using Windows.Win32;
using Windows.Win32.Foundation;
using Windows.Win32.Media.MediaFoundation;
using Windows.Win32.System.Com.StructuredStorage;

namespace Wcam.VirtualCamera;

[GeneratedComClass]
internal sealed unsafe partial class MediaSourceActivate : IMFActivate
{
    private readonly Lock _lock = new();
    private readonly IMFAttributes _attributes;
    private MediaSource? _source;

    public MediaSourceActivate()
    {
        PInvoke.MFCreateAttributes(out _attributes, 1).ThrowOnFailure();
    }

    public HRESULT ActivateObject(Guid* riid, out void* ppv)
    {
        ppv = null;
        try
        {
            MediaSource source;
            lock (_lock)
            {
                if (_source is null)
                {
                    AttributeLog.Write("activate", _attributes);
                    CameraOwner.TryRead(_attributes);
                    SessionChannelSpike.Probe();
                }
                source = _source ??= new MediaSource();
            }
            return ComObjects.QueryInterface<IMFMediaSourceEx>(source, riid, out ppv);
        }
        catch (Exception exception)
        {
            Log.Error("media source activation failed", exception);
            return (HRESULT)exception.HResult;
        }
    }

    public void ShutdownObject()
    {
        MediaSource? source;
        lock (_lock)
        {
            source = _source;
            _source = null;
        }
        source?.Shutdown();
    }

    public void DetachObject()
    {
        lock (_lock)
        {
            _source = null;
        }
    }

    public void GetItem(Guid* guidKey, PROPVARIANT_unmanaged* pValue) => _attributes.GetItem(guidKey, pValue);

    public void GetItemType(Guid* guidKey, MF_ATTRIBUTE_TYPE* pType) => _attributes.GetItemType(guidKey, pType);

    public void CompareItem(Guid* guidKey, in PROPVARIANT Value, BOOL* pbResult) =>
        _attributes.CompareItem(guidKey, in Value, pbResult);

    public void Compare(IMFAttributes pTheirs, MF_ATTRIBUTES_MATCH_TYPE MatchType, BOOL* pbResult) =>
        _attributes.Compare(pTheirs, MatchType, pbResult);

    public void GetUINT32(Guid* guidKey, out uint punValue) => _attributes.GetUINT32(guidKey, out punValue);

    public void GetUINT64(Guid* guidKey, out ulong punValue) => _attributes.GetUINT64(guidKey, out punValue);

    public void GetDouble(Guid* guidKey, out double pfValue) => _attributes.GetDouble(guidKey, out pfValue);

    public void GetGUID(Guid* guidKey, Guid* pguidValue) => _attributes.GetGUID(guidKey, pguidValue);

    public void GetStringLength(Guid* guidKey, out uint pcchLength) => _attributes.GetStringLength(guidKey, out pcchLength);

    public void GetString(Guid* guidKey, PWSTR pwszValue, uint cchBufSize, uint* pcchLength) =>
        _attributes.GetString(guidKey, pwszValue, cchBufSize, pcchLength);

    public void GetAllocatedString(Guid* guidKey, PWSTR* ppwszValue, out uint pcchLength) =>
        _attributes.GetAllocatedString(guidKey, ppwszValue, out pcchLength);

    public void GetBlobSize(Guid* guidKey, out uint pcbBlobSize) => _attributes.GetBlobSize(guidKey, out pcbBlobSize);

    public void GetBlob(Guid* guidKey, byte[] pBuf, uint cbBufSize, uint* pcbBlobSize) =>
        _attributes.GetBlob(guidKey, pBuf, cbBufSize, pcbBlobSize);

    public void GetAllocatedBlob(Guid* guidKey, byte** ppBuf, out uint pcbSize) =>
        _attributes.GetAllocatedBlob(guidKey, ppBuf, out pcbSize);

    public void GetUnknown(Guid* guidKey, Guid* riid, out void* ppv) => _attributes.GetUnknown(guidKey, riid, out ppv);

    public void SetItem(Guid* guidKey, in PROPVARIANT Value) => _attributes.SetItem(guidKey, in Value);

    public void DeleteItem(Guid* guidKey) => _attributes.DeleteItem(guidKey);

    public void DeleteAllItems() => _attributes.DeleteAllItems();

    public void SetUINT32(Guid* guidKey, uint unValue) => _attributes.SetUINT32(guidKey, unValue);

    public void SetUINT64(Guid* guidKey, ulong unValue) => _attributes.SetUINT64(guidKey, unValue);

    public void SetDouble(Guid* guidKey, double fValue) => _attributes.SetDouble(guidKey, fValue);

    public void SetGUID(Guid* guidKey, Guid* guidValue) => _attributes.SetGUID(guidKey, guidValue);

    public void SetString(Guid* guidKey, PCWSTR wszValue) => _attributes.SetString(guidKey, wszValue);

    public void SetBlob(Guid* guidKey, byte[] pBuf, uint cbBufSize) => _attributes.SetBlob(guidKey, pBuf, cbBufSize);

    public void SetUnknown(Guid* guidKey, object pUnknown) => _attributes.SetUnknown(guidKey, pUnknown);

    public void LockStore() => _attributes.LockStore();

    public void UnlockStore() => _attributes.UnlockStore();

    public void GetCount(out uint pcItems) => _attributes.GetCount(out pcItems);

    public void GetItemByIndex(uint unIndex, Guid* pguidKey, PROPVARIANT_unmanaged* pValue) =>
        _attributes.GetItemByIndex(unIndex, pguidKey, pValue);

    public void CopyAllItems(IMFAttributes pDest) => _attributes.CopyAllItems(pDest);
}
