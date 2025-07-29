/**
 * CinchDB TypeScript SDK - API Client
 */

import axios, { AxiosInstance, AxiosRequestConfig } from 'axios';
import {
  CinchDBConfig,
  Database,
  Branch,
  Tenant,
  Table,
  Column,
  View,
  QueryRequest,
  QueryResult,
  CreateTableRequest,
  CreateBranchRequest,
  CreateTenantRequest,
  CreateViewRequest,
  UpdateViewRequest,
  AddColumnRequest,
  RenameColumnRequest,
  CopyTableRequest,
  CopyTenantRequest,
  MergeCheckResult,
  MergeResult,
  BranchComparisonResult,
  APIKey,
  CreateAPIKeyRequest,
  DataRecord,
  CreateDataRequest,
  UpdateDataRequest,
  BulkCreateRequest,
  ProjectInfo,
  CodegenLanguage,
  GenerateModelsRequest,
  TableInfo,
  ColumnInfo,
} from './types';

export class CinchDBClient {
  private client: AxiosInstance;
  private config: CinchDBConfig;

  constructor(config: CinchDBConfig) {
    this.config = {
      database: 'main',
      branch: 'main',
      tenant: 'main',
      ...config,
    };

    this.client = axios.create({
      baseURL: `${config.apiUrl}/api/v1`,
      headers: {
        'X-API-Key': config.apiKey,
        'Content-Type': 'application/json',
      },
    });

    // Add request interceptor to add default params
    this.client.interceptors.request.use((config) => {
      if (!config.params) {
        config.params = {};
      }
      
      // Add default database and branch if not specified
      if (this.config.database && !config.params.database) {
        config.params.database = this.config.database;
      }
      if (this.config.branch && !config.params.branch) {
        config.params.branch = this.config.branch;
      }
      
      // Add tenant for specific endpoints
      if (this.needsTenant(config.url || '') && this.config.tenant && !config.params.tenant) {
        config.params.tenant = this.config.tenant;
      }
      
      return config;
    });

    // Add response interceptor for error handling
    this.client.interceptors.response.use(
      (response) => response,
      (error) => {
        if (error.response?.data?.detail) {
          const message = error.response.data.detail;
          const newError = new Error(message);
          (newError as any).status = error.response.status;
          throw newError;
        }
        throw error;
      }
    );
  }

  private needsTenant(url: string): boolean {
    return url.includes('/query') || url.includes('/data') || url.includes('/tenants');
  }

  // Project operations
  async getProjectInfo(): Promise<ProjectInfo> {
    const response = await this.client.get('/projects/info');
    return response.data;
  }

  async setActiveDatabase(database: string): Promise<void> {
    await this.client.put('/projects/active', { database });
    this.config.database = database;
  }

  async setActiveBranch(branch: string): Promise<void> {
    await this.client.put('/projects/active', { branch });
    this.config.branch = branch;
  }

  // Database operations
  async listDatabases(): Promise<Database[]> {
    const response = await this.client.get('/databases');
    return response.data;
  }

  async createDatabase(name: string, switchTo?: boolean): Promise<void> {
    await this.client.post('/databases', { name, switch: switchTo });
    if (switchTo) {
      this.config.database = name;
    }
  }

  async deleteDatabase(name: string): Promise<void> {
    await this.client.delete(`/databases/${name}`);
  }

  async getDatabaseInfo(name: string): Promise<Database> {
    const response = await this.client.get(`/databases/${name}`);
    return response.data;
  }

  // Branch operations
  async listBranches(): Promise<Branch[]> {
    const response = await this.client.get('/branches');
    return response.data;
  }

  async createBranch(request: CreateBranchRequest): Promise<void> {
    await this.client.post('/branches', request);
  }

  async deleteBranch(name: string): Promise<void> {
    await this.client.delete(`/branches/${name}`);
  }

  async switchBranch(name: string): Promise<void> {
    await this.client.put(`/branches/switch/${name}`);
    this.config.branch = name;
  }

  async compareBranches(source: string, target: string): Promise<BranchComparisonResult> {
    const response = await this.client.get(`/branches/${source}/compare/${target}`);
    return response.data;
  }

  async canMergeBranches(source: string, target: string): Promise<MergeCheckResult> {
    const response = await this.client.get(`/branches/${source}/can-merge/${target}`);
    return response.data;
  }

  async mergeBranches(source: string, target: string, force?: boolean, dryRun?: boolean): Promise<MergeResult> {
    const response = await this.client.post(`/branches/${source}/merge/${target}`, null, {
      params: { force, dry_run: dryRun }
    });
    return response.data;
  }

  async mergeIntoMain(source: string, force?: boolean, dryRun?: boolean): Promise<MergeResult> {
    const response = await this.client.post(`/branches/${source}/merge-into-main`, null, {
      params: { force, dry_run: dryRun }
    });
    return response.data;
  }

  // Tenant operations
  async listTenants(): Promise<Tenant[]> {
    const response = await this.client.get('/tenants');
    return response.data;
  }

  async createTenant(request: CreateTenantRequest): Promise<void> {
    await this.client.post('/tenants', request);
  }

  async deleteTenant(name: string): Promise<void> {
    await this.client.delete(`/tenants/${name}`);
  }

  async renameTenant(oldName: string, newName: string): Promise<void> {
    await this.client.put(`/tenants/${oldName}/rename`, { new_name: newName });
  }

  async copyTenant(request: CopyTenantRequest): Promise<void> {
    await this.client.post('/tenants/copy', request);
  }

  // Table operations
  async listTables(): Promise<TableInfo[]> {
    const response = await this.client.get('/tables');
    return response.data;
  }

  async createTable(request: CreateTableRequest): Promise<void> {
    await this.client.post('/tables', request);
  }

  async deleteTable(name: string): Promise<void> {
    await this.client.delete(`/tables/${name}`);
  }

  async copyTable(request: CopyTableRequest): Promise<void> {
    await this.client.post('/tables/copy', request);
  }

  async getTableInfo(name: string): Promise<TableInfo> {
    const response = await this.client.get(`/tables/${name}`);
    return response.data;
  }

  // Column operations
  async listColumns(table: string): Promise<ColumnInfo[]> {
    const response = await this.client.get(`/columns/${table}/columns`);
    return response.data;
  }

  async addColumn(table: string, request: AddColumnRequest): Promise<void> {
    await this.client.post(`/columns/${table}/columns`, request);
  }

  async dropColumn(table: string, column: string): Promise<void> {
    await this.client.delete(`/columns/${table}/columns/${column}`);
  }

  async renameColumn(table: string, request: RenameColumnRequest): Promise<void> {
    await this.client.put(`/columns/${table}/columns/rename`, request);
  }

  async getColumnInfo(table: string, column: string): Promise<ColumnInfo> {
    const response = await this.client.get(`/columns/${table}/columns/${column}`);
    return response.data;
  }

  // View operations
  async listViews(): Promise<View[]> {
    const response = await this.client.get('/views');
    return response.data;
  }

  async createView(request: CreateViewRequest): Promise<void> {
    await this.client.post('/views', request);
  }

  async updateView(name: string, request: UpdateViewRequest): Promise<void> {
    await this.client.put(`/views/${name}`, request);
  }

  async deleteView(name: string): Promise<void> {
    await this.client.delete(`/views/${name}`);
  }

  async getViewInfo(name: string): Promise<View> {
    const response = await this.client.get(`/views/${name}`);
    return response.data;
  }

  // Query operations
  async query(sql: string, params?: any[]): Promise<QueryResult> {
    const request: QueryRequest = { sql, params };
    const response = await this.client.post('/query/execute', request);
    const result = response.data;
    
    // Transform rows to records format if needed
    if (result.columns && result.rows) {
      result.data = result.rows.map((row: any[]) => {
        const record: Record<string, any> = {};
        result.columns.forEach((col: string, idx: number) => {
          record[col] = row[idx];
        });
        return record;
      });
    }
    
    return result;
  }

  // Data CRUD operations
  async getTableData(table: string, limit?: number, offset?: number): Promise<DataRecord[]> {
    const response = await this.client.get(`/tables/${table}/data`, {
      params: { limit, offset }
    });
    return response.data;
  }

  async getRecord(table: string, id: string): Promise<DataRecord> {
    const response = await this.client.get(`/tables/${table}/data/${id}`);
    return response.data;
  }

  async createRecord(table: string, data: Record<string, any>): Promise<DataRecord> {
    const response = await this.client.post(`/tables/${table}/data`, { data });
    return response.data;
  }

  async updateRecord(table: string, id: string, data: Record<string, any>): Promise<DataRecord> {
    const response = await this.client.put(`/tables/${table}/data/${id}`, { data });
    return response.data;
  }

  async deleteRecord(table: string, id: string): Promise<void> {
    await this.client.delete(`/tables/${table}/data/${id}`);
  }

  async bulkCreateRecords(table: string, records: Record<string, any>[]): Promise<DataRecord[]> {
    const response = await this.client.post(`/tables/${table}/data/bulk`, { records });
    return response.data;
  }

  async countRecords(table: string, filters?: Record<string, any>): Promise<number> {
    const response = await this.client.get(`/tables/${table}/data/count`, { params: filters });
    return response.data.count;
  }

  // API Key operations
  async listAPIKeys(): Promise<APIKey[]> {
    const response = await this.client.get('/auth/keys');
    return response.data;
  }

  async createAPIKey(request: CreateAPIKeyRequest): Promise<APIKey> {
    const response = await this.client.post('/auth/keys', request);
    return response.data;
  }

  async revokeAPIKey(key: string): Promise<void> {
    await this.client.delete(`/auth/keys/${key}`);
  }

  async getCurrentAPIKeyInfo(): Promise<APIKey> {
    const response = await this.client.get('/auth/me');
    return response.data;
  }

  // Code generation
  async listCodegenLanguages(): Promise<CodegenLanguage[]> {
    const response = await this.client.get('/codegen/languages');
    return response.data;
  }

  async generateModels(request: GenerateModelsRequest): Promise<Record<string, string>> {
    const response = await this.client.post('/codegen/generate/files', request);
    return response.data;
  }

  async getCodegenInfo(): Promise<any> {
    const response = await this.client.get('/codegen/info');
    return response.data;
  }

  // Helper methods for context switching
  switchDatabase(database: string): CinchDBClient {
    return new CinchDBClient({
      ...this.config,
      database,
    });
  }

  switchBranchContext(branch: string): CinchDBClient {
    return new CinchDBClient({
      ...this.config,
      branch,
    });
  }

  switchTenant(tenant: string): CinchDBClient {
    return new CinchDBClient({
      ...this.config,
      tenant,
    });
  }

  // Convenience methods matching Python SDK
  async insert(table: string, data: Record<string, any>): Promise<DataRecord> {
    return this.createRecord(table, data);
  }

  async update(table: string, id: string, data: Record<string, any>): Promise<DataRecord> {
    return this.updateRecord(table, id, data);
  }

  async delete(table: string, id: string): Promise<void> {
    return this.deleteRecord(table, id);
  }
}