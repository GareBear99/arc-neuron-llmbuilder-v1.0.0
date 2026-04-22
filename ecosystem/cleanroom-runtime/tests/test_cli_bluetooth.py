from lucifer_runtime.cli import main


def test_cli_bluetooth_commands(tmp_path, capsys):
    devices = '[{"device_id":"garage.main","display_name":"Main Garage Relay","profile":"garage_relay_profile","trusted":true,"pairing_state":"paired","ownership":"owned","signal_kind":"ble","last_seen_rssi":-50,"metadata":{}}]'
    assert main(['--workspace', str(tmp_path), 'bt', 'describe']) == 0
    assert 'trusted-device bluetooth bridge' in capsys.readouterr().out
    assert main(['--workspace', str(tmp_path), 'bt', 'device-template']) == 0
    assert 'device_template' in capsys.readouterr().out
    assert main(['--workspace', str(tmp_path), 'bt', 'signal-summary', '--devices-json', devices]) == 0
    assert 'visible_count' in capsys.readouterr().out
    assert main(['--workspace', str(tmp_path), 'bt', 'perform', '--devices-json', '[]', '--action', 'advertise_start', '--params-json', '{"beacon":{"node_id":"arc_1"}}']) == 0
    assert 'mock_advertising_started' in capsys.readouterr().out


def test_cli_bluetooth_signal_observation(tmp_path, capsys):
    devices = '[{"device_id":"garage.main","display_name":"Main Garage Relay","profile":"garage_relay_profile","trusted":true,"pairing_state":"paired","ownership":"owned","signal_kind":"ble","last_seen_rssi":-50,"metadata":{"zone":"garage"}}]'
    assert main(['--workspace', str(tmp_path), 'bt', 'signal-observation', '--devices-json', devices, '--device-id', 'garage.main']) == 0
    assert 'signal_observation' in capsys.readouterr().out
