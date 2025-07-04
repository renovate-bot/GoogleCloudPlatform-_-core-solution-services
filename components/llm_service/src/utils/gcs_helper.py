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

# pylint: disable=unused-argument,broad-exception-raised
"""
Google Storage helper functions.
"""
import io
import os
import uuid
import base64
from pathlib import Path
from typing import List
from common.utils.logging_handler import Logger
from schemas.llm_schema import FileB64
from google.cloud import storage

Logger = Logger.get_logger(__file__)

def get_blob_from_gcs_path(gcs_path):
  """
  Returns blob object using gcs_path
  """
  storage_client = storage.Client()
  bucket_name = gcs_path.split("gs://")[1].split("/")[0]
  blob_name = gcs_path.split(bucket_name)[-1].strip("/")
  bucket = storage_client.bucket(bucket_name)
  if not bucket:
    raise ValueError(f"Unknown path \"{gcs_path}\"")
  blob = bucket.get_blob(blob_name)
  if not blob:
    raise ValueError(f"Unknown path \"{gcs_path}\"")
  return blob

def download_file_from_gcs(gcs_path, destination_folder_path="data/"):
  """
  Downloads file from gcs
  """
  try:
    storage_client = storage.Client()
    bucket_name = gcs_path.split("gs://")[1].split("/")[0]
    bucket = storage_client.get_bucket(bucket_name)
    blob_name = gcs_path.split(bucket_name)[-1].strip("/")
    blob = bucket.blob(blob_name)
    os.makedirs(destination_folder_path, exist_ok=True)
    destination_path = destination_folder_path + blob_name.split("/")[-1]
    blob.download_to_filename(destination_path)
    return destination_path
  except Exception as e:
    Logger.error(e)
    raise Exception("Failed to download file from the GCS path") from e

def clear_bucket(storage_client: storage.Client, bucket_name: str) -> None:
  """
  Delete all the contents of the specified GCS bucket
  """
  Logger.info(f"Deleting all objects from GCS bucket {bucket_name}")
  bucket = storage_client.bucket(bucket_name)
  blobs = bucket.list_blobs()
  index = 0
  for blob in blobs:
    blob.delete()
    index += 1
  Logger.info(f"{index} files deleted")

def create_bucket(storage_client: storage.Client,
                  bucket_name: str, location: str = None,
                  clear: bool = True,
                  make_public: bool = False) -> None:
  # Check if the bucket exists
  bucket = storage_client.bucket(bucket_name)
  if not bucket.exists():
    # Create new bucket
    if make_public:
      _ = storage_client.create_bucket(bucket_name, location=location)
      set_bucket_viewer_iam(storage_client, bucket_name, ["allUsers"])
    else:
      _ = storage_client.create_bucket(bucket_name, location=location)
    Logger.info(f"Bucket {bucket_name} created.")
  else:
    Logger.info(f"Bucket {bucket_name} already exists.")
    if clear:
      clear_bucket(storage_client, bucket_name)

def set_bucket_viewer_iam(
    storage_client: storage.Client,
    bucket_name: str,
    members: List[str] = None,
):
  """Set viewer IAM Policy on bucket"""
  if members is None:
    members = ["allUsers"]
  bucket = storage_client.bucket(bucket_name)
  policy = bucket.get_iam_policy(requested_policy_version=3)
  policy.bindings.append(
      {"role": "roles/storage.objectViewer", "members": members}
  )
  bucket.set_iam_policy(policy)

def upload_to_gcs(storage_client: storage.Client, bucket_name: str,
                  file_path: str, bucket_folder: str = None) -> str:
  """ Upload file to GCS bucket. Returns URL to file. """
  Logger.info(f"""Uploading {file_path} to GCS bucket {bucket_name} \
              in folder {str(bucket_folder)}""")
  bucket = storage_client.bucket(bucket_name)
  file_name = Path(file_path).name
  if bucket_folder:
    file_name = f"{bucket_folder}/{file_name}"
  blob = bucket.blob(file_name)
  blob.upload_from_filename(file_path)
  gcs_url = f"gs://{bucket_name}/{file_name}"
  Logger.info(f"Uploaded {file_path} to {gcs_url}")
  return gcs_url

def upload_file_to_gcs(bucket: storage.Bucket,
                       file_name: str, file_obj: io.BytesIO) -> str:
  """ Upload file to GCS bucket. Returns URL to file. """
  bucket_name = bucket.name
  Logger.info(f"Uploading {file_name} to GCS bucket {bucket_name}")
  blob = bucket.blob(file_name)
  blob.upload_from_file(file_obj)
  gcs_url = f"gs://{bucket_name}/{file_name}"
  Logger.info(f"Uploaded {file_name} to {gcs_url}")
  return gcs_url

def create_bucket_for_file(filename: str) -> storage.Bucket:
  """This function creates a bucket to be used for storage
  The filename parameter was originally used to help create a unique name
  for a bucket but is no longer used. It has been left in for compatability"""
  storage_client = storage.Client()
  bucket_name = str(uuid.uuid4())
  bucket = storage_client.bucket(bucket_name)
  bucket.location = "US"
  bucket.storage_class = "STANDARD"
  bucket.create()
  Logger.info(f"Bucket {bucket.name} created")
  return bucket

async def upload_b64files_to_gcs(files: FileB64) -> storage.Bucket:
  """ Creates a bucket and uploads the files into it
  returns a storage bucket created for upload """
  bucket = create_bucket_for_file("")
  for file in files:
    upload_file_to_gcs(bucket, file["name"],
                       io.BytesIO(base64.b64decode(file["b64"])))
  return bucket
