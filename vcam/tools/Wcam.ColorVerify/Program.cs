namespace Wcam.ColorVerify;

internal static class Program
{
    private const string ChromeModelCommandName = "chrome-model";
    private const string VerifyCommandName = "verify";
    private const string PortOption = "--port";
    private const string OutputOption = "--out";
    private const string ModelOption = "--model";
    private const char ModelSeparator = '=';
    private const int DefaultPort = 8765;
    private const string DefaultOutput = "chrome-model.json";
    private const string Usage =
        "usage: Wcam.ColorVerify chrome-model [--port <port>] [--out <file>]\n" +
        "       Wcam.ColorVerify verify <trace dir> --model <label>=<file> [--model <label>=<file> ...]";

    private static async Task<int> Main(string[] args)
    {
        if (args.Length > 0 && args[0] == ChromeModelCommandName && TryParseChromeModel(args[1..], out int port, out string output))
        {
            return await ChromeModelCommand.RunAsync(port, output);
        }
        if (args.Length > 1 && args[0] == VerifyCommandName && TryParseModels(args[2..], out Dictionary<string, string> models))
        {
            return VerifyCommand.Run(args[1], models);
        }
        Console.Error.WriteLine(Usage);
        return 2;
    }

    private static bool TryParseChromeModel(string[] args, out int port, out string output)
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

    private static bool TryParseModels(string[] args, out Dictionary<string, string> models)
    {
        models = [];
        for (int index = 0; index < args.Length; index += 2)
        {
            if (args[index] != ModelOption || index + 1 >= args.Length)
            {
                return false;
            }
            string[] parts = args[index + 1].Split(ModelSeparator, 2);
            if (parts.Length != 2)
            {
                return false;
            }
            models[parts[0]] = parts[1];
        }
        return models.Count > 0;
    }
}
