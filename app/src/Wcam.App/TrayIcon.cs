using Windows.Win32;
using Windows.Win32.Foundation;
using Windows.Win32.UI.Input.KeyboardAndMouse;
using Windows.Win32.UI.Shell;
using Windows.Win32.UI.WindowsAndMessaging;

namespace Wcam.App;

internal sealed unsafe class TrayIcon : NativeWindow
{
    private const uint CallbackMessage = PInvoke.WM_APP + 1;
    private const int HotkeyId = 1;
    private const uint IconId = 1;
    private const int TooltipLength = 127;

    private readonly uint _taskbarCreated;
    private IReadOnlyList<MenuEntry> _entries = [];
    private IReadOnlyList<string> _texts = [];
    private string _tooltip = string.Empty;
    private HICON _icon;
    private bool _added;

    public TrayIcon()
    {
        Create(0, 0, HWND.HWND_MESSAGE);
        fixed (char* name = "TaskbarCreated")
        {
            _taskbarCreated = PInvoke.RegisterWindowMessage(name);
        }
    }

    public event Action<TrayAction>? Selected;

    public event Action? Activated;

    public event Action? HotkeyPressed;

    public void Update(TrayState state, string tooltip, IReadOnlyList<MenuEntry> entries, IReadOnlyList<string> texts)
    {
        _entries = entries;
        _texts = texts;
        _tooltip = tooltip.Length > TooltipLength ? tooltip[..TooltipLength] : tooltip;
        HICON previous = _icon;
        _icon = IconFactory.Create(IconPainter.Paint(state, IconFactory.SmallIconSize), IconFactory.SmallIconSize);
        Notify(_added ? NOTIFY_ICON_MESSAGE.NIM_MODIFY : NOTIFY_ICON_MESSAGE.NIM_ADD);
        _added = true;
        if (!previous.IsNull)
        {
            PInvoke.DestroyIcon(previous);
        }
    }

    public bool RegisterHotkey(Hotkey? hotkey)
    {
        PInvoke.UnregisterHotKey(Handle, HotkeyId);
        if (hotkey is null)
        {
            return false;
        }
        var modifiers = (HOT_KEY_MODIFIERS)hotkey.Modifiers | HOT_KEY_MODIFIERS.MOD_NOREPEAT;
        return PInvoke.RegisterHotKey(Handle, HotkeyId, modifiers, hotkey.VirtualKey);
    }

    protected override LRESULT OnMessage(uint message, WPARAM wParam, LPARAM lParam)
    {
        if (message == CallbackMessage)
        {
            OnTrayEvent((uint)(lParam.Value & 0xFFFF));
            return new LRESULT(0);
        }
        if (message == PInvoke.WM_HOTKEY)
        {
            HotkeyPressed?.Invoke();
            return new LRESULT(0);
        }
        if (message == _taskbarCreated && _added)
        {
            Notify(NOTIFY_ICON_MESSAGE.NIM_ADD);
        }
        return base.OnMessage(message, wParam, lParam);
    }

    protected override void OnDestroyed()
    {
        if (_added)
        {
            Notify(NOTIFY_ICON_MESSAGE.NIM_DELETE);
        }
        if (!_icon.IsNull)
        {
            PInvoke.DestroyIcon(_icon);
        }
    }

    private void OnTrayEvent(uint trayEvent)
    {
        if (trayEvent == PInvoke.WM_LBUTTONUP)
        {
            Activated?.Invoke();
        }
        else if (trayEvent == PInvoke.WM_RBUTTONUP)
        {
            ShowMenu();
        }
    }

    private void ShowMenu()
    {
        HMENU menu = PInvoke.CreatePopupMenu();
        for (int index = 0; index < _entries.Count; index++)
        {
            AppendEntry(menu, index);
        }
        PInvoke.GetCursorPos(out System.Drawing.Point cursor);
        PInvoke.SetForegroundWindow(Handle);
        uint command = (uint)PInvoke.TrackPopupMenuEx(
            menu,
            (uint)(TRACK_POPUP_MENU_FLAGS.TPM_RETURNCMD | TRACK_POPUP_MENU_FLAGS.TPM_RIGHTBUTTON),
            cursor.X,
            cursor.Y,
            Handle,
            null).Value;
        PInvoke.PostMessage(Handle, PInvoke.WM_NULL, default, default);
        PInvoke.DestroyMenu(menu);
        if (command > 0)
        {
            Selected?.Invoke(_entries[(int)command - 1].Action);
        }
    }

    private void AppendEntry(HMENU menu, int index)
    {
        MenuEntry entry = _entries[index];
        if (entry.Action == TrayAction.Separator)
        {
            PInvoke.AppendMenu(menu, MENU_ITEM_FLAGS.MF_SEPARATOR, 0, (PCWSTR)null);
            return;
        }
        MENU_ITEM_FLAGS flags = MENU_ITEM_FLAGS.MF_STRING;
        flags |= entry.Enabled && entry.Action != TrayAction.None ? 0 : MENU_ITEM_FLAGS.MF_GRAYED;
        flags |= entry.Checked ? MENU_ITEM_FLAGS.MF_CHECKED : 0;
        fixed (char* text = _texts[index])
        {
            PInvoke.AppendMenu(menu, flags, (nuint)(index + 1), text);
        }
    }

    private void Notify(NOTIFY_ICON_MESSAGE message)
    {
        var data = new NOTIFYICONDATAW
        {
            cbSize = (uint)sizeof(NOTIFYICONDATAW),
            hWnd = Handle,
            uID = IconId,
            uFlags = NOTIFY_ICON_DATA_FLAGS.NIF_ICON | NOTIFY_ICON_DATA_FLAGS.NIF_MESSAGE
                | NOTIFY_ICON_DATA_FLAGS.NIF_TIP | NOTIFY_ICON_DATA_FLAGS.NIF_SHOWTIP,
            uCallbackMessage = CallbackMessage,
            hIcon = _icon,
        };
        data.szTip = _tooltip;
        data.Anonymous.uVersion = PInvoke.NOTIFYICON_VERSION_4;
        PInvoke.Shell_NotifyIcon(message, &data);
        if (message == NOTIFY_ICON_MESSAGE.NIM_ADD)
        {
            PInvoke.Shell_NotifyIcon(NOTIFY_ICON_MESSAGE.NIM_SETVERSION, &data);
        }
    }
}
