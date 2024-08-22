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

FAKE_GENERATE_MULTI_PARAMS = {
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

FAKE_GENERATE_EMBEDDINGS_MULTI = {
  "embedding_type": "Embedding Test",
  "text": "test prompt",
  "user_file_b64": "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAAAXNSR0IArs\
    4c6QAAAA1JREFUGFdjYGBg+A8AAQQBAHAgZQsAAAAASUVORK5CYII=",
  "user_file_name": "test.png"
}

FAKE_GENERATE_RESPONSE = "test generation"
FAKE_EMBEDDINGS = [0.01234]
FAKE_EMBEDDINGS_MULTI = {
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
  url = f"{api_url}"
  resp = client_with_emulator.get(url)
  json_response = resp.json()
  assert resp.status_code == 200, "Status 200"
  assert json_response.get("data") == get_model_config().get_llm_types()


def test_embedding_types(client_with_emulator):
  url = f"{api_url}/embedding_types"
  resp = client_with_emulator.get(url)
  json_response = resp.json()
  assert resp.status_code == 200, "Status 200"
  assert json_response.get("data") == get_model_config().get_embedding_types()

def test_embedding_types_multi(client_with_emulator):
  url = f"{api_url}/embedding_types"
  params = {"is_multi": True}
  resp = client_with_emulator.get(url, params = params)
  json_response = resp.json()
  assert resp.status_code == 200, "Status 200"
  assert json_response.get("data") == \
    get_model_config().get_multimodal_embedding_types()

def test_embedding_types_text(client_with_emulator):
  url = f"{api_url}/embedding_types"
  params = {"is_multi": False}
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


def test_generate_embeddings_multi(client_with_emulator):
  url = f"{api_url}/embedding/multi"

  with mock.patch("routes.llm.get_multimodal_embeddings",
                  return_value=FAKE_EMBEDDINGS_MULTI):
    resp = client_with_emulator.post(url, json=FAKE_GENERATE_EMBEDDINGS_MULTI)

  json_response = resp.json()
  assert resp.status_code == 200, "Status 200"
  assert json_response.get("data") == FAKE_EMBEDDINGS_MULTI, \
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

def test_llm_generate_multi(client_with_emulator):
  url = f"{api_url}/generate/multi"

  with mock.patch("routes.llm.llm_generate_multi",
                  return_value=FAKE_GENERATE_RESPONSE):
    resp = client_with_emulator.post(url, data=json.dumps(
      FAKE_GENERATE_MULTI_PARAMS))

  json_response = resp.json()
  assert resp.status_code == 200, "Status 200"
  assert json_response.get("content") == FAKE_GENERATE_RESPONSE, \
    "returned generated text"
