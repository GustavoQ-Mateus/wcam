using System.Security.AccessControl;
using System.Security.Principal;

namespace Wcam.VirtualCamera.Tests;

public class FrameTransportTests
{
    private const string OwnerSid = "S-1-5-21-1000000000-2000000000-300000000-1001";
    private const int GenericAll = 0x10000000;
    private const int GenericRead = unchecked((int)0x80000000);
    private static readonly long Now = new DateTime(2026, 11, 2, 12, 0, 0, DateTimeKind.Utc).Ticks;

    [Fact]
    public void AccessDescriptor_ForOwner_GrantsOnlySystemOwnerAndLocalServiceRead()
    {
        var descriptor = new RawSecurityDescriptor(FrameTransport.AccessDescriptor(OwnerSid));
        var grants = descriptor.DiscretionaryAcl!.Cast<CommonAce>()
            .Select(ace => (ace.SecurityIdentifier.Value, ace.AceQualifier, ace.AccessMask))
            .ToArray();
        Assert.Equal(
            [
                (new SecurityIdentifier(WellKnownSidType.LocalSystemSid, null).Value, AceQualifier.AccessAllowed, GenericAll),
                (OwnerSid, AceQualifier.AccessAllowed, GenericAll),
                (new SecurityIdentifier(WellKnownSidType.LocalServiceSid, null).Value, AceQualifier.AccessAllowed, GenericRead),
            ],
            grants);
    }

    [Fact]
    public void AccessDescriptor_ForOwner_GrantsNothingToInteractiveOrEveryone()
    {
        var descriptor = new RawSecurityDescriptor(FrameTransport.AccessDescriptor(OwnerSid));
        string[] sids = descriptor.DiscretionaryAcl!.Cast<CommonAce>().Select(ace => ace.SecurityIdentifier.Value).ToArray();
        Assert.DoesNotContain(new SecurityIdentifier(WellKnownSidType.InteractiveSid, null).Value, sids);
        Assert.DoesNotContain(new SecurityIdentifier(WellKnownSidType.WorldSid, null).Value, sids);
    }

    [Fact]
    public void AcceptsFrame_FullHdNv12_IsAccepted()
    {
        Assert.True(FrameTransport.AcceptsFrame(VideoFormat.FrameSize, VideoFormat.Width, VideoFormat.Height, FrameFormat.Default));
    }

    [Theory]
    [InlineData(VideoFormat.FrameSize - 1, VideoFormat.Width, VideoFormat.Height)]
    [InlineData(VideoFormat.FrameSize + 1, VideoFormat.Width, VideoFormat.Height)]
    [InlineData(1280 * 720 * 3 / 2, 1280, 720)]
    [InlineData(VideoFormat.FrameSize, 1080, 1920)]
    [InlineData(0, 0, 0)]
    public void AcceptsFrame_OtherSizeOrLength_IsRejected(uint length, uint width, uint height)
    {
        Assert.False(FrameTransport.AcceptsFrame(length, width, height, FrameFormat.Default));
    }

    [Fact]
    public void AcceptsFrame_FrameOfCurrentOtherFormat_IsAccepted()
    {
        var format = new FrameFormat(1280, 720, 60);
        Assert.True(FrameTransport.AcceptsFrame((uint)format.FrameSize, 1280, 720, format));
    }

    [Fact]
    public void AcceptsFrame_FullHdFrameWhileFormatIs720p_IsRejected()
    {
        Assert.False(FrameTransport.AcceptsFrame(VideoFormat.FrameSize, VideoFormat.Width, VideoFormat.Height, new FrameFormat(1280, 720, 30)));
    }

    [Fact]
    public void IsFresh_FramePublishedJustUnderOneSecondAgo_IsFresh()
    {
        Assert.True(FrameTransport.IsFresh(Now - FrameTransport.FreshnessTicks + 1, Now));
    }

    [Fact]
    public void IsFresh_FramePublishedOneSecondAgo_IsStale()
    {
        Assert.False(FrameTransport.IsFresh(Now - FrameTransport.FreshnessTicks, Now));
    }

    [Fact]
    public void IsFresh_FrameStampedFarInTheFuture_IsStale()
    {
        Assert.False(FrameTransport.IsFresh(Now + FrameTransport.FreshnessTicks, Now));
    }

    [Fact]
    public void SessionSectionName_ForSession_UsesSessionNamespace()
    {
        Assert.Equal(@"Session\3\WCamFrames", FrameTransport.SessionSectionName(3));
    }
}
