# Official Home Assistant Inclusion Guide (Zone Touch 3)

This integration currently runs as a custom integration. To get it accepted into Home Assistant Core, follow this process.

## 1) Meet minimum quality requirements

- New integrations are expected to target at least `bronze` on the Integration Quality Scale.
- The config flow quality rules include having tests, a config flow, and required quality rules implemented.
- Use the quality checklist while preparing PRs.

References:
- https://developers.home-assistant.io/docs/core/integration-quality-scale/
- https://developers.home-assistant.io/docs/core/integration-quality-scale/rules/config-flow
- https://developers.home-assistant.io/docs/core/integration-quality-scale/checklist

## 2) Complete Home Assistant development checklist

- Follow the official development checklist for integrations.
- If your integration uses a Python library, it must be on PyPI and pinned in requirements.

Reference:
- https://developers.home-assistant.io/docs/development_checklist

## 3) Provide documentation page content

- Home Assistant docs require an integration page with required sections and metadata (`ha_domain`, title, etc.).
- This is submitted to `home-assistant/home-assistant.io`.

Reference:
- https://developers.home-assistant.io/docs/creating_integration_docs

## 4) Add official branding assets

- Add brand files to `home-assistant/brands`.
- For custom integrations the path is:
  - `custom_integrations/zonetouch3/icon.png`
  - `custom_integrations/zonetouch3/icon@2x.png`
  - `custom_integrations/zonetouch3/logo.png`
  - `custom_integrations/zonetouch3/logo@2x.png`
- If this moves to Core later, files go under `core/zonetouch3/`.

References:
- https://github.com/home-assistant/brands
- https://developers.home-assistant.io/docs/core/integration-quality-scale/rules/brands

## 5) Submit the Core PR

- Open a PR to `home-assistant/core` with integration code, tests, and checklist items complete.
- Keep `manifest.json` aligned with Core rules (for example, `version` is not used for Core integrations).

References:
- https://developers.home-assistant.io/docs/creating_integration_manifest
- https://developers.home-assistant.io/docs/creating_integration_code_review

## Status of assets prepared in this repo

Prepared branding files for a Brands PR are included here:

- `img/brands/custom_integrations/zonetouch3/icon.png`
- `img/brands/custom_integrations/zonetouch3/icon@2x.png`
- `img/brands/custom_integrations/zonetouch3/logo.png`
- `img/brands/custom_integrations/zonetouch3/logo@2x.png`

Source SVG files:

- `img/branding/icon.svg`
- `img/branding/logo.svg`
