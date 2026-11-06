namespace Wcam.ColorVerify;

internal sealed record YuvPlanes(int Width, int Height, byte[] Y, byte[] U, byte[] V)
{
    public void Validate()
    {
        int size = Width * Height;
        if (Y.Length != size || U.Length != size || V.Length != size)
        {
            throw new InvalidDataException($"each plane needs {Width}x{Height} = {size} bytes");
        }
    }
}
