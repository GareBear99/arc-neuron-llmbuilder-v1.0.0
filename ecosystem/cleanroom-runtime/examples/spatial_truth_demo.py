from spatial_truth import SpatialTruthEngine
from geo_overlay import GeoOverlayGateway
spatial=SpatialTruthEngine(); state=spatial.state_template()['spatial_world']
state=spatial.upsert_anchor(state,{'anchor_id':'dock','label':'charging dock','latitude':52.128,'longitude':-122.142,'floor':'site','confidence':0.99})['spatial_world']
state=spatial.ingest_observation(state,{'source':'front_depth','kind':'object','label':'chair','confidence':0.91,'x_m':2.0,'y_m':1.0,'z_m':0.0})['spatial_world']
print(spatial.summarize(state))
geo=GeoOverlayGateway(); print(geo.register_anchor([],{'anchor_id':'home','label':'home','address':'123 Example St, Williams Lake BC','latitude':52.128,'longitude':-122.142}))
