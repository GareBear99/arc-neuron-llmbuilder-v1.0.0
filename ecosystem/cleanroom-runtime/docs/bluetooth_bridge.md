# Bluetooth Bridge

The Bluetooth bridge is an **optional trusted-device signaling layer** for ARC Lucifer Cleanroom Runtime.

It is intentionally not a raw packet or arbitrary-control surface. The doctrine is:

- trusted device registry first
- bounded device profiles
- policy checks before execution
- local signal generation allowed only through explicit modes
- receipts for every action

## What it is for

Use it to connect the runtime to **authorized Bluetooth-capable devices** such as:
- garage relays you control
- beacons and tags
- nearby sensors
- wearable/operator signals
- approved vehicle telemetry accessories
- robot peripherals

## What it is not for

It is not designed as:
- a universal bypass tool
- arbitrary third-party device control
- an exploit surface for raw Bluetooth abuse

## Included command surface

- `lucifer bt describe`
- `lucifer bt device-template`
- `lucifer bt trusted-list`
- `lucifer bt register-device`
- `lucifer bt inspect-device`
- `lucifer bt signal-summary`
- `lucifer bt policy-check`
- `lucifer bt perform`

## Outbound signals

The bridge supports mocked doctrine-safe outbound signal modes now:
- `advertise_start`
- `advertise_stop`
- `peripheral_start`
- `peripheral_stop`

These represent the future platform adapters where Linux/BlueZ or Apple/CoreBluetooth helpers would provide the actual transport implementation.

## Profiles

Current bounded profiles include:
- `beacon_profile`
- `garage_relay_profile`
- `sensor_tag_profile`
- `vehicle_telemetry_profile`
- `door_lock_profile`

Each profile explicitly defines its allowed actions.

## Safety model

Bluetooth actions are only allowed when the request passes policy checks such as:
- device exists in the trusted registry
- device is marked trusted
- requested action is permitted by the profile
- operator approval is present for dangerous actions like `open`, `close`, `pulse`, or `unlock`

## Architecture fit

Bluetooth belongs below the executive shell:

1. ARC/Lucifer reasons about the intent
2. Bluetooth bridge checks trust + profile policy
3. bounded action is translated into a specific operation
4. receipt is written back into the runtime's source-of-truth flow

This keeps Bluetooth powerful without making it mandatory or unsafe.


## Spatial truth integration

Trusted Bluetooth device sightings can now be projected into the canonical spatial truth layer as `bluetooth_signal` observations. This keeps nearby devices, relays, vehicles, beacons, and accessory anchors visible to the same source-of-truth model used by mapping and robotics.

Recommended flow:

1. `lucifer bt signal-observation` to normalize one trusted device into a signal payload.
2. `lucifer spatial ingest-bt-signal` to merge that payload into the spatial world state.
3. Use the resulting labels, source counts, and confidence summaries inside higher-level planning/policy decisions.
