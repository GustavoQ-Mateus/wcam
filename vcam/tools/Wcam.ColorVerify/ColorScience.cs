namespace Wcam.ColorVerify;

internal static class ColorScience
{
    public const double CodeMaximum = 255.0;
    private const double WhiteX = 0.3127 / 0.3290;
    private const double WhiteY = 1.0;
    private const double WhiteZ = (1 - 0.3127 - 0.3290) / 0.3290;
    private const double LabEpsilon = 216.0 / 24389.0;
    private const double LabKappa = 24389.0 / 27.0;
    private const double TransferBreak = 0.04045;
    private const double LinearBreak = 0.0031308;
    private const double LinearSlope = 12.92;
    private const double TransferOffset = 0.055;
    private const double TransferGamma = 2.4;
    private static readonly double[,] SrgbToXyz =
    {
        { 0.41239079926595934, 0.357584339383878, 0.1804807884018343 },
        { 0.21263900587151027, 0.715168678767756, 0.07219231536073371 },
        { 0.01933081871559182, 0.11919477979462598, 0.9505321522496607 },
    };
    private static readonly double[,] DisplayP3ToXyz =
    {
        { 0.4865709486482162, 0.26566769316909306, 0.1982172852343625 },
        { 0.2289745640697488, 0.6917385218365064, 0.079286914093745 },
        { 0, 0.04511338185890264, 1.043944368900976 },
    };
    private static readonly double[,] XyzToSrgb = Invert(SrgbToXyz);
    private static readonly double[,] XyzToDisplayP3 = Invert(DisplayP3ToXyz);

    public static Lab ToLab(Rgb code, RgbColorSpace space)
    {
        (double x, double y, double z) = Multiply(ToXyzMatrix(space), Linearize(code));
        double fx = LabComponent(x / WhiteX);
        double fy = LabComponent(y / WhiteY);
        double fz = LabComponent(z / WhiteZ);
        return new Lab(116 * fy - 16, 500 * (fx - fy), 200 * (fy - fz));
    }

    public static Rgb Convert(Rgb code, RgbColorSpace from, RgbColorSpace to)
    {
        if (from == to)
        {
            return code;
        }
        (double x, double y, double z) = Multiply(ToXyzMatrix(from), Linearize(code));
        (double r, double g, double b) = Multiply(FromXyzMatrix(to), (x, y, z));
        return new Rgb(Encode(r), Encode(g), Encode(b));
    }

    public static Rgb Clamp(Rgb code) =>
        new(Math.Clamp(code.R, 0, CodeMaximum), Math.Clamp(code.G, 0, CodeMaximum), Math.Clamp(code.B, 0, CodeMaximum));

    public static double DeltaE2000(Lab first, Lab second)
    {
        double chromaMean = (Math.Sqrt(first.A * first.A + first.B * first.B) +
            Math.Sqrt(second.A * second.A + second.B * second.B)) / 2;
        double chromaMean7 = Math.Pow(chromaMean, 7);
        double aScale = 1 + 0.5 * (1 - Math.Sqrt(chromaMean7 / (chromaMean7 + Math.Pow(25, 7))));
        double a1 = first.A * aScale;
        double a2 = second.A * aScale;
        double c1 = Math.Sqrt(a1 * a1 + first.B * first.B);
        double c2 = Math.Sqrt(a2 * a2 + second.B * second.B);
        double h1 = HueDegrees(first.B, a1);
        double h2 = HueDegrees(second.B, a2);
        double deltaL = second.L - first.L;
        double deltaC = c2 - c1;
        double deltaHue = HueDifference(h1, h2, c1 * c2);
        double deltaH = 2 * Math.Sqrt(c1 * c2) * Math.Sin(Radians(deltaHue / 2));
        double lMean = (first.L + second.L) / 2;
        double cMean = (c1 + c2) / 2;
        double hMean = HueMean(h1, h2, c1 * c2);
        double t = 1 - 0.17 * Math.Cos(Radians(hMean - 30)) + 0.24 * Math.Cos(Radians(2 * hMean)) +
            0.32 * Math.Cos(Radians(3 * hMean + 6)) - 0.20 * Math.Cos(Radians(4 * hMean - 63));
        double lOffset = (lMean - 50) * (lMean - 50);
        double sl = 1 + 0.015 * lOffset / Math.Sqrt(20 + lOffset);
        double sc = 1 + 0.045 * cMean;
        double sh = 1 + 0.015 * cMean * t;
        double cMean7 = Math.Pow(cMean, 7);
        double rotation = -2 * Math.Sqrt(cMean7 / (cMean7 + Math.Pow(25, 7))) *
            Math.Sin(Radians(60 * Math.Exp(-Math.Pow((hMean - 275) / 25, 2))));
        double lightness = deltaL / sl;
        double chroma = deltaC / sc;
        double hue = deltaH / sh;
        return Math.Sqrt(lightness * lightness + chroma * chroma + hue * hue + rotation * chroma * hue);
    }

    private static double HueDegrees(double b, double a)
    {
        if (a == 0 && b == 0)
        {
            return 0;
        }
        double degrees = Math.Atan2(b, a) * 180 / Math.PI;
        return degrees < 0 ? degrees + 360 : degrees;
    }

    private static double HueDifference(double h1, double h2, double chromaProduct)
    {
        if (chromaProduct == 0)
        {
            return 0;
        }
        double difference = h2 - h1;
        if (difference > 180)
        {
            return difference - 360;
        }
        return difference < -180 ? difference + 360 : difference;
    }

    private static double HueMean(double h1, double h2, double chromaProduct)
    {
        if (chromaProduct == 0)
        {
            return h1 + h2;
        }
        if (Math.Abs(h1 - h2) <= 180)
        {
            return (h1 + h2) / 2;
        }
        return h1 + h2 < 360 ? (h1 + h2 + 360) / 2 : (h1 + h2 - 360) / 2;
    }

    private static double Radians(double degrees) => degrees * Math.PI / 180;

    private static double LabComponent(double ratio) =>
        ratio > LabEpsilon ? Math.Cbrt(ratio) : (LabKappa * ratio + 16) / 116;

    private static (double, double, double) Linearize(Rgb code) =>
        (Decode(code.R), Decode(code.G), Decode(code.B));

    private static double Decode(double code)
    {
        double value = code / CodeMaximum;
        double magnitude = Math.Abs(value);
        double linear = magnitude <= TransferBreak
            ? magnitude / LinearSlope
            : Math.Pow((magnitude + TransferOffset) / (1 + TransferOffset), TransferGamma);
        return Math.CopySign(linear, value);
    }

    private static double Encode(double linear)
    {
        double magnitude = Math.Abs(linear);
        double value = magnitude <= LinearBreak
            ? magnitude * LinearSlope
            : (1 + TransferOffset) * Math.Pow(magnitude, 1 / TransferGamma) - TransferOffset;
        return Math.CopySign(value, linear) * CodeMaximum;
    }

    private static double[,] ToXyzMatrix(RgbColorSpace space) => space == RgbColorSpace.Srgb ? SrgbToXyz : DisplayP3ToXyz;

    private static double[,] FromXyzMatrix(RgbColorSpace space) => space == RgbColorSpace.Srgb ? XyzToSrgb : XyzToDisplayP3;

    private static (double, double, double) Multiply(double[,] matrix, (double First, double Second, double Third) vector) =>
        (
            matrix[0, 0] * vector.First + matrix[0, 1] * vector.Second + matrix[0, 2] * vector.Third,
            matrix[1, 0] * vector.First + matrix[1, 1] * vector.Second + matrix[1, 2] * vector.Third,
            matrix[2, 0] * vector.First + matrix[2, 1] * vector.Second + matrix[2, 2] * vector.Third);

    private static double[,] Invert(double[,] m)
    {
        double determinant = m[0, 0] * (m[1, 1] * m[2, 2] - m[1, 2] * m[2, 1]) -
            m[0, 1] * (m[1, 0] * m[2, 2] - m[1, 2] * m[2, 0]) +
            m[0, 2] * (m[1, 0] * m[2, 1] - m[1, 1] * m[2, 0]);
        var inverse = new double[3, 3];
        for (int row = 0; row < 3; row++)
        {
            for (int column = 0; column < 3; column++)
            {
                inverse[row, column] = Cofactor(m, column, row) / determinant;
            }
        }
        return inverse;
    }

    private static double Cofactor(double[,] m, int row, int column)
    {
        int r0 = row == 0 ? 1 : 0;
        int r1 = row == 2 ? 1 : 2;
        int c0 = column == 0 ? 1 : 0;
        int c1 = column == 2 ? 1 : 2;
        double minor = m[r0, c0] * m[r1, c1] - m[r0, c1] * m[r1, c0];
        return (row + column) % 2 == 0 ? minor : -minor;
    }
}
