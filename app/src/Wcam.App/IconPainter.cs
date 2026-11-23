namespace Wcam.App;

internal static class IconPainter
{
    public const uint Data = 0xFF3ECF8E;
    public const uint Data2 = 0xFFE6E6E6;
    public const uint Warning = 0xFFE5A93B;
    public const uint Muted = 0xFFB4B4B4;
    public const uint Negative = 0xFFE5484D;
    public const uint Surface = 0xFF111111;
    public const uint Ink = 0xFFFFFFFF;
    private const int Supersample = 4;
    private const double MarkCenter = 0.78;
    private const double MarkRadius = 0.19;
    private const double MarkGap = 0.05;
    private const double CameraCenter = 0.42;
    private const double BodyLeft = 0.16;
    private const double BodyRight = 0.52;
    private const double BodyHalfHeight = 0.14;
    private const double LensRight = 0.68;
    private const double LensHalfHeightStart = 0.05;
    private const double LensHalfHeightEnd = 0.13;
    private const double MarginFraction = 0.125;
    private const double RingFraction = 0.125;
    private const double BarFraction = 0.22;
    private const double BarGapFraction = 0.16;

    public static uint[] Paint(TrayState state, int size)
    {
        var pixels = new uint[size * size];
        for (int y = 0; y < size; y++)
        {
            for (int x = 0; x < size; x++)
            {
                pixels[y * size + x] = Pixel(state, x, y, size);
            }
        }
        return pixels;
    }

    public static uint[] PaintOverlay(TrayState state, int size)
    {
        var pixels = new uint[size * size];
        for (int y = 0; y < size; y++)
        {
            for (int x = 0; x < size; x++)
            {
                pixels[y * size + x] = OverlayPixel(state, x, y, size);
            }
        }
        return pixels;
    }

    public static uint Color(TrayState state) => state switch
    {
        TrayState.Live => Data,
        TrayState.Video or TrayState.Frozen => Data2,
        TrayState.CameraOff => Warning,
        TrayState.Waiting => Muted,
        _ => Negative,
    };

    private static uint Pixel(TrayState state, int x, int y, int size)
    {
        int covered = 0;
        for (int sampleY = 0; sampleY < Supersample; sampleY++)
        {
            for (int sampleX = 0; sampleX < Supersample; sampleX++)
            {
                double u = (x + (sampleX + 0.5) / Supersample) / size;
                double v = (y + (sampleY + 0.5) / Supersample) / size;
                covered += Inside(state, u, v) ? 1 : 0;
            }
        }
        return Premultiply(Color(state), (double)covered / (Supersample * Supersample));
    }

    private static bool Inside(TrayState state, double u, double v)
    {
        const double low = MarginFraction;
        const double high = 1 - MarginFraction;
        double radius = (high - low) / 2;
        double distance = Math.Sqrt((u - 0.5) * (u - 0.5) + (v - 0.5) * (v - 0.5));
        bool inBox = u >= low && u <= high && v >= low && v <= high;
        return state switch
        {
            TrayState.Live => distance <= radius,
            TrayState.Video => inBox && Math.Abs(v - 0.5) <= (high - u) / 2,
            TrayState.Frozen => inBox,
            TrayState.CameraOff => inBox && InBars(u),
            TrayState.Waiting => distance <= radius && distance >= radius - RingFraction,
            _ => inBox && Math.Abs(u - 0.5) <= (v - low) / 2,
        };
    }

    private static uint OverlayPixel(TrayState state, int x, int y, int size)
    {
        double red = 0, green = 0, blue = 0, alpha = 0;
        const int samples = Supersample * Supersample;
        for (int sampleY = 0; sampleY < Supersample; sampleY++)
        {
            for (int sampleX = 0; sampleX < Supersample; sampleX++)
            {
                double u = (x + (sampleX + 0.5) / Supersample) / size;
                double v = (y + (sampleY + 0.5) / Supersample) / size;
                uint? color = OverlayColor(state, u, v);
                if (color is null)
                {
                    continue;
                }
                red += (color.Value >> 16) & 0xFF;
                green += (color.Value >> 8) & 0xFF;
                blue += color.Value & 0xFF;
                alpha += 1;
            }
        }
        return (uint)Math.Round(alpha / samples * 255) << 24
            | (uint)Math.Round(red / samples) << 16
            | (uint)Math.Round(green / samples) << 8
            | (uint)Math.Round(blue / samples);
    }

    private static uint? OverlayColor(TrayState state, double u, double v)
    {
        double markU = (u - MarkCenter) / MarkRadius;
        double markV = (v - MarkCenter) / MarkRadius;
        double markDistance = Math.Sqrt(markU * markU + markV * markV);
        if (markDistance <= 1)
        {
            return Inside(state, (markU + 1) / 2, (markV + 1) / 2) ? Color(state) : Surface;
        }
        if (markDistance <= 1 + MarkGap / MarkRadius)
        {
            return null;
        }
        double distance = Math.Sqrt((u - 0.5) * (u - 0.5) + (v - 0.5) * (v - 0.5));
        if (distance > 0.5)
        {
            return null;
        }
        return InCamera(u, v) ? Ink : Surface;
    }

    private static bool InCamera(double u, double v)
    {
        bool body = u >= BodyLeft && u <= BodyRight && Math.Abs(v - CameraCenter) <= BodyHalfHeight;
        double lensProgress = (u - BodyRight) / (LensRight - BodyRight);
        bool lens = lensProgress is >= 0 and <= 1
            && Math.Abs(v - CameraCenter) <= LensHalfHeightStart + lensProgress * (LensHalfHeightEnd - LensHalfHeightStart);
        return body || lens;
    }

    private static bool InBars(double u)
    {
        double left = (1 - 2 * BarFraction - BarGapFraction) / 2;
        double right = left + BarFraction + BarGapFraction;
        return (u >= left && u <= left + BarFraction) || (u >= right && u <= right + BarFraction);
    }

    private static uint Premultiply(uint color, double coverage)
    {
        uint alpha = (uint)Math.Round(255 * coverage);
        uint red = ((color >> 16) & 0xFF) * alpha / 255;
        uint green = ((color >> 8) & 0xFF) * alpha / 255;
        uint blue = (color & 0xFF) * alpha / 255;
        return alpha << 24 | red << 16 | green << 8 | blue;
    }
}
