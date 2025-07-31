/**
 * CinchDB TypeScript SDK - Type Definitions
 */

// Base types
export interface ForeignKeyRef {
  table: string;
  column?: string;
  on_delete?: 'CASCADE' | 'SET NULL' | 'RESTRICT' | 'NO ACTION';
  on_update?: 'CASCADE' | 'SET NULL' | 'RESTRICT' | 'NO ACTION';
}

export interface Column {
  name: string;
  type: 'TEXT' | 'INTEGER' | 'REAL' | 'BLOB' | 'NUMERIC';
  nullable?: boolean;
  default?: string;
  primary_key?: boolean;
  unique?: boolean;
  foreign_key?: ForeignKeyRef;
}

export interface Table {
  name: string;
  columns: Column[];
}

export interface View {
  name: string;
  sql_statement: string;
  sql_length: number;
  description?: string;
}

export interface Database {
  name: string;
  is_active: boolean;
  is_protected: boolean;
  branch_count: number;
}

export interface Branch {
  name: string;
  parent?: string;
  created_at: string;
  is_active: boolean;
  tenant_count: number;
}

export interface Tenant {
  name: string;
  size_bytes: number;
  is_protected: boolean;
}

// API Request/Response types
export interface QueryRequest {
  sql: string;
  limit?: number;
  params?: any[];
}

export interface QueryResult {
  columns: string[];
  rows: any[][];
  row_count: number;
  affected_rows?: number;
  data?: Record<string, any>[];
}

export interface CreateTableRequest {
  name: string;
  columns: Column[];
}

export interface CreateBranchRequest {
  name: string;
  source?: string;
}

export interface CreateTenantRequest {
  name: string;
}

export interface CreateViewRequest {
  name: string;
  sql: string;
  description?: string;
}

export interface UpdateViewRequest {
  sql: string;
  description?: string;
}

export interface AddColumnRequest {
  name: string;
  type: string;
  nullable?: boolean;
  default?: string;
}

export interface RenameColumnRequest {
  old_name: string;
  new_name: string;
}

export interface CopyTableRequest {
  source: string;
  target: string;
  copy_data?: boolean;
}

export interface CopyTenantRequest {
  source: string;
  target: string;
  copy_data?: boolean;
}

export interface MergeCheckResult {
  can_merge: boolean;
  reason?: string;
  merge_type?: string;
  changes_to_merge?: number;
  target_changes?: number;
  conflicts?: any[];
}

export interface MergeResult {
  success: boolean;
  message: string;
  changes_merged?: number;
  merge_type?: string;
  dry_run?: boolean;
  sql_statements?: any[];
}

export interface BranchComparisonResult {
  source_branch: string;
  target_branch: string;
  source_only_changes: number;
  target_only_changes: number;
  common_ancestor?: string;
  can_fast_forward: boolean;
}

// API Key types
export interface APIKey {
  key: string;
  name: string;
  created_at: string;
  permissions: 'read' | 'write';
  branches?: string[];
  active: boolean;
}

export interface CreateAPIKeyRequest {
  name: string;
  permissions?: 'read' | 'write';
  branches?: string[];
}

// Data CRUD types
export interface DataRecord {
  id?: string;
  created_at?: string;
  updated_at?: string;
  [key: string]: any;
}

export interface CreateDataRequest {
  data: Record<string, any>;
}

export interface UpdateDataRequest {
  data: Record<string, any>;
}

export interface BulkCreateRequest {
  records: Record<string, any>[];
}

// Config types
export interface ProjectInfo {
  path: string;
  active_database: string;
  active_branch: string;
  has_api_keys: boolean;
}

// Error response
export interface APIError {
  detail: string;
  status_code?: number;
}

// Code generation types
export interface CodegenLanguage {
  name: string;
  description: string;
}

export interface GenerateModelsRequest {
  language: string;
  include_tables?: boolean;
  include_views?: boolean;
}

export interface TableInfo {
  name: string;
  column_count: number;
  columns: Column[];
}

export interface ColumnInfo extends Column {
  // Extends Column with all properties
}

// Connection options
export interface CinchDBConfig {
  apiUrl: string;
  apiKey: string;
  database?: string;
  branch?: string;
  tenant?: string;
}