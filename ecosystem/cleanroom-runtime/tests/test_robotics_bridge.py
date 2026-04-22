from robotics_bridge import RoboticsGateway

def test_robotics_bridge_denies_blocked_motion():
    gateway=RoboticsGateway(); state=gateway.state_template()['state_template']; state['nearest_obstacle_m']=0.2
    result=gateway.safety_check(state,action='walk_to_relative',subsystem='dog_body',params={'x':1,'y':0})
    assert result['status']=='denied'
    assert 'near obstacle' in ' '.join(result['reasons'])

def test_robotics_bridge_allows_safe_arm_action():
    gateway=RoboticsGateway(); state=gateway.state_template()['state_template']
    result=gateway.perform(state,action='arm_ready',subsystem='tentacle_arm',params={'pose':'inspect'})
    assert result['status']=='ok'
    assert result['receipt']['translated_command']['driver']=='mock_tentacle_arm'
