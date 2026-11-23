namespace Wcam.App;

internal enum ScreenEdge
{
    Left,
    Top,
    Right,
    Bottom,
}

internal readonly record struct ScreenRect(int Left, int Top, int Right, int Bottom)
{
    public int Width => Right - Left;

    public int Height => Bottom - Top;

    public bool Contains(int x, int y) => x >= Left && x < Right && y >= Top && y < Bottom;
}

internal sealed record Monitor(string Id, ScreenRect WorkArea, bool IsPrimary);

internal sealed record EdgePlacement(string MonitorId, ScreenEdge Edge, double Offset)
{
    public const double CornerSnap = 0.05;

    public static EdgePlacement Default(Monitor primary) => new(primary.Id, ScreenEdge.Right, 0.5);

    public static EdgePlacement Snap(IReadOnlyList<Monitor> monitors, int centerX, int centerY)
    {
        Monitor monitor = MonitorAt(monitors, centerX, centerY);
        ScreenRect area = monitor.WorkArea;
        int x = Math.Clamp(centerX, area.Left, area.Right);
        int y = Math.Clamp(centerY, area.Top, area.Bottom);
        (ScreenEdge edge, int _)[] distances =
        [
            (ScreenEdge.Left, x - area.Left),
            (ScreenEdge.Top, y - area.Top),
            (ScreenEdge.Right, area.Right - x),
            (ScreenEdge.Bottom, area.Bottom - y),
        ];
        ScreenEdge nearest = distances.MinBy(distance => distance._).edge;
        double offset = nearest is ScreenEdge.Left or ScreenEdge.Right
            ? (double)(y - area.Top) / area.Height
            : (double)(x - area.Left) / area.Width;
        return new EdgePlacement(monitor.Id, nearest, SnapToCorner(offset));
    }

    public (int X, int Y) Position(IReadOnlyList<Monitor> monitors, int size, int inset)
    {
        Monitor monitor = monitors.FirstOrDefault(monitor => monitor.Id == MonitorId) ?? Primary(monitors);
        ScreenRect full = monitor.WorkArea;
        var area = new ScreenRect(full.Left + inset, full.Top + inset, full.Right - inset, full.Bottom - inset);
        int alongX = area.Left + (int)Math.Round(Offset * (area.Width - size));
        int alongY = area.Top + (int)Math.Round(Offset * (area.Height - size));
        return Edge switch
        {
            ScreenEdge.Left => (area.Left, alongY),
            ScreenEdge.Right => (area.Right - size, alongY),
            ScreenEdge.Top => (alongX, area.Top),
            _ => (alongX, area.Bottom - size),
        };
    }

    private static Monitor MonitorAt(IReadOnlyList<Monitor> monitors, int x, int y) =>
        monitors.FirstOrDefault(monitor => monitor.WorkArea.Contains(x, y)) ?? Primary(monitors);

    private static Monitor Primary(IReadOnlyList<Monitor> monitors) =>
        monitors.FirstOrDefault(monitor => monitor.IsPrimary) ?? monitors[0];

    private static double SnapToCorner(double offset)
    {
        double clamped = Math.Clamp(offset, 0, 1);
        if (clamped <= CornerSnap)
        {
            return 0;
        }
        return clamped >= 1 - CornerSnap ? 1 : clamped;
    }
}
