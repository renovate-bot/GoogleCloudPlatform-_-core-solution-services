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

""" Schema examples and test objects for unit tests """
# pylint: disable = line-too-long

LLM_GENERATE_EXAMPLE = {
  "prompt": "what is the meaning of life?",
  "llm_type": "VertexAI-Chat",
}

LLM_MULTIMODAL_GENERATE_EXAMPLE = {
  "prompt": "what is this image about?",
  "llm_type": "gemini-2.0-flash-001",
  "user_file_b64": "",
  "user_file_name": "",
}

LLM_EMBEDDINGS_EXAMPLE = {
  "embedding_type": "",
  "text": "",
}

LLM_MULTIMODAL_EMBEDDINGS_EXAMPLE = {
  "embedding_type": "",
  "user_file_b64": "",
  "user_file_name": "",
  "text": "",
}

QUERY_EXAMPLE = {
  "prompt": "test prompt",
  "llm_type": "gemini-2.0-flash-001",
  "query_filter": "{\"Title\":\"Document Title\"}"
}

USER_QUERY_EXAMPLE = {
  "id": "asd98798as7dhjgkjsdfh",
  "user_id": "fake-user-id",
  "title": "Test query",
  "prompt": "Test prompt",
  "query_engine_id": "asd98798as7dhjgkjsdfh",
  "history": [
    {"HumanQuestion": "test input 1"},
    {
      "AIResponse": "test response 1",
      "AIReferences": [
        {
          "query_engine": "query-engine-test",
          "query_engine_id": "asd98798as7dhjgkjsdfh",
          "document_id": "efghxxzzyy1234",
          "chunk_id": "abcdxxzzyy1234"
        }
      ]
    },
    {"HumanQuestion": "test input 2"},
    {
      "AIResponse": "test response 2",
      "AIReferences": [
        {
          "query_engine": "query-engine-test",
          "query_engine_id": "asd98798as7dhjgkjsdfh",
          "document_id": "efghxxzzyy5678",
          "chunk_id": "abcdxxzzyy5678"
        }
      ]
    }
  ]
}

QUERY_ENGINE_EXAMPLE = {
  "id": "asd98798as7dhjgkjsdfh",
  "name": "query-engine-test",
  "description": "sample description",
  "doc_url": "https://example.com",
  "query_engine_type": "qe_llm_service",
  "embedding_type": "VertexAI-Chat",
  "read_access_group": "2023:7:50:080:101:A1",
  "vector_store": "langchain_pgvector",
  "created_by": "fake-user-id",
  "is_public": True,
  "index_id": "projects/83285581741/locations/us-central1/indexes/682347240495461171",
  "index_name": "query_engine_test_MEindex",
  "endpoint": "projects/83285581741/locations/us-central1/indexEndpoints/420294037177840435"
}

QUERY_ENGINE_BUILD_EXAMPLE = {
  "name": "query-engine-build-test",
  "query_engine": "qe_llm_service",
  "doc_url": "gs-for-cloud-storage-bucket",
  "embedding_type": "VertexAI-Embedding-Vision",
  "vector_store": "langchain_pgvector",
  "description": "sample description",
  "params": {
      "depth_limit": "0",
      "is_multimodal": "True",
      }
  }

QUERY_ENGINE_UPDATE_EXAMPLE = {
  "name": "query-engine-update-test",
  "description": "sample description",
  "read_access_groups": "testgroup1,testgroup2"
  }

QUERY_RESULT_EXAMPLE = {
  "id": "asd98798as7dhjgkjsdfh",
  "query_engine_id": "asd98798as7dhjgkjsdfh",
  "query_engine": "query-engine-test",
  "response": "test response",
  "query_refs": ["abcd1234", "defg5678"],
  "archived_at_timestamp": None,
  "archived_by": None,
  "created_by": "fake-user-id",
  "created_time": "2023-07-04 19:22:50.799741+00:00"
}

QUERY_REFERENCE_EXAMPLE_1 = {
  "id": "easd98798as7dhjgkjsdf",
  "query_engine_id": "asd98798as7dhjgkjsdfh",
  "query_engine": "query-engine-test",
  "document_id": "asd98798as7dhjgkjsdfh1",
  "document_url": "https://example.com/content",
  "modality": "text",
  "chunk_id": "abcdxxzzyy5678",
  "document_text": "test doc content"
}

QUERY_REFERENCE_EXAMPLE_2 = {
  "id": "fasd98798as7dhjgkjsdf",
  "query_engine_id": "asd98798as7dhjgkjsdfh",
  "query_engine": "query-engine-test",
  "document_id": "asd98798as7dhjgkjsdfh1",
  "document_url": "https://example.com/content",
  "modality": "text",
  "chunk_id": "abcdxxzzyy5678",
  "document_text": "test doc content 2"
}

QUERY_DOCUMENT_EXAMPLE_1 = {
  "id": "asd98798as7dhjgkjsdfh1",
  "query_engine_id": "asd98798as7dhjgkjsdfh",
  "query_engine": "query-engine-test",
  "doc_url": "abcd.com/pdf1",
  "index_start": 0,
  "index_end": 123
}

QUERY_DOCUMENT_EXAMPLE_2 = {
  "id": "asd98798as7dhjgkjsdfh2",
  "query_engine_id": "asd98798as7dhjgkjsdfh",
  "query_engine": "query-engine-test",
  "doc_url": "abcd.com/pdf2",
  "index_start": 0,
  "index_end": 11,
  "metadata": {
    "author": "Michael Moorcock",
    "title": "The Eternal Champion"
  }
}

QUERY_DOCUMENT_EXAMPLE_3 = {
  "id": "asd98798as7dhjgkjsdfh3",
  "query_engine_id": "asd98798as7dhjgkjs",
  "query_engine": "query-engine-test",
  "doc_url": "abcd.com/pdf3",
  "index_start": 0,
  "index_end": 1234
}

QUERY_DOCUMENT_CHUNK_EXAMPLE_1 = {
  "id": "asd98798as7dhjhkkjhk1",
  "query_engine_id": "asd98798as7dhjgkjsdfh",
  "query_document_id": "asd98798as7dhjgkjsdfh1",
  "index": 0,
  "modality": "text",
  "text": "<p>query_document_chunk_example_1</p>",
  "clean_text": "query_document_chunk_example_1",
  "sentences": ["query_document_chunk_example_1"]
}

QUERY_DOCUMENT_CHUNK_EXAMPLE_2 = {
  "id": "asd98798as7dhjhkkjhk12",
  "query_engine_id": "asd98798as7dhjgkjsdfh",
  "query_document_id": "asd98798as7dhjgkjsdfh1",
  "index": 1,
  "modality": "text",
  "text": "<p>query_document_chunk_example_2</p>",
  "clean_text": "query_document_chunk_example_2",
  "sentences": ["query_document_chunk_example_2"]
}

QUERY_DOCUMENT_CHUNK_EXAMPLE_3 = {
  "id": "asd98798as7dhjhkkjhk13",
  "query_engine_id": "asd98798as7dhjgkjsdfh",
  "query_document_id": "asd98798as7dhjgkjsdfh1",
  "index": 2,
  "modality": "text",
  "text": "<p>query_document_chunk_example_3</p>",
  "clean_text": "query_document_chunk_example_3",
  "sentences": ["query_document_chunk_example_3"]
}

QUERY_RETRIEVE_EXAMPLE = {
  "user_query_id": USER_QUERY_EXAMPLE["id"],
  "query_result": QUERY_RESULT_EXAMPLE,
  "query_references": [QUERY_REFERENCE_EXAMPLE_1, QUERY_REFERENCE_EXAMPLE_2]
}

CHAT_EXAMPLE = {
  "id": "asd98798as7dhjgkjsdfh",
  "user_id": "fake-user-id",
  "prompt": "test input 1",
  "title": "Test chat",
  "llm_type": "VertexAI-Chat",
  "history": [
    {"HumanInput": "test input 1"},
    {"AIOutput": "test response 1"},
    {"HumanInput": "test input 2"},
    {"AIOutput": "test response 2"}
  ],
  "created_time": "2023-05-05 09:22:49.843674+00:00",
  "last_modified_time": "2023-05-05 09:22:49.843674+00:00"
}

USER_EXAMPLE = {
    "id": "fake-user-id",
    "first_name": "Test",
    "last_name": "Tester",
    "user_id": "fake-user-id",
#    "auth_id": "fake-user-id",
    "email": "user@gmail.com",
#    "role": "Admin",
    "user_type": "user",
    "status": "active"
}

USER_PLAN_EXAMPLE = {
  "id": "fake-plan-id",
  "name": "example plan",
  "user_id": "fake-user-id",
  "task_prompt": "fake task prompt",
  "task_response": "fake task response",
  "agent_name": "Task",
  "plan_steps": ["fake-planstep-id-1", "fake-planstep-id-2"]
}

USER_PLAN_STEPS_EXAMPLE_1 = {
  "id": "fake-planstep-id-1",
  "user_id": "fake-user-id",
  "plan_id": "fake-plan-id",
  "description": "Use [fake tool] to [perform step description 1]",
  "agent_name": "Task"
}

USER_PLAN_STEPS_EXAMPLE_2 = {
  "id": "fake-planstep-id-2",
  "user_id": "fake-user-id",
  "plan_id": "fake-plan-id",
  "description": "Use [fake tool] to [perform step description 2]",
  "agent_name": "Task"
}

AGENT_RUN_EXAMPLE = {
  "prompt": "hello"
}

AGENT_RUN_RESPONSE_EXAMPLE = {
  "output": "hello",
  "chat": CHAT_EXAMPLE
}

AGENT_PLAN_EXAMPLE = {
  "prompt": "hello"
}

AGENT_PLAN_RESPONSE_EXAMPLE = {
  "output": "hello",
  "chat": CHAT_EXAMPLE,
  "plan": {
    "id": "fake-plan-id",
    "name": "example plan",
    "user_id": "fake-user-id",
    "agent_name": "Task",
    "plan_steps": [
      {
        "id": "fake-planstep-id-1",
        "description": "Use [fake tool] to [perform step description 1]",
      },
      {
        "id": "fake-planstep-id-2",
        "description": "Use [fake tool] to [perform step description 2]",
      }
    ]
  }
}

USER_PLAN_RESPONSE_EXAMPLE = USER_PLAN_EXAMPLE
