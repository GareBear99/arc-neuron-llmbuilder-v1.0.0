from bluetooth_bridge import BluetoothGateway
from spatial_truth import SpatialTruthEngine


def test_bluetooth_signal_projects_into_spatial_truth():
    devices = [{
        'device_id': 'garage.main',
        'display_name': 'Main Garage Relay',
        'profile': 'garage_relay_profile',
        'trusted': True,
        'pairing_state': 'paired',
        'ownership': 'owned',
        'signal_kind': 'ble',
        'last_seen_rssi': -48,
        'metadata': {'zone': 'garage'},
        'x_m': 2.5,
        'y_m': 1.0,
    }]
    bt = BluetoothGateway()
    signal = bt.signal_observation(devices, 'garage.main')['signal_observation']
    engine = SpatialTruthEngine()
    state = engine.state_template()['spatial_world']
    out = engine.ingest_bluetooth_signal(state, signal)
    obs = out['spatial_world']['observations'][0]
    assert obs['kind'] == 'bluetooth_signal'
    assert obs['metadata']['device_id'] == 'garage.main'
    assert out['spatial_world']['confidence_world']['source_counts']['bluetooth_bridge'] == 1
