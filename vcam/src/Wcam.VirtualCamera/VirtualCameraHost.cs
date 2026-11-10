using Windows.Win32;
using Windows.Win32.Foundation;
using Windows.Win32.Media.MediaFoundation;
using Windows.Win32.System.Com;

namespace Wcam.VirtualCamera;

internal static class VirtualCameraHost
{
    private static readonly Lock Gate = new();
    private static IMFVirtualCamera? _camera;
    private static PublishedFrameSection? _section;
    private static FrameFormat _format = FrameFormat.Default;
    private static uint _changeMode;

    public static FrameFormat Format
    {
        get
        {
            lock (Gate)
            {
                return _format;
            }
        }
    }

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
                _section = PublishedFrameSection.Create(FrameTransport.LocalSectionName, _format);
                _section.SetChangeMode(_changeMode);
                _camera = CreateCamera();
            }
            catch
            {
                ReleaseSection();
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
                ReleaseSection();
                PInvoke.MFShutdown();
            }
        }
        Log.Info("virtual camera stopped");
    }

    public static void SetFormat(FrameFormat format)
    {
        lock (Gate)
        {
            _format = format;
            _section?.SetFormat(format);
        }
        Log.Info($"format set to {format}");
    }

    public static void SetChangeMode(uint mode)
    {
        lock (Gate)
        {
            _changeMode = mode;
            _section?.SetChangeMode(mode);
        }
        Log.Info($"format change mode set to {mode}");
    }

    public static bool Publish(ReadOnlySpan<byte> frame, uint width, uint height)
    {
        lock (Gate)
        {
            if (!FrameTransport.AcceptsFrame((uint)frame.Length, width, height, _format))
            {
                throw new ArgumentException($"frame {width}x{height} does not match {_format}");
            }
            if (_section is null)
            {
                return false;
            }
            _section.Publish(frame);
            return true;
        }
    }

    private static void ReleaseSection()
    {
        _section?.Dispose();
        _section = null;
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
