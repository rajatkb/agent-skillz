# Solaris + PlayState Integration (Session Notes)

## Final Working Design (approved visually, non-functional)

```xml
<!-- PlayState -->
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

**Structure:** Border (visual shell) → ContentControl (PlayState placeholder) with minimal Resources.

**Why Border instead of ToggleButtonEx:** Avoids nested interactive controls. Border is passive (no click handling); only the inner PlayState button is interactive.

## Design Iterations

1. **Initial**: 3 locations (GameDetails, GameStatus, Main). No styling → white opaque button, clipped bottom
2. **Style fix**: Added `ContentControl.Resources` with Button Background override + `Translucent10Brush` → design approved
3. **ToggleButtonEx wrapper**: Nested ContentControl inside ToggleButtonEx → "button inside a button" confusion
4. **Border wrapper**: Replaced ToggleButtonEx with passive Border → cleaner, approved
5. **Bare ContentControl** (no styling): Tested if Resources/Border blocked functionality → styling broke, functionality still didn't work
6. **Restored**: Border + Resources version restored (best design)

## Key Findings

- PlayState's `GameStateSwitchControl` inner Button uses the theme's **default `{x:Type Button}` style**, not `ButtonIconStyle`
- Default Button in Solaris: `Translucent05Brush` (5% white opacity), Height=50
- ToggleButtonEx (icon buttons): `Translucent10Brush` (10% white opacity), 50x50
- Fix: `ContentControl.Resources` overriding Button `Background="Transparent"` so the outer Border's `Translucent10Brush` shows through
- The `ContentControl.Resources` block does NOT break functionality—the bare ContentControl test proved the problem is elsewhere

## Functionality: Root Cause

**`GameContextChanged` does not fire for plugin custom elements inside fullscreen ControlTemplates.** This is a Playnite platform limitation:

- Desktop themes (KNARZnite): `GameContextChanged` fires → PlayState button works
- Fullscreen themes (Solaris): ControlTemplates in ResourceDictionaries don't propagate game context → button never knows which game is selected → `currentGameId` stays `Guid.Empty` → command does nothing

Confirmed via direct test (bare ContentControl with no Resources/Border wrappers — still didn't work). Not fixable from the theme side.

## Working Alternatives

- PlayState hotkeys: `Shift+Alt+A` (default) to suspend/resume
- PlayState right-click game menu → Suspend/Resume
- PlayState Manager sidebar item

## KNARZnite Reference

Desktop theme (`~/Work/Playnite-Theme-KNARZnite/`).

PlayState integration in `Views/DetailsViewGameOverview.xaml` line 221 and `Views/GridViewGameOverview.xaml` line 221:
```xml
<ContentControl x:Name="PlayState_GameStateSwitchControl" 
    Style="{DynamicResource ActionControl}" 
    Visibility="{PluginSettings Plugin=PlayState, Path=IsControlVisible, FallbackValue=Collapsed, Converter={StaticResource BooleanToVisibilityConverter}}" />
```

Uses `ActionControl` style (Height=40, MinWidth=40, Border, Margin). No inline Resources. Works because KNARZnite is a **Desktop theme** (UserControls/DataTemplates) where `GameContextChanged` fires properly.

## Files

- WSL source: `~/Work/Solaris/source/`
- Windows: `C:\Users\RAJAT\AppData\Roaming\Playnite\Themes\Fullscreen\Solaris_b6e50d04-24ae-4ecd-bd3a-080367930992\`
- Backup: `C:\Users\RAJAT\AppData\Roaming\Playnite\Backup\Solaris_backup_20260710_114833\`
- Reference theme: `~/Work/Playnite-Theme-KNARZnite/`