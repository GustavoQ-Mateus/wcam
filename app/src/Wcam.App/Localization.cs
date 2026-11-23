using System.Text.Json;

namespace Wcam.App;

internal sealed class Localization
{
    public const string English = "en";
    public const string Portuguese = "pt-BR";

    private readonly IReadOnlyDictionary<string, string> _catalog;

    public Localization(IReadOnlyDictionary<string, string> catalog)
    {
        _catalog = catalog;
    }

    public static string ResolveLanguage(string tag) =>
        tag.StartsWith("pt", StringComparison.OrdinalIgnoreCase) ? Portuguese : English;

    public static Localization Load(string localesDirectory, string language)
    {
        using FileStream stream = File.OpenRead(Path.Combine(localesDirectory, $"{language}.json"));
        using JsonDocument document = JsonDocument.Parse(stream);
        var catalog = new Dictionary<string, string>();
        foreach (JsonProperty property in document.RootElement.EnumerateObject())
        {
            catalog[property.Name] = property.Value.GetString() ?? string.Empty;
        }
        return new Localization(catalog);
    }

    public string Text(string key) => _catalog[key];

    public string Text(string key, string name, string value) => _catalog[key].Replace($"{{{name}}}", value);
}
