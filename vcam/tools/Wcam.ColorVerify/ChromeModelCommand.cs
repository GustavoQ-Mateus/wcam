using System.Globalization;
using System.Text;
using System.Text.Json;

namespace Wcam.ColorVerify;

internal static class ChromeModelCommand
{
    private static readonly JsonSerializerOptions Json = new(JsonSerializerDefaults.Web) { WriteIndented = true };

    public static async Task<int> RunAsync(int port, string outputPath)
    {
        var server = new ModelServer(port);
        Console.WriteLine($"open {server.Url} in Chrome and click \"Read WCam\" (the probe must be publishing --patches)");
        string report = "";
        CanvasReadings readings = await server.ReceiveReadingsAsync(received =>
        {
            ModelFit srgb = ModelFit.From(RgbColorSpace.Srgb, ToRgb(received.Srgb));
            ModelFit displayP3 = ModelFit.From(RgbColorSpace.DisplayP3, ToRgb(received.DisplayP3));
            File.WriteAllText(outputPath, JsonSerializer.Serialize(new { srgb = srgb.Model, displayP3 = displayP3.Model }, Json));
            report = Format(srgb) + Format(displayP3) + $"model written to {Path.GetFullPath(outputPath)}\n";
            return report;
        });
        Console.WriteLine($"settings: {JsonSerializer.Serialize(readings.Settings)}");
        Console.Write(report);
        return 0;
    }

    public static string Format(ModelFit fit)
    {
        var text = new StringBuilder();
        text.AppendLine(CultureInfo.InvariantCulture, $"canvas {fit.CanvasSpace}: {fit.PatchesUsed} unclipped patches");
        text.AppendLine("  channel  offset   (Y-16)   (U-128)  (V-128)");
        AppendRow(text, "R fitted", fit.Model.Red);
        AppendRow(text, "R 709", ChromeModel.Bt709Exact.Red);
        AppendRow(text, "G fitted", fit.Model.Green);
        AppendRow(text, "G 709", ChromeModel.Bt709Exact.Green);
        AppendRow(text, "B fitted", fit.Model.Blue);
        AppendRow(text, "B 709", ChromeModel.Bt709Exact.Blue);
        AppendRow(text, "B libyuv", ChromeModel.Bt709Libyuv.Blue);
        text.AppendLine(CultureInfo.InvariantCulture,
            $"  residual: rms {fit.ResidualRms:F2}, max {fit.ResidualMaximum:F2} codes");
        text.AppendLine(CultureInfo.InvariantCulture,
            $"  dE2000 against exact BT.709, all patches: model mean {fit.ModelDeltaEMean:F2} max {fit.ModelDeltaEMaximum:F2}; " +
            $"measured mean {fit.MeasuredDeltaEMean:F2} max {fit.MeasuredDeltaEMaximum:F2}");
        return text.ToString();
    }

    private static void AppendRow(StringBuilder text, string label, double[] coefficients) =>
        text.AppendLine(CultureInfo.InvariantCulture,
            $"  {label,-8} {coefficients[0],7:F3}  {coefficients[1],7:F4}  {coefficients[2],7:F4}  {coefficients[3],7:F4}");

    private static Rgb[] ToRgb(double[][] values) => values.Select(value => new Rgb(value[0], value[1], value[2])).ToArray();
}
