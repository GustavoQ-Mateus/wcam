using System.Text.Json;
using Microsoft.UI.Dispatching;
using Microsoft.Web.WebView2.Core;
using Wcam.VirtualCamera;

namespace Wcam.App;

internal sealed class PreviewBridge : IDisposable
{
    private readonly CoreWebView2 _core;
    private readonly DispatcherQueue _ui;
    private PreviewSession? _session;

    public PreviewBridge(CoreWebView2 core, DispatcherQueue ui)
    {
        _core = core;
        _ui = ui;
        _core.WebMessageReceived += OnWebMessage;
    }

    public void Dispose()
    {
        _core.WebMessageReceived -= OnWebMessage;
        Stop();
    }

    private void OnWebMessage(CoreWebView2 sender, CoreWebView2WebMessageReceivedEventArgs args)
    {
        using JsonDocument document = JsonDocument.Parse(args.WebMessageAsJson);
        JsonElement root = document.RootElement;
        if (root.ValueKind != JsonValueKind.Object || !root.TryGetProperty("type", out JsonElement type))
        {
            return;
        }
        switch (type.GetString())
        {
            case "preview.start":
                Start();
                break;
            case "preview.stop":
                Stop();
                break;
            case "preview.release" when root.TryGetProperty("slot", out JsonElement slot)
                && slot.ValueKind == JsonValueKind.Number:
                _session?.Release(slot.GetInt32());
                break;
        }
    }

    private void Start()
    {
        if (_session is not null)
        {
            return;
        }
        _session = new PreviewSession(_core, _ui);
        _session.Start();
    }

    private void Stop()
    {
        _session?.Stop();
        _session = null;
    }
}

internal sealed unsafe class PreviewSession
{
    private static readonly TimeSpan FramePoll = TimeSpan.FromMilliseconds(3);
    private static readonly TimeSpan IdlePoll = TimeSpan.FromMilliseconds(250);

    private readonly CoreWebView2 _core;
    private readonly DispatcherQueue _ui;
    private readonly PreviewSlots _slots = new();
    private readonly CancellationTokenSource _stop = new();
    private readonly CoreWebView2SharedBuffer?[] _buffers = new CoreWebView2SharedBuffer?[PreviewSlots.Count];
    private readonly nint[] _pointers = new nint[PreviewSlots.Count];

    public PreviewSession(CoreWebView2 core, DispatcherQueue ui)
    {
        _core = core;
        _ui = ui;
    }

    public void Start()
    {
        var thread = new Thread(Run) { IsBackground = true, Name = "WCam preview" };
        thread.Start();
    }

    public void Stop() => _stop.Cancel();

    public void Release(int slot)
    {
        lock (_slots)
        {
            _slots.Release(slot);
        }
    }

    private void Run()
    {
        using var reader = new PublishedFrameReader(AppPaths.FramesSection, TimeProvider.System);
        using var timer = new PollTimer();
        try
        {
            while (!_stop.IsCancellationRequested)
            {
                TimeSpan wait = Step(reader);
                timer.Wait(wait, _stop.Token.WaitHandle);
            }
        }
        finally
        {
            _ui.TryEnqueue(CloseBuffers);
        }
    }

    private TimeSpan Step(PublishedFrameReader reader)
    {
        if (!reader.TryReadFormat(out FrameFormat format))
        {
            ReportIdle();
            return IdlePoll;
        }
        if (NeedsBuffers(format) && !ReplaceBuffers(format))
        {
            return IdlePoll;
        }
        int? slot = FreeSlot();
        if (slot is null)
        {
            return FramePoll;
        }
        var destination = new Span<byte>((void*)_pointers[slot.Value], format.FrameSize);
        FrameRead read = reader.ReadLatest(destination, format, out ulong sequence);
        if (read == FrameRead.Idle)
        {
            ReportIdle();
            return IdlePoll;
        }
        if (read == FrameRead.New)
        {
            SendFrame(slot.Value, sequence);
        }
        return FramePoll;
    }

    private bool ReplaceBuffers(FrameFormat format)
    {
        var created = new TaskCompletionSource<bool>(TaskCreationOptions.RunContinuationsAsynchronously);
        if (!_ui.TryEnqueue(() => created.SetResult(PostBuffers(format))))
        {
            return false;
        }
        bool posted;
        try
        {
            posted = created.Task.Wait(Timeout.Infinite, _stop.Token) && created.Task.Result;
        }
        catch (OperationCanceledException)
        {
            return false;
        }
        if (posted)
        {
            lock (_slots)
            {
                _slots.BuffersSent(format);
            }
        }
        return posted;
    }

    private bool PostBuffers(FrameFormat format)
    {
        if (_stop.IsCancellationRequested)
        {
            return false;
        }
        CloseBuffers();
        for (int slot = 0; slot < PreviewSlots.Count; slot++)
        {
            CoreWebView2SharedBuffer buffer = _core.Environment.CreateSharedBuffer((ulong)format.FrameSize);
            _buffers[slot] = buffer;
            _pointers[slot] = (nint)MemoryBufferAccess.Pointer(buffer.Buffer);
            string data = $"{{\"type\":\"preview.buffer\",\"slot\":{slot},\"width\":{format.Width},\"height\":{format.Height}}}";
            _core.PostSharedBufferToScript(buffer, CoreWebView2SharedBufferAccess.ReadOnly, data);
        }
        return true;
    }

    private void CloseBuffers()
    {
        for (int slot = 0; slot < PreviewSlots.Count; slot++)
        {
            _buffers[slot]?.Dispose();
            _buffers[slot] = null;
            _pointers[slot] = 0;
        }
    }

    private bool NeedsBuffers(FrameFormat format)
    {
        lock (_slots)
        {
            return _slots.NeedsBuffers(format);
        }
    }

    private int? FreeSlot()
    {
        lock (_slots)
        {
            return _slots.FreeSlot();
        }
    }

    private void SendFrame(int slot, ulong sequence)
    {
        lock (_slots)
        {
            _slots.GiveToPage(slot);
            _slots.MarkActive();
        }
        OnUi(() => _core.PostWebMessageAsJson($"{{\"type\":\"preview.frame\",\"slot\":{slot},\"sequence\":{sequence}}}"));
    }

    private void ReportIdle()
    {
        bool becameIdle;
        lock (_slots)
        {
            becameIdle = _slots.BecameIdle();
        }
        if (becameIdle)
        {
            OnUi(() => _core.PostWebMessageAsJson("{\"type\":\"preview.idle\"}"));
        }
    }

    private void OnUi(Action action) => _ui.TryEnqueue(() =>
    {
        if (!_stop.IsCancellationRequested)
        {
            action();
        }
    });
}
