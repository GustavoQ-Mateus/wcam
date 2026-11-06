namespace Wcam.ColorVerify;

internal sealed record PlaneTables(int[] Y, int[] U, int[] V)
{
    public const int Entries = 256;

    public static PlaneTables Identity { get; } = new(IdentityTable(), IdentityTable(), IdentityTable());

    public void Validate()
    {
        if (Y.Length != Entries || U.Length != Entries || V.Length != Entries)
        {
            throw new InvalidDataException($"each table needs {Entries} entries");
        }
    }

    private static int[] IdentityTable() => Enumerable.Range(0, Entries).ToArray();
}
