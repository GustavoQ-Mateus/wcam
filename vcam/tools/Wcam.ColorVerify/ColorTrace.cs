using System.Text.Json;

namespace Wcam.ColorVerify;

internal sealed record TracePlanes(string Y, string U, string V);

internal sealed record TraceSample(
    string ColorSpace,
    int Width,
    int Height,
    string Rgb,
    double CapturedAt,
    double ReceivedAt,
    string CalibrationState,
    double Correlation,
    bool Mirrored,
    string? ColorRange,
    TracePlanes MatchedFrame)
{
    private const string SrgbName = "srgb";
    private const string DisplayP3Name = "display-p3";

    public RgbColorSpace Space => ColorSpace switch
    {
        SrgbName => RgbColorSpace.Srgb,
        DisplayP3Name => RgbColorSpace.DisplayP3,
        _ => throw new InvalidDataException($"unknown colorSpace {ColorSpace}"),
    };

    public byte[] RgbBytes => Convert.FromBase64String(Rgb);

    public YuvPlanes Frame => new(
        Width,
        Height,
        Convert.FromBase64String(MatchedFrame.Y),
        Convert.FromBase64String(MatchedFrame.U),
        Convert.FromBase64String(MatchedFrame.V));
}

internal sealed record CalibrationTrace(string State, double? DeltaE, PlaneTables RangeTables, PlaneTables AppliedTables);

internal sealed record ModelSet(ChromeModel Srgb, ChromeModel DisplayP3)
{
    public ChromeModel For(RgbColorSpace space) => space == RgbColorSpace.Srgb ? Srgb : DisplayP3;
}

internal static class ColorTrace
{
    public const string CalibrationFile = "color-calibration.json";
    public const string SamplePattern = "color-sample-*.json";
    private static readonly JsonSerializerOptions Json = new(JsonSerializerDefaults.Web);

    public static T Read<T>(string path) =>
        JsonSerializer.Deserialize<T>(File.ReadAllText(path), Json) ?? throw new InvalidDataException($"empty file {path}");

    public static IReadOnlyList<(string Name, TraceSample Sample)> ReadSamples(string directory) =>
        Directory.GetFiles(directory, SamplePattern)
            .OrderBy(path => path.Length)
            .ThenBy(path => path, StringComparer.Ordinal)
            .Select(path => (Path.GetFileName(path), Read<TraceSample>(path)))
            .ToArray();
}
