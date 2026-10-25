# Changelog

## 0.1.2 - 2026-10-25

### Fixed

- Rebuild the board overlay for Halloween game build 26187517, preserving the updated original board functions and properties. Fixes the car-to-cabin loading crash reported by Trixarian.

### Added

- Apply the host's turn speed to the new visitor rewind animation. Intro, dialogue and minigame timers remain unchanged.

## 0.1.1 - 2026-10-23

### Fixed

- Wait for the speed receiver hook before sending the initial host value.
- Recover host speed initialization when a running round predates hook registration.
- Report missing host speed once per board instead of silently retaining native speed.

## 0.1.0

### Added

- Speed up table, card and board-piece transitions at 2x by default.
- Keep intro and minigame timers at their original pace.
