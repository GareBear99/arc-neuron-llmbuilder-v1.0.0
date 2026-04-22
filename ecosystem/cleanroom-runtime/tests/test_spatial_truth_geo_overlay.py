from geo_overlay import GeoOverlayGateway
from spatial_truth import SpatialTruthEngine

def test_spatial_truth_and_geo_overlay_flow():
    engine=SpatialTruthEngine(); state=engine.state_template()['spatial_world']
    state=engine.upsert_anchor(state,{'anchor_id':'dock','label':'dock','latitude':52.1,'longitude':-122.1,'floor':'site','confidence':0.99})['spatial_world']
    state=engine.ingest_observation(state,{'source':'depth','kind':'object','label':'chair','confidence':0.8,'x_m':1.0,'y_m':2.0,'z_m':0.0})['spatial_world']
    summary=engine.summarize(state)
    assert summary['spatial_world']['confidence_world']['anchor_count']==1
    assert summary['spatial_world']['confidence_world']['observation_count']==1
    geo=GeoOverlayGateway(); reg=geo.register_anchor([],{'anchor_id':'home','label':'home','address':'123 Example St, Williams Lake BC','latitude':52.1,'longitude':-122.1})
    assert reg['anchors'][0]['address_canonical']=='123 example st williams lake bc'
    near=geo.nearest_anchor(reg['anchors'],52.1001,-122.1001)
    assert near['status']=='ok'
