namespace Wcam.App.Tests;

public class EdgePlacementTests
{
    private const int Size = 40;
    private static readonly Monitor Primary = new("primary", new ScreenRect(0, 0, 1920, 1040), true);
    private static readonly Monitor Second = new("second", new ScreenRect(1920, 0, 3840, 1040), false);
    private static readonly Monitor[] Both = [Primary, Second];

    [Fact]
    public void DropNearLeft_SnapsToLeftEdge()
    {
        EdgePlacement placement = EdgePlacement.Snap(Both, 30, 520);

        Assert.Equal(new EdgePlacement("primary", ScreenEdge.Left, 0.5), placement);
    }

    [Fact]
    public void DropNearBottom_SnapsToBottomEdge()
    {
        EdgePlacement placement = EdgePlacement.Snap(Both, 960, 1020);

        Assert.Equal(ScreenEdge.Bottom, placement.Edge);
        Assert.Equal(0.5, placement.Offset);
    }

    [Fact]
    public void DropNearCorner_SnapsToTheCorner()
    {
        EdgePlacement placement = EdgePlacement.Snap(Both, 1910, 15);

        Assert.Equal(ScreenEdge.Right, placement.Edge);
        Assert.Equal(0, placement.Offset);
    }

    [Fact]
    public void DropOnSecondMonitor_RemembersThatMonitor()
    {
        EdgePlacement placement = EdgePlacement.Snap(Both, 3830, 520);

        Assert.Equal(new EdgePlacement("second", ScreenEdge.Right, 0.5), placement);
        Assert.Equal((3840 - Size, 500), placement.Position(Both, Size));
    }

    [Fact]
    public void DropOutsideEveryMonitor_UsesThePrimary()
    {
        EdgePlacement placement = EdgePlacement.Snap(Both, -500, 520);

        Assert.Equal("primary", placement.MonitorId);
        Assert.Equal(ScreenEdge.Left, placement.Edge);
    }

    [Fact]
    public void RemovedMonitor_FallsBackToThePrimary()
    {
        var placement = new EdgePlacement("second", ScreenEdge.Top, 1);

        Assert.Equal((1920 - Size, 0), placement.Position([Primary], Size));
    }

    [Fact]
    public void LeftEdgePlacement_StaysInsideTheWorkArea()
    {
        var placement = new EdgePlacement("primary", ScreenEdge.Bottom, 1);

        Assert.Equal((1920 - Size, 1040 - Size), placement.Position(Both, Size));
    }
}
