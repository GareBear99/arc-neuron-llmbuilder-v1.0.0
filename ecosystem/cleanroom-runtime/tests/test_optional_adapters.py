from perception_adapters import AdapterRegistry, Observation, OptionalAdapterConfig, SensorPacket
from perception_adapters.interfaces import ObservationBatch


class DummyVision:
    def describe(self):
        return {"kind": "vision", "required": False}

    def process(self, packet: SensorPacket) -> ObservationBatch:
        return ObservationBatch(
            source=packet.source,
            timestamp=packet.timestamp,
            observations=(Observation(kind="object", confidence=0.9, attributes={"label": "mug"}),),
            raw_summary="detected mug",
        )


class DummyArm:
    def describe(self):
        return {"kind": "robotics", "required": False}

    def perform(self, action: str, params=None):
        return {"status": "ok", "action": action, "params": params or {}}


def test_optional_adapter_registry_describes_non_required_surfaces():
    registry = AdapterRegistry()
    registry.register_perception("front_camera", DummyVision())
    registry.register_action(
        "desk_arm",
        DummyArm(),
        OptionalAdapterConfig(enabled=False, mode="robotics", options={"hot_plug": True}),
    )

    description = registry.describe()
    assert description["perception"]["front_camera"]["required"] is False
    assert description["action"]["desk_arm"]["required"] is False
    assert description["configs"]["desk_arm"]["enabled"] is False
    assert description["configs"]["desk_arm"]["options"]["hot_plug"] is True


def test_observation_batch_converts_to_world_facts():
    packet = SensorPacket(source="front_camera", modality="vision", timestamp="2026-04-03T00:00:00Z")
    batch = DummyVision().process(packet)
    facts = batch.to_world_facts()
    assert facts["source"] == "front_camera"
    assert facts["observation_count"] == 1
    assert facts["observations"][0]["attributes"]["label"] == "mug"
