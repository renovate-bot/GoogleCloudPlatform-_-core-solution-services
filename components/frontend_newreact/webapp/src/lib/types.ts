// Copyright 2024 Google LLC
//
// Licensed under the Apache License, Version 2.0 (the License);
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//     https://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

import { ReactNode } from "react"
import { z } from "zod"
import { User as FirebaseUser } from 'firebase/auth'

export type INavigationItem = {
  name: string
  href: string
  show: () => boolean
  icon?: ReactNode
}

export type Theme = "light" | "dark"

export type IAuthProvider = "google" | "password"

export type IAppConfig = {
  siteName: string
  locale: string
  logoPath: string
  simpleLogoPath: string
  imagesPath: string
  theme: string
  authProviders: IAuthProvider[]
  authorizedDomains: RegExp[]
  oAuthScopes: string[]
}

export interface User extends FirebaseUser {
  token: string;
  firstName: string;
  lastName: string;
}

export const UserSchema = z.object({
  token: z.string(),
  firstName: z.string(),
  lastName: z.string(),
  uid: z.string(),
  email: z.string().nullable(),
  displayName: z.string().nullable(),
  photoURL: z.string().nullable(),
})

export type IUser = z.infer<typeof UserSchema>

export const Users = z.array(UserSchema)

const FIELD_TYPE = [
  "string",
  "number",
  "bool",
  "select",
  "list(string)",
  "file",
] as const

const FIELD_TYPE_ENUM = z.enum(FIELD_TYPE)

export const FormVariable = z.object({
  name: z.string(),
  display: z.string(),
  type: FIELD_TYPE_ENUM,
  description: z.string(),
  default: z.any().optional(),
  required: z.boolean(),
  group: z.number(),
  options: z.string().array().optional(),
  tooltip: z.string().optional(),
  fileLabel: z.string().optional(),
  multiple: z.boolean().default(false).optional(),
  accept: z.string().optional(),
  onClick: z.function().optional(),
})

export type IFormVariable = z.infer<typeof FormVariable>

export type IFormData = {
  [key: string]: string | number | boolean
}

export type IFieldValidateValue = { value: string | number | boolean }

export type IFormValidationData = {
  [key: string]: any
}

export enum ALERT_TYPE {
  INFO,
  SUCCESS,
  WARNING,
  ERROR,
}

export interface IAlert {
  type: ALERT_TYPE
  message: string | React.ReactNode
  durationMs?: number
  closeable?: boolean
}

export interface QueryResponse {
  response: string
}

export interface QueryReferences {
  chunk_id: string
  chunk_url: string
  document_url: string
  document_text: string
  modality: string
}

export type QueryContents = {
  HumanQuestion?: string
  AIResponse?: string
  AIReferences?: QueryReferences[]
}

export type ChatContents = {
  HumanInput?: string
  AIOutput?: string
  UploadedFile?: string
  FileURL?: string
  FileContentsBase64?: string
}

export type Query = {
  archived_at_timestamp: string | null
  archived_by: string
  created_by: string
  created_time: string
  deleted_at_timestamp: string | null
  deleted_by: string
  id: string
  last_modified_by: string
  last_modified_time: string
  llm_type: string | null
  title: string | null
  prompt: string
  user_id: string
  history: QueryContents[]
  query_result?: QueryResponse
  query_references?: QueryReferences[]
  user_query_id?: string
  user_chat?: Chat
}

export interface QueryReference {
  chunk_id: string;
  document_url: string;
  document_text: string;
  modality: string;
  chunk_url?: string;
  page?: number;
  timestamp_start?: number;
  timestamp_stop?: number;
}

export interface ChatHistoryEntry {
  HumanInput?: string;
  AIOutput?: string;
  UploadedFile?: string;
  FileURL?: string;
  FileContentsBase64?: string;
  FileType?: string;
  Source?: {
    id: string;
    name: string;
    type: string;
  };
  QueryReferences?: QueryReference[];
}

export interface Chat {
  id?: string;
  title: string;
  created_time: string;
  created_by: string;
  last_modified_time: string;
  last_modified_by: string;
  archived_at_timestamp: string | null;
  archived_by: string;
  deleted_at_timestamp: string | null;
  deleted_by: string;
  prompt: string;
  llm_type: string;
  user_id: string;
  agent_name: string | null;
  history: ChatHistoryEntry[];
  streamingHistory?: string;
}

export const QUERY_ENGINE_TYPES = {
  "qe_vertex_search": "Vertex Search",
  "qe_llm_service": "GENIE Search",
  "qe_integrated_search": "Integrated Search"
}

export const QUERY_ENGINE_DEFAULT_TYPE = "qe_llm_service"

export type QueryEngine = {
  id: string
  name: string
  archived_at_timestamp: string | null
  archived_by: string
  created_by: string
  created_time: string
  deleted_at_timestamp: string | null
  deleted_by: string
  last_modified_by: string
  last_modified_time: string
  llm_type: string | null
  parent_engine_id: string
  user_id: string
  query_engine_type: string
  description: string
  embedding_type: string
  vector_store: string | null
  is_public: boolean | null
  index_id: string | null
  index_name: string | null
  endpoint: string | null
  doc_url: string | null
  manifest_url: string | null
  // TODO: The params field is used by the ORM object for storing
  // a map of possible keys and values, which is not reflected in the
  // current QueryEngine interface
  params: {
    is_multimodal: string
    // typing for an object with any fields taken from
    // https://stackoverflow.com/questions/42723922
    [key: string]: any
  } | null
  depth_limit: number | null
  chunk_size: number | null
  agents: string[] | null
  child_engines: string[] | null
  is_multimodal: boolean | null
  status?: string | undefined
}

export type QueryEngineBuildParams = {
  depth_limit: string | null
  chunk_size?: string | null
  agents: string | null
  associated_engines: string | null
  manifest_url: string | null
}

export type QueryEngineBuild = {
  user_id: string
  doc_url: string
  query_engine: string
  query_engine_type: string
  llm_type: string
  embedding_type: string
  vector_store: string
  description: string
  params: QueryEngineBuildParams
}

export type QueryEngineBuildJob = {
  id: string
  uuid: string
  name: string
  archived_at_timestamp: string | null
  archived_by: string
  created_by: string
  created_time: string
  deleted_at_timestamp: string | null
  deleted_by: string
  last_modified_by: string
  last_modified_time: string
  type: string
  status: string
  input_data: QueryEngineBuild
  result_data: any
  message: string
  generated_item_id: any
  output_gcs_path: any
  errors: any
  job_logs: any
  metadata: any
}

export interface ChatModel {
  id: string;  // llm_type used in API calls
  name: string; // Display name shown to users
  description?: string;
  purposes?: string[];
  isNew?: boolean;
  isMultimodal?: boolean;
  modelParams?: {
    temperature?: number;
    [key: string]: any;
  };
}

export interface CreateChatRequest {
  prompt: string;
  llm_type?: string;
  stream?: boolean;
  history?: string;
  chat_file?: File;
  chat_file_url?: string;
  tool_names?: string;
  query_engine_id?: string;
  query_filter?: string;
}

export interface GenerateChatRequest {
  prompt: string;
  llm_type?: string;
  stream?: boolean;
  chat_file_b64?: string;
  chat_file_b64_name?: string;
  chat_file_url?: string;
  tool_names?: string[];
  query_engine_id?: string;
  query_filter?: Record<string, any>;
}

