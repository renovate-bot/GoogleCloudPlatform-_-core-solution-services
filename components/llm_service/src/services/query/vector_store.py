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
# pylint: disable=broad-exception-caught,ungrouped-imports,invalid-name

from abc import ABC, abstractmethod
from base64 import b64decode
import json
import gc
import os
import re
import shutil
import tempfile
import numpy as np
from pathlib import Path
from typing import List, Tuple, Any, Optional, Union
from google.cloud import aiplatform, storage
import pyparsing
from pyparsing import (Word, alphanums, Suppress, ParseResults,
                       delimitedList, Literal, Forward, ZeroOrMore,
                       oneOf, ParserElement, QuotedString, Regex)
from common.models import QueryEngine
from common.utils.logging_handler import Logger
from common.utils.http_exceptions import InternalServerError
from services import embeddings
from config import PROJECT_ID, REGION, MODALITY_SET
from config.vector_store_config import (PG_HOST, PG_PORT,
                                        PG_DBNAME, PG_USER, PG_PASSWD,
                                        DEFAULT_VECTOR_STORE,
                                        VECTOR_STORE_LANGCHAIN_PGVECTOR,
                                        VECTOR_STORE_MATCHING_ENGINE)
from langchain.schema.vectorstore import VectorStore as LCVectorStore
from langchain.vectorstores.pgvector import PGVector as LangchainPGVector
from langchain.docstore.document import Document
from utils.gcs_helper import create_bucket

Logger = Logger.get_logger(__file__)

# embedding dimensions generated by TextEmbeddingModel
DIMENSIONS = 768

# number of document match results to retrieve from a single embeddings search
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
  async def index_document(self, doc_name: str, text_chunks: List[str],
                           index_base: int,
                           metadata: List[dict] = None) -> int:
    """
    Generate index for a document in this vector store
    Args:
      doc_name (str): name of document to be indexed
      text_chunks (List[str]): list of text content chunks for document
      index_base (int): index to start from; each chunk gets its own index
      metadata (List[dict]): list of metadata dicts for chunks
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
                        query_embedding: List[float],
                        query_filter: Optional[str] = None) -> List[int]:
    """
    Retrieve text matches for query embeddings.
    Allows filter expressions to limit documents based on metadata.
    Filter expressions use the Vertex Search syntax as documented here:
        https://cloud.google.com/generative-ai-app-builder/docs/filter-search-metadata#filter-expression-syntax

    Args:
      q_engine: QueryEngine model
      query_embedding: single embedding array for query
      query_filter: (optional) filter expression
    Returns:
      list of indexes that are matched of length NUM_MATCH_RESULTS
    """

  def parse_filter(self, filter_str: str) -> Union[ParseResults, dict]:
    """
    Parse filter expressions in the Vertex Search format:
      https://cloud.google.com/generative-ai-app-builder/docs/filter-search-metadata#filter-expression-syntax

    Returns:
      A pyparsing ParseResults object
    """
    # Enable packrat parsing for better performance
    ParserElement.enable_packrat()

    # Define basic elements
    LPAR, RPAR, COMMA, COLON = map(Suppress, "(),:")
    double = Regex(r"[+-]?\d+\.?\d*").set_parse_action(lambda t: float(t[0]))
    literal = QuotedString('"')
    text_field = Word(alphanums + "_")
    numerical_field = Word(alphanums + "_")
    comparison = oneOf("< <= >= > =")
    bound_type = oneOf("e i")

    # Define lower and upper bounds
    lower_bound = (double + pyparsing.Optional(bound_type)) | oneOf("*")
    upper_bound = (double + pyparsing.Optional(bound_type)) | oneOf("*")

    # Define expressions
    simple_text_expr = (
        text_field
        + COLON
        + Literal("ANY")
        + LPAR
        + delimitedList(literal, delim=COMMA)
        + RPAR
    )
    simple_numerical_expr = (
        numerical_field
        + COLON
        + Literal("IN")
        + LPAR
        + lower_bound
        + COMMA
        + upper_bound
        + RPAR
    ) | (numerical_field + comparison + double)

    expression = Forward()
    expression <<= (
        pyparsing.Optional(oneOf("- NOT"))
        + (simple_text_expr | simple_numerical_expr | \
          (LPAR + expression + RPAR))
    )

    # Define the full filter with AND/OR combinations
    filter_expr = expression + ZeroOrMore((oneOf("AND OR") + expression))

    # parse expression
    parsed_expr = filter_expr.parse_string(filter_str, parse_all=True)

    return parsed_expr


class MatchingEngineVectorStore(VectorStore):
  """
  Class for vector store based on Vertex matching engine.
  """
  def __init__(self, q_engine: QueryEngine, embedding_type:str=None) -> None:
    super().__init__(q_engine)
    self.storage_client = storage.Client(project=PROJECT_ID)
    self.bucket_name = self.data_bucket_name(q_engine)
    self.bucket_uri = f"gs://{self.bucket_name}"
    qe_name = q_engine.name.replace(" ", "-")
    qe_name = qe_name.replace("_", "-").lower()
    self.index_name = qe_name + "_MEindex"
    self.index_endpoint = None
    self.tree_ah_index = None
    self.index_description = ("Matching Engine index for LLM Service "
                              "query engine: " + self.q_engine.name)

  @classmethod
  def data_bucket_name(cls, q_engine: QueryEngine) -> str:
    """
    Generate a unique index data bucket name, that obeys the rules of
    GCS bucket names.

    Args:
        q_engine: the QueryEngine to generate the bucket name for.

    Returns:
        bucket name (str)
    """
    qe_name = q_engine.name.replace(" ", "-")
    qe_name = qe_name.replace("_", "-").lower()
    bucket_name = f"{PROJECT_ID}-{qe_name}-data"
    if not re.fullmatch("^[a-z0-9][a-z0-9._-]{1,61}[a-z0-9]$", bucket_name):
      raise RuntimeError(f"Invalid downloads bucket name {bucket_name}")
    return bucket_name

  def init_index(self):
    # create bucket for ME index data
    create_bucket(self.storage_client, self.bucket_name, location=REGION)

  @property
  def vector_store_type(self):
    return VECTOR_STORE_MATCHING_ENGINE

  async def index_document(self, doc_name: str, text_chunks: List[str],
                           index_base: int,
                           metadata: List[dict] = None) -> int:
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
      is_successful, chunk_embeddings = await embeddings.get_embeddings(
          process_chunks,
          self.embedding_type
      )

      # check for success
      if len(chunk_embeddings) == 0 or not all(is_successful):
        raise RuntimeError(f"failed to generate embeddings for {doc_name}")

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
                        query_embedding: List[float],
                        query_filter: Optional[str] = None) -> List[int]:
    """
    Retrieve text matches for query embeddings.
    Args:
      q_engine: QueryEngine model
      query_embedding: single embedding array for query
      query_filter: (optional) filter expression
    Returns:
      list of indexes that are matched of length NUM_MATCH_RESULTS
    """
    # TODO: implement query filters for matching engine
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

  async def index_document_multimodal(self,
                                 doc_name: str,
                                 doc_chunks: List[object],
                                 index_base: int) -> \
                                  int:

    # Initialize counter for all embeddings of all modalities
    # created from all chunks of document
    num_embeddings = 0

    # Convert multimodal chunks to embeddings
    # Note that multimodal embedding model can only embed one chunk
    # at a time. As opposed to the text-only embedding model, which
    # can embed an array of multiple chunks at the same time.
    chunk_texts = []
    chunk_embeddings = []

    # Loop over chunks
    for doc in doc_chunks:
      # Raise error is doc object is formatted incorrectly
      modality_list_sorted = sorted(MODALITY_SET)
      modality_list_sorted_exist = \
        [modality in doc.keys() for modality in modality_list_sorted]
      if not any(modality_list_sorted_exist):
        raise RuntimeError(
          f"failed to retrieve any modality for {doc_name}")
      for modality, exist in \
        zip(modality_list_sorted, modality_list_sorted_exist):
        if not exist:
          doc[modality] = None

      # Get chunk embeddings
      user_file_bytes = None
      if doc["image"]:
        user_file_bytes = b64decode(doc["image"])
      chunk_embedding = \
        await embeddings.get_multimodal_embeddings(
          user_text=doc["text"],
          user_file_bytes=user_file_bytes,
          embedding_type=self.embedding_type)
      # TODO: Also embed doc["video"] (video chunk) and
      # potentially doc["audio"] (audio chunk)

      # Check to make sure that embeddings for available modalities exist
      for modality in modality_list_sorted:
        if modality in chunk_embedding:
          chunk_texts.append(doc["text"])
          chunk_embeddings.append(chunk_embedding[modality])
          # Increment counter
          num_embeddings += 1
        else:
          raise RuntimeError(
            f"failed to generate {modality} chunk embedding for {doc_name}")

    # now that all embeddings are created for all modalities of all chunks,
    # generate list of chunk IDs starting from index base
    ids = list(range(index_base, index_base + num_embeddings))
    Logger.info(f"Indexed {len(ids)} embeddings for [{doc_name}]")

    # check for success
    if len(chunk_embeddings) == 0:
      raise RuntimeError(f"failed to generate embeddings for {doc_name}")

    # add image embeddings to vector store
    self.lc_vector_store.add_embeddings(texts=chunk_texts,
                                        embeddings=chunk_embeddings,
                                        ids=ids)
    # return new index base
    new_index_base = index_base + num_embeddings
    self.index_length = new_index_base

    return new_index_base

  async def index_document(self,
                           doc_name: str,
                           text_chunks: List[str],
                           index_base: int,
                           metadata: List[dict] = None) -> \
                            int:
    # generate list of chunk IDs starting from index base
    ids = list(range(index_base, index_base + len(text_chunks)))
    Logger.info(f"Indexed {len(ids)} embeddings for [{doc_name}]")

    # Convert chunks to embeddings
    is_successful, chunk_embeddings = \
      await embeddings.get_embeddings(text_chunks,
                                      self.embedding_type)

    # check for success
    if len(chunk_embeddings) == 0 or not all(is_successful):
      raise RuntimeError(f"failed to generate embeddings for {doc_name}")

    # add embeddings to vector store
    self.lc_vector_store.add_embeddings(texts=text_chunks,
                                        embeddings=chunk_embeddings,
                                        ids=ids,
                                        metadatas=metadata)
    # return new index base
    new_index_base = index_base + len(text_chunks)
    self.index_length = new_index_base
    return new_index_base

  def similarity_search(self, q_engine: QueryEngine,
                       query_embedding: List[float],
                       query_filter: Optional[str] = None) -> List[int]:
    """
    Retrieve text matches for query embeddings from a langchain
    vector store.
    Args:
      q_engine: QueryEngine model
      query_embedding: single embedding array for query
      query_filter: (optional) filter expression
    Returns:
      list of indexes that are matched of length NUM_MATCH_RESULTS
    """
    langchain_filter = None
    if query_filter:
      parsed_filter = self.parse_filter(query_filter)
      langchain_filter = self.translate_filter(parsed_filter)

    results = self.lc_vector_store.similarity_search_with_score_by_vector(
        embedding=query_embedding,
        k=NUM_MATCH_RESULTS,
        filter=langchain_filter
    )
    processed_results = self.process_results(results)
    return processed_results

  def parse_filter(self, filter_str: str) -> Union[ParseResults, dict]:
    """
    Parse a filter for a langchain vector store.
    For now assume this is a string specifying a json dict
    {"key":{"$op": "value"}}
    """
    if filter_str is not None:
      filter_dict = json.loads(filter_str)
    else:
      filter_dict = None
    return filter_dict

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

  def translate_filter(self,
                       parsed_filter: Union[str, dict, ParseResults]) -> dict:
    """
    Converts a parsed filter expression into a dictionary representation
    of the filter compatible with langchain vector store filters.
    """
    if isinstance(parsed_filter, dict):
      return parsed_filter

    if isinstance(parsed_filter, str):
      # Handle single field name (no operator/value)
      return {parsed_filter: {}}

    if isinstance(parsed_filter, list) and len(parsed_filter) == 2:
      # Handle numerical comparisons
      field_name, (operator, value) = parsed_filter
      return {field_name: {operator.upper(): value}}

    if isinstance(parsed_filter, list) and len(parsed_filter) == 4:
      # Handle "ANY" filter
      field_name, _, _, literals = parsed_filter
      return {field_name: {"IN": list(literals)}}

    if isinstance(parsed_filter, list) and len(parsed_filter) == 6:
      # Handle "IN" filter
      field_name, _, _, lower, _, upper = parsed_filter
      return {field_name: {"BETWEEN": [lower, upper]}}

    if isinstance(parsed_filter, list) and len(parsed_filter) > 2:
      # Handle "AND" or "OR" combinations
      operator = parsed_filter[1]
      clauses = [self.translate_filter(expr) for expr in parsed_filter[0::2]]
      return {operator.upper(): clauses}

    return None


class LLMServicePGVector(LangchainPGVector):
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

    # get postgres connection string using LangchainPGVector utility method
    connection_string = LangchainPGVector.connection_string_from_db_params(
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
