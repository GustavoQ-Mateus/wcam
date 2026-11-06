namespace Wcam.VirtualCamera.Probe;

internal delegate void FrameRenderer(Span<byte> frame, long frameNumber);
