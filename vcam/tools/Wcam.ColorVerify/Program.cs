namespace Wcam.ColorVerify;

internal static class Program
{
    private const string ChromeModelCommandName = "chrome-model";
    private const string PortOption = "--port";
    private const string OutputOption = "--out";
    private const int DefaultPort = 8765;
    private const string DefaultOutput = "chrome-model.json";
    private const string Usage = "usage: Wcam.ColorVerify chrome-model [--port <port>] [--out <file>]";

    private static async Task<int> Main(string[] args)
    {
        if (args.Length == 0 || args[0] != ChromeModelCommandName || !TryParse(args[1..], out int port, out string output))
        {
            Console.Error.WriteLine(Usage);
            return 2;
        }
        return await ChromeModelCommand.RunAsync(port, output);
    }

    private static bool TryParse(string[] args, out int port, out string output)
    {
        port = DefaultPort;
        output = DefaultOutput;
        for (int index = 0; index < args.Length; index++)
        {
            if (index + 1 >= args.Length)
            {
                return false;
            }
            switch (args[index])
            {
                case PortOption when int.TryParse(args[++index], out int parsed):
                    port = parsed;
                    break;
                case OutputOption:
                    output = args[++index];
                    break;
                default:
                    return false;
            }
        }
        return true;
    }
}
