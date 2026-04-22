# Spatial Truth Layer

This package extracts the strongest ideas from the spatial intelligence reference package without inheriting its browser-first authority model.

It introduces a canonical `spatial_truth/` layer for anchors, structured observations, semantic confidence summaries, and geo/site/interior transform helpers.


## Bluetooth awareness anchors

The spatial truth layer can ingest trusted Bluetooth signal observations. These are stored as `bluetooth_signal` observations with device metadata such as device ID, profile, trust state, signal kind, RSSI, and semantic zone. This lets the source-of-truth model treat nearby authorized devices as first-class awareness anchors.
