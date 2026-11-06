namespace Wcam.ColorVerify;

internal sealed record ChromeModel(double[] Red, double[] Green, double[] Blue)
{
    public const int LimitedBlack = 16;
    public const int NeutralChroma = 128;
    private const double LumaScale = 255.0 / 219.0;
    private const double ChromaScale = 255.0 / 224.0;
    private const double Bt709Red = 0.2126;
    private const double Bt709Blue = 0.0722;
    private const double LibyuvBlueFromU = 2.0;
    private const int Terms = 4;

    public static ChromeModel Bt709Exact { get; } = Bt709(2 * (1 - Bt709Blue) * ChromaScale);

    public static ChromeModel Bt709Libyuv { get; } = Bt709(LibyuvBlueFromU);

    public Rgb Predict(byte y, byte u, byte v)
    {
        double[] terms = Terms4(y, u, v);
        return new Rgb(Dot(Red, terms), Dot(Green, terms), Dot(Blue, terms));
    }

    public static ChromeModel Fit(IReadOnlyCollection<PatchReading> readings)
    {
        if (readings.Count < Terms)
        {
            throw new ArgumentException($"at least {Terms} unclipped patches are needed, got {readings.Count}");
        }
        double[,] normal = new double[Terms, Terms];
        double[][] targets = [new double[Terms], new double[Terms], new double[Terms]];
        foreach (PatchReading reading in readings)
        {
            double[] terms = Terms4(reading.Y, reading.U, reading.V);
            Accumulate(normal, targets, terms, reading.Measured);
        }
        return new ChromeModel(Solve(normal, targets[0]), Solve(normal, targets[1]), Solve(normal, targets[2]));
    }

    private static ChromeModel Bt709(double blueFromU)
    {
        double green = 1 - Bt709Red - Bt709Blue;
        double redFromV = 2 * (1 - Bt709Red) * ChromaScale;
        double greenFromU = -2 * (1 - Bt709Blue) * Bt709Blue / green * ChromaScale;
        double greenFromV = -2 * (1 - Bt709Red) * Bt709Red / green * ChromaScale;
        return new ChromeModel(
            [0, LumaScale, 0, redFromV],
            [0, LumaScale, greenFromU, greenFromV],
            [0, LumaScale, blueFromU, 0]);
    }

    private static double[] Terms4(byte y, byte u, byte v) => [1, y - LimitedBlack, u - NeutralChroma, v - NeutralChroma];

    private static double Dot(double[] coefficients, double[] terms)
    {
        double sum = 0;
        for (int index = 0; index < Terms; index++)
        {
            sum += coefficients[index] * terms[index];
        }
        return sum;
    }

    private static void Accumulate(double[,] normal, double[][] targets, double[] terms, Rgb measured)
    {
        double[] channels = [measured.R, measured.G, measured.B];
        for (int row = 0; row < Terms; row++)
        {
            for (int column = 0; column < Terms; column++)
            {
                normal[row, column] += terms[row] * terms[column];
            }
            for (int channel = 0; channel < channels.Length; channel++)
            {
                targets[channel][row] += terms[row] * channels[channel];
            }
        }
    }

    private static double[] Solve(double[,] normal, double[] target)
    {
        double[,] matrix = (double[,])normal.Clone();
        double[] result = (double[])target.Clone();
        for (int pivot = 0; pivot < Terms; pivot++)
        {
            SwapLargestRow(matrix, result, pivot);
            for (int row = pivot + 1; row < Terms; row++)
            {
                double factor = matrix[row, pivot] / matrix[pivot, pivot];
                for (int column = pivot; column < Terms; column++)
                {
                    matrix[row, column] -= factor * matrix[pivot, column];
                }
                result[row] -= factor * result[pivot];
            }
        }
        for (int row = Terms - 1; row >= 0; row--)
        {
            for (int column = row + 1; column < Terms; column++)
            {
                result[row] -= matrix[row, column] * result[column];
            }
            result[row] /= matrix[row, row];
        }
        return result;
    }

    private static void SwapLargestRow(double[,] matrix, double[] result, int pivot)
    {
        int largest = pivot;
        for (int row = pivot + 1; row < Terms; row++)
        {
            if (Math.Abs(matrix[row, pivot]) > Math.Abs(matrix[largest, pivot]))
            {
                largest = row;
            }
        }
        if (largest == pivot)
        {
            return;
        }
        for (int column = 0; column < Terms; column++)
        {
            (matrix[pivot, column], matrix[largest, column]) = (matrix[largest, column], matrix[pivot, column]);
        }
        (result[pivot], result[largest]) = (result[largest], result[pivot]);
    }
}
