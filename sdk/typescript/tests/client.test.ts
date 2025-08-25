/**
 * CinchDB TypeScript SDK Tests
 */

import { CinchDBClient } from '../src/client';
import axios from 'axios';

// Mock axios
jest.mock('axios');
const mockedAxios = axios as jest.Mocked<typeof axios>;

describe('CinchDBClient', () => {
  let client: CinchDBClient;
  const mockConfig = {
    apiUrl: 'http://localhost:8000',
    apiKey: 'test-api-key',
    database: 'testdb',
    branch: 'main',
    tenant: 'main',
  };

  beforeEach(() => {
    // Reset mocks
    jest.clearAllMocks();
    
    // Setup axios create mock
    const mockAxiosInstance = {
      get: jest.fn(),
      post: jest.fn(),
      put: jest.fn(),
      delete: jest.fn(),
      interceptors: {
        request: { use: jest.fn() },
        response: { use: jest.fn() },
      },
    };
    
    mockedAxios.create.mockReturnValue(mockAxiosInstance as any);
    
    client = new CinchDBClient(mockConfig);
  });

  describe('constructor', () => {
    it('should create client with proper configuration', () => {
      expect(mockedAxios.create).toHaveBeenCalledWith({
        baseURL: 'http://localhost:8000/api/v1',
        headers: {
          'X-API-Key': 'test-api-key',
          'Content-Type': 'application/json',
        },
      });
    });
  });

  describe('query operations', () => {
    it('should execute a query', async () => {
      const mockAxiosInstance = mockedAxios.create();
      const mockResponse = {
        data: {
          columns: ['id', 'name'],
          rows: [['1', 'test']],
          row_count: 1,
        },
      };
      
      (mockAxiosInstance.post as jest.Mock).mockResolvedValue(mockResponse);

      const result = await client.query('SELECT * FROM users');
      
      expect(mockAxiosInstance.post).toHaveBeenCalledWith('/query/execute', {
        sql: 'SELECT * FROM users',
        params: undefined,
      });
      
      expect(result).toHaveProperty('columns');
      expect(result).toHaveProperty('rows');
      expect(result).toHaveProperty('data');
      expect(result.data).toEqual([{ id: '1', name: 'test' }]);
    });
  });

  describe('table operations', () => {
    it('should list tables', async () => {
      const mockAxiosInstance = mockedAxios.create();
      const mockResponse = {
        data: [
          { name: 'users', column_count: 3, columns: [] },
          { name: 'posts', column_count: 5, columns: [] },
        ],
      };
      
      (mockAxiosInstance.get as jest.Mock).mockResolvedValue(mockResponse);

      const tables = await client.listTables();
      
      expect(mockAxiosInstance.get).toHaveBeenCalledWith('/tables');
      expect(tables).toHaveLength(2);
      expect(tables[0].name).toBe('users');
    });

    it('should create a table', async () => {
      const mockAxiosInstance = mockedAxios.create();
      (mockAxiosInstance.post as jest.Mock).mockResolvedValue({ data: {} });

      await client.createTable({
        name: 'products',
        columns: [
          { name: 'name', type: 'TEXT', nullable: false },
          { name: 'price', type: 'REAL', nullable: true },
        ],
      });
      
      expect(mockAxiosInstance.post).toHaveBeenCalledWith('/tables', {
        name: 'products',
        columns: [
          { name: 'name', type: 'TEXT', nullable: false },
          { name: 'price', type: 'REAL', nullable: true },
        ],
      });
    });
  });

  describe('data operations', () => {
    it('should insert a record', async () => {
      const mockAxiosInstance = mockedAxios.create();
      const mockResponse = {
        data: {
          id: '123',
          name: 'Test Product',
          price: 99.99,
          created_at: '2024-01-01T00:00:00Z',
          updated_at: '2024-01-01T00:00:00Z',
        },
      };
      
      (mockAxiosInstance.post as jest.Mock).mockResolvedValue(mockResponse);

      const result = await client.insert('products', {
        name: 'Test Product',
        price: 99.99,
      });
      
      expect(mockAxiosInstance.post).toHaveBeenCalledWith('/tables/products/data', {
        data: { name: 'Test Product', price: 99.99 },
      });
      expect(result.id).toBe('123');
    });

    it('should update a record', async () => {
      const mockAxiosInstance = mockedAxios.create();
      const mockResponse = {
        data: {
          id: '123',
          name: 'Updated Product',
          price: 149.99,
          created_at: '2024-01-01T00:00:00Z',
          updated_at: '2024-01-02T00:00:00Z',
        },
      };
      
      (mockAxiosInstance.put as jest.Mock).mockResolvedValue(mockResponse);

      const result = await client.update('products', '123', {
        name: 'Updated Product',
        price: 149.99,
      });
      
      expect(mockAxiosInstance.put).toHaveBeenCalledWith('/tables/products/data/123', {
        data: { name: 'Updated Product', price: 149.99 },
      });
      expect(result.name).toBe('Updated Product');
    });

    it('should delete a record', async () => {
      const mockAxiosInstance = mockedAxios.create();
      (mockAxiosInstance.delete as jest.Mock).mockResolvedValue({ data: {} });

      await client.delete('products', '123');
      
      expect(mockAxiosInstance.delete).toHaveBeenCalledWith('/tables/products/data/123');
    });
  });
  
  describe('insert operations', () => {
    it('should insert a single record', async () => {
      const mockAxiosInstance = mockedAxios.create();
      const mockResponse = {
        data: { id: '123', name: 'Test User', created_at: '2024-01-01' }
      };
      
      (mockAxiosInstance.post as jest.Mock).mockResolvedValue(mockResponse);
      
      const result = await client.insert('users', { name: 'Test User' });
      
      expect(mockAxiosInstance.post).toHaveBeenCalledWith('/tables/users/data', {
        data: { name: 'Test User' }
      });
      expect(result).toHaveProperty('id', '123');
      expect(result).toHaveProperty('name', 'Test User');
    });
    
    it('should insert multiple records using spread operator', async () => {
      const mockAxiosInstance = mockedAxios.create();
      const mockResponse = {
        data: [
          { id: '1', name: 'User 1' },
          { id: '2', name: 'User 2' },
          { id: '3', name: 'User 3' }
        ]
      };
      
      (mockAxiosInstance.post as jest.Mock).mockResolvedValue(mockResponse);
      
      const result = await client.insert('users',
        { name: 'User 1' },
        { name: 'User 2' },
        { name: 'User 3' }
      );
      
      expect(mockAxiosInstance.post).toHaveBeenCalledWith('/tables/users/data/bulk', {
        records: [
          { name: 'User 1' },
          { name: 'User 2' },
          { name: 'User 3' }
        ]
      });
      expect(result).toHaveLength(3);
      expect((result as any[])[0]).toHaveProperty('id', '1');
      expect((result as any[])[2]).toHaveProperty('name', 'User 3');
    });
    
    it('should insert array using spread operator', async () => {
      const mockAxiosInstance = mockedAxios.create();
      const mockResponse = {
        data: [
          { id: '1', name: 'Alice' },
          { id: '2', name: 'Bob' }
        ]
      };
      
      (mockAxiosInstance.post as jest.Mock).mockResolvedValue(mockResponse);
      
      const users = [
        { name: 'Alice' },
        { name: 'Bob' }
      ];
      
      const result = await client.insert('users', ...users);
      
      expect(mockAxiosInstance.post).toHaveBeenCalledWith('/tables/users/data/bulk', {
        records: users
      });
      expect(result).toHaveLength(2);
    });
    
    it('should throw error when no data provided', async () => {
      await expect(client.insert('users')).rejects.toThrow('At least one record must be provided');
    });
  });
});