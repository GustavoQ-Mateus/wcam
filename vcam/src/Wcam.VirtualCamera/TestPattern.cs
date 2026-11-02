namespace Wcam.VirtualCamera;

internal sealed class TestPattern
{
    public const int BarsHeight = VideoFormat.Height * 2 / 3;
    public const int BarCount = 8;
    public const int SweepTop = BarsHeight + 16;
    public const int SweepHeight = 40;
    public const int SweepWidth = 64;
    public const int SweepStep = 16;
    public const int CounterTop = SweepTop + SweepHeight + 40;
    public const int CounterDigits = 6;
    public const byte BackgroundLuma = 32;
    public const byte ForegroundLuma = 235;
    public const byte NeutralChroma = 128;
    private const int GlyphColumns = 5;
    private const int GlyphRows = 7;
    private const int GlyphScale = 16;
    private const int DigitSpacing = GlyphScale;
    private const int DigitAdvance = GlyphColumns * GlyphScale + DigitSpacing;
    private const int CounterModulo = 1_000_000;
    private const int ChromaPlaneOffset = VideoFormat.Width * VideoFormat.Height;
    private static readonly (byte Y, byte U, byte V)[] Bars =
    [
        (235, 128, 128),
        (219, 16, 138),
        (188, 154, 16),
        (173, 42, 26),
        (78, 214, 230),
        (63, 102, 240),
        (32, 240, 118),
        (16, 128, 128),
    ];
    private readonly byte[] _background = new byte[VideoFormat.FrameSize];

    public TestPattern()
    {
        RenderBackground(_background);
    }

    public static int BarWidth => VideoFormat.Width / BarCount;

    public static int CounterLeft => (VideoFormat.Width - CounterDigits * DigitAdvance + DigitSpacing) / 2;

    private static ReadOnlySpan<byte> DigitGlyphs =>
    [
        0b01110, 0b10001, 0b10011, 0b10101, 0b11001, 0b10001, 0b01110,
        0b00100, 0b01100, 0b00100, 0b00100, 0b00100, 0b00100, 0b01110,
        0b01110, 0b10001, 0b00001, 0b00010, 0b00100, 0b01000, 0b11111,
        0b11111, 0b00010, 0b00100, 0b00010, 0b00001, 0b10001, 0b01110,
        0b00010, 0b00110, 0b01010, 0b10010, 0b11111, 0b00010, 0b00010,
        0b11111, 0b10000, 0b11110, 0b00001, 0b00001, 0b10001, 0b01110,
        0b00110, 0b01000, 0b10000, 0b11110, 0b10001, 0b10001, 0b01110,
        0b11111, 0b00001, 0b00010, 0b00100, 0b01000, 0b01000, 0b01000,
        0b01110, 0b10001, 0b10001, 0b01110, 0b10001, 0b10001, 0b01110,
        0b01110, 0b10001, 0b10001, 0b01111, 0b00001, 0b00010, 0b01100,
    ];

    public static (byte Y, byte U, byte V) BarColor(int index) => Bars[index];

    public static int SweepLeft(long frameNumber) => (int)(frameNumber * SweepStep % (VideoFormat.Width - SweepWidth));

    public void Render(Span<byte> frame, long frameNumber)
    {
        _background.CopyTo(frame);
        FillLuma(frame, SweepLeft(frameNumber), SweepTop, SweepWidth, SweepHeight);
        DrawCounter(frame, (int)(frameNumber % CounterModulo));
    }

    private static void RenderBackground(Span<byte> frame)
    {
        Span<byte> luma = frame[..ChromaPlaneOffset];
        Span<byte> chroma = frame[ChromaPlaneOffset..];
        luma.Fill(BackgroundLuma);
        chroma.Fill(NeutralChroma);
        for (int row = 0; row < BarsHeight; row++)
        {
            for (int bar = 0; bar < BarCount; bar++)
            {
                luma.Slice(row * VideoFormat.Width + bar * BarWidth, BarWidth).Fill(Bars[bar].Y);
            }
        }
        for (int row = 0; row < BarsHeight / 2; row++)
        {
            for (int column = 0; column < VideoFormat.Width / 2; column++)
            {
                (byte _, byte u, byte v) = Bars[column * 2 / BarWidth];
                int offset = row * VideoFormat.Width + column * 2;
                chroma[offset] = u;
                chroma[offset + 1] = v;
            }
        }
    }

    private static void DrawCounter(Span<byte> frame, int value)
    {
        for (int position = CounterDigits - 1; position >= 0; position--)
        {
            DrawDigit(frame, value % 10, CounterLeft + position * DigitAdvance);
            value /= 10;
        }
    }

    private static void DrawDigit(Span<byte> frame, int digit, int left)
    {
        ReadOnlySpan<byte> glyph = DigitGlyphs.Slice(digit * GlyphRows, GlyphRows);
        for (int row = 0; row < GlyphRows; row++)
        {
            for (int column = 0; column < GlyphColumns; column++)
            {
                if ((glyph[row] & (1 << (GlyphColumns - 1 - column))) == 0)
                {
                    continue;
                }
                FillLuma(frame, left + column * GlyphScale, CounterTop + row * GlyphScale, GlyphScale, GlyphScale);
            }
        }
    }

    private static void FillLuma(Span<byte> frame, int left, int top, int width, int height)
    {
        for (int row = top; row < top + height; row++)
        {
            frame.Slice(row * VideoFormat.Width + left, width).Fill(ForegroundLuma);
        }
    }
}
