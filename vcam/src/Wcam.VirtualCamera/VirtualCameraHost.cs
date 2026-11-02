using Windows.Win32;
using Windows.Win32.Foundation;
using Windows.Win32.Media.MediaFoundation;
using Windows.Win32.System.Com;

namespace Wcam.VirtualCamera;

internal static class VirtualCameraHost
{
    private static readonly Lock Gate = new();
    private static IMFVirtualCamera? _camera;

    public static void Start()
    {
        lock (Gate)
        {
            if (_camera is not null)
            {
                return;
            }
            InitializeCom();
            PInvoke.MFStartup(PInvoke.MF_VERSION, PInvoke.MFSTARTUP_FULL).ThrowOnFailure();
            try
            {
                _camera = CreateCamera();
            }
            catch
            {
                PInvoke.MFShutdown();
                throw;
            }
        }
        Log.Info("virtual camera started");
    }

    public static void Stop()
    {
        lock (Gate)
        {
            if (_camera is null)
            {
                return;
            }
            try
            {
                _camera.Stop();
            }
            finally
            {
                _camera.Shutdown();
                ComObjects.Release(_camera);
                _camera = null;
                PInvoke.MFShutdown();
            }
        }
        Log.Info("virtual camera stopped");
    }

    private static void InitializeCom()
    {
        HRESULT status = PInvoke.CoInitializeEx(COINIT.COINIT_MULTITHREADED);
        if (status.Failed && status != HRESULT.RPC_E_CHANGED_MODE)
        {
            status.ThrowOnFailure();
        }
    }

    private static IMFVirtualCamera CreateCamera()
    {
        PInvoke.MFCreateVirtualCamera(
            MFVirtualCameraType.MFVirtualCameraType_SoftwareCameraSource,
            MFVirtualCameraLifetime.MFVirtualCameraLifetime_Session,
            MFVirtualCameraAccess.MFVirtualCameraAccess_CurrentUser,
            CameraIdentity.FriendlyName,
            CameraIdentity.SourceClassId.ToString("B"),
            default,
            out IMFVirtualCamera camera).ThrowOnFailure();
        try
        {
            CameraOwner.Record(camera);
            SessionChannelSpike.Create();
            camera.Start(null!);
            return camera;
        }
        catch
        {
            camera.Shutdown();
            ComObjects.Release(camera);
            throw;
        }
    }
}
