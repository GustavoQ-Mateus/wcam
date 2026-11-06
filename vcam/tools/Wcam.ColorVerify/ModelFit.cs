using Wcam.VirtualCamera.Probe;

namespace Wcam.ColorVerify;

internal sealed record ModelFit(
    RgbColorSpace CanvasSpace,
    ChromeModel Model,
    int PatchesUsed,
    double ResidualRms,
    double ResidualMaximum,
    double ModelDeltaEMean,
    double ModelDeltaEMaximum,
    double MeasuredDeltaEMean,
    double MeasuredDeltaEMaximum)
{
    private const double ClipMargin = 3;

    public static ModelFit From(RgbColorSpace canvasSpace, IReadOnlyList<Rgb> canvasCodes)
    {
        IReadOnlyList<Patch> patches = PatchGrid.Patches;
        if (canvasCodes.Count != patches.Count)
        {
            throw new ArgumentException($"expected {patches.Count} readings, got {canvasCodes.Count}");
        }
        var unclipped = new List<PatchReading>();
        var all = new List<PatchReading>();
        for (int index = 0; index < patches.Count; index++)
        {
            Patch patch = patches[index];
            var reading = new PatchReading(patch.Y, patch.U, patch.V, ToSrgb(canvasCodes[index], canvasSpace));
            all.Add(reading);
            if (IsUnclipped(reading.Measured))
            {
                unclipped.Add(reading);
            }
        }
        ChromeModel model = ChromeModel.Fit(unclipped);
        (double rms, double maximum) = Residuals(model, unclipped);
        (double modelMean, double modelMaximum) = DeltaE(all, reading => model.Predict(reading.Y, reading.U, reading.V));
        (double measuredMean, double measuredMaximum) = DeltaE(all, reading => reading.Measured);
        return new ModelFit(canvasSpace, model, unclipped.Count, rms, maximum, modelMean, modelMaximum, measuredMean, measuredMaximum);
    }

    public static bool IsUnclipped(Rgb code) =>
        IsInside(code.R) && IsInside(code.G) && IsInside(code.B);

    private static bool IsInside(double code) => code >= ClipMargin && code <= ColorScience.CodeMaximum - ClipMargin;

    private static Rgb ToSrgb(Rgb code, RgbColorSpace space) => ColorScience.Convert(code, space, RgbColorSpace.Srgb);

    private static (double Rms, double Maximum) Residuals(ChromeModel model, IReadOnlyList<PatchReading> readings)
    {
        double sumOfSquares = 0;
        double maximum = 0;
        foreach (PatchReading reading in readings)
        {
            Rgb predicted = model.Predict(reading.Y, reading.U, reading.V);
            double[] errors =
            [
                predicted.R - reading.Measured.R,
                predicted.G - reading.Measured.G,
                predicted.B - reading.Measured.B,
            ];
            foreach (double error in errors)
            {
                sumOfSquares += error * error;
                maximum = Math.Max(maximum, Math.Abs(error));
            }
        }
        return (Math.Sqrt(sumOfSquares / (readings.Count * 3)), maximum);
    }

    private static (double Mean, double Maximum) DeltaE(IReadOnlyList<PatchReading> readings, Func<PatchReading, Rgb> chrome)
    {
        double sum = 0;
        double maximum = 0;
        foreach (PatchReading reading in readings)
        {
            Rgb exact = ColorScience.Clamp(ChromeModel.Bt709Exact.Predict(reading.Y, reading.U, reading.V));
            Rgb observed = ColorScience.Clamp(chrome(reading));
            double deltaE = ColorScience.DeltaE2000(
                ColorScience.ToLab(exact, RgbColorSpace.Srgb),
                ColorScience.ToLab(observed, RgbColorSpace.Srgb));
            sum += deltaE;
            maximum = Math.Max(maximum, deltaE);
        }
        return (sum / readings.Count, maximum);
    }
}
