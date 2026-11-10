using Windows.Win32;
using Windows.Win32.Foundation;
using Windows.Win32.Media.MediaFoundation;
using Windows.Win32.System.Com;

namespace Wcam.VirtualCamera;

internal static class VirtualCameraHost
{
    private static readonly Lock CameraGate = new();
    private static readonly Lock StateGate = new();
    private static readonly FormatSwitch Formats = new(FrameFormat.Default);
    private static IMFVirtualCamera? _camera;
    private static PublishedFrameSection? _section;
    private static StreamingMonitor? _monitor;
    private static bool _running;

    public static WcamFormatState State
    {
        get
        {
            lock (StateGate)
            {
                return WcamFormatState.From(Formats, _running);
            }
        }
    }

    public static void Start()
    {
        lock (CameraGate)
        {
            if (_section is not null)
            {
                return;
            }
            InitializeCom();
            PInvoke.MFStartup(PInvoke.MF_VERSION, PInvoke.MFSTARTUP_FULL).ThrowOnFailure();
            try
            {
                OpenSection();
                _camera = CreateCamera();
                SetRunning(true);
                _monitor = StreamingMonitor.Start(OnStreamingAppsChanged);
            }
            catch
            {
                ReleaseCamera();
                ReleaseSection();
                PInvoke.MFShutdown();
                throw;
            }
        }
        Log.Info($"virtual camera started at {State.Width}x{State.Height}@{State.FramesPerSecond}");
    }

    public static void Stop()
    {
        lock (CameraGate)
        {
            if (_section is null)
            {
                return;
            }
            _monitor?.Dispose();
            _monitor = null;
            try
            {
                ReleaseCamera();
            }
            finally
            {
                ReleaseSection();
                PInvoke.MFShutdown();
            }
        }
        Log.Info("virtual camera stopped");
    }

    public static FormatRequestOutcome SetFormat(FrameFormat format)
    {
        lock (CameraGate)
        {
            FormatRequestOutcome outcome;
            lock (StateGate)
            {
                outcome = Formats.Request(format, _section is not null);
            }
            Log.Info($"format {format} requested: {outcome}");
            if (outcome == FormatRequestOutcome.RestartCamera)
            {
                Restart(format);
            }
            return outcome;
        }
    }

    public static bool Publish(ReadOnlySpan<byte> frame, uint width, uint height)
    {
        lock (StateGate)
        {
            if (!FrameTransport.AcceptsFrame((uint)frame.Length, width, height, Formats.Announced))
            {
                throw new ArgumentException($"frame {width}x{height} does not match {Formats.Announced}");
            }
            if (_section is null)
            {
                return false;
            }
            _section.Publish(frame);
            return true;
        }
    }

    private static void OpenSection()
    {
        lock (StateGate)
        {
            _section = PublishedFrameSection.Create(FrameTransport.LocalSectionName, Formats.Requested);
            Formats.Announce(Formats.Requested);
        }
    }

    private static void Restart(FrameFormat format)
    {
        SetRunning(false);
        ReleaseCamera();
        lock (StateGate)
        {
            _section?.SetFormat(format);
            Formats.Announce(format);
        }
        _camera = CreateCamera();
        SetRunning(true);
        Log.Info($"virtual camera restarted at {format}");
    }

    private static void OnStreamingAppsChanged(int count)
    {
        bool applyPending;
        lock (StateGate)
        {
            applyPending = Formats.UpdateStreamingApps(count);
        }
        if (applyPending)
        {
            ThreadPool.QueueUserWorkItem(_ => ApplyPending());
        }
    }

    private static void ApplyPending()
    {
        try
        {
            lock (CameraGate)
            {
                FrameFormat format;
                lock (StateGate)
                {
                    if (_section is null || !Formats.IsPending || Formats.StreamingApps > 0)
                    {
                        return;
                    }
                    format = Formats.Requested;
                }
                Restart(format);
            }
        }
        catch (Exception exception)
        {
            Log.Error("pending format change failed", exception);
        }
    }

    private static void SetRunning(bool running)
    {
        lock (StateGate)
        {
            _running = running;
        }
    }

    private static void ReleaseCamera()
    {
        SetRunning(false);
        IMFVirtualCamera? camera = _camera;
        _camera = null;
        if (camera is null)
        {
            return;
        }
        try
        {
            camera.Stop();
        }
        finally
        {
            camera.Shutdown();
            ComObjects.Release(camera);
        }
    }

    private static void ReleaseSection()
    {
        lock (StateGate)
        {
            _section?.Dispose();
            _section = null;
        }
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
