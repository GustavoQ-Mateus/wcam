using System.Text.Json;
using Wcam.ColorVerify;

namespace Wcam.VirtualCamera.Tests;

public class SampleComparisonTests
{
    private const int Width = 16;
    private const int Height = 9;

    [Fact]
    public void MeanDeltaE_SampleRenderedFromSameFrame_IsBelowRoundingNoise()
    {
        YuvPlanes frame = Frame();
        byte[] sample = Render(frame, PlaneTables.Identity, ChromeModel.Bt709Exact, mirrored: false);
        double deltaE = SampleComparison.MeanDeltaE(
            sample, RgbColorSpace.Srgb, frame, false, PlaneTables.Identity, ChromeModel.Bt709Exact);
        Assert.True(deltaE < 0.3, $"dE {deltaE}");
    }

    [Fact]
    public void MeanDeltaE_MirroredMatch_ComparesFlippedFrame()
    {
        YuvPlanes frame = Frame();
        byte[] sample = Render(frame, PlaneTables.Identity, ChromeModel.Bt709Exact, mirrored: true);
        double flipped = SampleComparison.MeanDeltaE(
            sample, RgbColorSpace.Srgb, frame, true, PlaneTables.Identity, ChromeModel.Bt709Exact);
        double straight = SampleComparison.MeanDeltaE(
            sample, RgbColorSpace.Srgb, frame, false, PlaneTables.Identity, ChromeModel.Bt709Exact);
        Assert.True(flipped < 0.3, $"dE {flipped}");
        Assert.True(straight > 5, $"dE {straight}");
    }

    [Fact]
    public void MeanDeltaE_SampleFromCorrectedFrame_IsLowAfterAndHighBeforeTheTables()
    {
        YuvPlanes frame = Frame();
        PlaneTables brighter = new(Shift(20), PlaneTables.Identity.U, PlaneTables.Identity.V);
        byte[] sample = Render(frame, brighter, ChromeModel.Bt709Exact, mirrored: false);
        double before = SampleComparison.MeanDeltaE(
            sample, RgbColorSpace.Srgb, frame, false, PlaneTables.Identity, ChromeModel.Bt709Exact);
        double after = SampleComparison.MeanDeltaE(
            sample, RgbColorSpace.Srgb, frame, false, brighter, ChromeModel.Bt709Exact);
        Assert.True(after < 0.3, $"after {after}");
        Assert.True(before > 3, $"before {before}");
    }

    [Fact]
    public void MeanDeltaE_DisplayP3Sample_MatchesSameColorsInSrgb()
    {
        YuvPlanes frame = Frame();
        byte[] srgb = Render(frame, PlaneTables.Identity, ChromeModel.Bt709Exact, mirrored: false);
        byte[] displayP3 = ToDisplayP3(srgb);
        double deltaE = SampleComparison.MeanDeltaE(
            displayP3, RgbColorSpace.DisplayP3, frame, false, PlaneTables.Identity, ChromeModel.Bt709Exact);
        Assert.True(deltaE < 0.5, $"dE {deltaE}");
    }

    [Fact]
    public void MeanDeltaE_SampleSizeDifferentFromFrame_IsRejected()
    {
        Assert.Throws<InvalidDataException>(() => SampleComparison.MeanDeltaE(
            new byte[3], RgbColorSpace.Srgb, Frame(), false, PlaneTables.Identity, ChromeModel.Bt709Exact));
    }

    [Fact]
    public void ReadTrace_AgentJson_ParsesSampleAndTables()
    {
        string directory = Directory.CreateTempSubdirectory().FullName;
        try
        {
            string plane = Convert.ToBase64String(new byte[4]);
            var sampleJson = new Dictionary<string, object>
            {
                ["colorSpace"] = "display-p3",
                ["width"] = 2,
                ["height"] = 2,
                ["rgb"] = Convert.ToBase64String(new byte[12]),
                ["capturedAt"] = 1.5,
                ["receivedAt"] = 2.5,
                ["calibrationState"] = "measuring",
                ["correlation"] = 0.97,
                ["mirrored"] = true,
                ["colorRange"] = "full",
                ["matchedFrame"] = new { y = plane, u = plane, v = plane },
            };
            int[] table = Enumerable.Range(0, PlaneTables.Entries).ToArray();
            var tables = new { y = table, u = table, v = table };
            var calibrationJson = new { state = "applied", deltaE = 1.2, rangeTables = tables, appliedTables = tables };
            File.WriteAllText(Path.Combine(directory, "color-sample-1.json"), JsonSerializer.Serialize(sampleJson));
            File.WriteAllText(Path.Combine(directory, ColorTrace.CalibrationFile), JsonSerializer.Serialize(calibrationJson));
            TraceSample sample = ColorTrace.ReadSamples(directory).Single().Sample;
            CalibrationTrace calibration = ColorTrace.Read<CalibrationTrace>(Path.Combine(directory, ColorTrace.CalibrationFile));
            Assert.Equal(RgbColorSpace.DisplayP3, sample.Space);
            Assert.True(sample.Mirrored);
            Assert.Equal(4, sample.Frame.Y.Length);
            Assert.Equal("applied", calibration.State);
            Assert.Equal(255, calibration.AppliedTables.V[255]);
        }
        finally
        {
            Directory.Delete(directory, true);
        }
    }

    private static YuvPlanes Frame()
    {
        int size = Width * Height;
        byte[] y = new byte[size];
        byte[] u = new byte[size];
        byte[] v = new byte[size];
        for (int pixel = 0; pixel < size; pixel++)
        {
            int column = pixel % Width;
            int row = pixel / Width;
            y[pixel] = (byte)(40 + column * 10);
            u[pixel] = (byte)(100 + row * 6);
            v[pixel] = (byte)(150 - column * 3);
        }
        return new YuvPlanes(Width, Height, y, u, v);
    }

    private static byte[] Render(YuvPlanes frame, PlaneTables tables, ChromeModel model, bool mirrored)
    {
        byte[] rgb = new byte[Width * Height * 3];
        for (int pixel = 0; pixel < Width * Height; pixel++)
        {
            int column = pixel % Width;
            int source = pixel - column + (mirrored ? Width - 1 - column : column);
            Rgb color = ColorScience.Clamp(model.Predict(
                (byte)tables.Y[frame.Y[source]], (byte)tables.U[frame.U[source]], (byte)tables.V[frame.V[source]]));
            rgb[pixel * 3] = (byte)Math.Round(color.R);
            rgb[pixel * 3 + 1] = (byte)Math.Round(color.G);
            rgb[pixel * 3 + 2] = (byte)Math.Round(color.B);
        }
        return rgb;
    }

    private static byte[] ToDisplayP3(byte[] srgb)
    {
        byte[] result = new byte[srgb.Length];
        for (int offset = 0; offset < srgb.Length; offset += 3)
        {
            Rgb converted = ColorScience.Convert(
                new Rgb(srgb[offset], srgb[offset + 1], srgb[offset + 2]), RgbColorSpace.Srgb, RgbColorSpace.DisplayP3);
            result[offset] = (byte)Math.Round(converted.R);
            result[offset + 1] = (byte)Math.Round(converted.G);
            result[offset + 2] = (byte)Math.Round(converted.B);
        }
        return result;
    }

    private static int[] Shift(int amount) => Enumerable.Range(0, PlaneTables.Entries).Select(value => Math.Min(255, value + amount)).ToArray();
}
