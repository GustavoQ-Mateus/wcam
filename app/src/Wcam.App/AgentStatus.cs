using System.Text.Json;

namespace Wcam.App;

internal enum Facing
{
    None,
    User,
    Environment,
}

internal sealed record Controls(bool Frozen, bool CameraOff, bool Mirror, Facing Facing);

internal sealed record AgentStatus(
    bool CameraActive,
    string? CameraSource,
    string? SessionState,
    Controls Controls,
    bool VideoActive,
    bool TimelineHasClips)
{
    public const string LiveState = "live";
    public const string PhoneSource = "phone";

    public static readonly AgentStatus Unknown =
        new(false, null, null, new Controls(false, false, false, Facing.None), false, false);

    public bool HasSession => SessionState is not null;

    public bool Live => SessionState == LiveState;

    public static AgentStatus Parse(string json)
    {
        using JsonDocument document = JsonDocument.Parse(json);
        JsonElement root = document.RootElement;
        JsonElement camera = Child(root, "virtualCamera");
        JsonElement session = Child(root, "session");
        JsonElement controls = Child(root, "controls");
        JsonElement video = Child(root, "videoSource");
        JsonElement timeline = Child(video, "timeline");
        JsonElement clips = Child(timeline, "clips");
        return new AgentStatus(
            String(camera, "state") == "active",
            String(camera, "source"),
            String(session, "state"),
            new Controls(
                Boolean(controls, "frozen"),
                Boolean(controls, "cameraOff"),
                Boolean(controls, "mirror"),
                ParseFacing(String(controls, "facing"))),
            Boolean(video, "active"),
            clips.ValueKind == JsonValueKind.Array && clips.GetArrayLength() > 0);
    }

    private static Facing ParseFacing(string? facing) => facing switch
    {
        "user" => Facing.User,
        "environment" => Facing.Environment,
        _ => Facing.None,
    };

    private static JsonElement Child(JsonElement parent, string name) =>
        parent.ValueKind == JsonValueKind.Object && parent.TryGetProperty(name, out JsonElement child) ? child : default;

    private static string? String(JsonElement parent, string name)
    {
        JsonElement value = Child(parent, name);
        return value.ValueKind == JsonValueKind.String ? value.GetString() : null;
    }

    private static bool Boolean(JsonElement parent, string name) => Child(parent, name).ValueKind == JsonValueKind.True;
}
