using Wcam.VirtualCamera.Probe;

namespace Wcam.VirtualCamera.Tests;

public class PatchGridTests
{
    private const int ChromaPlaneOffset = VideoFormat.Width * VideoFormat.Height;

    [Fact]
    public void Patches_CoverWholeFrameWithoutOverlap()
    {
        var covered = new bool[PatchGrid.Columns, PatchGrid.Rows];
        foreach (Patch patch in PatchGrid.Patches)
        {
            int column = patch.Left / PatchGrid.CellSize;
            int row = patch.Top / PatchGrid.CellSize;
            Assert.False(covered[column, row]);
            covered[column, row] = true;
        }
        Assert.Equal(VideoFormat.Width, PatchGrid.Columns * PatchGrid.CellSize);
        Assert.Equal(VideoFormat.Height, PatchGrid.Rows * PatchGrid.CellSize);
        Assert.All(covered.Cast<bool>(), Assert.True);
    }

    [Fact]
    public void Patches_AreAlignedToChromaSubsampling()
    {
        Assert.Equal(0, PatchGrid.CellSize % 2);
        Assert.All(PatchGrid.Patches, patch => Assert.Equal(0, patch.Left % 2 + patch.Top % 2));
    }

    [Fact]
    public void Patches_FirstRowIsNeutralRampFromBlackToWhite()
    {
        Patch[] ramp = PatchGrid.Patches.Where(patch => patch.Top == 0).OrderBy(patch => patch.Left).ToArray();
        Assert.Equal(16, ramp[0].Y);
        Assert.Equal(235, ramp[^1].Y);
        Assert.All(ramp, patch => Assert.Equal((PatchGrid.NeutralChroma, PatchGrid.NeutralChroma), (patch.U, patch.V)));
        Assert.True(ramp.Zip(ramp.Skip(1)).All(pair => pair.First.Y < pair.Second.Y));
    }

    [Fact]
    public void Patches_ColorRowsCoverBothLumaLevelsWithDistinctColors()
    {
        Patch[] colors = PatchGrid.Patches.Where(patch => patch.Top > 0).ToArray();
        Assert.Equal([PatchGrid.LowLuma, PatchGrid.HighLuma], colors.Select(patch => patch.Y).Distinct().Order());
        Assert.Equal(colors.Length, colors.Select(patch => (patch.Y, patch.U, patch.V)).Distinct().Count());
    }

    [Fact]
    public void Render_EachPatchCenter_HasPatchLumaAndChroma()
    {
        byte[] frame = new byte[VideoFormat.FrameSize];
        PatchGrid.Render(frame);
        foreach (Patch patch in PatchGrid.Patches)
        {
            int row = patch.Top + PatchGrid.CellSize / 2;
            int column = patch.Left + PatchGrid.CellSize / 2;
            int chroma = ChromaPlaneOffset + row / 2 * VideoFormat.Width + column / 2 * 2;
            Assert.Equal(patch.Y, frame[row * VideoFormat.Width + column]);
            Assert.Equal(patch.U, frame[chroma]);
            Assert.Equal(patch.V, frame[chroma + 1]);
        }
    }
}
