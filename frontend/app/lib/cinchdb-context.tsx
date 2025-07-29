'use client';

import React, { createContext, useContext, useState, useCallback, ReactNode } from 'react';
import { CinchDBClient } from '@cinchdb/client';
import type { Database, Branch, Tenant, TableInfo } from '@cinchdb/client';

interface CinchDBContextValue {
  client: CinchDBClient | null;
  connected: boolean;
  connecting: boolean;
  error: string | null;
  
  // Connection
  connect: (apiKey: string, apiUrl?: string) => Promise<void>;
  disconnect: () => void;
  
  // Current context
  currentDatabase: string;
  currentBranch: string;
  currentTenant: string;
  
  // Data
  databases: Database[];
  branches: Branch[];
  tenants: Tenant[];
  tables: TableInfo[];
  
  // Context switching
  setDatabase: (database: string) => Promise<void>;
  setBranch: (branch: string) => Promise<void>;
  setTenant: (tenant: string) => Promise<void>;
  
  // Data refresh
  refreshDatabases: () => Promise<void>;
  refreshBranches: () => Promise<void>;
  refreshTenants: () => Promise<void>;
  refreshTables: () => Promise<void>;
}

const CinchDBContext = createContext<CinchDBContextValue | null>(null);

export function CinchDBProvider({ children }: { children: ReactNode }) {
  const [client, setClient] = useState<CinchDBClient | null>(null);
  const [connected, setConnected] = useState(false);
  const [connecting, setConnecting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  
  const [currentDatabase, setCurrentDatabase] = useState('');
  const [currentBranch, setCurrentBranch] = useState('');
  const [currentTenant, setCurrentTenant] = useState('');
  
  const [databases, setDatabases] = useState<Database[]>([]);
  const [branches, setBranches] = useState<Branch[]>([]);
  const [tenants, setTenants] = useState<Tenant[]>([]);
  const [tables, setTables] = useState<TableInfo[]>([]);

  const connect = useCallback(async (apiKey: string, apiUrl?: string) => {
    setConnecting(true);
    setError(null);
    
    try {
      const newClient = new CinchDBClient({
        apiKey,
        apiUrl: apiUrl || 'http://localhost:8000',
      });
      
      // Test connection by fetching databases
      const dbs = await newClient.listDatabases();
      
      setClient(newClient);
      setDatabases(dbs);
      setConnected(true);
      
      // Set default database if available
      if (dbs.length > 0) {
        const defaultDb = dbs.find(db => db.name === 'main') || dbs[0];
        setCurrentDatabase(defaultDb.name);
        
        // Set database context first
        await newClient.setActiveDatabase(defaultDb.name);
        
        // Fetch branches for default database
        const branchList = await newClient.listBranches();
        setBranches(branchList);
        
        if (branchList.length > 0) {
          const defaultBranch = branchList.find(b => b.name === 'main') || branchList[0];
          setCurrentBranch(defaultBranch.name);
          
          // Set context and fetch initial data
          await newClient.setActiveBranch(defaultBranch.name);
          
          const [tenantList, tableList] = await Promise.all([
            newClient.listTenants(),
            newClient.listTables(),
          ]);
          
          setTenants(tenantList);
          setTables(tableList);
          
          // Set default tenant
          if (tenantList.length > 0) {
            const defaultTenant = tenantList.find(t => t.name === 'main') || tenantList[0];
            setCurrentTenant(defaultTenant.name);
          }
        }
      }
      
      // Store API key in localStorage
      localStorage.setItem('cinchdb_api_key', apiKey);
      if (apiUrl) {
        localStorage.setItem('cinchdb_api_url', apiUrl);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to connect');
      setConnected(false);
    } finally {
      setConnecting(false);
    }
  }, []);

  const disconnect = useCallback(() => {
    setClient(null);
    setConnected(false);
    setCurrentDatabase('');
    setCurrentBranch('');
    setCurrentTenant('');
    setDatabases([]);
    setBranches([]);
    setTenants([]);
    setTables([]);
    localStorage.removeItem('cinchdb_api_key');
    localStorage.removeItem('cinchdb_api_url');
  }, []);

  const setDatabase = useCallback(async (database: string) => {
    if (!client) return;
    
    try {
      setCurrentDatabase(database);
      await client.setActiveDatabase(database);
      const branchList = await client.listBranches();
      setBranches(branchList);
      
      if (branchList.length > 0) {
        const defaultBranch = branchList.find(b => b.name === 'main') || branchList[0];
        await setBranch(defaultBranch.name);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to switch database');
    }
  }, [client]);

  const setBranch = useCallback(async (branch: string) => {
    if (!client || !currentDatabase) return;
    
    try {
      setCurrentBranch(branch);
      await client.setActiveBranch(branch);
      
      // Refresh data for new context
      const [tenantList, tableList] = await Promise.all([
        client.listTenants(),
        client.listTables(),
      ]);
      
      setTenants(tenantList);
      setTables(tableList);
      
      // Reset to main tenant
      if (tenantList.length > 0) {
        const defaultTenant = tenantList.find(t => t.name === 'main') || tenantList[0];
        setCurrentTenant(defaultTenant.name);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to switch branch');
    }
  }, [client, currentDatabase]);

  const setTenant = useCallback(async (tenant: string) => {
    if (!client) return;
    
    try {
      setCurrentTenant(tenant);
      
      // Note: Tenant switching is handled at query time, not as a context switch
      // Just update the UI state
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to switch tenant');
    }
  }, [client]);

  const refreshDatabases = useCallback(async () => {
    if (!client) return;
    
    try {
      const dbs = await client.listDatabases();
      setDatabases(dbs);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to refresh databases');
    }
  }, [client]);

  const refreshBranches = useCallback(async () => {
    if (!client || !currentDatabase) return;
    
    try {
      const branchList = await client.listBranches();
      setBranches(branchList);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to refresh branches');
    }
  }, [client, currentDatabase]);

  const refreshTenants = useCallback(async () => {
    if (!client) return;
    
    try {
      const tenantList = await client.listTenants();
      setTenants(tenantList);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to refresh tenants');
    }
  }, [client]);

  const refreshTables = useCallback(async () => {
    if (!client) return;
    
    try {
      const tableList = await client.listTables();
      setTables(tableList);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to refresh tables');
    }
  }, [client]);

  const value: CinchDBContextValue = {
    client,
    connected,
    connecting,
    error,
    connect,
    disconnect,
    currentDatabase,
    currentBranch,
    currentTenant,
    databases,
    branches,
    tenants,
    tables,
    setDatabase,
    setBranch,
    setTenant,
    refreshDatabases,
    refreshBranches,
    refreshTenants,
    refreshTables,
  };

  return (
    <CinchDBContext.Provider value={value}>
      {children}
    </CinchDBContext.Provider>
  );
}

export function useCinchDB() {
  const context = useContext(CinchDBContext);
  if (!context) {
    throw new Error('useCinchDB must be used within a CinchDBProvider');
  }
  return context;
}