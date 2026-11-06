using Wcam.ColorVerify;
using Wcam.VirtualCamera.Probe;

namespace Wcam.VirtualCamera.Tests;

public class ChromeModelTests
{
    private const double CoefficientTolerance = 1e-9;

    [Fact]
    public void Fit_ExactAffineReadings_RecoversCoefficients()
    {
        var known = new ChromeModel([3, 1.1, 0.05, 1.7], [-2, 1.2, -0.25, -0.5], [1, 1.15, 1.9, 0.02]);
        ChromeModel fitted = ChromeModel.Fit(Readings(known));
        for (int index = 0; index < 4; index++)
        {
            Assert.Equal(known.Red[index], fitted.Red[index], CoefficientTolerance);
            Assert.Equal(known.Green[index], fitted.Green[index], CoefficientTolerance);
            Assert.Equal(known.Blue[index], fitted.Blue[index], CoefficientTolerance);
        }
    }

    [Fact]
    public void Fit_LibyuvBt709Readings_RecoversBlueFromUOfTwo()
    {
        ChromeModel fitted = ChromeModel.Fit(Readings(ChromeModel.Bt709Libyuv));
        Assert.Equal(2.0, fitted.Blue[2], CoefficientTolerance);
    }

    [Fact]
    public void Fit_SaturationScaledReadings_ScalesOnlyChromaCoefficients()
    {
        const double saturation = 0.9;
        ChromeModel exact = ChromeModel.Bt709Exact;
        var scaled = new ChromeModel(Scale(exact.Red, saturation), Scale(exact.Green, saturation), Scale(exact.Blue, saturation));
        ChromeModel fitted = ChromeModel.Fit(Readings(scaled));
        Assert.Equal(exact.Red[1], fitted.Red[1], CoefficientTolerance);
        Assert.Equal(exact.Red[3] * saturation, fitted.Red[3], CoefficientTolerance);
        Assert.Equal(exact.Blue[2] * saturation, fitted.Blue[2], CoefficientTolerance);
    }

    [Fact]
    public void Fit_FewerThanFourReadings_IsRejected()
    {
        PatchReading[] readings = Readings(ChromeModel.Bt709Exact).Take(3).ToArray();
        Assert.Throws<ArgumentException>(() => ChromeModel.Fit(readings));
    }

    [Fact]
    public void Bt709Exact_LimitedRangeExtremes_DecodeToBlackAndWhite()
    {
        Rgb black = ChromeModel.Bt709Exact.Predict(16, 128, 128);
        Rgb white = ChromeModel.Bt709Exact.Predict(235, 128, 128);
        Assert.Equal(new Rgb(0, 0, 0), black);
        Assert.Equal(255, white.R, 1e-9);
        Assert.Equal(255, white.G, 1e-9);
        Assert.Equal(255, white.B, 1e-9);
    }

    [Fact]
    public void Bt709Exact_ChromaCoefficients_MatchStandard()
    {
        Assert.Equal(1.7927, ChromeModel.Bt709Exact.Red[3], 0.0001);
        Assert.Equal(-0.2132, ChromeModel.Bt709Exact.Green[2], 0.0001);
        Assert.Equal(-0.5329, ChromeModel.Bt709Exact.Green[3], 0.0001);
        Assert.Equal(2.1124, ChromeModel.Bt709Exact.Blue[2], 0.0001);
    }

    private static PatchReading[] Readings(ChromeModel model) =>
        PatchGrid.Patches
            .Select(patch => new PatchReading(patch.Y, patch.U, patch.V, model.Predict(patch.Y, patch.U, patch.V)))
            .ToArray();

    private static double[] Scale(double[] coefficients, double saturation) =>
        [coefficients[0], coefficients[1], coefficients[2] * saturation, coefficients[3] * saturation];
}
