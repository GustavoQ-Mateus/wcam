namespace Wcam.App;

internal static class IconPainter
{
    public const uint Data = 0xFF3ECF8E;
    public const uint Data2 = 0xFFE6E6E6;
    public const uint Warning = 0xFFE5A93B;
    public const uint Muted = 0xFFB4B4B4;
    public const uint Negative = 0xFFE5484D;
    private const int Supersample = 4;
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
