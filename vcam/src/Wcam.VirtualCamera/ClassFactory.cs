using System.Runtime.InteropServices.Marshalling;
using Windows.Win32.Foundation;
using Windows.Win32.Media.MediaFoundation;
using Windows.Win32.System.Com;

namespace Wcam.VirtualCamera;

[GeneratedComClass]
internal sealed unsafe partial class ClassFactory : IClassFactory
{
    public HRESULT CreateInstance(object pUnkOuter, Guid* riid, out void* ppvObject)
    {
        ppvObject = null;
        if (pUnkOuter is not null)
        {
            return HRESULT.CLASS_E_NOAGGREGATION;
        }
        try
        {
            return ComObjects.QueryInterface<IMFActivate>(new MediaSourceActivate(), riid, out ppvObject);
        }
        catch (Exception exception)
        {
            Log.Error("class factory could not create the activate object", exception);
            return (HRESULT)exception.HResult;
        }
    }

    public HRESULT LockServer(BOOL fLock) => HRESULT.S_OK;
}
