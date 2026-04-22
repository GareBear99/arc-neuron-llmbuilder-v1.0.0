from bluetooth_bridge import BluetoothGateway


def _devices():
    return [
        {
            'device_id': 'garage.main',
            'display_name': 'Main Garage Relay',
            'profile': 'garage_relay_profile',
            'trusted': True,
            'pairing_state': 'paired',
            'ownership': 'owned',
            'signal_kind': 'ble',
            'last_seen_rssi': -55,
            'metadata': {'zone': 'garage'},
        }
    ]


def test_bluetooth_gateway_describe_and_template():
    gateway = BluetoothGateway()
    assert gateway.describe()['status'] == 'ok'
    assert 'garage_relay_profile' in gateway.describe()['profiles']
    assert gateway.device_template()['device_template']['device_id'] == 'device.example'


def test_bluetooth_policy_blocks_unapproved_unlock_like_actions():
    gateway = BluetoothGateway()
    verdict = gateway.policy_check(_devices(), action='open', device_id='garage.main')
    assert verdict['status'] == 'denied'
    assert verdict['reason'] == 'operator_approval_required'


def test_bluetooth_perform_allows_approved_profile_action():
    gateway = BluetoothGateway()
    result = gateway.perform(_devices(), action='open', device_id='garage.main', operator_approved=True)
    assert result['status'] == 'ok'
    assert result['receipt']['action'] == 'open'
    assert result['receipt']['translated_operation']['transport'] == 'mock_ble_client'


def test_bluetooth_local_signal_generation_requires_no_device():
    gateway = BluetoothGateway()
    result = gateway.perform([], action='advertise_start', params={'beacon': {'node_id': 'arc_1'}})
    assert result['status'] == 'ok'
    assert result['receipt']['action'] == 'advertise_start'
    assert result['receipt']['response']['emitting'] is True
