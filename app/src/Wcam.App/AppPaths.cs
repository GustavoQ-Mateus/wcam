namespace Wcam.App;

internal static class AppPaths
{
    public const string ChildArgument = "--child";
    private const string DataVariable = "WCAM_DATA_DIR";
    private const string LocalesVariable = "WCAM_LOCALES_DIR";
    private const string UvVariable = "WCAM_UV";
    private const string FramesSectionVariable = "WCAM_FRAMES_SECTION";
    private const string AgentFolder = "agent";
    private const string AgentExecutable = "wcam.exe";
    private const string SettingsFile = "app.json";

    public static string DataDirectory => Environment.GetEnvironmentVariable(DataVariable)
        ?? Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData), "wcam");

    public static string Settings => Path.Combine(DataDirectory, SettingsFile);

    public static string Executable => Environment.ProcessPath ?? Path.Combine(AppContext.BaseDirectory, "WCam.exe");

    public static string Locales => Environment.GetEnvironmentVariable(LocalesVariable)
        ?? FindUpwards("locales")
        ?? Path.Combine(AppContext.BaseDirectory, "locales");

    public static string FramesSection =>
        Environment.GetEnvironmentVariable(FramesSectionVariable) ?? PublishedFrameReader.SectionName;

    public static AgentCommand Agent()
    {
        string installed = Path.Combine(AppContext.BaseDirectory, AgentFolder, AgentExecutable);
        if (File.Exists(installed))
        {
            return new AgentCommand(installed, [ChildArgument], Path.GetDirectoryName(installed)!);
        }
        string repositoryAgent = FindUpwards(AgentFolder) ?? AgentFolder;
        string uv = Environment.GetEnvironmentVariable(UvVariable) ?? "uv";
        return new AgentCommand(uv, ["run", "wcam", ChildArgument], repositoryAgent);
    }

    private static string? FindUpwards(string folder)
    {
        for (DirectoryInfo? directory = new(AppContext.BaseDirectory); directory is not null; directory = directory.Parent)
        {
            string candidate = Path.Combine(directory.FullName, folder);
            if (Directory.Exists(candidate))
            {
                return candidate;
            }
        }
        return null;
    }
}
