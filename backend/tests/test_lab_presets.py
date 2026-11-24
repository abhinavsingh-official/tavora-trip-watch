"""
Presets let the Simulation page set a request to one of the three real
demo users' exact trip configs - a read-only template, never a pointer
into User A/B/C's actual rows - so a scenario can start from a known,
realistic trip without ever touching someone else's real data.
"""


def test_presets_list_the_three_demo_configs(client):
    response = client.get("/api/lab/presets")
    assert response.status_code == 200
    presets = response.json()
    assert [p["label"] for p in presets] == ["User A", "User B", "User C"]
    assert presets[0]["origin"] == "Mumbai"
    assert presets[0]["destination"] == "Goa"
    assert presets[1]["adults"] == 4
    assert presets[1]["rooms"] == 2
