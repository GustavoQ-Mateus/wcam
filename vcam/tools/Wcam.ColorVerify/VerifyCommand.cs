using System.Globalization;

namespace Wcam.ColorVerify;

internal static class VerifyCommand
{
    public static int Run(string traceDirectory, IReadOnlyDictionary<string, string> modelPaths)
    {
        var calibration = ColorTrace.Read<CalibrationTrace>(Path.Combine(traceDirectory, ColorTrace.CalibrationFile));
        IReadOnlyList<(string Name, TraceSample Sample)> samples = ColorTrace.ReadSamples(traceDirectory);
        if (samples.Count == 0)
        {
            Console.Error.WriteLine($"no {ColorTrace.SamplePattern} in {traceDirectory}");
            return 1;
        }
        Console.WriteLine(Invariant($"agent calibration: state {calibration.State}, deltaE {calibration.DeltaE?.ToString("F2") ?? "null"}"));
        foreach ((string label, string path) in modelPaths)
        {
            ModelSet models = ColorTrace.Read<ModelSet>(path);
            ReportModel(label, models, calibration, samples);
        }
        return 0;
    }

    private static void ReportModel(
        string label,
        ModelSet models,
        CalibrationTrace calibration,
        IReadOnlyList<(string Name, TraceSample Sample)> samples)
    {
        Console.WriteLine($"chrome model {label}:");
        Console.WriteLine("  sample                 space       state      corr  mirror  range      dE before  dE after");
        double beforeSum = 0;
        double afterSum = 0;
        foreach ((string name, TraceSample sample) in samples)
        {
            ChromeModel chrome = models.For(sample.Space);
            byte[] rgb = sample.RgbBytes;
            YuvPlanes frame = sample.Frame;
            double before = SampleComparison.MeanDeltaE(rgb, sample.Space, frame, sample.Mirrored, calibration.RangeTables, chrome);
            double after = SampleComparison.MeanDeltaE(rgb, sample.Space, frame, sample.Mirrored, calibration.AppliedTables, chrome);
            beforeSum += before;
            afterSum += after;
            string range = sample.ColorRange ?? "-";
            Console.WriteLine(Invariant(
                $"  {name,-22} {sample.ColorSpace,-11} {sample.CalibrationState,-10} {sample.Correlation,4:F2}  {sample.Mirrored,-6}  {range,-9}  {before,9:F2}  {after,8:F2}"));
        }
        Console.WriteLine(Invariant(
            $"  mean dE2000 over {samples.Count} samples: before {beforeSum / samples.Count:F2}, after {afterSum / samples.Count:F2}"));
    }

    private static string Invariant(FormattableString text) => text.ToString(CultureInfo.InvariantCulture);
}
