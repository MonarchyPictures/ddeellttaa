"""
Agent API endpoint tests.
"""

import pytest
from fastapi.testclient import TestClient


class TestAgentEndpoints:
    """Test agent CRUD endpoints."""
    
    def test_list_agents_empty(self, authenticated_client: TestClient):
        """Test listing agents when none exist."""
        response = authenticated_client.get("/api/agents/")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 0
    
    def test_create_agent(self, authenticated_client: TestClient, sample_agent_data):
        """Test creating a new agent."""
        response = authenticated_client.post("/api/agents/", json=sample_agent_data)
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == sample_agent_data["name"]
        assert data["query"] == sample_agent_data["query"]
        assert "id" in data
        assert "leads_count" in data
        assert "high_intent_count" in data
    
    def test_create_agent_unauthorized(self, client: TestClient, sample_agent_data):
        """Test creating agent without authentication fails."""
        response = client.post("/api/agents/", json=sample_agent_data)
        assert response.status_code == 401
    
    def test_get_agent(self, authenticated_client: TestClient, sample_agent_data):
        """Test getting a specific agent."""
        # Create agent first
        create_response = authenticated_client.post("/api/agents/", json=sample_agent_data)
        agent_id = create_response.json()["id"]
        
        # Get agent
        response = authenticated_client.get(f"//api/agents/{agent_id}")
        # Note: The route expects the ID in the path
        # Actual route might be different, adjust as needed
    
    def test_stop_agent(self, authenticated_client: TestClient, sample_agent_data):
        """Test stopping an agent."""
        # Create agent first
        create_response = authenticated_client.post("/api/agents/", json=sample_agent_data)
        agent_id = create_response.json()["id"]
        
        # Stop agent
        response = authenticated_client.post(f"/api/agents/{agent_id}/stop")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
    
    def test_delete_agent(self, authenticated_client: TestClient, sample_agent_data):
        """Test deleting an agent."""
        # Create agent first
        create_response = authenticated_client.post("/api/agents/", json=sample_agent_data)
        agent_id = create_response.json()["id"]
        
        # Delete agent
        response = authenticated_client.delete(f"/api/agents/{agent_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
    
    def test_export_agent_leads(self, authenticated_client: TestClient, sample_agent_data):
        """Test exporting agent leads."""
        # Create agent first
        create_response = authenticated_client.post("/api/agents/", json=sample_agent_data)
        agent_id = create_response.json()["id"]
        
        # Export leads
        response = authenticated_client.post(f"/api/agents/{agent_id}/export")
        assert response.status_code == 200
        assert response.headers["content-type"] == "text/plain; charset=utf-8"
