using System.Net.Http.Headers;
using System.Text;

namespace Wcam.App;

internal sealed class ConsoleClient : IHealthProbe, IDisposable
{
    public const int DefaultPort = 8080;
    private const string PortVariable = "WCAM_CONSOLE_PORT";
    private const string StatusEvent = "event: status";
    private const string DataPrefix = "data: ";
    private static readonly TimeSpan RequestTimeout = TimeSpan.FromSeconds(2);
    private static readonly TimeSpan ReconnectDelay = TimeSpan.FromSeconds(1);

    private readonly HttpClient _http;
    private readonly HttpClient _events;

    public ConsoleClient()
    {
        BaseAddress = new Uri($"http://127.0.0.1:{Port()}/");
        _http = new HttpClient { BaseAddress = BaseAddress, Timeout = RequestTimeout };
        _events = new HttpClient { BaseAddress = BaseAddress, Timeout = Timeout.InfiniteTimeSpan };
    }

    public Uri BaseAddress { get; }

    public async Task<bool> IsHealthyAsync(CancellationToken cancellation)
    {
        using HttpResponseMessage response = await _http.GetAsync("api/health", cancellation);
        return response.IsSuccessStatusCode;
    }

    public async Task WatchStatusAsync(Action<AgentStatus> changed, CancellationToken cancellation)
    {
        while (!cancellation.IsCancellationRequested)
        {
            try
            {
                await ReadEventsAsync(changed, cancellation);
            }
            catch (Exception exception) when (exception is HttpRequestException or IOException)
            {
                changed(AgentStatus.Unknown);
            }
            catch (OperationCanceledException)
            {
                return;
            }
            if (!await DelayAsync(cancellation))
            {
                return;
            }
        }
    }

    public Task ChangeControlsAsync(string field, string jsonValue) =>
        SendAsync(HttpMethod.Patch, "api/controls", $"{{\"{field}\":{jsonValue}}}");

    public Task SetVideoSourceAsync(bool active) =>
        SendAsync(HttpMethod.Put, "api/video-source", $"{{\"active\":{Json(active)}}}");

    public Task DisconnectAsync() => SendAsync(HttpMethod.Delete, "api/sessions/current", null);

    public static string Json(bool value) => value ? "true" : "false";

    public void Dispose()
    {
        _http.Dispose();
        _events.Dispose();
    }

    private async Task ReadEventsAsync(Action<AgentStatus> changed, CancellationToken cancellation)
    {
        using var request = new HttpRequestMessage(HttpMethod.Get, "api/events");
        request.Headers.Accept.Add(new MediaTypeWithQualityHeaderValue("text/event-stream"));
        using HttpResponseMessage response =
            await _events.SendAsync(request, HttpCompletionOption.ResponseHeadersRead, cancellation);
        response.EnsureSuccessStatusCode();
        using var reader = new StreamReader(await response.Content.ReadAsStreamAsync(cancellation));
        bool statusEvent = false;
        while (await reader.ReadLineAsync(cancellation) is { } line)
        {
            if (line.StartsWith("event:", StringComparison.Ordinal))
            {
                statusEvent = line == StatusEvent;
            }
            else if (statusEvent && line.StartsWith(DataPrefix, StringComparison.Ordinal))
            {
                changed(AgentStatus.Parse(line[DataPrefix.Length..]));
            }
        }
    }

    private async Task SendAsync(HttpMethod method, string path, string? json)
    {
        using var request = new HttpRequestMessage(method, path);
        if (json is not null)
        {
            request.Content = new StringContent(json, Encoding.UTF8, "application/json");
        }
        try
        {
            using HttpResponseMessage response = await _http.SendAsync(request);
        }
        catch (Exception exception) when (exception is HttpRequestException or TaskCanceledException)
        {
        }
    }

    private static async Task<bool> DelayAsync(CancellationToken cancellation)
    {
        try
        {
            await Task.Delay(ReconnectDelay, cancellation);
            return true;
        }
        catch (OperationCanceledException)
        {
            return false;
        }
    }

    private static int Port() =>
        int.TryParse(Environment.GetEnvironmentVariable(PortVariable), out int port) ? port : DefaultPort;
}
