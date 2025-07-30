'use client';

import { useEffect, useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Command } from 'cmdk';
import { 
  Search, 
  Database, 
  GitBranch, 
  Table, 
  Code2, 
  History, 
  Bookmark,
  Settings,
  Moon,
  Sun,
  Monitor,
  Users,
  LogOut,
  FileText,
  Plus,
  ChevronRight,
  Sparkles
} from 'lucide-react';
import { useCinchDB } from '@/app/lib/cinchdb-context';
import { useTheme } from '@/app/lib/theme-provider';
import { useRouter } from 'next/navigation';
import { Badge } from '@/components/ui/badge';

export function CommandPalette() {
  const [open, setOpen] = useState(false);
  const [search, setSearch] = useState('');
  const router = useRouter();
  const { 
    databases, 
    tables, 
    currentDatabase, 
    setDatabase,
    currentBranch,
    branches,
    setBranch,
    disconnect
  } = useCinchDB();
  const { theme, setTheme } = useTheme();

  // Toggle command palette with Cmd+K
  useEffect(() => {
    const down = (e: KeyboardEvent) => {
      if (e.key === 'k' && (e.metaKey || e.ctrlKey)) {
        e.preventDefault();
        setOpen((open) => !open);
      }
    };

    document.addEventListener('keydown', down);
    return () => document.removeEventListener('keydown', down);
  }, []);

  const runCommand = (command: () => void) => {
    setOpen(false);
    command();
  };

  return (
    <AnimatePresence>
      {open && (
        <>
          {/* Backdrop */}
          <motion.div
            className="fixed inset-0 bg-background/80 backdrop-blur-sm z-50"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={() => setOpen(false)}
          />
          
          {/* Command palette */}
          <motion.div
            className="fixed inset-x-0 top-20 z-50 mx-auto max-w-2xl"
            initial={{ opacity: 0, scale: 0.95, y: -20 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.95, y: -20 }}
            transition={{ duration: 0.2 }}
          >
            <Command className="glass border shadow-2xl rounded-xl overflow-hidden">
              <div className="flex items-center gap-3 px-4 py-3 border-b">
                <Search className="h-5 w-5 text-muted-foreground" />
                <Command.Input
                  value={search}
                  onValueChange={setSearch}
                  placeholder="Type a command or search..."
                  className="flex-1 bg-transparent outline-none placeholder:text-muted-foreground"
                />
                <kbd className="px-2 py-1 text-xs font-mono bg-muted rounded">ESC</kbd>
              </div>
              
              <Command.List className="max-h-[400px] overflow-y-auto p-2">
                <Command.Empty className="flex flex-col items-center justify-center py-8 text-center">
                  <Sparkles className="h-8 w-8 text-muted-foreground mb-2" />
                  <p className="text-sm text-muted-foreground">No results found.</p>
                </Command.Empty>

                {/* Databases */}
                <Command.Group heading="Databases">
                  {databases.map((db) => (
                    <Command.Item
                      key={db.name}
                      value={`database-${db.name}`}
                      onSelect={() => runCommand(() => setDatabase(db.name))}
                      className="flex items-center gap-3 px-3 py-2 rounded-lg hover:bg-muted/50 cursor-pointer transition-colors"
                    >
                      <Database className="h-4 w-4 text-muted-foreground" />
                      <span className="flex-1">{db.name}</span>
                      {db.name === currentDatabase && (
                        <Badge variant="secondary" className="text-xs">Active</Badge>
                      )}
                    </Command.Item>
                  ))}
                </Command.Group>

                <Command.Separator className="my-2" />

                {/* Branches */}
                <Command.Group heading="Branches">
                  {branches.map((branch) => (
                    <Command.Item
                      key={branch.name}
                      value={`branch-${branch.name}`}
                      onSelect={() => runCommand(() => setBranch(branch.name))}
                      className="flex items-center gap-3 px-3 py-2 rounded-lg hover:bg-muted/50 cursor-pointer transition-colors"
                    >
                      <GitBranch className="h-4 w-4 text-muted-foreground" />
                      <span className="flex-1">{branch.name}</span>
                      {branch.name === currentBranch && (
                        <Badge variant="secondary" className="text-xs">Active</Badge>
                      )}
                    </Command.Item>
                  ))}
                </Command.Group>

                <Command.Separator className="my-2" />

                {/* Tables */}
                <Command.Group heading="Tables">
                  {tables.slice(0, 5).map((table) => (
                    <Command.Item
                      key={table.name}
                      value={`table-${table.name}`}
                      onSelect={() => runCommand(() => {
                        // Could open table in query editor
                        console.log('Selected table:', table.name);
                      })}
                      className="flex items-center gap-3 px-3 py-2 rounded-lg hover:bg-muted/50 cursor-pointer transition-colors"
                    >
                      <Table className="h-4 w-4 text-muted-foreground" />
                      <span className="flex-1 font-mono text-sm">{table.name}</span>
                      <span className="text-xs text-muted-foreground">
                        {table.columns.length} columns
                      </span>
                    </Command.Item>
                  ))}
                  {tables.length > 5 && (
                    <Command.Item
                      value="view-all-tables"
                      className="flex items-center gap-3 px-3 py-2 rounded-lg hover:bg-muted/50 cursor-pointer transition-colors text-primary"
                    >
                      <ChevronRight className="h-4 w-4" />
                      <span>View all {tables.length} tables</span>
                    </Command.Item>
                  )}
                </Command.Group>

                <Command.Separator className="my-2" />

                {/* Actions */}
                <Command.Group heading="Actions">
                  <Command.Item
                    value="new-query"
                    onSelect={() => runCommand(() => {
                      console.log('New query');
                    })}
                    className="flex items-center gap-3 px-3 py-2 rounded-lg hover:bg-muted/50 cursor-pointer transition-colors"
                  >
                    <Code2 className="h-4 w-4 text-muted-foreground" />
                    <span className="flex-1">New Query</span>
                    <kbd className="px-1.5 py-0.5 text-xs font-mono bg-muted rounded">⌘N</kbd>
                  </Command.Item>
                  
                  <Command.Item
                    value="query-history"
                    onSelect={() => runCommand(() => {
                      console.log('Query history');
                    })}
                    className="flex items-center gap-3 px-3 py-2 rounded-lg hover:bg-muted/50 cursor-pointer transition-colors"
                  >
                    <History className="h-4 w-4 text-muted-foreground" />
                    <span className="flex-1">Query History</span>
                    <kbd className="px-1.5 py-0.5 text-xs font-mono bg-muted rounded">⌘H</kbd>
                  </Command.Item>
                  
                  <Command.Item
                    value="saved-queries"
                    onSelect={() => runCommand(() => {
                      console.log('Saved queries');
                    })}
                    className="flex items-center gap-3 px-3 py-2 rounded-lg hover:bg-muted/50 cursor-pointer transition-colors"
                  >
                    <Bookmark className="h-4 w-4 text-muted-foreground" />
                    <span className="flex-1">Saved Queries</span>
                    <kbd className="px-1.5 py-0.5 text-xs font-mono bg-muted rounded">⌘B</kbd>
                  </Command.Item>
                </Command.Group>

                <Command.Separator className="my-2" />

                {/* Settings */}
                <Command.Group heading="Settings">
                  <Command.Item
                    value="theme-light"
                    onSelect={() => runCommand(() => setTheme('light'))}
                    className="flex items-center gap-3 px-3 py-2 rounded-lg hover:bg-muted/50 cursor-pointer transition-colors"
                  >
                    <Sun className="h-4 w-4 text-muted-foreground" />
                    <span className="flex-1">Light Theme</span>
                    {theme === 'light' && (
                      <Badge variant="secondary" className="text-xs">Active</Badge>
                    )}
                  </Command.Item>
                  
                  <Command.Item
                    value="theme-dark"
                    onSelect={() => runCommand(() => setTheme('dark'))}
                    className="flex items-center gap-3 px-3 py-2 rounded-lg hover:bg-muted/50 cursor-pointer transition-colors"
                  >
                    <Moon className="h-4 w-4 text-muted-foreground" />
                    <span className="flex-1">Dark Theme</span>
                    {theme === 'dark' && (
                      <Badge variant="secondary" className="text-xs">Active</Badge>
                    )}
                  </Command.Item>
                  
                  <Command.Item
                    value="theme-system"
                    onSelect={() => runCommand(() => setTheme('system'))}
                    className="flex items-center gap-3 px-3 py-2 rounded-lg hover:bg-muted/50 cursor-pointer transition-colors"
                  >
                    <Monitor className="h-4 w-4 text-muted-foreground" />
                    <span className="flex-1">System Theme</span>
                    {theme === 'system' && (
                      <Badge variant="secondary" className="text-xs">Active</Badge>
                    )}
                  </Command.Item>
                  
                  <Command.Item
                    value="settings"
                    onSelect={() => runCommand(() => {
                      console.log('Open settings');
                    })}
                    className="flex items-center gap-3 px-3 py-2 rounded-lg hover:bg-muted/50 cursor-pointer transition-colors"
                  >
                    <Settings className="h-4 w-4 text-muted-foreground" />
                    <span className="flex-1">Settings</span>
                    <kbd className="px-1.5 py-0.5 text-xs font-mono bg-muted rounded">⌘,</kbd>
                  </Command.Item>
                </Command.Group>

                <Command.Separator className="my-2" />

                {/* Other */}
                <Command.Group heading="Other">
                  <Command.Item
                    value="documentation"
                    onSelect={() => runCommand(() => {
                      window.open('https://docs.cinchdb.com', '_blank');
                    })}
                    className="flex items-center gap-3 px-3 py-2 rounded-lg hover:bg-muted/50 cursor-pointer transition-colors"
                  >
                    <FileText className="h-4 w-4 text-muted-foreground" />
                    <span className="flex-1">Documentation</span>
                  </Command.Item>
                  
                  <Command.Item
                    value="disconnect"
                    onSelect={() => runCommand(() => {
                      disconnect();
                      router.push('/');
                    })}
                    className="flex items-center gap-3 px-3 py-2 rounded-lg hover:bg-muted/50 cursor-pointer transition-colors text-destructive"
                  >
                    <LogOut className="h-4 w-4" />
                    <span className="flex-1">Disconnect</span>
                  </Command.Item>
                </Command.Group>
              </Command.List>
            </Command>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  );
}