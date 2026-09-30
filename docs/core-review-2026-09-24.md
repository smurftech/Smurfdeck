# SmurfDeck core-function and UI review

Reviewed: 24 September 2026. Baseline: `main` before `feature/core-review-shortcuts`.

## Assessment

SmurfDeck has a working personal-use foundation for a Stream Deck on CachyOS/KDE
Wayland. Profiles, pages, shortcut injection, media keys and desktop actions are
already implemented. The former roadmap's completion describes those planned
phases; it does not mean feature equivalence with Elgato's Windows application.

The strongest immediate improvements are a useful preset library, image buttons,
and reliable editing. This branch delivers those, plus a deliberately bounded
first version of multi-actions. It preserves SmurfDeck's dark blue identity and
existing action-library / deck / lower-editor layout.

This is a source-code review, documented-product comparison, automated test run,
and offscreen Qt visual inspection. There is no attached Stream Deck, CachyOS
session, KWin compositor or Windows installation in the review environment.
Hardware acceptance from previous releases has not been repeated here.

## Core-function comparison

“Before” refers to the inspected implementation, not just README claims.

| Area | Elgato Windows workflow | SmurfDeck before | This branch / remaining difference |
|---|---|---|---|
| Action selection | Library to key, then properties | Searchable library, click and drag assignment | Adds category filter, chord search and 50 complete shortcut presets |
| Key images | Custom image files, image library | Text-only icon presets | PNG/JPEG/BMP, GIF and WebP selection; owned copy; shared preview/hardware composition |
| Animation | Animated key images | Missing | GIF/WebP frames, active page only, up to 10 fps; no video files |
| Labels | Key titles and visual controls | Label plus foreground/background presets | Measured font fitting; long-label wrapping; arbitrary existing colours retained; no title placement/font picker |
| Profiles | Named profiles and switching | Create, rename, duplicate, delete, select | Fixes duplicated page links and active-page preservation |
| Application profiles | Application-linked profiles | Optional `kdotool` polling | Delayed mapping lets the user focus the target app; no switch while editing window is active; still requires `kdotool` |
| Pages | Multiple layouts and navigation | Add/rename/reorder/delete, next/previous/specific page keys | Visible navigation, page count and add button; duplicate page added |
| Folders | Nested action organisation | Missing; flat pages only | Still missing; pages are not equivalent to folders |
| Pinned keys | Shared actions across pages | Missing | Still missing |
| Multi-actions | Ordered actions and delays | Missing | Visual step editor; shortcut/media/launch/open/delay; 1–32 steps; cancellation; stop on failure |
| Multi-action switches | Alternate action sets | Missing | Still missing; no toggle state, looping, nesting or parallel execution |
| Commands in sequences | Windows action ecosystem differs | Standalone shell-free commands supported | Standalone commands remain; asynchronous command steps are intentionally not offered until completion/cancellation semantics are implemented |
| Keyboard/media | Configurable hotkeys and media | Both implemented, press/release/both triggers | Adds 50 presets and fixes release binding; input still needs `/dev/uinput` access |
| Text insertion | Text action | Missing | Still missing; Unicode/layout-aware input needs separate design |
| Launch/open | Apps and URLs/files | Implemented | Retained; no shell evaluation added |
| Move/copy/edit | Rearrange and reuse actions | Drag move/swap, Ctrl-drag copy, undo/redo | Adds key context menu copy/paste/clear; page-specific undo/redo |
| Profile sharing/backup | Export/import and profile backups | Atomic local config and invalid-file recovery | Adds pre-upgrade schema backup; portable profile import/export still missing |
| Device lifecycle | Device selection and settings | Discovery, preferred device, tray, brightness, reconnect | Resets stale press state on device switch/reconnect; this is one active device, not independent simultaneous layouts |
| Sleep/screensaver | Additional device settings | Missing | Still missing |
| Extra device controls | Model-specific controls | Rectangular key grid | Dials, touch strips and model-specific controls remain outside implemented adapter/UI |

## Fixed defects and evidence

| Priority | Finding before changes | Resolution / verification |
|---|---|---|
| High | A global undo stack could replace keys on a different page | History scoped to profile/page; regression switches pages and checks both layouts |
| High | A release after navigation used the destination key's configuration | Engine snapshots the pressed action; regression changes the configuration between press and release |
| High | Duplicating a profile copied navigation references unchanged | Remaps links to newly created pages and preserves the selected page |
| High | Partial input failure could leave a modifier pressed | Attempts all releases and reports failure; simulated failed chord test |
| Medium | Old command completion could decorate another page or superseded command | Page-generation and per-key command tokens discard stale callbacks |
| Medium | Small editor hid controls and deck overlapped editor | Adjusted canvas height and editor width; visual check and geometry assertions at 900×600 |
| Medium | Hardware key presses replaced the visible draft | Physical input no longer selects another editor key |
| Medium | Label edits could silently replace colours not found in the preset list | Preserve existing custom values in selectors; regression checks exact colours |
| Medium | “Map active application” usually inspected SmurfDeck itself | Four-second focus handoff; cancelled if SmurfDeck still has focus |
| Medium | Hot unplug during rendering could raise from feedback or repeatedly open dialogs | Handles write errors and disconnects failed device; recovery stays available |
| Medium | A new schema made returning to the previous build unsafe without a copy | Saves the original schema configuration before the first upgrade write |
| Medium | Animation could repeatedly query USB metadata | Device geometry/identity cached for the lifetime of an opened device |
| Low | Corrupt drag MIME data could raise an exception | Malformed key IDs rejected; library transfers stable action/preset IDs |
| Low | Invalid subprocess result data could escape completion error handling | Handles value/decoding failures as action errors |

Core changes are in `actions/engine.py`, `input/uinput.py`, `models/config.py`,
`rendering/`, `persistence/config_store.py` and `ui/main_window.py`.
New functionality is separated into `actions/presets.py`, `actions/sequences.py`,
`rendering/images.py` and `ui/sequence_editor.py`.

## Boundaries of the new features

- The 50 shortcuts are a curated everyday set based on KDE's published defaults,
  not a measured “top 50” ranking. See [the full catalogue](shortcuts.md).
- Application shortcuts go to the focused application. Choosing a Konsole preset
  does not activate Konsole. Custom shortcuts and other desktop environments can
  differ; each preset remains editable after assignment.
- There is no conventional Konsole clipboard-cut equivalent. Desktop Cut is
  `Ctrl+X`; terminal Copy/Paste are separately named. Shell line editing and
  terminal interrupt signals must not be confused with clipboard operations.
- Images are proportionally fitted, not stretched. Empty labels allow image-only
  buttons. Animation loops with a minimum frame duration of 100 ms. Limits:
  10 MiB input, 4 million pixels, 120 frames. Images live beside the configuration
  under `images/`. Copying only `config.json` is not a portable image backup.
- A single multi-action runs at a time. Ordinary actions remain available. There
  is a 100 ms inter-action interval, explicit delays of 0–60,000 ms, and a total
  explicit delay limit of five minutes. Changing page/profile or device and
  quitting cancel scheduled steps. Stop does not close an application already
  launched, undo completed steps or terminate a separate standalone command.
- A launch step confirms process start, not that a window is ready. Use an
  explicit delay before shortcuts, and physically test the focus transition.
- Changes are saved with **Apply to key**. There is still no complete draft
  recovery/unsaved-edit guard across manual page/profile changes. Finish edits
  before navigating. This should precede broader editor expansion.

## Remaining engineering priorities

1. **Editor durability and portable backup:** protect unfinished drafts across
   all navigation paths; export/import versioned profiles with bundled images;
   manage orphaned image assets. Current copying is additive and does not delete
   images when a key is cleared.
2. **Runtime/device acceptance:** validate uinput first-use readiness, layout
   differences, 15/32 animated keys, CPU/USB throughput, reconnect while pressed,
   device switches and tray quit in the actual CachyOS session. Native writes
   remain synchronous on Qt's thread; move to a bounded rendering worker if
   hardware measurements show stalls.
3. **Profile automation:** `kdotool` detection can block for up to one second and
   polls every 1.5 seconds. Move detection off the UI thread, expose rule editing,
   define behaviour for unknown apps, and preserve unfinished drafts on focus loss.
4. **Navigation organisation:** folders, pinned navigation keys, profile-switch
   keys and explicit cross-profile page links. Existing page IDs are local to a
   profile; pasting a specific-page key across profiles may need retargeting.
5. **Richer actions:** Unicode text, multi-action switches, command completion
   steps, richer label placement and optional animation speed. Keep these in
   distinct feature releases with clear execution semantics.
6. **Hardening:** profile/page ID uniqueness validation for manually edited
   configs; bounded command output capture; process-tree shutdown for long-lived
   child commands; stronger provenance for queued events during device changes.
   Commands remain local user-authored commands, without implicit shell parsing.
7. **Release tooling:** no GitHub Actions workflow exists in this checkout.
   Add a reproducible CI lint/test/build gate and then the existing public-site /
   Arch-package distribution checkpoint. This review does not install or deploy
   software onto the user's PC.

## Validation

- Baseline: 57 tests passing; Ruff clean.
- This branch: 79 tests passing; Ruff clean; `git diff --check` clean;
  source distribution and wheel built successfully, with all new modules included.
- Visually inspected offscreen Qt at 900×600, 1180×780 and an 8×4 grid at
  1920×900. These are rendered application screenshots, not design mockups.
- Tests cover all 50 shortcut emissions using fake input, persistence/migration,
  page history isolation, copied navigation links, GIF frame composition/native
  encoding, sequence ordering/cancellation/failure, and compact-control geometry.
- No physical device, actual desktop shortcut delivery or Windows app execution
  was tested. Elgato comparisons use its published feature documentation.

## Reference documentation

Checked 24 September 2026; product behaviour can change independently.

- [Elgato Multi Action Switch](https://help.elgato.com/hc/en-us/articles/5162934218637-Elgato-Stream-Deck-4-4-Release-Notes)
- [Elgato Text action updates](https://help.elgato.com/hc/en-us/articles/34904105205777-Elgato-Stream-Deck-6-9-Release-Notes)
- [Elgato custom key icons](https://help.elgato.com/hc/en-us/articles/360028237271-Elgato-Stream-Deck-Customizing-Key-Icons)
- [Elgato Multi Actions](https://help.elgato.com/hc/en-us/articles/360027960912-Elgato-Stream-Deck-Multi-Actions)
- [Elgato pinned actions and folders](https://help.elgato.com/hc/en-us/articles/26638431612429-Elgato-Stream-Deck-Pinned-Actions-and-Folders)
- [Elgato folders](https://help.elgato.com/hc/en-us/articles/360027957912-Elgato-Stream-Deck-Using-Folders)
- [Elgato profile backups](https://help.elgato.com/hc/en-us/articles/360048424432-Elgato-Stream-Deck-How-to-Back-Up-and-Restore-Profiles)
- [KDE common shortcuts](https://docs.kde.org/trunk_kf6/en/khelpcenter/fundamentals/kbd.html)
- [Dolphin commands](https://docs.kde.org/stable_kf6/en/dolphin/dolphin/command-reference.html)
- [Konsole commands](https://docs.kde.org/trunk_kf6/en/konsole/konsole/commandreference.html)
