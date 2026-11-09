def employee(client, name="Demo User"):
    response = client.post("/api/employees", json={"name": name, "email": None})
    assert response.status_code == 201
    return response.json()

def test_create_employee_and_list(client):
    created = employee(client)
    response = client.get("/api/employees")
    assert response.status_code == 200
    assert response.json()[0]["id"] == created["id"]

def test_start_and_stop_timer(client):
    person = employee(client)
    started = client.post(f"/api/employees/{person['id']}/timer/start", json={"task":"Prepare report"})
    assert started.status_code == 201
    assert started.json()["is_running"] is True
    stopped = client.post(f"/api/sessions/{started.json()['id']}/stop")
    assert stopped.status_code == 200
    assert stopped.json()["is_running"] is False
    assert stopped.json()["duration_seconds"] >= 0

def test_repeated_start_is_rejected(client):
    person = employee(client)
    first = client.post(f"/api/employees/{person['id']}/timer/start", json={"task":"First task"})
    second = client.post(f"/api/employees/{person['id']}/timer/start", json={"task":"Second task"})
    assert first.status_code == 201
    assert second.status_code == 409
    assert "active timer" in second.json()["detail"].lower()

def test_stopping_timer_twice_is_rejected(client):
    person = employee(client)
    started = client.post(f"/api/employees/{person['id']}/timer/start", json={"task":"Task"})
    session_id = started.json()["id"]
    assert client.post(f"/api/sessions/{session_id}/stop").status_code == 200
    assert client.post(f"/api/sessions/{session_id}/stop").status_code == 409

def test_empty_report_returns_zero_totals(client):
    person = employee(client)
    response = client.get("/api/reports", params={"date_from":"2026-01-01T00:00:00Z","date_to":"2026-01-31T23:59:59Z"})
    assert response.status_code == 200
    row = next(x for x in response.json() if x["employee_id"] == person["id"])
    assert row["total_seconds"] == 0
    assert row["sessions_count"] == 0

def test_invalid_report_range_is_rejected(client):
    response = client.get("/api/reports", params={"date_from":"2026-02-01T00:00:00Z","date_to":"2026-01-01T00:00:00Z"})
    assert response.status_code == 422

def test_missing_employee_timer_returns_404(client):
    response = client.post("/api/employees/999/timer/start", json={"task":"Task"})
    assert response.status_code == 404
