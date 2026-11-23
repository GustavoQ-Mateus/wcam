namespace Wcam.App.Tests;

public class RestartPolicyTests
{
    private static readonly DateTimeOffset Start = new(2026, 11, 23, 12, 0, 0, TimeSpan.Zero);

    [Fact]
    public void RestartsWithinTheLimit_AreAllowed()
    {
        var policy = new RestartPolicy(3, TimeSpan.FromMinutes(5));

        Assert.True(policy.TryRestart(Start));
        Assert.True(policy.TryRestart(Start.AddMinutes(1)));
        Assert.True(policy.TryRestart(Start.AddMinutes(2)));
    }

    [Fact]
    public void RestartPastTheLimit_IsRefused()
    {
        var policy = new RestartPolicy(3, TimeSpan.FromMinutes(5));
        policy.TryRestart(Start);
        policy.TryRestart(Start.AddMinutes(1));
        policy.TryRestart(Start.AddMinutes(2));

        Assert.False(policy.TryRestart(Start.AddMinutes(3)));
    }

    [Fact]
    public void RestartsOlderThanTheWindow_StopCounting()
    {
        var policy = new RestartPolicy(3, TimeSpan.FromMinutes(5));
        policy.TryRestart(Start);
        policy.TryRestart(Start.AddMinutes(1));
        policy.TryRestart(Start.AddMinutes(2));

        Assert.True(policy.TryRestart(Start.AddMinutes(5)));
    }
}

public class HotkeyTests
{
    [Fact]
    public void ModifiersAndLetter_AreParsed()
    {
        Assert.Equal(new Hotkey(HotkeyModifiers.Control | HotkeyModifiers.Alt, 'W'), Hotkey.Parse("Ctrl+Alt+W"));
    }

    [Fact]
    public void FunctionKey_IsParsed()
    {
        Assert.Equal(new Hotkey(HotkeyModifiers.Windows | HotkeyModifiers.Shift, 0x7B), Hotkey.Parse("win + shift + f12"));
    }

    [Theory]
    [InlineData("W")]
    [InlineData("Ctrl+Meta+W")]
    [InlineData("Ctrl+F25")]
    [InlineData("Ctrl+?")]
    public void InvalidText_IsRejected(string text)
    {
        Assert.Null(Hotkey.Parse(text));
    }
}

public class PreviewSlotsTests
{
    [Fact]
    public void NewSlots_AreAllFree()
    {
        Assert.Equal(0, new PreviewSlots().FreeSlot());
    }

    [Fact]
    public void BothSlotsWithThePage_LeaveNoFreeSlot()
    {
        var slots = new PreviewSlots();
        slots.GiveToPage(0);
        slots.GiveToPage(1);

        Assert.Null(slots.FreeSlot());
    }

    [Fact]
    public void ReleasedSlot_IsFreeAgain()
    {
        var slots = new PreviewSlots();
        slots.GiveToPage(0);
        slots.GiveToPage(1);

        slots.Release(1);

        Assert.Equal(1, slots.FreeSlot());
    }

    [Fact]
    public void Idle_IsReportedOncePerTransition()
    {
        var slots = new PreviewSlots();

        Assert.True(slots.BecameIdle());
        Assert.False(slots.BecameIdle());
        slots.MarkActive();
        Assert.True(slots.BecameIdle());
    }

    [Fact]
    public void ReleaseOfUnknownSlot_IsIgnored()
    {
        var slots = new PreviewSlots();
        slots.GiveToPage(0);

        slots.Release(7);

        Assert.Equal(1, slots.FreeSlot());
    }
}

public class LocalizationTests
{
    [Theory]
    [InlineData("pt-BR", "pt-BR")]
    [InlineData("pt-PT", "pt-BR")]
    [InlineData("en-US", "en")]
    [InlineData("de-DE", "en")]
    public void SystemLanguage_ResolvesToASupportedLanguage(string tag, string language)
    {
        Assert.Equal(language, Localization.ResolveLanguage(tag));
    }

    [Fact]
    public void ProjectLocales_HaveTheTrayTexts()
    {
        string locales = Path.Combine(RepositoryRoot(), "locales");

        Localization portuguese = Localization.Load(locales, Localization.Portuguese);

        Assert.Equal("WCam: Ao vivo", portuguese.Text("tray.tooltip", "state", "Ao vivo"));
    }

    [Fact]
    public void BothLocales_HaveTheSameKeysTheAppUses()
    {
        string locales = Path.Combine(RepositoryRoot(), "locales");
        Localization english = Localization.Load(locales, Localization.English);
        Localization portuguese = Localization.Load(locales, Localization.Portuguese);
        string[] keys = ["tray.show_overlay", "tray.start_with_windows", "overlay.panel", "app.name"];

        Assert.All(keys, key => Assert.NotEmpty(english.Text(key) + portuguese.Text(key)));
    }

    private static string RepositoryRoot()
    {
        DirectoryInfo? directory = new(AppContext.BaseDirectory);
        while (directory is not null && !Directory.Exists(Path.Combine(directory.FullName, "locales")))
        {
            directory = directory.Parent;
        }
        return directory!.FullName;
    }
}

public class AppSettingsTests
{
    [Fact]
    public void SavedSettings_AreLoadedBack()
    {
        string path = Path.Combine(Path.GetTempPath(), $"wcam-settings-{Guid.NewGuid()}.json");
        var settings = new AppSettings
        {
            ConsoleWindow = new WindowBounds(10, 20, 900, 700),
            OverlayPlacement = new EdgePlacement("primary", ScreenEdge.Bottom, 0.25),
            FloatingPreviewVisible = true,
            Hotkey = "Win+Alt+W",
        };

        settings.Save(path);
        AppSettings loaded = AppSettings.Load(path);
        File.Delete(path);

        Assert.Equal(settings, loaded);
    }

    [Fact]
    public void MissingFile_GivesDefaults()
    {
        AppSettings loaded = AppSettings.Load(Path.Combine(Path.GetTempPath(), $"missing-{Guid.NewGuid()}.json"));

        Assert.Equal(new AppSettings(), loaded);
        Assert.True(loaded.OverlayVisible);
    }

    [Fact]
    public void CorruptFile_GivesDefaults()
    {
        string path = Path.Combine(Path.GetTempPath(), $"wcam-settings-{Guid.NewGuid()}.json");
        File.WriteAllText(path, "{ not json");

        AppSettings loaded = AppSettings.Load(path);
        File.Delete(path);

        Assert.Equal(new AppSettings(), loaded);
    }
}

public class SingleInstanceTests
{
    [Fact]
    public void SecondInstance_IsRefusedAndAsksTheFirstToShow()
    {
        string name = $@"Local\WCam.Tests.{Guid.NewGuid()}";
        using SingleInstance? first = SingleInstance.TryAcquire(name);

        SingleInstance? second = SingleInstance.TryAcquire(name);

        Assert.NotNull(first);
        Assert.Null(second);
        Assert.True(first.ShowRequested.WaitOne(0));
    }

    [Fact]
    public void ReleasedInstance_CanBeAcquiredAgain()
    {
        string name = $@"Local\WCam.Tests.{Guid.NewGuid()}";
        SingleInstance.TryAcquire(name)!.Dispose();

        using SingleInstance? again = SingleInstance.TryAcquire(name);

        Assert.NotNull(again);
    }
}

public class StartupRegistrationTests
{
    [Fact]
    public void Enabling_WritesTheQuotedExecutableWithTheStartupArgument()
    {
        string key = $@"Software\WCam.Tests\{Guid.NewGuid()}";
        var registration = new StartupRegistration(key, @"C:\Program Files\WCam\WCam.exe");

        registration.Set(true);
        bool enabled = registration.IsEnabled;
        string? value = Microsoft.Win32.Registry.CurrentUser.OpenSubKey(key)?.GetValue(StartupRegistration.ValueName) as string;
        Microsoft.Win32.Registry.CurrentUser.DeleteSubKeyTree(key);

        Assert.True(enabled);
        Assert.Equal("\"C:\\Program Files\\WCam\\WCam.exe\" --startup", value);
    }

    [Fact]
    public void Disabling_RemovesTheValue()
    {
        string key = $@"Software\WCam.Tests\{Guid.NewGuid()}";
        var registration = new StartupRegistration(key, @"C:\WCam.exe");
        registration.Set(true);

        registration.Set(false);
        bool enabled = registration.IsEnabled;
        Microsoft.Win32.Registry.CurrentUser.DeleteSubKeyTree(key);

        Assert.False(enabled);
    }
}

public class AgentStatusTests
{
    [Fact]
    public void ContractStatus_IsParsed()
    {
        const string json = """
            {"pairing": null,
             "session": {"state": "live"},
             "controls": {"frozen": true, "cameraOff": false, "mirror": true, "facing": "user"},
             "virtualCamera": {"state": "active", "source": "held"},
             "videoSource": {"timeline": {"clips": [{"id": "c1"}]}, "active": false}}
            """;

        AgentStatus status = AgentStatus.Parse(json);

        Assert.Equal(new AgentStatus(true, "held", "live", new Controls(true, false, true, Facing.User), false, true), status);
    }

    [Fact]
    public void StatusWithoutSession_HasNoSession()
    {
        AgentStatus status = AgentStatus.Parse("""{"session": null, "controls": {"facing": null}}""");

        Assert.False(status.HasSession);
        Assert.Equal(Facing.None, status.Controls.Facing);
    }
}
