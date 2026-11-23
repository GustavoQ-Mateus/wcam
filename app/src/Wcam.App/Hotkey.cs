namespace Wcam.App;

[Flags]
internal enum HotkeyModifiers : uint
{
    None = 0,
    Alt = 0x1,
    Control = 0x2,
    Shift = 0x4,
    Windows = 0x8,
}

internal sealed record Hotkey(HotkeyModifiers Modifiers, uint VirtualKey)
{
    private const uint FirstFunctionKey = 0x70;
    private const int LastFunctionNumber = 24;

    public static Hotkey? Parse(string text)
    {
        string[] parts = text.Split('+', StringSplitOptions.TrimEntries | StringSplitOptions.RemoveEmptyEntries);
        if (parts.Length < 2)
        {
            return null;
        }
        HotkeyModifiers modifiers = HotkeyModifiers.None;
        foreach (string part in parts[..^1])
        {
            HotkeyModifiers? modifier = ParseModifier(part);
            if (modifier is null)
            {
                return null;
            }
            modifiers |= modifier.Value;
        }
        uint? key = ParseKey(parts[^1]);
        return key is null ? null : new Hotkey(modifiers, key.Value);
    }

    private static HotkeyModifiers? ParseModifier(string part) => part.ToUpperInvariant() switch
    {
        "CTRL" or "CONTROL" => HotkeyModifiers.Control,
        "ALT" => HotkeyModifiers.Alt,
        "SHIFT" => HotkeyModifiers.Shift,
        "WIN" or "WINDOWS" => HotkeyModifiers.Windows,
        _ => null,
    };

    private static uint? ParseKey(string part)
    {
        string key = part.ToUpperInvariant();
        if (key.Length == 1 && char.IsAsciiLetterOrDigit(key[0]))
        {
            return key[0];
        }
        if (key.Length > 1 && key[0] == 'F' && int.TryParse(key[1..], out int number)
            && number is >= 1 and <= LastFunctionNumber)
        {
            return FirstFunctionKey + (uint)number - 1;
        }
        return null;
    }
}
