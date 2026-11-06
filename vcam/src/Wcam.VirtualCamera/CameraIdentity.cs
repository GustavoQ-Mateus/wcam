namespace Wcam.VirtualCamera;

internal static class CameraIdentity
{
    public const string FriendlyName = "WCam";
    public const string SourceDescription = "WCam Media Source";
    public static readonly Guid SourceClassId = new("F2F06D1E-FA8A-4930-83F6-D85D4E2190C3");
    public static string SourceClassKey => $@"SOFTWARE\Classes\CLSID\{SourceClassId:B}";
}
