"""End-to-end smoke tests covering the core product workflow:
add dataset -> inspect -> recommend style -> layer -> process -> derived layer.
"""


def test_health(client):
    r = client.get("/api/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_demo_workspace_bootstraps(client):
    r = client.get("/api/maps")
    assert r.status_code == 200
    names = [m["name"] for m in r.json()]
    assert "Gold Exploration Demo" in names


def test_demo_datasets_have_recommended_styles(client):
    r = client.get("/api/layers")
    assert r.status_code == 200
    layers = r.json()
    render_types = {l["render_type"] for l in layers}
    # points, lines, polygons, and two rasters should each get a sensible default
    assert "raster" in render_types
    assert "line" in render_types
    assert {"proportional_circle", "cluster", "circle"} & render_types
    assert "choropleth" in render_types or "fill" in render_types


def test_vector_preview_is_bounded(client):
    r = client.get("/api/datasets")
    gold_id = next(d["id"] for d in r.json() if "gold" in d["tags"])
    r = client.get(f"/api/datasets/{gold_id}/preview")
    assert r.status_code == 200
    body = r.json()
    assert body["geojson"]["type"] == "FeatureCollection"
    assert len(body["geojson"]["features"]) > 0


def test_hillshade_creates_derived_layer(client):
    r = client.get("/api/datasets")
    dem_id = next(d["id"] for d in r.json() if "dem" in d["tags"])
    before = len(client.get("/api/layers").json())

    r = client.post("/api/process/hillshade", json={"dataset_id": dem_id})
    assert r.status_code == 200
    derived_id = r.json()["dataset_id"]

    after = client.get("/api/layers").json()
    assert len(after) == before + 1
    assert any(l["dataset_id"] == derived_id for l in after)


def test_unknown_dataset_returns_friendly_404(client):
    r = client.get("/api/datasets/does-not-exist")
    assert r.status_code == 404
    assert "couldn't find" in r.json()["error"]


def test_intent_router_matches_domains(client):
    r = client.post("/api/intent", json={"text": "I want to see gold occurrences"})
    assert r.status_code == 200
    body = r.json()
    assert "gold" in body["domains"]
    assert any("Gold" in d["name"] for d in body["matched_datasets"])


def test_csv_without_coordinates_gives_friendly_error(client, tmp_path):
    bad_csv = b"name,value\nA,1\nB,2\n"
    r = client.post(
        "/api/datasets",
        files={"file": ("bad.csv", bad_csv, "text/csv")},
    )
    assert r.status_code == 400
    assert "coordinates" in r.json()["error"]


def test_unsupported_format_gives_friendly_error(client):
    r = client.post(
        "/api/datasets",
        files={"file": ("data.nc", b"not really netcdf", "application/octet-stream")},
    )
    assert r.status_code == 400
    assert "hint" in r.json()
