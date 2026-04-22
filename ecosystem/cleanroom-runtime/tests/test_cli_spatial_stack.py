from lucifer_runtime.cli import main

def test_cli_robot_mapping_and_spatial_commands(tmp_path, capsys):
    assert main(['--workspace',str(tmp_path),'robot','describe'])==0
    assert 'mock_dog_body' in capsys.readouterr().out
    assert main(['--workspace',str(tmp_path),'mapping','state-template'])==0
    assert 'mapping_state' in capsys.readouterr().out
    assert main(['--workspace',str(tmp_path),'spatial','state-template'])==0
    assert 'spatial_world' in capsys.readouterr().out
    assert main(['--workspace',str(tmp_path),'geo','anchor-template'])==0
    assert 'anchor_template' in capsys.readouterr().out


def test_cli_spatial_ingest_bt_signal(tmp_path, capsys):
    signal = '{"device_id":"garage.main","display_name":"Main Garage Relay","profile":"garage_relay_profile","trusted":true,"pairing_state":"paired","ownership":"owned","signal_kind":"ble","last_seen_rssi":-50,"metadata":{"zone":"garage"}}'
    assert main(['--workspace', str(tmp_path), 'spatial', 'ingest-bt-signal', '--state-json', '{"anchors":[],"observations":[],"confidence_world":{}}', '--signal-json', signal]) == 0
    out = capsys.readouterr().out
    assert 'bluetooth_signal' in out
    assert 'source_counts' in out
