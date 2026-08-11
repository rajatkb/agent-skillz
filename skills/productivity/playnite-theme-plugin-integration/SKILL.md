---
name: playnite-theme-plugin-integration
description: Modify Playnite fullscreen themes to add plugin integration support (PlayState, NowPlaying, etc.). Covers XAML ContentControl placeholder pattern and WSL→Windows deployment.
---

# Playnite Theme Plugin Integration

## How Playnite Plugin UI Integration Works

Playnite plugins expose custom UI controls via `AddCustomElementSupport`. Themes place a **ContentControl placeholder** with a specific `x:Name` naming convention:

```
x:Name="{PluginAbbreviation}_{ElementName}"
```

Playnite's theme engine matches the `x:Name` to the plugin's `GetGameViewControl()` and replaces the ContentControl at runtime with the plugin's actual control.

## The Core Pattern

```xml
<ContentControl x:Name="PluginName_ElementName"
    Style="{DynamicResource SomeStyle}"
    Visibility="{PluginSettings Plugin=PluginName, Path=SomeVisibilityProperty, FallbackValue=Collapsed, Converter={StaticResource BooleanToVisibilityConverter}}" />
```

- **x:Name** — Must match `{PluginAbbreviation}_{ElementName}` from the plugin's `AddCustomElementSupport`.
- **PluginSettings** binding — Controls visibility. `FallbackValue=Collapsed` hides the element when plugin isn't installed.
- Apply basic layout (Margin, VerticalAlignment) — the plugin control brings its own template.

## Common Plugin x:Name Patterns

| Plugin | x:Name Pattern | Visibility Binding |
|---|---|---|
| PlayState | `PlayState_GameStateSwitchControl` | `Plugin=PlayState, Path=IsControlVisible` |
| ScreenshotsVisualizer | `ScreenshotsVisualizer_PluginButton` | `Plugin=ScreenshotsVisualizer, Path=HasData` |
| CheckDlc | `CheckDlc_PluginButton` | `Plugin=CheckDlc, Path=EnableIntegrationButton` |
| Playnite Achievements | `PlayniteAchievements_PluginButton` | `Plugin=PlayniteAchievements, Path=HasData` |
| HowLongToBeat | `HowLongToBeat_PluginButton` | `Plugin=HowLongToBeat, Path=EnableIntegrationButton` |
| ScreenshotUtilities | `ScreenshotUtilities_ButtonControl` | `Plugin=ScreenshotUtilities, Path=IsViewerControlVisible` |

## Styling the Inner Plugin Control

Plugin controls (like PlayState's GameStateSwitchControl) contain a Button that uses the **theme's default `{x:Type Button}` style**, NOT a named style like `ButtonIconStyle`. This causes visual mismatches:

| Style | Background | Used By |
|---|---|---|
| Default `{x:Type Button}` | `ButtonBackgroundStyle` → `Translucent05Brush` (5% white) | PlayState inner Button |
| `ButtonIconStyle` / ToggleButton | `ToggleBackgroundStyle` → `Translucent10Brush` (10% white) | Neighboring plugin icons |

### Approach 1: ContentControl with Local Resources (Fullscreen)

Override the inner Button's appearance locally on the ContentControl placeholder:

```xml
<ContentControl x:Name="PlayState_GameStateSwitchControl" Height="46" Width="46" Margin="0,0,10,0" Tag="Alt"
    VerticalAlignment="Center"
    Visibility="{PluginSettings Plugin=PlayState, Path=IsControlVisible, FallbackValue=Collapsed, Converter={StaticResource BooleanToVisibilityConverter}}">
    <ContentControl.Resources>
        <!-- Kill the opaque system default background on the inner Button -->
        <Style TargetType="Button" BasedOn="{StaticResource {x:Type Button}}">
            <Setter Property="Background" Value="Transparent" />
        </Style>
        <!-- Match ToggleButton's Translucent10Brush instead of default 5% -->
        <Style x:Key="ButtonBackgroundStyle" TargetType="Border">
            <Setter Property="IsHitTestVisible" Value="False" />
            <Setter Property="CornerRadius" Value="{DynamicResource InfoBoxCorner}" />
            <Setter Property="Background" Value="{DynamicResource Translucent10Brush}" />
            <Setter Property="Margin" Value="5" />
        </Style>
    </ContentControl.Resources>
</ContentControl>
```

### Approach 2: Border Wrapper (avoids nested interactive controls)

For plugins like PlayState whose inner control IS a Button, wrapping in a ToggleButtonEx creates nested interactive controls. Use a passive **Border** instead:

```xml
<Border Width="50" Height="50" Margin="0,0,10,0" Tag="Alt"
    CornerRadius="{DynamicResource InfoBoxCorner}"
    Background="{DynamicResource Translucent10Brush}"
    Visibility="{PluginSettings Plugin=PlayState, Path=IsControlVisible, FallbackValue=Collapsed, Converter={StaticResource BooleanToVisibilityConverter}}">
    <ContentControl x:Name="PlayState_GameStateSwitchControl">
        <ContentControl.Resources>
            <Style TargetType="Button" BasedOn="{StaticResource {x:Type Button}}">
                <Setter Property="Background" Value="Transparent" />
            </Style>
        </ContentControl.Resources>
    </ContentControl>
</Border>
```

The Border provides the visual shell (Translucent10Brush, rounded corners). Only the inner PlayState button is interactive — no nested clickable controls.

> **Caveat**: `ContentControl.Resources` may interfere with Playnite's custom element resolution in some cases. If the button appears styled correctly but doesn't function, try removing the Resources block and styling via a shared style in DerivedStyles instead.

## Known Limitation: GameContextChanged in Fullscreen

**`GameContextChanged` does not fire for plugin custom elements inside fullscreen ControlTemplates.** This is a Playnite platform limitation, confirmed through direct testing:

- Desktop themes (e.g. KNARZnite): Views are `UserControls`/`DataTemplates` → `GameContextChanged` fires → plugin controls know which game is selected → suspend/resume works
- Fullscreen themes (e.g. Solaris): Views are `ControlTemplates` in `ResourceDictionary` files → Playnite doesn't propagate game context → `currentGameId` stays `Guid.Empty` → button command does nothing

**Not fixable from the theme side.** The plugin developer would need to either:
- Expose the suspend/resume command via a `PluginSettings` binding path
- Use a different mechanism than `GameContextChanged` (e.g. polling, global events)
- The plugin control's `OnGameStarted`/`OnGameStopped` events do fire in the plugin host, but aren't propagated to custom elements in fullscreen templates

**Workarounds for the user:**
- Use the plugin's hotkeys (PlayState default: `Shift+Alt+A`)
- Use the plugin's right-click game menu items
- Use the plugin's sidebar/manager view

## Design-First Workflow

When integrating a plugin control that isn't working yet:

1. **Fix design first** — Match size, spacing, colors to surrounding elements exactly. Use the same element types (ToggleButtonEx, Border) as nearby controls. Only move to functionality after design is approved.
2. **One change at a time** — Don't add the control to multiple views at once. Place it in ONE location, get it approved, then expand.
3. **Test functionality separately** — After design is approved, investigate why the control doesn't function
4. **Compare with a working reference theme** — Look for the exact same plugin integration pattern in a theme that works (e.g. KNARZnite for PlayState)
5. **Isolate variables** — Remove one styling element at a time (e.g. ContentControl.Resources, Border wrapper) to see if it breaks functionality. Keep a clean "design version" to restore.
6. **Learn from surrounding elements** — Check the exact style, size, margin, and tag patterns of adjacent controls. Copy them exactly rather than guessing.

## Fullscreen vs Desktop Differences

| Aspect | Desktop Theme | Fullscreen Theme |
|---|---|---|
| View system | UserControls / DataTemplates | ControlTemplates in ResourceDictionaries |
| Custom element resolution | `GetGameViewControl` works reliably | Same mechanism, but `GameContextChanged` may not fire |
| Plugin control styling | Style applied via named styles like `ActionControl` | Need local resource overrides (ContentControl.Resources) |

`GameContextChanged` (used by PlayState to know which game is selected) may not fire reliably for plugin controls inside fullscreen ControlTemplates. This is a Playnite limitation, not a theme bug.

## Workflow: Modify → Deploy → Test

1. **Backup first** — Copy the Windows theme folder:
   ```
   cp -r /mnt/c/.../Themes/Fullscreen/{ThemeId}/ ~/backups/
   ```

2. **Get theme source** — .pthm files are ZIP archives:
   ```
   python3 -c "import zipfile; zipfile.ZipFile('theme.pthm').extractall('source/')"
   ```

3. **Patch XAML** — Add ContentControl placeholders. Typical spots:
   - **GameDetails.xaml** — Plugin buttons row (near `ToggleGameInfo` or `ScreenshotUtilities`)
   - **GameStatus.xaml** — Buttons StackPanel (near `ReturnToGame` / `CloseGame`)
   - **Main.xaml** — Top bar (near `NowPlaying` button) or game list item template

4. **Deploy to Windows**:
   ```
   WIN_THEME="/mnt/c/Users/{USER}/AppData/Roaming/Playnite/Themes/Fullscreen/{ThemeId}"
   cp source/Views\\File.xaml "$WIN_THEME/Views/File.xaml"
   ```

5. **Test** — Restart Playnite fullscreen. Control appears when plugin installed + game state active.

## Finding Plugin Integration Points

- Plugin's `extension.yaml` — plugin ID and type
- Plugin's `Plugin.cs` — `AddCustomElementSupport` and `GetGameViewControl` methods
- Other themes with support — `grep -rn "PluginSettings Plugin=<Name>" . --include="*.xaml"`

## Pitfalls

- **Backslash paths in extracted .pthm** — ZIP from Windows builds uses `\`. Reference with `\\` in shell: `"Views\\File.xaml"`.
- **Escape-drift in patch** — Copy exact text from `sed -n 'N,Np'` output. Don't retype quotes.
- **Case-sensitive /mnt/ paths** — List the Fullscreen dir first to confirm exact folder name (has GUID).
- **Backup to Playnite's Backup folder**, not inside the theme dir.
