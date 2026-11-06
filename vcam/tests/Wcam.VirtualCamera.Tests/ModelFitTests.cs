using Wcam.ColorVerify;
using Wcam.VirtualCamera.Probe;

namespace Wcam.VirtualCamera.Tests;

public class ModelFitTests
{
    [Fact]
    public void From_RoundedLibyuvSrgbCanvas_RecoversBlueFromUWithSmallResidual()
    {
        ModelFit fit = ModelFit.From(RgbColorSpace.Srgb, CanvasCodes(ChromeModel.Bt709Libyuv, RgbColorSpace.Srgb));
        Assert.Equal(2.0, fit.Model.Blue[2], 0.01);
        Assert.Equal(ChromeModel.Bt709Exact.Red[3], fit.Model.Red[3], 0.01);
        Assert.True(fit.ResidualMaximum <= 1, $"max residual {fit.ResidualMaximum}");
    }

    [Fact]
    public void From_DisplayP3Canvas_RecoversSameModelAsSrgb()
    {
        ModelFit fit = ModelFit.From(RgbColorSpace.DisplayP3, CanvasCodes(ChromeModel.Bt709Libyuv, RgbColorSpace.DisplayP3));
        Assert.Equal(2.0, fit.Model.Blue[2], 0.02);
        Assert.Equal(ChromeModel.Bt709Exact.Red[3], fit.Model.Red[3], 0.02);
    }

    [Fact]
    public void From_ClippedPatches_AreLeftOutOfTheFit()
    {
        Rgb[] codes = CanvasCodes(ChromeModel.Bt709Exact, RgbColorSpace.Srgb);
        ModelFit fit = ModelFit.From(RgbColorSpace.Srgb, codes);
        Assert.Equal(codes.Count(ModelFit.IsUnclipped), fit.PatchesUsed);
        Assert.True(fit.PatchesUsed < PatchGrid.Patches.Count);
    }

    [Fact]
    public void From_ExactBt709Canvas_HasNoDeltaEAgainstBt709()
    {
        ModelFit fit = ModelFit.From(RgbColorSpace.Srgb, CanvasCodes(ChromeModel.Bt709Exact, RgbColorSpace.Srgb));
        Assert.True(fit.MeasuredDeltaEMaximum < 0.5, $"max dE {fit.MeasuredDeltaEMaximum}");
    }

    [Fact]
    public void From_LibyuvCanvas_ShowsBlueDeviationAsDeltaE()
    {
        ModelFit fit = ModelFit.From(RgbColorSpace.Srgb, CanvasCodes(ChromeModel.Bt709Libyuv, RgbColorSpace.Srgb));
        Assert.True(fit.ModelDeltaEMaximum > 1, $"max dE {fit.ModelDeltaEMaximum}");
    }

    [Fact]
    public void From_WrongReadingCount_IsRejected()
    {
        Assert.Throws<ArgumentException>(() => ModelFit.From(RgbColorSpace.Srgb, [new Rgb(0, 0, 0)]));
    }

    private static Rgb[] CanvasCodes(ChromeModel model, RgbColorSpace space) =>
        PatchGrid.Patches
            .Select(patch => ColorScience.Clamp(model.Predict(patch.Y, patch.U, patch.V)))
            .Select(srgb => ColorScience.Convert(srgb, RgbColorSpace.Srgb, space))
            .Select(code => new Rgb(Math.Round(code.R), Math.Round(code.G), Math.Round(code.B)))
            .ToArray();
}
