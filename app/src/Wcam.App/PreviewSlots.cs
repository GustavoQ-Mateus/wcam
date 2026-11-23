using Wcam.VirtualCamera;

namespace Wcam.App;

internal sealed class PreviewSlots
{
    public const int Count = 2;

    private readonly bool[] _withPage = new bool[Count];
    private bool _idle;
    private FrameFormat _buffersFormat;

    public bool NeedsBuffers(FrameFormat format) => format != _buffersFormat;

    public void BuffersSent(FrameFormat format)
    {
        Array.Clear(_withPage);
        _buffersFormat = format;
    }

    public int? FreeSlot()
    {
        for (int slot = 0; slot < Count; slot++)
        {
            if (!_withPage[slot])
            {
                return slot;
            }
        }
        return null;
    }

    public void GiveToPage(int slot) => _withPage[slot] = true;

    public void Release(int slot)
    {
        if (slot is >= 0 and < Count)
        {
            _withPage[slot] = false;
        }
    }

    public bool BecameIdle()
    {
        if (_idle)
        {
            return false;
        }
        _idle = true;
        _buffersFormat = default;
        return true;
    }

    public void MarkActive() => _idle = false;
}
