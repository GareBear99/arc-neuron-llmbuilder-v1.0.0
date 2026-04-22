from __future__ import annotations
from typing import Any
from .schemas import SpatialAnchor, SpatialObservation, SpatialWorldState

class SpatialTruthEngine:
    def describe(self)->dict[str,Any]:
        return {
            'status':'ok',
            'required':False,
            'layers':['geo_world','site_world','structure_world','interior_world','dynamic_world','confidence_world'],
            'doctrine':'semantic spatial source of truth below the executive shell',
            'bridges':['robotics_mapping','geo_overlay','bluetooth_bridge'],
        }

    def state_template(self)->dict[str,Any]:
        return {'status':'ok','spatial_world':SpatialWorldState().to_dict()}

    def upsert_anchor(self,state:dict[str,Any],anchor:dict[str,Any])->dict[str,Any]:
        model=SpatialWorldState(**state)
        incoming=SpatialAnchor(**anchor).to_dict()
        model.anchors=[a for a in model.anchors if a['anchor_id']!=incoming['anchor_id']] + [incoming]
        return {'status':'ok','spatial_world':self._summarize(model)}

    def ingest_observation(self,state:dict[str,Any],observation:dict[str,Any])->dict[str,Any]:
        model=SpatialWorldState(**state)
        model.observations.append(SpatialObservation(**observation).to_dict())
        return {'status':'ok','spatial_world':self._summarize(model)}

    def ingest_bluetooth_signal(self,state:dict[str,Any],signal:dict[str,Any])->dict[str,Any]:
        metadata = dict(signal.get('metadata', {}))
        metadata.update({
            'device_id': signal.get('device_id'),
            'profile': signal.get('profile'),
            'trusted': bool(signal.get('trusted', False)),
            'pairing_state': signal.get('pairing_state'),
            'ownership': signal.get('ownership'),
            'signal_kind': signal.get('signal_kind', 'ble'),
            'rssi': signal.get('last_seen_rssi'),
            'zone': metadata.get('zone') or signal.get('zone'),
        })
        raw_confidence = signal.get('confidence')
        confidence = float(raw_confidence if raw_confidence is not None else (0.9 if signal.get('trusted') else 0.5))
        if signal.get('last_seen_rssi') is not None:
            rssi = max(-100, min(-20, int(signal['last_seen_rssi'])))
            confidence = max(confidence, round((100 + rssi) / 100, 4))
        observation = {
            'source': 'bluetooth_bridge',
            'kind': 'bluetooth_signal',
            'label': signal.get('display_name') or signal.get('device_id') or 'bluetooth_device',
            'confidence': min(1.0, max(0.0, confidence)),
            'x_m': float(signal.get('x_m', 0.0)),
            'y_m': float(signal.get('y_m', 0.0)),
            'z_m': float(signal.get('z_m', 0.0)),
            'metadata': metadata,
        }
        return self.ingest_observation(state, observation)

    def summarize(self,state:dict[str,Any])->dict[str,Any]:
        return {'status':'ok','spatial_world':self._summarize(SpatialWorldState(**state))}

    def _summarize(self,model:SpatialWorldState)->dict[str,Any]:
        count=len(model.observations)
        avg=round(sum(o['confidence'] for o in model.observations)/count,4) if count else 1.0
        labels=sorted({o['label'] for o in model.observations})
        source_counts:dict[str,int]={}
        kind_counts:dict[str,int]={}
        for obs in model.observations:
            source_counts[obs['source']]=source_counts.get(obs['source'],0)+1
            kind_counts[obs['kind']]=kind_counts.get(obs['kind'],0)+1
        model.confidence_world={
            'average_confidence':avg,
            'observation_count':count,
            'anchor_count':len(model.anchors),
            'labels':labels,
            'source_counts':source_counts,
            'kind_counts':kind_counts,
        }
        return model.to_dict()
