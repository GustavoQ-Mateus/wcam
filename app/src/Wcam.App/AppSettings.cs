using System.Text.Json;
using System.Text.Json.Serialization;

namespace Wcam.App;

internal sealed record WindowBounds(int X, int Y, int Width, int Height);

internal sealed record AppSettings
{
    public const string DefaultHotkey = "Ctrl+Alt+W";

    public WindowBounds? ConsoleWindow { get; init; }

    public bool OverlayVisible { get; init; } = true;

    public EdgePlacement? OverlayPlacement { get; init; }

    public bool FloatingPreviewVisible { get; init; }

    public WindowBounds? FloatingPreview { get; init; }

    public string Hotkey { get; init; } = DefaultHotkey;

    public static AppSettings Load(string path)
    {
        try
        {
            using FileStream stream = File.OpenRead(path);
            return JsonSerializer.Deserialize(stream, SettingsJson.Default.AppSettings) ?? new AppSettings();
        }
        catch (Exception exception) when (exception is IOException or JsonException or UnauthorizedAccessException)
        {
            return new AppSettings();
        }
    }

    public void Save(string path)
    {
        Directory.CreateDirectory(Path.GetDirectoryName(path)!);
        string temporary = path + ".tmp";
        File.WriteAllText(temporary, JsonSerializer.Serialize(this, SettingsJson.Default.AppSettings));
        File.Move(temporary, path, overwrite: true);
    }
}

[JsonSourceGenerationOptions(WriteIndented = true, UseStringEnumConverter = true)]
[JsonSerializable(typeof(AppSettings))]
internal sealed partial class SettingsJson : JsonSerializerContext;
