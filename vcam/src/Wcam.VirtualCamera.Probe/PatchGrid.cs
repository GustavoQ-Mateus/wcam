namespace Wcam.VirtualCamera.Probe;

internal readonly record struct Patch(int Left, int Top, byte Y, byte U, byte V);

internal static class PatchGrid
{
    public const int Columns = 16;
    public const int Rows = 9;
    public const int CellSize = VideoFormat.Width / Columns;
    public const int ReadMargin = CellSize / 4;
    public const byte LowLuma = 80;
    public const byte HighLuma = 150;
    public const byte NeutralChroma = 128;
    private const int ChromaPlaneOffset = VideoFormat.Width * VideoFormat.Height;
    private const int ChromaLevelCount = 8;
    private const int LimitedBlack = 16;
    private const int LimitedRange = 219;
    private static readonly byte[] ChromaLevels = [44, 68, 92, 116, 140, 164, 188, 212];

    public static IReadOnlyList<Patch> Patches { get; } = CreatePatches();

    public static void Render(Span<byte> frame)
    {
        foreach (Patch patch in Patches)
        {
            FillPatch(frame, patch);
        }
    }

    private static List<Patch> CreatePatches()
    {
        var patches = new List<Patch>(Columns * Rows);
        for (int column = 0; column < Columns; column++)
        {
            byte luma = (byte)Math.Round(LimitedBlack + column * LimitedRange / (double)(Columns - 1));
            patches.Add(new Patch(column * CellSize, 0, luma, NeutralChroma, NeutralChroma));
        }
        for (int row = 1; row < Rows; row++)
        {
            for (int column = 0; column < Columns; column++)
            {
                byte luma = column < ChromaLevelCount ? LowLuma : HighLuma;
                byte u = ChromaLevels[column % ChromaLevelCount];
                byte v = ChromaLevels[row - 1];
                patches.Add(new Patch(column * CellSize, row * CellSize, luma, u, v));
            }
        }
        return patches;
    }

    private static void FillPatch(Span<byte> frame, Patch patch)
    {
        for (int row = patch.Top; row < patch.Top + CellSize; row++)
        {
            frame.Slice(row * VideoFormat.Width + patch.Left, CellSize).Fill(patch.Y);
        }
        for (int row = patch.Top / 2; row < (patch.Top + CellSize) / 2; row++)
        {
            Span<byte> chromaRow = frame.Slice(ChromaPlaneOffset + row * VideoFormat.Width + patch.Left, CellSize);
            for (int column = 0; column < CellSize; column += 2)
            {
                chromaRow[column] = patch.U;
                chromaRow[column + 1] = patch.V;
            }
        }
    }
}
