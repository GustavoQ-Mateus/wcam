using System.Net;
using System.Reflection;
using System.Text;
using System.Text.Json;
using Wcam.VirtualCamera.Probe;

namespace Wcam.ColorVerify;

internal sealed class ModelServer(int port)
{
    private const string PageResource = "chrome-model.html";
    private static readonly JsonSerializerOptions Json = new(JsonSerializerDefaults.Web);

    public string Url => $"http://localhost:{port}/";

    public async Task<CanvasReadings> ReceiveReadingsAsync(Func<CanvasReadings, string> respond)
    {
        using var listener = new HttpListener();
        listener.Prefixes.Add(Url);
        listener.Start();
        while (true)
        {
            HttpListenerContext context = await listener.GetContextAsync();
            CanvasReadings? readings = await HandleAsync(context, respond);
            if (readings is not null)
            {
                return readings;
            }
        }
    }

    private static async Task<CanvasReadings?> HandleAsync(HttpListenerContext context, Func<CanvasReadings, string> respond)
    {
        string path = context.Request.Url?.AbsolutePath ?? "/";
        if (context.Request.HttpMethod == "POST" && path == "/readings")
        {
            CanvasReadings readings = await JsonSerializer.DeserializeAsync<CanvasReadings>(context.Request.InputStream, Json)
                ?? throw new InvalidDataException("empty readings");
            await WriteAsync(context, "text/plain; charset=utf-8", respond(readings));
            return readings;
        }
        if (path == "/grid")
        {
            await WriteAsync(context, "application/json", JsonSerializer.Serialize(GridWindows(), Json));
            return null;
        }
        if (path == "/")
        {
            await WriteAsync(context, "text/html; charset=utf-8", ReadPage());
            return null;
        }
        context.Response.StatusCode = (int)HttpStatusCode.NotFound;
        context.Response.Close();
        return null;
    }

    private static int[][] GridWindows()
    {
        int size = PatchGrid.CellSize - 2 * PatchGrid.ReadMargin;
        return PatchGrid.Patches
            .Select(patch => new[] { patch.Left + PatchGrid.ReadMargin, patch.Top + PatchGrid.ReadMargin, size, size })
            .ToArray();
    }

    private static string ReadPage()
    {
        using Stream stream = Assembly.GetExecutingAssembly().GetManifestResourceStream(PageResource)
            ?? throw new InvalidOperationException($"missing resource {PageResource}");
        using var reader = new StreamReader(stream);
        return reader.ReadToEnd();
    }

    private static async Task WriteAsync(HttpListenerContext context, string contentType, string body)
    {
        byte[] bytes = Encoding.UTF8.GetBytes(body);
        context.Response.ContentType = contentType;
        context.Response.ContentLength64 = bytes.Length;
        await context.Response.OutputStream.WriteAsync(bytes);
        context.Response.Close();
    }
}
