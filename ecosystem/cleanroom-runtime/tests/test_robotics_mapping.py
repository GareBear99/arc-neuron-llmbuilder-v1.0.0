from robotics_mapping import MappingGateway

def test_mapping_ingest_and_route():
    gateway=MappingGateway(); state=gateway.state_template()['mapping_state']
    state=gateway.ingest_update(state,[{'x':1,'y':0,'value':0},{'x':1,'y':1,'value':0},{'x':0,'y':1,'value':0}],robot_position=[0,0])['mapping_state']
    route=gateway.plan_route(state,[1,1])
    assert route['status']=='ok'
    assert route['path'][0]==[0,0]
    assert route['path'][-1]==[1,1]
