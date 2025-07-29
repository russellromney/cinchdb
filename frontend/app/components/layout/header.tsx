'use client';

import { LogOut, Database, GitBranch, Users } from 'lucide-react';
import { useCinchDB } from '@/app/lib/cinchdb-context';

export function Header() {
  const { 
    disconnect, 
    currentDatabase, 
    currentBranch, 
    currentTenant,
    databases,
    branches,
    tenants,
    setDatabase,
    setBranch,
    setTenant,
  } = useCinchDB();

  return (
    <header className="bg-white border-b border-gray-200 px-6 py-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-4">
          <h1 className="text-xl font-semibold">CinchDB</h1>
          
          <div className="flex items-center space-x-2">
            <Database className="h-4 w-4 text-gray-500" />
            <select
              value={currentDatabase}
              onChange={(e) => setDatabase(e.target.value)}
              className="text-sm border-gray-300 rounded-md focus:ring-primary focus:border-primary"
            >
              {databases.map((db) => (
                <option key={db.name} value={db.name}>
                  {db.name}
                </option>
              ))}
            </select>
          </div>

          <div className="flex items-center space-x-2">
            <GitBranch className="h-4 w-4 text-gray-500" />
            <select
              value={currentBranch}
              onChange={(e) => setBranch(e.target.value)}
              className="text-sm border-gray-300 rounded-md focus:ring-primary focus:border-primary"
            >
              {branches.map((branch) => (
                <option key={branch.name} value={branch.name}>
                  {branch.name}
                </option>
              ))}
            </select>
          </div>

          <div className="flex items-center space-x-2">
            <Users className="h-4 w-4 text-gray-500" />
            <select
              value={currentTenant}
              onChange={(e) => setTenant(e.target.value)}
              className="text-sm border-gray-300 rounded-md focus:ring-primary focus:border-primary"
            >
              {tenants.map((tenant) => (
                <option key={tenant.name} value={tenant.name}>
                  {tenant.name}
                </option>
              ))}
            </select>
          </div>
        </div>

        <button
          onClick={disconnect}
          className="flex items-center space-x-2 text-sm text-gray-600 hover:text-gray-900"
        >
          <LogOut className="h-4 w-4" />
          <span>Disconnect</span>
        </button>
      </div>
    </header>
  );
}