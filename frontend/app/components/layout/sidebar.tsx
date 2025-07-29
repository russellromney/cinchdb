'use client';

import { useState } from 'react';
import { Database, GitBranch, Table, ChevronRight, ChevronDown, Users } from 'lucide-react';
import { useCinchDB } from '@/app/lib/cinchdb-context';
import type { TableInfo } from '@cinchdb/client';

interface TreeNodeProps {
  label: string;
  icon: React.ReactNode;
  children?: React.ReactNode;
  defaultOpen?: boolean;
}

function TreeNode({ label, icon, children, defaultOpen = false }: TreeNodeProps) {
  const [isOpen, setIsOpen] = useState(defaultOpen);
  const hasChildren = Boolean(children);

  return (
    <div>
      <div
        className={`flex items-center space-x-2 px-2 py-1 rounded cursor-pointer hover:bg-gray-100 ${
          hasChildren ? '' : 'ml-4'
        }`}
        onClick={() => hasChildren && setIsOpen(!isOpen)}
      >
        {hasChildren && (
          <div className="w-4 h-4">
            {isOpen ? (
              <ChevronDown className="w-4 h-4 text-gray-400" />
            ) : (
              <ChevronRight className="w-4 h-4 text-gray-400" />
            )}
          </div>
        )}
        {icon}
        <span className="text-sm">{label}</span>
      </div>
      {isOpen && children && <div className="ml-4">{children}</div>}
    </div>
  );
}

export function Sidebar() {
  const { 
    currentDatabase, 
    currentBranch, 
    tables, 
    tenants,
    currentTenant,
  } = useCinchDB();

  const groupTablesByDatabase = () => {
    const grouped: Record<string, TableInfo[]> = {};
    tables.forEach((table) => {
      if (!grouped[currentDatabase]) {
        grouped[currentDatabase] = [];
      }
      grouped[currentDatabase].push(table);
    });
    return grouped;
  };

  const groupedTables = groupTablesByDatabase();

  return (
    <aside className="w-64 bg-gray-50 border-r border-gray-200 p-4 h-full overflow-y-auto">
      <div className="space-y-4">
        <div>
          <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-2">
            Schema
          </h3>
          <div className="space-y-1">
            {Object.entries(groupedTables).map(([database, dbTables]) => (
              <TreeNode
                key={database}
                label={database}
                icon={<Database className="w-4 h-4 text-gray-500" />}
                defaultOpen={true}
              >
                <TreeNode
                  label={currentBranch}
                  icon={<GitBranch className="w-4 h-4 text-gray-500" />}
                  defaultOpen={true}
                >
                  {dbTables.map((table) => (
                    <TreeNode
                      key={table.name}
                      label={table.name}
                      icon={<Table className="w-4 h-4 text-gray-500" />}
                    >
                      {table.columns.map((column) => (
                        <div
                          key={column.name}
                          className="flex items-center space-x-2 px-2 py-1 ml-4 text-xs text-gray-600"
                        >
                          <span>{column.name}</span>
                          <span className="text-gray-400">({column.type})</span>
                        </div>
                      ))}
                    </TreeNode>
                  ))}
                </TreeNode>
              </TreeNode>
            ))}
          </div>
        </div>

        <div>
          <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-2">
            Tenants
          </h3>
          <div className="space-y-1">
            {tenants.map((tenant) => (
              <div
                key={tenant.name}
                className={`flex items-center space-x-2 px-2 py-1 rounded cursor-pointer hover:bg-gray-100 ${
                  tenant.name === currentTenant ? 'bg-gray-200' : ''
                }`}
              >
                <Users className="w-4 h-4 text-gray-500" />
                <span className="text-sm">{tenant.name}</span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </aside>
  );
}