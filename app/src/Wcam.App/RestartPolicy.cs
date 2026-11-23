namespace Wcam.App;

internal sealed class RestartPolicy
{
    private readonly int _maximumRestarts;
    private readonly TimeSpan _window;
    private readonly Queue<DateTimeOffset> _restarts = new();

    public RestartPolicy(int maximumRestarts, TimeSpan window)
    {
        _maximumRestarts = maximumRestarts;
        _window = window;
    }

    public bool TryRestart(DateTimeOffset now)
    {
        while (_restarts.Count > 0 && now - _restarts.Peek() >= _window)
        {
            _restarts.Dequeue();
        }
        if (_restarts.Count >= _maximumRestarts)
        {
            return false;
        }
        _restarts.Enqueue(now);
        return true;
    }
}
