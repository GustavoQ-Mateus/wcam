namespace Wcam.VirtualCamera.Probe;

internal static class FormatPattern
{
    public const byte BackgroundLuma = 32;
    public const byte ForegroundLuma = 235;
    public const byte NeutralChroma = 128;
    private const int GlyphColumns = 5;
    private const int GlyphRows = 7;
    private const int GlyphScaleDivisor = 68;
    private const int SweepDivisor = 30;
    private const int CounterDigits = 6;
    private const int CounterModulo = 1_000_000;

    public static void Render(Span<byte> frame, FrameFormat format, long frameNumber)
    {
        frame[..format.LumaSize].Fill(BackgroundLuma);
        frame[format.LumaSize..format.FrameSize].Fill(NeutralChroma);
        int scale = format.Height / GlyphScaleDivisor;
        DrawNumber(frame, format, format.Width, 4, scale, scale);
        DrawNumber(frame, format, format.Height, 4, scale, scale * 10);
        DrawNumber(frame, format, format.FramesPerSecond, 2, scale, scale * 19);
        DrawNumber(frame, format, (int)(frameNumber % CounterModulo), CounterDigits, scale, scale * 28);
        DrawSweep(frame, format, frameNumber, scale);
    }

    private static void DrawSweep(Span<byte> frame, FrameFormat format, long frameNumber, int scale)
    {
        int width = format.Width / SweepDivisor;
        int left = (int)(frameNumber * scale % (format.Width - width));
        FillLuma(frame, format, left, scale * 40, width, scale * 10);
    }

    private static void DrawNumber(Span<byte> frame, FrameFormat format, int value, int digits, int scale, int top)
    {
        int advance = (GlyphColumns + 1) * scale;
        for (int position = digits - 1; position >= 0; position--)
        {
            DrawDigit(frame, format, value % 10, scale + position * advance, top, scale);
            value /= 10;
        }
    }

    private static void DrawDigit(Span<byte> frame, FrameFormat format, int digit, int left, int top, int scale)
    {
        ReadOnlySpan<byte> glyph = TestPattern.DigitGlyphs.Slice(digit * GlyphRows, GlyphRows);
        for (int row = 0; row < GlyphRows; row++)
        {
            for (int column = 0; column < GlyphColumns; column++)
            {
                if ((glyph[row] & (1 << (GlyphColumns - 1 - column))) != 0)
                {
                    FillLuma(frame, format, left + column * scale, top + row * scale, scale, scale);
                }
            }
        }
    }

    private static void FillLuma(Span<byte> frame, FrameFormat format, int left, int top, int width, int height)
    {
        for (int row = top; row < top + height; row++)
        {
            frame.Slice(row * format.Width + left, width).Fill(ForegroundLuma);
        }
    }
}
