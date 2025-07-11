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

""" Config used for testing in unit tests """
# pylint: disable=line-too-long,unused-argument
import os
from typing import List, Optional, Any
from common.models.agent import AgentCapability
from langchain.schema import (Generation, ChatGeneration, LLMResult)
from langchain.schema.messages import AIMessage
from langchain_core.language_models.llms import BaseLLM
from langchain_core.callbacks import CallbackManagerForLLMRun

from config import (COHERE_LLM_TYPE,
                    OPENAI_LLM_TYPE_GPT3_5, OPENAI_LLM_TYPE_GPT4,
                    OPENAI_LLM_TYPE_GPT4_LATEST,
                    VERTEX_LLM_TYPE_GEMINI_PRO_LANGCHAIN,
                    VERTEX_LLM_TYPE_BISON_TEXT,
                    VERTEX_LLM_TYPE_CHAT,
                    VERTEX_LLM_TYPE_GEMINI_PRO,
                    VERTEX_LLM_TYPE_GEMINI_PRO_VISION,
                    VERTEX_LLM_TYPE_GEMINI_FLASH,
                    PROVIDER_LANGCHAIN, PROVIDER_VERTEX,
                    PROVIDER_TRUSS, PROVIDER_VLLM,
                    PROVIDER_MODEL_GARDEN,
                    VERTEX_AI_MODEL_GARDEN_LLAMA2_CHAT,
                    TRUSS_LLM_LLAMA2_CHAT, VLLM_LLM_GEMMA_CHAT,
                    KEY_PROVIDER, KEY_IS_CHAT, KEY_IS_MULTI, KEY_ENABLED,
                    KEY_MODEL_CLASS, KEY_MODEL_PARAMS, KEY_MODEL_NAME,
                    KEY_MODEL_ENDPOINT)

API_URL = "http://localhost/llm-service/api/v1"

TESTING_FOLDER_PATH = os.path.join(os.getcwd(), "testing")

FAKE_PREDICTION_RESPONSE = "test prediction"

FAKE_GENERATE_RESPONSE = "test generation"

FAKE_LANGCHAIN_GENERATION = Generation(text=FAKE_GENERATE_RESPONSE)

FAKE_CHAT_RESPONSE = ChatGeneration(message=AIMessage(
                                    content=FAKE_GENERATE_RESPONSE))

FAKE_GENERATE_RESULT = LLMResult(generations=[[FAKE_LANGCHAIN_GENERATION]])

FAKE_CHAT_RESULT = LLMResult(generations=[[FAKE_CHAT_RESPONSE]])

class FakeModelClass(BaseLLM):
  """ Fake model class for langchain tests """
  async def agenerate(self, prompts):
    return FAKE_CHAT_RESULT

  def _generate(
      self,
      prompts: List[str],
      stop: Optional[List[str]] = None,
      run_manager: Optional[CallbackManagerForLLMRun] = None,
      stream: Optional[bool] = None,
      **kwargs: Any,
  ) -> LLMResult:
    return FAKE_CHAT_RESULT

  def _call(
      self,
      prompt: str,
      stop: Optional[List[str]] = None,
      run_manager: Optional[CallbackManagerForLLMRun] = None,
      **kwargs: Any,
  ) -> str:
    """Run the LLM on the given prompt and input."""
    return FAKE_CHAT_RESULT

  @property
  def _llm_type(self) -> str:
    return "vertexai"

CHAT_AGENT = "Chat"
FAKE_AGENT_LOGS = "fake logs"
FAKE_AGENT_OUTPUT = "fake agent output"

class FakeAgentExecutor():
  async def arun(self, prompt):
    return FAKE_AGENT_OUTPUT

class FakeLangchainAgent():
  pass

class FakeAgent():
  """ Fake agent class """
  def __init__(self):
    self.name = CHAT_AGENT
  def get_tools(self):
    return []
  def load_langchain_agent(self):
    return FakeLangchainAgent()
  def capabilities(self):
    return [AgentCapability.CHAT]


TEST_COHERE_CONFIG = {
  COHERE_LLM_TYPE: {
    KEY_PROVIDER: PROVIDER_LANGCHAIN,
    KEY_IS_CHAT: True,
    KEY_ENABLED: True,
    KEY_MODEL_CLASS: FakeModelClass()
  }
}

TEST_OPENAI_CONFIG = {
  OPENAI_LLM_TYPE_GPT3_5: {
    KEY_PROVIDER: PROVIDER_LANGCHAIN,
    KEY_IS_CHAT: True,
    KEY_ENABLED: True,
    KEY_MODEL_CLASS: FakeModelClass()
  },
  OPENAI_LLM_TYPE_GPT4: {
    KEY_PROVIDER: PROVIDER_LANGCHAIN,
    KEY_IS_CHAT: True,
    KEY_ENABLED: True,
    KEY_MODEL_CLASS: FakeModelClass()
  },
  OPENAI_LLM_TYPE_GPT4_LATEST: {
    KEY_PROVIDER: PROVIDER_LANGCHAIN,
    KEY_IS_CHAT: True,
    KEY_ENABLED: True,
    KEY_MODEL_CLASS: FakeModelClass()
  },
  VERTEX_LLM_TYPE_GEMINI_PRO_LANGCHAIN: {
    KEY_PROVIDER: PROVIDER_LANGCHAIN,
    KEY_IS_CHAT: True,
    KEY_ENABLED: True,
    KEY_MODEL_CLASS: FakeModelClass()
  }
}

TEST_VERTEX_CONFIG = {
  KEY_MODEL_PARAMS: {
    "temperature": 0.2,
    "max_output_tokens": 900,
    "top_p": 1.0,
    "top_k": 10
  },
  VERTEX_LLM_TYPE_CHAT: {
    KEY_PROVIDER: PROVIDER_VERTEX,
    KEY_IS_CHAT: True,
    KEY_ENABLED: True,
    KEY_MODEL_NAME: "gemini-1.5-flash"
  },
  VERTEX_LLM_TYPE_BISON_TEXT: {
    KEY_PROVIDER: PROVIDER_VERTEX,
    KEY_IS_CHAT: False,
    KEY_ENABLED: True,
    KEY_MODEL_NAME: "text-bison@002"
  },
  VERTEX_LLM_TYPE_GEMINI_PRO: {
    KEY_PROVIDER: PROVIDER_VERTEX,
    KEY_IS_CHAT: True,
    KEY_IS_MULTI: True,
    KEY_ENABLED: True,
    KEY_MODEL_NAME: "gemini-pro"
  },
  VERTEX_LLM_TYPE_GEMINI_PRO_VISION: {
    KEY_PROVIDER: PROVIDER_VERTEX,
    KEY_IS_CHAT: True,
    KEY_IS_MULTI: True,
    KEY_ENABLED: True,
    KEY_MODEL_NAME: "gemini-pro-vision"
  },
  VERTEX_LLM_TYPE_GEMINI_FLASH: {
    KEY_PROVIDER: PROVIDER_VERTEX,
    KEY_IS_CHAT: True,
    KEY_IS_MULTI: True,
    KEY_ENABLED: True,
    KEY_MODEL_NAME: "gemini-1.5-flash"
  }
}

TEST_MODEL_GARDEN_CONFIG = {
  VERTEX_AI_MODEL_GARDEN_LLAMA2_CHAT: {
    KEY_PROVIDER: PROVIDER_MODEL_GARDEN,
    KEY_MODEL_ENDPOINT: "fake-endpoint",
    KEY_IS_CHAT: True,
    KEY_MODEL_PARAMS: {
      "temperature": 0.2,
      "max_tokens": 900,
      "top_p": 1.0,
      "top_k": 10
    },
    KEY_ENABLED: True
  }
}

TEST_TRUSS_CONFIG = {
  TRUSS_LLM_LLAMA2_CHAT: {
    KEY_PROVIDER: PROVIDER_TRUSS,
    KEY_MODEL_ENDPOINT: "fake-endpoint",
    KEY_IS_CHAT: True,
    KEY_MODEL_PARAMS: {
      "temperature": 0.2,
      "max_tokens": 900,
      "top_p": 1.0,
      "top_k": 10
    },
    KEY_ENABLED: True
  }
}

TEST_VLLM_CONFIG = {
  VLLM_LLM_GEMMA_CHAT: {
    KEY_PROVIDER: PROVIDER_VLLM,
    KEY_MODEL_ENDPOINT: "fake-endpoint",
    KEY_IS_CHAT: True,
    KEY_MODEL_PARAMS: {
      "temperature": 0.2,
      "max_tokens": 900,
      "top_p": 1.0,
      "top_k": 10
    },
    KEY_ENABLED: True
  }
}

