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
Query Vector Store
"""
# pylint: disable=broad-exception-caught,ungrouped-imports

from abc import ABC, abstractmethod
import json
import gc
import os
import shutil
import tempfile
import numpy as np
from pathlib import Path
from typing import List, Tuple, Any
from google.cloud import aiplatform, storage
from common.models import QueryEngine
from common.utils.logging_handler import Logger
from common.utils.http_exceptions import InternalServerError
from services import embeddings
from config import PROJECT_ID, REGION
from config.vector_store_config import (PG_HOST, PG_PORT,
                                        PG_DBNAME, PG_USER, PG_PASSWD,
                                        DEFAULT_VECTOR_STORE,
                                        VECTOR_STORE_LANGCHAIN_PGVECTOR,
                                        VECTOR_STORE_MATCHING_ENGINE)
from langchain.schema.vectorstore import VectorStore as LCVectorStore
from langchain.vectorstores.pgvector import PGVector
from langchain.docstore.document import Document
from utils.gcs_helper import create_bucket

Logger = Logger.get_logger(__file__)

# embedding dimensions generated by TextEmbeddingModel
DIMENSIONS = 768

# number of document match results to retrieve
NUM_MATCH_RESULTS = 5

# number of text chunks to process into an embeddings file
MAX_NUM_TEXT_CHUNK_PROCESS = 1000


class VectorStore(ABC):
  """
  Abstract class for vector store db operations.  A VectorStore is created
  for a QueryEngine instance and manages the document index for that engine.
  """

  def __init__(self, q_engine: QueryEngine, embedding_type: str=None) -> None:
    self.q_engine = q_engine
    self.embedding_type = embedding_type

  @property
  def vector_store_type(self):
    return DEFAULT_VECTOR_STORE

  @abstractmethod
  def init_index(self):
    """
    Called before starting a new index build.
    """

  @abstractmethod
  def index_document(self, doc_name: str, text_chunks: List[str],
                          index_base: int) -> int:
    """
    Generate index for a document in this vector store
    Args:
      doc_name (str): name of document to be indexed
      text_chunks (List[str]): list of text content chunks for document
      index_base (int): index to start from; each chunk gets its own index
    Returns:
      new_index_base: updated query engine index base
    """

  @abstractmethod
  def deploy(self):
    """ Deploy vector store index for this query engine """

  def delete(self):
    """ Delete vector store index for this query engine """
    raise NotImplementedError("Not implemented")

  @abstractmethod
  def similarity_search(self, q_engine: QueryEngine,
                        query_embedding: List[float]) -> List[int]:
    """
    Retrieve text matches for query embeddings.
    Args:
      q_engine: QueryEngine model
      query_embedding: single embedding array for query
    Returns:
      list of indexes that are matched of length NUM_MATCH_RESULTS
    """

class MatchingEngineVectorStore(VectorStore):
  """
  Class for vector store based on Vertex matching engine.
  """
  def __init__(self, q_engine: QueryEngine, embedding_type:str=None) -> None:
    super().__init__(q_engine)
    self.storage_client = storage.Client(project=PROJECT_ID)
    self.bucket_name = f"{PROJECT_ID}-{self.q_engine.name}-data"
    self.bucket_uri = f"gs://{self.bucket_name}"
    self.index_name = self.q_engine.name.replace("-", "_") + "_MEindex"
    self.index_endpoint = None
    self.tree_ah_index = None
    self.index_description = ("Matching Engine index for LLM Service "
                              "query engine: " + self.q_engine.name)

  def init_index(self):
    # create bucket for ME index data
    create_bucket(self.storage_client, self.bucket_name, location=REGION)

  @property
  def vector_store_type(self):
    return VECTOR_STORE_MATCHING_ENGINE

  def index_document(self, doc_name: str, text_chunks: List[str],
                     index_base: int) -> int:
    """
    Generate matching engine index data files in a local directory.
    Args:
      doc_name (str): name of document to be indexed
      text_chunks (List[str]): list of text content chunks for document
      index_base (int): index to start from; each chunk gets its own index
    """


    chunk_index = 0
    num_chunks = len(text_chunks)
    embeddings_dir = None

    # create a list of chunks to process
    while chunk_index < num_chunks:
      remaining_chunks = num_chunks - chunk_index
      chunk_size = min(MAX_NUM_TEXT_CHUNK_PROCESS, remaining_chunks)
      end_chunk_index = chunk_index + chunk_size
      process_chunks = text_chunks[chunk_index:end_chunk_index]

      Logger.info(f"processing {chunk_size} chunks for file {doc_name} "
                  f"remaining chunks {remaining_chunks}")

      # generate np array of chunk IDs starting from index base
      ids = np.arange(index_base, index_base + len(process_chunks))

      # Create temporary folder to write embeddings to
      embeddings_dir = Path(tempfile.mkdtemp())

      # Convert chunks to embeddings in batches, to manage API throttling
      is_successful, chunk_embeddings = embeddings.get_embeddings(
          process_chunks,
          self.embedding_type
      )

      Logger.info(f"generated embeddings for chunks"
                  f" {chunk_index} to {end_chunk_index}")

      # create JSON
      embeddings_formatted = [
        json.dumps(
          {
            "id": str(idx),
            "embedding": [str(value) for value in embedding],
          }
        )
        + "\n"
        for idx, embedding in zip(ids[is_successful], chunk_embeddings)
      ]

      # Create output file
      doc_stem = Path(doc_name).stem
      chunk_path = embeddings_dir.joinpath(
          f"{doc_stem}_{index_base}_index.json")

      # write embeddings for chunk to file
      with open(chunk_path, "w", encoding="utf-8") as f:
        f.writelines(embeddings_formatted)

      Logger.info(f"wrote embeddings file for chunks {chunk_index} "
                  f"to {end_chunk_index}")

      # clean up any large data structures
      gc.collect()

      index_base = index_base + len(process_chunks)
      chunk_index = chunk_index + len(process_chunks)

    # copy data files up to bucket
    bucket = self.storage_client.get_bucket(self.bucket_name)
    for root, _, files in os.walk(embeddings_dir):
      for filename in files:
        local_path = os.path.join(root, filename)
        blob = bucket.blob(filename)
        blob.upload_from_filename(local_path)

    Logger.info(f"data uploaded for {doc_name}")

    # clean up tmp files
    shutil.rmtree(embeddings_dir)

    return index_base

  def delete(self):
    """ Delete vector store index for this query engine """
    Logger.info(f"deleting matching engine index {self.index_name}")
    if self.index_endpoint:
      self.index_endpoint.delete(force=True)
    if self.tree_ah_index:
      self.tree_ah_index.delete()

  def deploy(self):
    """ Create matching engine index and endpoint """

    # create ME index
    Logger.info(f"creating matching engine index {self.index_name}")

    self.tree_ah_index = aiplatform.MatchingEngineIndex.create_tree_ah_index(
        display_name=self.index_name,
        contents_delta_uri=self.bucket_uri,
        dimensions=DIMENSIONS,
        approximate_neighbors_count=150,
        distance_measure_type="DOT_PRODUCT_DISTANCE",
        leaf_node_embedding_count=500,
        leaf_nodes_to_search_percent=80,
        description=self.index_description,
    )
    Logger.info(f"Created matching engine index {self.index_name}")

    # create index endpoint
    self.index_endpoint = aiplatform.MatchingEngineIndexEndpoint.create(
        display_name=self.index_name,
        description=self.index_name,
        public_endpoint_enabled=True,
    )
    Logger.info(f"Created matching engine endpoint for {self.index_name}")

    # store index in query engine model
    self.q_engine.index_id = self.tree_ah_index.resource_name
    self.q_engine.index_name = self.index_name
    self.q_engine.endpoint = self.index_endpoint.resource_name
    self.q_engine.update()

    # deploy index endpoint
    try:
      # this seems to consistently time out, throwing an error, but
      # actually successfully deploys the endpoint
      self.index_endpoint.deploy_index(
          index=self.tree_ah_index,
          deployed_index_id=self.q_engine.deployed_index_name
      )
      Logger.info(f"Deployed matching engine endpoint for {self.index_name}")
    except Exception as e:
      Logger.error(f"Error creating ME index or endpoint {e}")

  def similarity_search(self, q_engine: QueryEngine,
                        query_embedding: List[float]) -> List[int]:
    """
    Retrieve text matches for query embeddings.
    Args:
      q_engine: QueryEngine model
      query_embedding: single embedding array for query
    Returns:
      list of indexes that are matched of length NUM_MATCH_RESULTS
    """
    index_endpoint = aiplatform.MatchingEngineIndexEndpoint(q_engine.endpoint)

    match_indexes_list = index_endpoint.find_neighbors(
        queries=[query_embedding],
        deployed_index_id=q_engine.deployed_index_name,
        num_neighbors=NUM_MATCH_RESULTS
    )
    match_indexes = [int(match.id) for match in match_indexes_list[0]]
    return match_indexes

class LangChainVectorStore(VectorStore):
  """
  Generic LLM Service interface to Langchain vector store classes.
  """
  def __init__(self, q_engine: QueryEngine, embedding_type: str = None) -> None:
    super().__init__(q_engine, embedding_type)
    self.lc_vector_store = self._get_langchain_vector_store()
    self.index_length = 0

  def delete(self):
    self.lc_vector_store.index.remove_ids(
      np.array(np.arange(self.index_length), dtype=np.int64)
    )

  def init_index(self):
    pass

  def _get_langchain_vector_store(self) -> LCVectorStore:
    # retrieve langchain vector store obj from config
    lc_vectorstore = LC_VECTOR_STORES.get(self.q_engine.vector_store)
    if lc_vectorstore is None:
      raise InternalServerError(
          f"vector store {self.q_engine.vector_store} not found in config")
    return lc_vectorstore

  def index_document(self, doc_name: str, text_chunks: List[str],
                          index_base: int) -> int:
    # generate list of chunk IDs starting from index base
    ids = list(range(index_base, index_base + len(text_chunks)))

    # Convert chunks to embeddings
    _, chunk_embeddings = embeddings.get_embeddings(
        text_chunks,
        self.embedding_type
    )

    # add embeddings to vector store
    self.lc_vector_store.add_embeddings(texts=text_chunks,
                                        embeddings=chunk_embeddings,
                                        ids=ids)
    # return new index base
    new_index_base = index_base + len(text_chunks)
    self.index_length = new_index_base
    return new_index_base

  def similarity_search(self, q_engine: QueryEngine,
                       query_embedding: List[float]) -> List[int]:
    results = self.lc_vector_store.similarity_search_with_score_by_vector(
        embedding=query_embedding,
        k=NUM_MATCH_RESULTS
    )
    processed_results = self.process_results(results)
    return processed_results

  def process_results(self, results: List[Any]) -> List[int]:
    """
    Process langchain vector store results to return list of indexes.  The
    default behavior for langchain is to return list of Documents, but we
    manage the documents separately in the LLM Service.  So we need the vector
    store to return the list of matching indexes.
    """
    raise NotImplementedError(
      "Must implement process_results for Langchain vectorstore")

  def deploy(self):
    """ Create matching engine index and endpoint """
    pass

class LLMServicePGVector(PGVector):
  """
  Our version of langchain PGVector with override for result processing.
  """
  def _results_to_docs_and_scores(self, results: Any) -> \
    List[Tuple[Document, float, int]]:
    """
    Override langchain class results to return doc indexes along with docs.
    """
    docs = [
      (
        Document(
            page_content=result.EmbeddingStore.document,
            metadata=result.EmbeddingStore.cmetadata,
        ),
        result.distance \
            if self.embedding_function is not None else None,
        result.EmbeddingStore.custom_id
      )
      for result in results
    ]
    return docs

class PostgresVectorStore(LangChainVectorStore):
  """
  LLM Service interface for Postgres Vector Stores, based on langchain
  PGVector VectorStore class.
  """
  @property
  def vector_store_type(self):
    return VECTOR_STORE_LANGCHAIN_PGVECTOR

  def _get_langchain_vector_store(self) -> LCVectorStore:

    # get postgres connection string using PGVector utility method
    connection_string = PGVector.connection_string_from_db_params(
        driver="psycopg2",
        host=PG_HOST,
        port=PG_PORT,
        database=PG_DBNAME,
        user=PG_USER,
        password=PG_PASSWD
    )

    # Each query engine is stored in a different PGVector collection,
    # where the collection name is just the query engine name.
    collection_name = self.q_engine.name

    # instantiate the langchain vector store object
    langchain_vector_store = LLMServicePGVector(
        embedding_function=embeddings.LangchainEmbeddings,
        connection_string=connection_string,
        collection_name=collection_name
        )

    return langchain_vector_store

  def process_results(self, results: List[Any]) -> List[int]:
    """
    Our overridden method _results_to_docs_and_scores returns a tuple of
    (Document, distance, index). So return a list of indexes extracted from
    result tuples.
    """
    processed_results = [int(result[2]) for result in results]
    return processed_results


LC_VECTOR_STORES = {
  VECTOR_STORE_LANGCHAIN_PGVECTOR: PostgresVectorStore
}
