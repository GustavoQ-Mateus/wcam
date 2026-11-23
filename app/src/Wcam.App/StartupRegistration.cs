using Microsoft.Win32;

namespace Wcam.App;

internal sealed class StartupRegistration
{
    public const string RunKey = @"Software\Microsoft\Windows\CurrentVersion\Run";
    public const string ValueName = "WCam";
    public const string StartupArgument = "--startup";

    private readonly string _keyPath;
    private readonly string _executable;

    public StartupRegistration(string keyPath, string executable)
    {
        _keyPath = keyPath;
        _executable = executable;
    }

    public bool IsEnabled
    {
        get
        {
            using RegistryKey? key = Registry.CurrentUser.OpenSubKey(_keyPath);
            return key?.GetValue(ValueName) is string;
        }
    }

    public void Set(bool enabled)
    {
        using RegistryKey key = Registry.CurrentUser.CreateSubKey(_keyPath);
        if (enabled)
        {
            key.SetValue(ValueName, $"\"{_executable}\" {StartupArgument}");
            return;
        }
        key.DeleteValue(ValueName, throwOnMissingValue: false);
    }
}
