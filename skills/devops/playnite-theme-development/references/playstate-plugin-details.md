# PlayState Plugin (darklinkpower)

**Repo:** https://github.com/darklinkpower/PlayniteExtensionsCollection  
**Location:** `source/Generic/PlayState/`  
**Extension ID (extension.yaml):** `PlayState`  
**Addon GUID (PluginStatus):** `26375941-d460-4d32-925f-ad11e2facd8f`  
**Latest version:** 2.80

## What it does

Lets you suspend and resume any game process, freeing CPU/GPU while keeping the process alive. Works via:
- Keyboard hotkeys
- Controller combos (XInput)
- A custom UI control (`GameStateSwitchControl`)

## Theme integration

### Custom element (works in fullscreen AND desktop)

```csharp
AddCustomElementSupport(new AddCustomElementSupportArgs
{
    ElementList = new List<string> { "GameStateSwitchControl" },
    SourceName = "PlayState",
});
```

In the theme, use a **ContentControl with naming convention** (proven working in fullscreen ControlTemplates):

```xml
<ContentControl x:Name="PlayState_GameStateSwitchControl"
                Height="50" MinWidth="50" Margin="0,0,10,0"
                VerticalAlignment="Center"
                Visibility="{PluginSettings Plugin=PlayState, Path=IsControlVisible,
                             FallbackValue=Collapsed,
                             Converter={StaticResource BooleanToVisibilityConverter}}" />
```

The naming convention is `{SourceName}_{ElementName}` — Playnite replaces this ContentControl with PlayState's actual pause/resume button at runtime.

**CRITICAL: The ContentControl MUST be a direct child** in the visual tree. Wrapping it inside `ToggleButtonEx.Content`, `Button.Content`, or any other control's content section hides it from Playnite's custom element resolver. Only direct children of StackPanel, Grid, Border, or similar layout containers are found. This was verified empirically — the user's preferred approach (ToggleButtonEx wrapper) produces a styled but non-functional button.

### Visibility mechanism

- **Outer** (`PluginSettings Plugin=PlayState, Path=IsControlVisible`): Controls whether the ContentControl placeholder is shown. Only `true` when a tracked game is running or paused. Property is `[DontSerialize]` (runtime-only).
- **Inner** (`ControlVisibility` on the Button inside GameStateSwitchControl): The plugin's own visibility management.
- **Setting**: `EnableGameStateSwitchControl` (default: `true`) in PlayState settings must be enabled for the control to function.
- Both layers must be Visible for the button to appear.

### Desktop-only legacy approach

Some themes may use the `Custom:PluginControl` syntax instead:

```xml
<Custom:PluginControl Plugin="PlayState" Name="GameStateSwitchControl" />
```

This works primarily in desktop mode. For fullscreen, the ContentControl approach is preferred and confirmed working.

### Internal control structure (from GameStateSwitchControl.xaml)

```xml
<Button Visibility="{Binding ControlVisibility}"
        Command="{Binding SwitchCurrentGameStatusCommand}">
    <Grid>
        <TextBlock Text="&#xEC72;" FontFamily="{DynamicResource FontIcoFont}"
                   Visibility="{Binding PauseIconVisibility}" />
        <TextBlock Text="&#xEC74;" FontFamily="{DynamicResource FontIcoFont}"
                   Visibility="{Binding ResumeIconVisibility}" />
    </Grid>
</Button>
```

- Uses IcoFont glyphs for icons (no external image dependency)
- `ControlVisibility` binding handles show/hide automatically (based on whether a game is running)
- `PauseIconVisibility` / `ResumeIconVisibility` toggle based on current suspend state

### The "white button" problem

The Button above has **no explicit `Background` set**. WPF's default Button background is solid white (system default). The theme's `DefaultControls/Button.xaml` style typically does NOT set `Background` explicitly — it only sets the `ControlTemplate`. So the Button renders as a **solid white box**.

To fix, wrap the ContentControl with local resource overrides:

```xml
<ContentControl x:Name="PlayState_GameStateSwitchControl" Height="50" Width="50" ...>
    <ContentControl.Resources>
        <Style TargetType="Button" BasedOn="{StaticResource {x:Type Button}}">
            <Setter Property="Background" Value="Transparent" />
        </Style>
        <Style x:Key="ButtonBackgroundStyle" TargetType="Border">
            <Setter Property="IsHitTestVisible" Value="False" />
            <Setter Property="CornerRadius" Value="{DynamicResource InfoBoxCorner}" />
            <Setter Property="Background" Value="{DynamicResource Translucent10Brush}" />
            <Setter Property="Margin" Value="5" />
        </Style>
    </ContentControl.Resources>
</ContentControl>
```

The `Background="Transparent"` override kills the white system default on the Button's Grid. The `ButtonBackgroundStyle` override changes the translucent overlay from the default `Translucent05Brush` (5%) to `Translucent10Brush` (10%) to match the surrounding `ToggleButtonEx` icon buttons which use `ToggleBackgroundStyle`.

### 46x46 sizing with bottom margin

To prevent clipping from the ToggleBackgroundStyle's `Margin="5"`, use `Height="46" Width="46"` with `Margin="0,0,10,10"`:

```xml
<ContentControl x:Name="PlayState_GameStateSwitchControl" Height="46" Width="46" 
                Margin="0,0,10,10" Tag="Alt" VerticalAlignment="Center" ...>
```

This matches the visual alignment of neighboring `ToggleButtonEx` buttons (50x50 with 5px margin on the background border inside).

### Color matching with surrounding buttons

| Element | Background Style | Brush | Opacity |
|---------|-----------------|-------|---------|
| `ToggleButtonEx` (plugin icons) | `ToggleBackgroundStyle` | `Translucent10Brush` | 10% |
| Default `Button` (PlayState inner) | `ButtonBackgroundStyle` | `Translucent05Brush` | 5% |
| Fixed PlayState (with override) | `ButtonBackgroundStyle` override | `Translucent10Brush` | 10% |

### Sidebar item

PlayState also registers a sidebar item (manager view) for the desktop mode — this doesn't need theme styling.

### No PluginSettings bindings (except IsControlVisible)

Unlike NowPlaying, PlayState does **not** expose game-specific data via `PluginSettings` markup extension (no `SessionLength`, `RunningGame.GameName`, etc.). The only `PluginSettings`-accessible property is:

- `Path=IsControlVisible` — bool, runtime-only (`[DontSerialize]`), reflects whether the GameStateSwitchControl's inner button is visible (game is running/paused).

All other interaction (suspend, resume, status) is handled internally by the `GameStateSwitchControl`.

## Settings reference

| Setting | Default | Description |
|---------|---------|-------------|
| `EnableGameStateSwitchControl` | `true` | Show the in-theme pause/resume button |
| `SuspendHotKey` | Shift+Alt+A | Keyboard shortcut to suspend/resume |
| `InformationHotkey` | Shift+Alt+I | Show game info |
| `GlobalSuspendMode` | Processes | Suspend method (Processes vs Playtime) |
| `UseForegroundAutomaticSuspend` | `false` | Auto-suspend when game loses focus |

The `"Show game state switch control"` checkbox in PlayState settings must be checked for the theme button to function.

## How to verify integration in Playnite

1. Install PlayState from Playnite addon browser
2. Apply the theme
3. Launch a game
4. The GameStateSwitchControl button should appear where placed in the theme's XAML
5. Press it to suspend — CPU/GPU usage should drop to near-zero
6. Press again to resume

## Known issues

### ContentControl.Resources may break GetGameViewControl resolution

Putting a `<ContentControl.Resources>` block on the ContentControl placeholder (to override Button styling) may prevent Playnite from calling `GetGameViewControl`, which means the PlayState GameStateSwitchControl is never instantiated. The button would appear (as an empty ContentControl with styling) but clicking does nothing.

**Root cause**: Unknown — likely a limitation in how Playnite's custom element resolver interacts with XAML resource scopes on the placeholder element.

**Patterns tested:**

| Approach | Styling | Functionality |
|----------|---------|---------------|
| Bare ContentControl, no Resources | Unstyled (white button) | Works (if GameContextChanged fires) |
| ContentControl with Resources block | Correct (matches ToggleButtonEx) | May not work (button appears but no action) |
| ContentControl inside ToggleButtonEx.Content | Nested — not found by resolver | Does not work |
| ToggleButtonEx wrapping ContentControl as direct child | Not possible (different types) | N/A |

### GameContextChanged in Fullscreen vs Desktop

The `GameContextChanged` method on `PluginUserControl` is called by Playnite when the selected game changes. In Desktop themes (UserControls), this fires reliably. In Fullscreen themes (ControlTemplates in ResourceDictionaries), it may **not** fire at all for custom elements resolved via `GetGameViewControl`. This is a Playnite SDK limitation — the Fullscreen theme system doesn't propagate game context changes to embedded plugin controls the same way Desktop does.

**Workarounds:**
- None known. The GameStateSwitchControl relies entirely on `GameContextChanged` to know which game ID to track.
- Hotkeys (default Shift+Alt+A) still work regardless of theme integration.
- The PlayState manager sidebar item (Desktop mode) still works.

| File | Purpose |
|------|---------|
| `PlayState.cs` | Main plugin class, registers custom element via `AddCustomElementSupport` |
| `PlayState2.cs` | Hotkey registration, Windows hooks |
| `Controls/GameStateSwitchControl.xaml` | The toggle button UI |
| `Controls/GameStateSwitchControl.xaml.cs` | Code-behind with visibility bindings |
| `extension.yaml` | Addon metadata (Id: PlayState) |
