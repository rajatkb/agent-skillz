---
name: playnite-theme-development
description: Modifying and extending Playnite fullscreen themes — .pthm extraction, XAML structure, plugin integration patterns, and adding custom controls like PlayState's GameStateSwitchControl.
triggers:
  - user mentions editing/modifying a Playnite theme
  - user mentions PlayState, NowPlaying, or other Playnite plugin integration
  - user references .pthm files or Playnite XAML themes
  - user wants to add plugin UI elements to a theme
---

# Playnite Theme Development

## Source extraction

Playnite themes are distributed as `.pthm` files — this is just a renamed ZIP archive.

```bash
# Download latest release
curl -sL "$RELEASE_URL" -o theme.pthm

# Extract with Python (if unzip not available)
python3 -c "
import zipfile, os
os.makedirs('source', exist_ok=True)
with zipfile.ZipFile('theme.pthm', 'r') as z:
    z.extractall('source/')
"
```

The GitHub repo for a theme often only contains metadata (`theme.yaml`, screenshots, `InstallerManifest.yaml`) — the actual XAML source is only in the `.pthm` releases.

## Theme structure

| Path | Purpose |
|------|---------|
| `theme.yaml` | Theme metadata — ID, name, version, required API version |
| `options.yaml` | Theme Options customization presets (scales, avatars, colors, etc.) |
| `Constants.xaml` | Brushes, colors, sizes, and other design tokens |
| `Media.xaml` | Image brushes, icons, paths, and resource dictionaries |
| `DefaultControls/*.xaml` | Styled overrides for Playnite's built-in controls (Button, CheckBox, etc.) |
| `DerivedStyles/*.xaml` | Custom composite styles (game list items, menu buttons) |
| `Views/Main.xaml` | Main fullscreen view template (often the largest file) |
| `Views/GameDetails.xaml` | Game details view (screens, metadata, trailer) |
| `Views/GameStatus.xaml` | Running game overlay (Return to Game, Close, time counter) |
| `Views/GameMenu.xaml` | Right-click / context menu on games |
| `Views/MainMenu.xaml` | Main hamburger menu |
| `Views/FiltersView.xaml` | Filter/sort panels |
| `Localization/*.xaml` | String resources per language |
| `CustomControls/*.xaml` | Theme-specific custom controls |

## Plugin integration patterns

### Pattern 1: PluginSettings bindings (data-driven, e.g. NowPlaying)

Used when a plugin exposes data via `PluginSettings` markup extension:

```xml
<!-- Check if a plugin is installed -->
<Condition Binding="{PluginStatus Plugin=NowPlaying_db4e7ade-57fb-426c-8392-60e2347a0209, Status=Installed}" Value="True" />

<!-- Get a value from the plugin -->
<TextBlock Text="{PluginSettings Plugin=NowPlaying, Path=SessionLength}" />
<TextBlock Text="{PluginSettings Plugin=NowPlaying, Path=RunningGame.GameName}" />

<!-- Bind a command -->
<ButtonEx Command="{PluginSettings Plugin=NowPlaying, Path=ReturnToGame}" />
```

Use `MultiDataTrigger` with both `PluginSettings` and `PluginStatus` to conditionally show/hide UI:

```xml
<MultiDataTrigger>
    <MultiDataTrigger.Conditions>
        <Condition Binding="{PluginSettings Plugin=NowPlaying, Path=IsGameRunning}" Value="True" />
        <Condition Binding="{PluginStatus Plugin=NowPlaying_db4e7ade-57fb-426c-8392-60e2347a0209, Status=Installed}" Value="True" />
    </MultiDataTrigger.Conditions>
    <Setter Property="Visibility" Value="Visible" TargetName="SomeElement" />
</MultiDataTrigger>
```

### Pattern 2: Custom controls via ContentControl naming convention (e.g. PlayState's GameStateSwitchControl)

Used when a plugin registers a custom UI control via `AddCustomElementSupport` in C#:

```csharp
AddCustomElementSupport(new AddCustomElementSupportArgs
{
    ElementList = new List<string> { "GameStateSwitchControl" },
    SourceName = "PlayState",
});
```

Themes place a **ContentControl placeholder** with a specific `x:Name` convention:

```xml
<ContentControl x:Name="PlayState_GameStateSwitchControl" ... />
```

The naming convention is `{SourceName}_{ElementName}` — this tells Playnite to replace the ContentControl at runtime with the actual plugin control returned by `GetGameViewControl`.

**Visibility binding** — always use `PluginSettings` so the placeholder hides when the plugin isn't installed:

```xml
<ContentControl x:Name="PlayState_GameStateSwitchControl"
    Visibility="{PluginSettings Plugin=PlayState, Path=IsControlVisible,
                 FallbackValue=Collapsed,
                 Converter={StaticResource BooleanToVisibilityConverter}}" />
```

The `IsControlVisible` property is marked `[DontSerialize]` and gets set by the control itself at runtime — it's `true` only when a tracked game is running or paused.

**CRITICAL: Styling the inner control — the "white button" fix**

The PlayState `GameStateSwitchControl` is a `PluginUserControl` containing a bare `<Button>` with no explicit `Background`. This button uses the theme's default `Button` style for its template but inherits **WPF's system default background** (solid white) because the theme's default Button style typically doesn't set `Background` explicitly. This causes the button to render as a **solid white box**.

Fix by overriding at the ContentControl's local resource scope:

```xml
<ContentControl x:Name="PlayState_GameStateSwitchControl"
                Height="50" Width="50" Margin="0,0,10,0" Tag="Alt"
                VerticalAlignment="Center"
                Visibility="{PluginSettings Plugin=PlayState, Path=IsControlVisible,
                             FallbackValue=Collapsed,
                             Converter={StaticResource BooleanToVisibilityConverter}}">
    <ContentControl.Resources>
        <!-- Kill white background on inner button -->
        <Style TargetType="Button" BasedOn="{StaticResource {x:Type Button}}">
            <Setter Property="Background" Value="Transparent" />
        </Style>
        <!-- Match ToggleButtonEx Translucent10Brush instead of default 05Brush -->
        <Style x:Key="ButtonBackgroundStyle" TargetType="Border">
            <Setter Property="Background" Value="{DynamicResource Translucent10Brush}" />
            <Setter Property="CornerRadius" Value="{DynamicResource InfoBoxCorner}" />
            <Setter Property="Margin" Value="5" />
        </Style>
    </ContentControl.Resources>
</ContentControl>
```

⚠️ **Tradeoff**: The `ContentControl.Resources` block provides proper styling but may prevent Playnite from calling `GetGameViewControl` to resolve the custom element, causing the button to appear styled but non-functional. If the button doesn't work, try removing the Resources block (the button will look different but may function). This is a known limitation — see `references/playstate-plugin-details.md` for more details.

**Why Translucent10Brush vs Translucent05Brush?** Surrounding `ToggleButtonEx` icon buttons use `ToggleBackgroundStyle` → `Translucent10Brush` (10% white). The default `Button` template uses `ButtonBackgroundStyle` → `Translucent05Brush` (5% white). The inner PlayState button uses the default `Button` template, so you must override `ButtonBackgroundStyle` locally to match the surrounding buttons' opacity.

**Fullscreen vs Desktop dimension sizing:**

- **Desktop themes** (e.g. KNARZnite): Use a shared `ActionControl` style with `BasedOn="{StaticResource BaseStyle}"` — the ContentControl inherits sizing from the style.
- **Fullscreen themes** (e.g. Solaris): Must set explicit `Height` and `MinWidth` on the ContentControl. Without these, the control collapses to 0. Match the theme's button dimensions (Solaris icon buttons are `Height="50" Width="50"`).

**Known working naming convention examples from Solaris (fullscreen):**
- `ExtraMetadataLoader_VideoLoaderControl_NoControls_Sound`
- `CheckLocalizations_PluginFlags`
- `LibraryManagement_PluginFeaturesIconList`
- `NewsViewer_PlayersInGameViewerControl`
- `BackgroundChanger_PluginCoverImage`
- `HowLongToBeat_PluginProgressBar`
- `PlayState_GameStateSwitchControl`

### Pattern 2 (legacy/desktop-only): PluginControl markup extension

Older themes may use the `Custom:PluginControl` syntax:

```xml
<Custom:PluginControl Plugin="PlayState" Name="GameStateSwitchControl" />
```

This requires the namespace `xmlns:Custom="clr-namespace:Playnite.Controls;assembly=Playnite"` and primarily works in desktop mode. For fullscreen themes, prefer the ContentControl naming convention (Pattern 2 variant above), which is proven to work in ControlTemplates.

### Finding plugin IDs

Plugin extension IDs are defined in `extension.yaml` as `Id:` and also in the C# source as `public override Guid Id`. The `PluginStatus` binding uses `Plugin=<AddonId>` from the addon manifest.

- PlayState ID: `26375941-d460-4d32-925f-ad11e2facd8f`
- NowPlaying ID: `db4e7ade-57fb-426c-8392-60e2347a0209`

For `PluginStatus`, use the addon ID (GUID). For `PluginSettings`, use the short plugin name.

## Adding PlayState GameStateSwitchControl to a theme

PlayState's core UI element is a pause/resume toggle button for the currently running game.

### 1. Add the control reference to GameStatus.xaml

Add next to the existing NowPlaying buttons:

```xml
<!-- PlayState//Suspend/Resume -->
<Custom:PluginControl Plugin="PlayState" Name="GameStateSwitchControl"
    x:Name="PlayStateButton" />

<!-- Show only when a game is running -->
<MultiDataTrigger>
    <MultiDataTrigger.Conditions>
        <Condition Binding="{PluginStatus Plugin=PlayState, Status=Installed}" Value="True" />
        <Condition Binding="{PluginSettings Plugin=NowPlaying, Path=IsGameRunning}" Value="True" />
    </MultiDataTrigger.Conditions>
    <Setter Property="Visibility" Value="Visible" TargetName="PlayStateButton" />
</MultiDataTrigger>
```

### 2. Add namespace if needed

The `Custom:` prefix may need:
```xml
xmlns:Custom="clr-namespace:Playnite.Controls;assembly=Playnite"
```

Or just use the full `PluginControl` syntax — many themes already have Playnite namespaces imported in Main.xaml.

### 3. Style the control

The GameStateSwitchControl is a `Button` with `Visibility` bindings internally. Style it like other action buttons in the theme:

```xml
<Style x:Key="ButtonPlayStateAction" BasedOn="{StaticResource {x:Type ButtonEx}}" TargetType="ButtonEx">
    <Setter Property="Tag" Value="GameStateButton" />
</Style>
```

## WSL → Windows deployment workflow

When developing themes from WSL for installation on Windows:

### 1. Backup existing theme first

```bash
THEME_DIR="/mnt/c/Users/<user>/AppData/Roaming/Playnite/Themes/Fullscreen/<ThemeId>/"
BACKUP_DIR="/mnt/c/Users/<user>/AppData/Roaming/Playnite/Backup/<ThemeId>_backup_$(date +%Y%m%d_%H%M%S)"
mkdir -p "$BACKUP_DIR"
cp -r "$THEME_DIR/"* "$BACKUP_DIR/"
```

### 2. Copy modified files

Only copy the files you changed — no need to re-copy assets:

```bash
WIN_THEME="/mnt/c/Users/<user>/AppData/Roaming/Playnite/Themes/Fullscreen/<ThemeId>/"
cp "$SRC/Views\\GameDetails.xaml" "$WIN_THEME/Views/GameDetails.xaml"
# ... repeat for each modified file
diff -q "$SRC/Views\\GameDetails.xaml" "$WIN_THEME/Views/GameDetails.xaml"  # verify
```

**Note:** Files extracted from `.pthm` on Linux have `\` in their names (Windows path separator). Reference them with quotes: `"Views\\GameDetails.xaml"`, or use Python to rename them.

### 3. Restart Playnite

User must restart Playnite fullscreen to pick up changes. No hot-reload.

## Plugin compatibility checklist

When adding a new plugin integration to a theme:

1. Find the plugin's GitHub repo and check `extension.yaml` for ID
2. Check C# source for `AddCustomElementSupport` (custom controls) vs `PluginSettings` bindings
3. Look for existing theme integration in the plugin's wiki or README
4. Check the `PluginControl` styling to match the theme's button aesthetics
5. Add appropriate visibility triggers (PluginStatus conditionals)

## Pitfalls

- **White button**: The PlayState GameStateSwitchControl's inner Button inherits WPF's solid white system background. Override with local `Style TargetType="Button"` setting `Background="Transparent"` — see Pattern 2 section above for the full solution.
- **Color matching**: Use `Translucent10Brush` for `ButtonBackgroundStyle` override to match `ToggleButtonEx` icons (default is `Translucent05Brush`, too dim).
- **ContentControl.Resources may block custom element resolution**: Putting `ContentControl.Resources` on the ContentControl placeholder (with Button style override + ButtonBackgroundStyle override) might prevent Playnite from calling `GetGameViewControl`, making the button appear but not function. Tradeoff: Resources block = correct styling but possibly broken functionality; bare ContentControl = correct functionality but unstyled button. If the button doesn't work, try removing the Resources block first to isolate the issue.
- **ToggleButtonEx wrapper approach FAILS**: The user may ask you to wrap the PlayState ContentControl in a ToggleButtonEx for styling consistency (matching adjacent `ToggleButtonEx` icon buttons). Do NOT do this — nesting a ContentControl inside `ToggleButtonEx.Content` prevents Playnite's custom element resolver from finding it. The ContentControl must be a **direct child** in the visual tree (e.g. a direct child of a StackPanel, Grid, or Border). Skip the ToggleButtonEx wrapper entirely and use the ContentControl.Resources approach instead for styling.
- **46x46 sizing with VerticalAlignment prevents clipping**: The PlayState inner Button renders at Height=50 (default Button style), but the background border's Margin=5 causes bottom clipping. Fix: set the outer ContentControl to Height=46 Width=46 with VerticalAlignment=Center (no bottom margin — user reported Margin=0,0,10,10 as "too much").
- **GameContextChanged may not fire in Fullscreen ControlTemplates**: The `GameContextChanged` method on `PluginUserControl` (used by PlayState's GameStateSwitchControl to detect the selected game) may not fire reliably when the ContentControl is inside a Fullscreen `ControlTemplate` (ResourceDictionary-based). Desktop themes (UserControl-based) don't have this issue. If the button appears but clicking does nothing, `GameContextChanged` is likely not being called.
- **Backslash paths**: `.pthm` files built on Windows use `\\` as path separator. When extracting on Linux, files are flat in a single directory. Access them with quoted paths: `cat "Views\\\\Main.xaml"`
- **Plugin IDs**: The ID used in `PluginStatus` is the addon GUID from `extension.yaml`, NOT the short name used in `PluginSettings`
- **Main.xaml is huge**: Solaris Main.xaml is ~1MB with thousands of lines — use `read_file` with offset/limit to navigate, not `cat`
- **Animation triggers**: Many Solaris UI elements use complex MultiDataTrigger chains with custom tags. Don't remove existing triggers — add new ones alongside them
- **Theme API version**: Check `theme.yaml` RequiredApiVersion matches installed Playnite version
- **`.gitignore` extracted artifacts**: Theme repos typically only track metadata (theme.yaml, InstallerManifest.yaml, screenshots). Add `source/` and `*.pthm` to `.gitignore` after extracting — they're build artifacts, not source files.

## User preferences (Rajat)

- **One change at a time**: Make ONE edit per iteration. Don't batch multiple fixes (e.g. styling + size + margin all at once). The user will reject batched edits.
- **Style first, functionality later**: Get visual appearance right first — match size, spacing, colors, and surrounding element patterns exactly. Get user approval on design before investigating functionality issues.
- **Learn from surrounding code**: Before writing new XAML, study the exact structure and styling of adjacent elements. Match `Tag`, `Margin`, nesting patterns, and brush references exactly. Copy-paste an existing button and swap the content.
- **Explicit copy confirmation**: State clearly when code has been copied from WSL → Windows. Confirm with `diff -q` and say "Copied". The user needs explicit confirmation that Windows files are updated.
- **Revert cleanly**: When something doesn't work, revert to the last working state (re-extract from `.pthm`) rather than piling on more edits. Don't try to fix two issues in one pass.
