using Microsoft.UI;
using Windows.Win32.UI.WindowsAndMessaging;

namespace Wcam.App;

internal static unsafe class AppIcon
{
    private const int Size = 64;
    private static IconId? _id;

    public static IconId Id => _id ??= Create();

    private static IconId Create()
    {
        HICON icon = IconFactory.Create(IconPainter.Paint(TrayState.Live, Size), Size);
        return Win32Interop.GetIconIdFromIcon((nint)icon.Value);
    }
}
