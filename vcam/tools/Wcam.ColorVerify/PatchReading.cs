namespace Wcam.ColorVerify;

internal readonly record struct PatchReading(byte Y, byte U, byte V, Rgb Measured);
