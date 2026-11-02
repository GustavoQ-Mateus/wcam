using System.ComponentModel;
using System.Runtime.InteropServices;
using Microsoft.Win32;
using Windows.Win32;
using Windows.Win32.Foundation;
using Windows.Win32.System.Com;

namespace Wcam.VirtualCamera;

internal static unsafe class Exports
{
    private const string InprocServerKey = "InprocServer32";
    private const string ThreadingModelValue = "ThreadingModel";
    private const string BothThreadingModel = "Both";
    private const int ModulePathCapacity = 32768;

    [UnmanagedCallersOnly(EntryPoint = "DllGetClassObject")]
    public static int DllGetClassObject(Guid* rclsid, Guid* riid, void** ppv)
    {
        try
        {
            *ppv = null;
            if (*rclsid != CameraIdentity.SourceClassId)
            {
                return HRESULT.CLASS_E_CLASSNOTAVAILABLE;
            }
            HRESULT status = ComObjects.QueryInterface<IClassFactory>(new ClassFactory(), riid, out void* factory);
            *ppv = factory;
            return status;
        }
        catch (Exception exception)
        {
            Log.Error("DllGetClassObject failed", exception);
            return exception.HResult;
        }
    }

    [UnmanagedCallersOnly(EntryPoint = "DllCanUnloadNow")]
    public static int DllCanUnloadNow() => HRESULT.S_FALSE;

    [UnmanagedCallersOnly(EntryPoint = "DllRegisterServer")]
    public static int DllRegisterServer()
    {
        try
        {
            using RegistryKey classKey = Registry.LocalMachine.CreateSubKey(CameraIdentity.SourceClassKey);
            classKey.SetValue(null, CameraIdentity.SourceDescription);
            using RegistryKey serverKey = classKey.CreateSubKey(InprocServerKey);
            serverKey.SetValue(null, ModulePath());
            serverKey.SetValue(ThreadingModelValue, BothThreadingModel);
            return HRESULT.S_OK;
        }
        catch (Exception exception)
        {
            Log.Error("DllRegisterServer failed", exception);
            return HRESULT.SELFREG_E_CLASS;
        }
    }

    [UnmanagedCallersOnly(EntryPoint = "DllUnregisterServer")]
    public static int DllUnregisterServer()
    {
        try
        {
            Registry.LocalMachine.DeleteSubKeyTree(CameraIdentity.SourceClassKey, throwOnMissingSubKey: false);
            return HRESULT.S_OK;
        }
        catch (Exception exception)
        {
            Log.Error("DllUnregisterServer failed", exception);
            return HRESULT.SELFREG_E_CLASS;
        }
    }

    [UnmanagedCallersOnly(EntryPoint = "WcamCameraStart")]
    public static int WcamCameraStart()
    {
        try
        {
            VirtualCameraHost.Start();
            return HRESULT.S_OK;
        }
        catch (Exception exception)
        {
            Log.Error("WcamCameraStart failed", exception);
            return exception.HResult;
        }
    }

    [UnmanagedCallersOnly(EntryPoint = "WcamCameraStop")]
    public static int WcamCameraStop()
    {
        try
        {
            VirtualCameraHost.Stop();
            return HRESULT.S_OK;
        }
        catch (Exception exception)
        {
            Log.Error("WcamCameraStop failed", exception);
            return exception.HResult;
        }
    }

    private static string ModulePath()
    {
        HMODULE module;
        delegate* unmanaged<int> addressInModule = &DllRegisterServer;
        uint flags = PInvoke.GET_MODULE_HANDLE_EX_FLAG_FROM_ADDRESS | PInvoke.GET_MODULE_HANDLE_EX_FLAG_UNCHANGED_REFCOUNT;
        if (!PInvoke.GetModuleHandleEx(flags, (PCWSTR)(char*)addressInModule, &module))
        {
            throw new Win32Exception();
        }
        char[] buffer = new char[ModulePathCapacity];
        fixed (char* path = buffer)
        {
            uint length = PInvoke.GetModuleFileName(module, path, ModulePathCapacity);
            if (length == 0 || length == ModulePathCapacity)
            {
                throw new Win32Exception();
            }
            return new string(path, 0, (int)length);
        }
    }
}
