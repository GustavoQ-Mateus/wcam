namespace Wcam.ColorVerify;

internal static class SampleComparison
{
    private const int Channels = 3;

    public static double MeanDeltaE(
        byte[] sampleRgb,
        RgbColorSpace sampleSpace,
        YuvPlanes frame,
        bool mirrored,
        PlaneTables tables,
        ChromeModel chrome)
    {
        frame.Validate();
        tables.Validate();
        if (sampleRgb.Length != frame.Width * frame.Height * Channels)
        {
            throw new InvalidDataException("sample and matched frame have different sizes");
        }
        double sum = 0;
        for (int row = 0; row < frame.Height; row++)
        {
            for (int column = 0; column < frame.Width; column++)
            {
                int samplePixel = row * frame.Width + column;
                int framePixel = row * frame.Width + (mirrored ? frame.Width - 1 - column : column);
                Lab expected = SampleLab(sampleRgb, samplePixel, sampleSpace);
                Lab shown = ChromeLab(frame, framePixel, tables, chrome);
                sum += ColorScience.DeltaE2000(expected, shown);
            }
        }
        return sum / (frame.Width * frame.Height);
    }

    private static Lab SampleLab(byte[] rgb, int pixel, RgbColorSpace space)
    {
        int offset = pixel * Channels;
        return ColorScience.ToLab(new Rgb(rgb[offset], rgb[offset + 1], rgb[offset + 2]), space);
    }

    private static Lab ChromeLab(YuvPlanes frame, int pixel, PlaneTables tables, ChromeModel chrome)
    {
        byte y = (byte)tables.Y[frame.Y[pixel]];
        byte u = (byte)tables.U[frame.U[pixel]];
        byte v = (byte)tables.V[frame.V[pixel]];
        Rgb srgb = ColorScience.Clamp(chrome.Predict(y, u, v));
        return ColorScience.ToLab(srgb, RgbColorSpace.Srgb);
    }
}
