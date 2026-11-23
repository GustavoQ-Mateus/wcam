using System.ComponentModel;
using Windows.Win32;
using Windows.Win32.Foundation;
using Windows.Win32.Graphics.Gdi;
using Windows.Win32.UI.WindowsAndMessaging;

namespace Wcam.App;

internal static unsafe class IconFactory
{
    public static int SmallIconSize => PInvoke.GetSystemMetricsForDpi(SYSTEM_METRICS_INDEX.SM_CXSMICON, PInvoke.GetDpiForSystem());

    public static HICON Create(uint[] premultipliedPixels, int size)
    {
        HBITMAP color = CreateBitmap(premultipliedPixels, size);
        HBITMAP mask = PInvoke.CreateBitmap(size, size, 1, 1, null);
        var info = new ICONINFO { fIcon = true, hbmColor = color, hbmMask = mask };
        HICON icon = PInvoke.CreateIconIndirect(&info);
        PInvoke.DeleteObject(color);
        PInvoke.DeleteObject(mask);
        if (icon.IsNull)
        {
            throw new Win32Exception();
        }
        return icon;
    }

    public static HBITMAP CreateBitmap(uint[] premultipliedPixels, int size)
    {
        var header = new BITMAPINFO
        {
            bmiHeader = new BITMAPINFOHEADER
            {
                biSize = (uint)sizeof(BITMAPINFOHEADER),
                biWidth = size,
                biHeight = -size,
                biPlanes = 1,
                biBitCount = 32,
                biCompression = 0,
            },
        };
        void* bits;
        HBITMAP bitmap = PInvoke.CreateDIBSection(HDC.Null, &header, DIB_USAGE.DIB_RGB_COLORS, &bits, HANDLE.Null, 0);
        if (bitmap.IsNull)
        {
            throw new Win32Exception();
        }
        premultipliedPixels.AsSpan().CopyTo(new Span<uint>(bits, size * size));
        return bitmap;
    }
}
