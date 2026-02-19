# Zone Touch 3 Home Assistant Integration

![Zone Touch 3 logo](img/logo.png)

A modern local integration for Polyaire Zone Touch 3 controllers.

## What This Integration Provides

- Config-entry setup (UI-based, no YAML required)
- Auto-discovery of zones and zone names from the controller
- One fan entity per zone damper (open/close + percentage)
- Coordinator-based polling with connection recovery
- Optional safety guard to prevent closing the last open zone
- Burst-safe command sequencing (command pacing + debounced refresh)
- Bulk service: `zonetouch3.set_all_zones` for reliable all-zone updates
- Diagnostics support for troubleshooting

## Requirements

- Home Assistant with `custom_components` support
- Zone Touch 3 reachable over LAN (default port `7030`)

## Installation

### Via HACS

Use the repository in HACS and restart Home Assistant after installation.

[![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=Paint-The-Night&repository=ha_zonetouch3&category=integration)
[GitHub Repository](https://github.com/Paint-The-Night/ha_zonetouch3)

### Manual

Copy this integration folder to:

`/config/custom_components/zonetouch3/`

Then restart Home Assistant.

## Setup

1. Go to `Settings -> Devices & Services -> Add Integration`
2. Search for `Zone Touch 3`
3. Enter:
   - Controller IP address
   - Port (default: `7030`)
   - Poll interval
   - Socket timeout
   - Safety guard preference
   - Command gap and post-command settle delay (for multi-zone action reliability)

No `configuration.yaml` fan platform config is required.

## Service

Use `zonetouch3.set_all_zones` to apply one target to all zones in a coordinated way.

- `percentage`: target for all zones (`0` turns all zones off)
- `entry_id` (optional): target one Zone Touch 3 config entry
- `bypass_min_open_guard` (default: `true`): allows all zones to close even when safety guard is enabled

## Notes

- Zone names are read from the Zone Touch 3 controller.
- The integration communicates locally only.
- If your HVAC setup requires a spill zone, keep at least one zone open.
- HA Brands assets for this integration are in `img/brands/custom_integrations/zonetouch3/`.
- Branding uses the official Zone Touch 3 app icon source (`img/branding/SOURCE.md`).

## Known Limitations

- This integration currently models zones as fan entities (damper percentage), not climate thermostat entities.

## Official Inclusion Path

See `OFFICIAL_HA_SUBMISSION.md` for the exact checklist to move this integration into official Home Assistant repositories.
