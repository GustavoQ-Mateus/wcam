using Microsoft.UI.Dispatching;
using Microsoft.UI.Xaml;

namespace Wcam.App;

public static class Program
{
    private const string WebViewDataVariable = "WEBVIEW2_USER_DATA_FOLDER";

    [STAThread]
    public static void Main(string[] args)
    {
        using SingleInstance? instance = SingleInstance.TryAcquire(SingleInstance.ProductName);
        if (instance is null)
        {
            return;
        }
        Environment.SetEnvironmentVariable(WebViewDataVariable, Path.Combine(AppPaths.DataDirectory, "WebView2"));
        bool startup = args.Contains(StartupRegistration.StartupArgument);
        WinRT.ComWrappersSupport.InitializeComWrappers();
        Application.Start(callback =>
        {
            var context = new DispatcherQueueSynchronizationContext(DispatcherQueue.GetForCurrentThread());
            SynchronizationContext.SetSynchronizationContext(context);
            _ = new App(instance, startup);
        });
    }
}
