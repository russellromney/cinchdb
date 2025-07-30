'use client';

import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { 
  Database, 
  GitBranch, 
  Table, 
  ChevronRight, 
  ChevronLeft,
  Users, 
  Columns3, 
  Eye,
  Search,
  Plus,
  History,
  Bookmark,
  Code2,
  FileText,
  Sparkles,
  BarChart3,
  Key,
  Hash,
  Type,
  Calendar,
  Toggle
} from 'lucide-react';
import { useCinchDB } from '@/app/lib/cinchdb-context';
import type { TableInfo } from '@cinchdb/client';
import { cn } from '@/lib/utils';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Separator } from '@/components/ui/separator';
import { Input } from '@/components/ui/input';
import { ScrollArea } from '@/components/ui/scroll-area';
import { 
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from '@/components/ui/tooltip';

interface TreeNodeProps {
  label: string;
  icon: React.ReactNode;
  children?: React.ReactNode;
  defaultOpen?: boolean;
  badge?: string;
  level?: number;
  onClick?: () => void;
  isActive?: boolean;
}

const typeIcons = {
  'INTEGER': Hash,
  'TEXT': Type,
  'REAL': BarChart3,
  'BLOB': FileText,
  'NULL': Toggle,
  'DATETIME': Calendar,
  'BOOLEAN': Toggle,
};

function TreeNode({ label, icon, children, defaultOpen = false, badge, level = 0, onClick, isActive }: TreeNodeProps) {
  const [isOpen, setIsOpen] = useState(defaultOpen);
  const hasChildren = Boolean(children);

  return (
    <motion.div
      initial={{ opacity: 0, x: -10 }}
      animate={{ opacity: 1, x: 0 }}
      transition={{ duration: 0.2, delay: level * 0.05 }}
    >
      <Button
        variant="ghost"
        size="sm"
        className={cn(
          "w-full justify-start h-9 px-2 font-normal group hover:bg-muted/50 transition-all",
          level > 0 && `pl-${(level * 4 + 2)}`,
          isActive && "bg-primary/10 text-primary hover:bg-primary/20"
        )}
        onClick={() => {
          if (hasChildren) setIsOpen(!isOpen);
          onClick?.();
        }}
      >
        <AnimatePresence mode="wait">
          {hasChildren && (
            <motion.div 
              className="mr-1"
              initial={{ rotate: 0 }}
              animate={{ rotate: isOpen ? 90 : 0 }}
              transition={{ duration: 0.2 }}
            >
              <ChevronRight className="h-3 w-3" />
            </motion.div>
          )}
        </AnimatePresence>
        <div className="mr-2 group-hover:scale-110 transition-transform">{icon}</div>
        <span className="flex-1 text-left truncate">{label}</span>
        {badge && (
          <Badge variant="secondary" className="ml-auto h-5 px-1.5 text-xs">
            {badge}
          </Badge>
        )}
      </Button>
      <AnimatePresence>
        {isOpen && children && (
          <motion.div 
            className="space-y-0.5 overflow-hidden"
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.2 }}
          >
            {children}
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
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
  
  const [searchQuery, setSearchQuery] = useState('');
  const [isCollapsed, setIsCollapsed] = useState(false);
  const [activeTable, setActiveTable] = useState<string | null>(null);

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
  
  // Filter tables based on search
  const filteredTables = (dbTables: TableInfo[]) => {
    if (!searchQuery) return dbTables;
    return dbTables.filter(table => 
      table.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      table.columns.some(col => col.name.toLowerCase().includes(searchQuery.toLowerCase()))
    );
  };

  return (
    <TooltipProvider>
      <motion.aside 
        className={cn(
          "relative flex flex-col h-full border-r glass transition-all duration-300",
          isCollapsed ? "w-16" : "w-72"
        )}
        initial={false}
        animate={{ width: isCollapsed ? 64 : 288 }}
      >
        {/* Collapse Toggle */}
        <Button
          variant="ghost"
          size="icon"
          className="absolute -right-3 top-20 z-10 h-6 w-6 rounded-full border bg-background shadow-md hover:shadow-lg"
          onClick={() => setIsCollapsed(!isCollapsed)}
        >
          {isCollapsed ? (
            <ChevronRight className="h-3 w-3" />
          ) : (
            <ChevronLeft className="h-3 w-3" />
          )}
        </Button>

        {/* Header */}
        <div className="p-4 space-y-3">
          {!isCollapsed && (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
            >
              <div className="flex items-center justify-between mb-3">
                <h3 className="text-sm font-semibold flex items-center gap-2">
                  <Sparkles className="h-4 w-4 text-primary" />
                  Explorer
                </h3>
                <div className="flex gap-1">
                  <Tooltip>
                    <TooltipTrigger asChild>
                      <Button variant="ghost" size="icon" className="h-7 w-7">
                        <Plus className="h-3.5 w-3.5" />
                      </Button>
                    </TooltipTrigger>
                    <TooltipContent>New Query</TooltipContent>
                  </Tooltip>
                  <Tooltip>
                    <TooltipTrigger asChild>
                      <Button variant="ghost" size="icon" className="h-7 w-7">
                        <History className="h-3.5 w-3.5" />
                      </Button>
                    </TooltipTrigger>
                    <TooltipContent>Query History</TooltipContent>
                  </Tooltip>
                </div>
              </div>
              
              {/* Search */}
              <div className="relative">
                <Search className="absolute left-2 top-2 h-4 w-4 text-muted-foreground" />
                <Input
                  placeholder="Search tables..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="h-8 pl-8 glass border-0"
                />
              </div>
            </motion.div>
          )}
          
          {isCollapsed && (
            <div className="flex flex-col items-center gap-2">
              <Tooltip>
                <TooltipTrigger asChild>
                  <Button variant="ghost" size="icon" className="h-8 w-8">
                    <Search className="h-4 w-4" />
                  </Button>
                </TooltipTrigger>
                <TooltipContent side="right">Search</TooltipContent>
              </Tooltip>
            </div>
          )}
        </div>

        <Separator />

        {/* Content */}
        <ScrollArea className="flex-1 px-4 py-2">
          {!isCollapsed ? (
            <div className="space-y-4">
              {/* Quick Actions */}
              <div className="space-y-1">
                <h4 className="text-xs font-medium text-muted-foreground px-2 mb-2">
                  Quick Actions
                </h4>
                <Button variant="ghost" size="sm" className="w-full justify-start h-9 px-2">
                  <Code2 className="mr-2 h-4 w-4" />
                  New Query
                </Button>
                <Button variant="ghost" size="sm" className="w-full justify-start h-9 px-2">
                  <Bookmark className="mr-2 h-4 w-4" />
                  Saved Queries
                </Button>
                <Button variant="ghost" size="sm" className="w-full justify-start h-9 px-2">
                  <History className="mr-2 h-4 w-4" />
                  Query History
                </Button>
              </div>

              <Separator />

              {/* Schema Explorer */}
              <div className="space-y-1">
                <h4 className="text-xs font-medium text-muted-foreground px-2 mb-2">
                  Database Schema
                </h4>
                {Object.entries(groupedTables).map(([database, dbTables]) => (
                  <TreeNode
                    key={database}
                    label={database}
                    icon={<Database className="h-4 w-4 text-muted-foreground" />}
                    defaultOpen={true}
                    badge={`${filteredTables(dbTables).length}`}
                  >
                    <TreeNode
                      label={currentBranch}
                      icon={<GitBranch className="h-4 w-4 text-muted-foreground" />}
                      defaultOpen={true}
                      level={1}
                    >
                      {filteredTables(dbTables).map((table) => (
                        <TreeNode
                          key={table.name}
                          label={table.name}
                          icon={<Table className="h-4 w-4 text-muted-foreground" />}
                          badge={`${table.columns.length}`}
                          level={2}
                          isActive={activeTable === table.name}
                          onClick={() => setActiveTable(table.name)}
                        >
                          {table.columns.map((column) => {
                            const TypeIcon = typeIcons[column.type as keyof typeof typeIcons] || Type;
                            const isPrimary = column.primaryKey;
                            
                            return (
                              <motion.div
                                key={column.name}
                                className="flex items-center gap-2 pl-12 pr-2 py-1.5 text-xs hover:bg-muted/50 rounded transition-colors group cursor-pointer"
                                whileHover={{ x: 2 }}
                              >
                                <TypeIcon className="h-3 w-3 text-muted-foreground group-hover:text-foreground transition-colors" />
                                <span className="font-mono flex-1">{column.name}</span>
                                {isPrimary && (
                                  <Tooltip>
                                    <TooltipTrigger>
                                      <Key className="h-3 w-3 text-primary" />
                                    </TooltipTrigger>
                                    <TooltipContent>Primary Key</TooltipContent>
                                  </Tooltip>
                                )}
                                <Badge variant="outline" className="h-5 px-1 text-xs font-mono opacity-60 group-hover:opacity-100 transition-opacity">
                                  {column.type}
                                </Badge>
                              </motion.div>
                            );
                          })}
                        </TreeNode>
                      ))}
                    </TreeNode>
                  </TreeNode>
                ))}
              </div>

              <Separator />

              {/* Tenants */}
              <div className="space-y-1">
                <h4 className="text-xs font-medium text-muted-foreground px-2 mb-2">
                  Tenants
                </h4>
                {tenants.map((tenant) => (
                  <Button
                    key={tenant.name}
                    variant={tenant.name === currentTenant ? "secondary" : "ghost"}
                    size="sm"
                    className="w-full justify-start h-9 px-2 font-normal"
                  >
                    <Users className="mr-2 h-4 w-4" />
                    <span className="flex-1 text-left">{tenant.name}</span>
                    {tenant.name === currentTenant && (
                      <Eye className="h-3 w-3 ml-auto" />
                    )}
                  </Button>
                ))}
              </div>
            </div>
          ) : (
            /* Collapsed view */
            <div className="space-y-2">
              <Tooltip>
                <TooltipTrigger asChild>
                  <Button variant="ghost" size="icon" className="w-full">
                    <Code2 className="h-4 w-4" />
                  </Button>
                </TooltipTrigger>
                <TooltipContent side="right">New Query</TooltipContent>
              </Tooltip>
              <Tooltip>
                <TooltipTrigger asChild>
                  <Button variant="ghost" size="icon" className="w-full">
                    <Database className="h-4 w-4" />
                  </Button>
                </TooltipTrigger>
                <TooltipContent side="right">Database</TooltipContent>
              </Tooltip>
              <Tooltip>
                <TooltipTrigger asChild>
                  <Button variant="ghost" size="icon" className="w-full">
                    <History className="h-4 w-4" />
                  </Button>
                </TooltipTrigger>
                <TooltipContent side="right">History</TooltipContent>
              </Tooltip>
            </div>
          )}
        </ScrollArea>
        
        {/* Footer */}
        {!isCollapsed && (
          <div className="p-4 border-t">
            <div className="text-xs space-y-2">
              <div className="flex items-center justify-between text-muted-foreground">
                <span>Tables</span>
                <span className="font-mono font-medium">{tables.length}</span>
              </div>
              <div className="flex items-center justify-between text-muted-foreground">
                <span>Tenants</span>
                <span className="font-mono font-medium">{tenants.length}</span>
              </div>
              <motion.div 
                className="pt-2"
                whileHover={{ scale: 1.02 }}
                whileTap={{ scale: 0.98 }}
              >
                <Button 
                  variant="outline" 
                  size="sm" 
                  className="w-full text-xs gradient-primary text-white border-0"
                >
                  <Sparkles className="mr-2 h-3 w-3" />
                  Upgrade to Pro
                </Button>
              </motion.div>
            </div>
          </div>
        )}
      </motion.aside>
    </TooltipProvider>
  );
}