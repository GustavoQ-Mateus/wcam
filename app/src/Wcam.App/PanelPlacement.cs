namespace Wcam.App;

internal static class PanelPlacement
{
    public static (int X, int Y) Beside(
        IReadOnlyList<Monitor> monitors,
        int iconX,
        int iconY,
        int iconSize,
        int width,
        int height,
        int gap)
    {
        int centerX = iconX + iconSize / 2;
        int centerY = iconY + iconSize / 2;
        EdgePlacement nearest = EdgePlacement.Snap(monitors, centerX, centerY);
        ScreenRect area = (monitors.FirstOrDefault(monitor => monitor.Id == nearest.MonitorId) ?? monitors[0]).WorkArea;
        (int x, int y) = nearest.Edge switch
        {
            ScreenEdge.Left => (iconX + iconSize + gap, centerY - height / 2),
            ScreenEdge.Right => (iconX - gap - width, centerY - height / 2),
            ScreenEdge.Top => (centerX - width / 2, iconY + iconSize + gap),
            _ => (centerX - width / 2, iconY - gap - height),
        };
        return (Math.Clamp(x, area.Left, Math.Max(area.Left, area.Right - width)),
            Math.Clamp(y, area.Top, Math.Max(area.Top, area.Bottom - height)));
    }
}
