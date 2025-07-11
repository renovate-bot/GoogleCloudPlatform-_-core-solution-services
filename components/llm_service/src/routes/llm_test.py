# Copyright 2023 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
  Unit tests for LLM Service endpoints
"""
# disabling pylint rules that conflict with pytest fixtures
# pylint: disable=unused-argument,redefined-outer-name,unused-import,unused-variable,ungrouped-imports
import os
import pytest
import base64
import json
from fastapi import FastAPI
from fastapi.testclient import TestClient
from unittest import mock
from testing.test_config import API_URL, TESTING_FOLDER_PATH
from common.utils.http_exceptions import add_exception_handlers
from common.utils.auth_service import validate_user
from common.utils.auth_service import validate_token
from common.testing.firestore_emulator import firestore_emulator, clean_firestore

os.environ["FIRESTORE_EMULATOR_HOST"] = "localhost:8080"
os.environ["PROJECT_ID"] = "fake-project"
os.environ["OPENAI_API_KEY"] = "fake-key"
os.environ["COHERE_API_KEY"] = "fake-key"

with mock.patch("common.utils.secrets.get_secret"):
  with mock.patch("langchain.chat_models.ChatOpenAI", new=mock.AsyncMock()):
    with mock.patch("langchain.llms.Cohere", new=mock.AsyncMock()):
      from config import get_model_config

# assigning url
api_url = f"{API_URL}/llm"
LLM_TESTDATA_FILENAME = os.path.join(TESTING_FOLDER_PATH,
                                        "llm_generate.json")

with mock.patch("common.utils.secrets.get_secret"):
  from routes.llm import router

app = FastAPI()
add_exception_handlers(app)
app.include_router(router, prefix="/llm-service/api/v1")

FAKE_USER_DATA = {
  "id": "fake-user-id",
  "user_id": "fake-user-id",
  "auth_id": "fake-user-id",
  "email": "user@gmail.com",
  "role": "Admin"
}

FAKE_GENERATE_PARAMS = {
  "llm_type": "LLM Test",
  "prompt": "test prompt"
}

FAKE_GENERATE_MULTIMODAL_PARAMS = {
  "llm_type": "LLM Test",
  "prompt": "test prompt",
  "user_file_b64": "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAAAXNSR0IArs\
    4c6QAAAA1JREFUGFdjYGBg+A8AAQQBAHAgZQsAAAAASUVORK5CYII=",
  "user_file_name": "test.png"
}

FAKE_GENERATE_EMBEDDINGS = {
  "embedding_type": "Embedding Test",
  "text": "test prompt"
}

FAKE_GENERATE_EMBEDDINGS_MULTIMODAL = {
  "embedding_type": "Embedding Test",
  "text": "test prompt",
  "user_file_b64": "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAAAXNSR0IArs\
    4c6QAAAA1JREFUGFdjYGBg+A8AAQQBAHAgZQsAAAAASUVORK5CYII=",
  "user_file_name": "test.png"
}

FAKE_GENERATE_RESPONSE = "test generation"
FAKE_EMBEDDINGS = [0.01234]
FAKE_EMBEDDINGS_MULTIMODAL = {
  "image_embeddings": FAKE_EMBEDDINGS,
  "text_embeddings": FAKE_EMBEDDINGS
}

@pytest.fixture
def client_with_emulator(clean_firestore, scope="module"):
  """ Create FastAPI test client with clean firestore emulator """
  def mock_validate_user():
    return True

  def mock_validate_token():
    return FAKE_USER_DATA

  app.dependency_overrides[validate_user] = mock_validate_user
  app.dependency_overrides[validate_token] = mock_validate_token
  test_client = TestClient(app)
  yield test_client


def test_get_llm_list(client_with_emulator):
  removed_model = "VertexAI-Gemini-Pro"
  def mock_is_model_enabled_for_user(model_id, user_data):
    if model_id == removed_model:
      return False
    return True

  url = f"{api_url}"
  with mock.patch("config.model_config.ModelConfig.is_model_enabled_for_user",
                  side_effect=mock_is_model_enabled_for_user):
    resp = client_with_emulator.get(url)
  json_response = resp.json()
  all_llm_list = get_model_config().get_llm_types()
  assert resp.status_code == 200, "Status 200"
  if removed_model in all_llm_list:
    assert len(json_response.get("data")) == len(all_llm_list) - 1
  assert json_response.get("data") == [m for m in all_llm_list \
                                       if m != removed_model]
  assert removed_model not in json_response.get("data")


def test_embedding_types(client_with_emulator):
  url = f"{api_url}/embedding_types"
  resp = client_with_emulator.get(url)
  json_response = resp.json()
  assert resp.status_code == 200, "Status 200"
  assert json_response.get("data") == get_model_config().get_embedding_types()

def test_embedding_types_multimodal(client_with_emulator):
  url = f"{api_url}/embedding_types"
  params = {"is_multimodal": True}
  resp = client_with_emulator.get(url, params = params)
  json_response = resp.json()
  assert resp.status_code == 200, "Status 200"
  assert json_response.get("data") == \
    get_model_config().get_multimodal_embedding_types()

def test_embedding_types_text(client_with_emulator):
  url = f"{api_url}/embedding_types"
  params = {"is_multimodal": False}
  resp = client_with_emulator.get(url, params = params)
  json_response = resp.json()
  assert resp.status_code == 200, "Status 200"
  assert json_response.get("data") == \
    get_model_config().get_text_embedding_types()

def test_generate_embeddings(client_with_emulator):
  url = f"{api_url}/embedding"

  with mock.patch("routes.llm.get_embeddings",
                  return_value=([True], FAKE_EMBEDDINGS)):
    resp = client_with_emulator.post(url, json=FAKE_GENERATE_EMBEDDINGS)

  json_response = resp.json()
  assert resp.status_code == 200, "Status 200"
  assert json_response.get("data") == FAKE_EMBEDDINGS, \
    "returned generated embeddings"


def test_generate_embeddings_multimodal(client_with_emulator):
  url = f"{api_url}/embedding/multimodal"

  with mock.patch("routes.llm.get_multimodal_embeddings",
                  return_value=FAKE_EMBEDDINGS_MULTIMODAL):
    resp = client_with_emulator.post(url,
                                     json=FAKE_GENERATE_EMBEDDINGS_MULTIMODAL)

  json_response = resp.json()
  assert resp.status_code == 200, "Status 200"
  assert json_response.get("data") == FAKE_EMBEDDINGS_MULTIMODAL, \
    "returned generated embeddings"


def test_llm_generate(client_with_emulator):
  url = f"{api_url}/generate"

  with mock.patch("routes.llm.llm_generate",
                  return_value=FAKE_GENERATE_RESPONSE):
    resp = client_with_emulator.post(url, json=FAKE_GENERATE_PARAMS)

  json_response = resp.json()
  assert resp.status_code == 200, "Status 200"
  assert json_response.get("content") == FAKE_GENERATE_RESPONSE, \
    "returned generated text"

def test_llm_generate_multimodal(client_with_emulator):
  url = f"{api_url}/generate/multimodal"

  with mock.patch("routes.llm.llm_generate_multimodal",
                  return_value=FAKE_GENERATE_RESPONSE):
    resp = client_with_emulator.post(url, data=json.dumps(
      FAKE_GENERATE_MULTIMODAL_PARAMS))

  json_response = resp.json()
  assert resp.status_code == 200, "Status 200"
  assert json_response.get("content") == FAKE_GENERATE_RESPONSE, \
    "returned generated text"

def test_get_llm_details(client_with_emulator):
  """Test getting detailed LLM information"""
  url = f"{api_url}/details"

  # Mock the model config to return test data
  test_model_config = {
    "name": "Test Model",
    "description": "A test model",
    "capabilities": ["text", "chat"],
    "date_added": "2024-01-01",
    "is_multi": False,
    "model_params": {
      "temperature": 0.7,
      "max_tokens": 1000
    }
  }

  test_provider_config = {
    "model_params": {
      "temperature": 0.5,  # This should be overridden by model config
      "top_p": 0.9  # This should be preserved
    }
  }

  def mock_get_model_config(model_id):
    return test_model_config

  def mock_get_model_provider_config(model_id):
    return "test_provider", test_provider_config

  def mock_is_model_enabled_for_user(model_id, user_data):
    return True

  with mock.patch("config.model_config.ModelConfig.get_model_config",
                 side_effect=mock_get_model_config), \
       mock.patch("config.model_config.ModelConfig.get_model_provider_config",
                 side_effect=mock_get_model_provider_config), \
       mock.patch("config.model_config.ModelConfig.is_model_enabled_for_user",
                 side_effect=mock_is_model_enabled_for_user):

    # Test getting all models
    resp = client_with_emulator.get(url)
    assert resp.status_code == 200, "Status 200"
    json_response = resp.json()
    assert json_response["success"] is True
    assert len(json_response["data"]) > 0

    # Verify model details structure
    model = json_response["data"][0]
    assert "id" in model
    assert model["name"] == test_model_config["name"]
    assert model["description"] == test_model_config["description"]
    assert model["capabilities"] == test_model_config["capabilities"]
    assert model["date_added"] == test_model_config["date_added"]
    assert model["is_multi"] == test_model_config["is_multi"]

    # Verify merged model parameters
    assert "model_params" in model
    assert model["model_params"]["temperature"] == 0.7  # From model config
    assert model["model_params"]["top_p"] == 0.9  # From provider config
    assert model["model_params"]["max_tokens"] == 1000  # From model config

def test_get_llm_details_multimodal_filter(client_with_emulator):
  """Test filtering LLM details by multimodal capability"""
  url = f"{api_url}/details"

  def mock_is_model_enabled_for_user(model_id, user_data):
    return True

  with mock.patch("config.model_config.ModelConfig.is_model_enabled_for_user",
                 side_effect=mock_is_model_enabled_for_user):
    # Test multimodal filter True
    resp = client_with_emulator.get(url, params={"is_multimodal": True})
    assert resp.status_code == 200
    json_response = resp.json()
    assert json_response["success"] is True
    # Verify all returned models have is_multi=True
    assert all(model["is_multi"] for model in json_response["data"])

    # Test multimodal filter False
    resp = client_with_emulator.get(url, params={"is_multimodal": False})
    assert resp.status_code == 200
    json_response = resp.json()
    assert json_response["success"] is True
    # Verify all returned models have is_multi=False
    assert all(not model["is_multi"] for model in json_response["data"])

def test_get_llm_details_error_handling(client_with_emulator):
  """Test error handling in get_llm_details"""
  url = f"{api_url}/details"

  def mock_get_llm_types_error():
    raise RuntimeError("Test error")

  with mock.patch("config.model_config.ModelConfig.get_llm_types",
                 side_effect=mock_get_llm_types_error):
    resp = client_with_emulator.get(url)
    assert resp.status_code == 500
    json_response = resp.json()
    assert not json_response["success"]
    assert "Test error" in json_response["message"]
