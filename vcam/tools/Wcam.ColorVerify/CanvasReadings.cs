namespace Wcam.ColorVerify;

internal sealed record CanvasReadings(double[][] Srgb, double[][] DisplayP3, Dictionary<string, object>? Settings);
