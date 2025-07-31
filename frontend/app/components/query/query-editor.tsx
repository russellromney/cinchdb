'use client';

import { useState, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import CodeMirror from '@uiw/react-codemirror';
import { sql } from '@codemirror/lang-sql';
import { oneDark } from '@codemirror/theme-one-dark';
import { EditorView } from '@codemirror/view';
import { 
  Play, 
  Trash2, 
  Loader2, 
  Code2, 
  History, 
  Save,
  Download,
  Copy,
  CheckCircle,
  Plus,
  X,
  Sparkles,
  Terminal,
  Timer,
  Database,
  GitBranch,
  AlertTriangle,
  Shield
} from 'lucide-react';
import { useCinchDB } from '@/app/lib/cinchdb-context';
import { useTheme } from '@/app/lib/theme-provider';
import type { QueryResult } from '@cinchdb/client';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from '@/components/ui/tooltip';
import { toast } from 'sonner';
import { validateSQLQuery, getValidationErrorMessage } from '@/app/lib/sql-validator';

interface QueryTab {
  id: string;
  name: string;
  query: string;
  isDirty: boolean;
}

interface QueryEditorProps {
  onResults: (results: QueryResult) => void;
  onError: (error: string) => void;
}

const defaultQuery = `-- Welcome to CinchDB Query Editor
-- Try running this query to see all tables in your database

SELECT name, type, sql 
FROM sqlite_master 
WHERE type = 'table'
ORDER BY name;`;

// Light theme for CodeMirror
const lightTheme = EditorView.theme({
  '&': {
    color: 'hsl(var(--foreground))',
    backgroundColor: 'hsl(var(--background))'
  },
  '.cm-content': {
    caretColor: 'hsl(var(--foreground))'
  },
  '.cm-cursor, .cm-dropCursor': {
    borderLeftColor: 'hsl(var(--foreground))'
  },
  '&.cm-focused .cm-selectionBackground, .cm-selectionBackground, .cm-content ::selection': {
    backgroundColor: 'hsl(var(--primary) / 0.2)'
  },
  '.cm-gutters': {
    backgroundColor: 'hsl(var(--muted))',
    color: 'hsl(var(--muted-foreground))',
    border: 'none'
  },
  '.cm-activeLineGutter': {
    backgroundColor: 'hsl(var(--muted))'
  },
  '.cm-foldGutter': {
    color: 'hsl(var(--muted-foreground))'
  },
  '.cm-line': {
    color: 'hsl(var(--foreground))'
  }
});

export function QueryEditor({ onResults, onError }: QueryEditorProps) {
  const { client, currentDatabase, currentBranch, currentTenant } = useCinchDB();
  const { theme } = useTheme();
  const [executing, setExecuting] = useState(false);
  const [copied, setCopied] = useState(false);
  const [executionTime, setExecutionTime] = useState<number | null>(null);
  const [queryValidation, setQueryValidation] = useState<{ isValid: boolean; error?: string } | null>(null);
  
  // Tab management
  const [tabs, setTabs] = useState<QueryTab[]>([
    { id: '1', name: 'Query 1', query: defaultQuery, isDirty: false }
  ]);
  const [activeTab, setActiveTab] = useState('1');
  
  const activeQuery = tabs.find(tab => tab.id === activeTab);

  const addNewTab = () => {
    const newId = Date.now().toString();
    const newTab = {
      id: newId,
      name: `Query ${tabs.length + 1}`,
      query: '',
      isDirty: false
    };
    setTabs([...tabs, newTab]);
    setActiveTab(newId);
  };

  const closeTab = (tabId: string) => {
    if (tabs.length === 1) {
      toast.error('Cannot close the last tab');
      return;
    }
    
    const tabIndex = tabs.findIndex(tab => tab.id === tabId);
    const newTabs = tabs.filter(tab => tab.id !== tabId);
    setTabs(newTabs);
    
    if (activeTab === tabId) {
      const newActiveIndex = Math.max(0, tabIndex - 1);
      setActiveTab(newTabs[newActiveIndex].id);
    }
  };

  const updateQuery = (value: string) => {
    setTabs(tabs.map(tab => 
      tab.id === activeTab 
        ? { ...tab, query: value, isDirty: true }
        : tab
    ));
    
    // Validate query in real-time for user feedback
    if (value.trim()) {
      const validation = validateSQLQuery(value);
      setQueryValidation(validation);
    } else {
      setQueryValidation(null);
    }
  };

  const executeQuery = async () => {
    if (!client || !activeQuery?.query.trim()) return;

    // Validate the query before execution
    const validation = validateSQLQuery(activeQuery.query);
    if (!validation.isValid) {
      const errorMessage = getValidationErrorMessage(validation);
      onError(errorMessage);
      toast.error(errorMessage);
      return;
    }

    setExecuting(true);
    onError('');
    const startTime = performance.now();

    try {
      const result = await client.query(activeQuery.query);
      const endTime = performance.now();
      setExecutionTime(Math.round(endTime - startTime));
      onResults(result);
      toast.success(`Query executed successfully in ${Math.round(endTime - startTime)}ms`);
    } catch (err) {
      onError(err instanceof Error ? err.message : 'Query execution failed');
      toast.error('Query execution failed');
    } finally {
      setExecuting(false);
    }
  };

  const clearQuery = () => {
    updateQuery('');
    onResults({ columns: [], rows: [], row_count: 0, data: [] });
    onError('');
    setExecutionTime(null);
  };

  const copyQuery = async () => {
    if (!activeQuery?.query) return;
    
    await navigator.clipboard.writeText(activeQuery.query);
    setCopied(true);
    toast.success('Query copied to clipboard');
    setTimeout(() => setCopied(false), 2000);
  };

  const saveQuery = () => {
    // This would save to backend in real implementation
    toast.success('Query saved successfully');
    setTabs(tabs.map(tab => 
      tab.id === activeTab 
        ? { ...tab, isDirty: false }
        : tab
    ));
  };

  // Keyboard shortcuts
  const handleKeyDown = useCallback((e: React.KeyboardEvent) => {
    if ((e.metaKey || e.ctrlKey) && e.key === 'Enter') {
      e.preventDefault();
      executeQuery();
    }
    if ((e.metaKey || e.ctrlKey) && e.key === 's') {
      e.preventDefault();
      saveQuery();
    }
  }, [activeQuery]);

  return (
    <TooltipProvider>
      <Card className="flex flex-col h-full glass border-0 shadow-xl">
        <CardHeader className="pb-0">
          {/* Header Bar */}
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-3">
              <motion.div
                className="flex items-center gap-2"
                initial={{ opacity: 0, x: -20 }}
                animate={{ opacity: 1, x: 0 }}
              >
                <div className="p-2 rounded-lg" style={{ background: 'linear-gradient(to right, rgb(147 51 234), rgb(219 39 119))' }}>
                  <Terminal className="h-5 w-5 text-white" />
                </div>
                <h3 className="text-lg font-semibold">Query Editor</h3>
              </motion.div>
              
              <div className="flex items-center gap-2">
                <Badge variant="outline" className="glass text-xs">
                  <Database className="h-3 w-3 mr-1" />
                  {currentDatabase}
                </Badge>
                <Badge variant="outline" className="glass text-xs">
                  <GitBranch className="h-3 w-3 mr-1" />
                  {currentBranch}
                </Badge>
                {executionTime !== null && (
                  <motion.div
                    initial={{ opacity: 0, scale: 0.8 }}
                    animate={{ opacity: 1, scale: 1 }}
                  >
                    <Badge variant="secondary" className="text-xs">
                      <Timer className="h-3 w-3 mr-1" />
                      {executionTime}ms
                    </Badge>
                  </motion.div>
                )}
                {queryValidation && !queryValidation.isValid && (
                  <motion.div
                    initial={{ opacity: 0, scale: 0.8 }}
                    animate={{ opacity: 1, scale: 1 }}
                  >
                    <Tooltip>
                      <TooltipTrigger>
                        <Badge variant="destructive" className="text-xs">
                          <AlertTriangle className="h-3 w-3 mr-1" />
                          Restricted Query
                        </Badge>
                      </TooltipTrigger>
                      <TooltipContent className="max-w-sm">
                        <p>{queryValidation.error}</p>
                      </TooltipContent>
                    </Tooltip>
                  </motion.div>
                )}
                {queryValidation && queryValidation.isValid && (
                  <motion.div
                    initial={{ opacity: 0, scale: 0.8 }}
                    animate={{ opacity: 1, scale: 1 }}
                  >
                    <Badge variant="outline" className="text-xs text-green-600 border-green-600">
                      <Shield className="h-3 w-3 mr-1" />
                      Safe Query
                    </Badge>
                  </motion.div>
                )}
              </div>
            </div>
            
            {/* Action Buttons */}
            <div className="flex items-center gap-2">
              <Tooltip>
                <TooltipTrigger asChild>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={copyQuery}
                    disabled={!activeQuery?.query}
                  >
                    {copied ? (
                      <CheckCircle className="h-4 w-4 text-green-500" />
                    ) : (
                      <Copy className="h-4 w-4" />
                    )}
                  </Button>
                </TooltipTrigger>
                <TooltipContent>Copy Query</TooltipContent>
              </Tooltip>
              
              <Tooltip>
                <TooltipTrigger asChild>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={saveQuery}
                    disabled={!activeQuery?.isDirty}
                  >
                    <Save className="h-4 w-4" />
                  </Button>
                </TooltipTrigger>
                <TooltipContent>
                  Save Query
                  <kbd className="ml-2 px-1 py-0.5 text-xs bg-muted rounded">⌘S</kbd>
                </TooltipContent>
              </Tooltip>
              
              <Tooltip>
                <TooltipTrigger asChild>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={clearQuery}
                    disabled={!activeQuery?.query.trim()}
                  >
                    <Trash2 className="h-4 w-4" />
                  </Button>
                </TooltipTrigger>
                <TooltipContent>Clear Query</TooltipContent>
              </Tooltip>
              
              <Tooltip>
                <TooltipTrigger asChild>
                  <Button
                    size="sm"
                    onClick={executeQuery}
                    disabled={executing || !activeQuery?.query.trim()}
                    className="text-white border-0 shadow-glow"
                    style={{ background: 'linear-gradient(to right, rgb(147 51 234), rgb(219 39 119))' }}
                  >
                    {executing ? (
                      <>
                        <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                        Executing...
                      </>
                    ) : (
                      <>
                        <Play className="mr-2 h-4 w-4" />
                        Execute
                      </>
                    )}
                  </Button>
                </TooltipTrigger>
                <TooltipContent>
                  Execute Query
                  <kbd className="ml-2 px-1 py-0.5 text-xs bg-muted rounded">⌘↵</kbd>
                </TooltipContent>
              </Tooltip>
            </div>
          </div>

          {/* Tabs */}
          <Tabs value={activeTab} onValueChange={setActiveTab} className="w-full">
            <div className="flex items-center gap-2">
              <TabsList className="glass h-9 p-1 flex-1 justify-start">
                <AnimatePresence mode="popLayout">
                  {tabs.map((tab) => (
                    <motion.div
                      key={tab.id}
                      initial={{ opacity: 0, scale: 0.8 }}
                      animate={{ opacity: 1, scale: 1 }}
                      exit={{ opacity: 0, scale: 0.8 }}
                      className="relative"
                    >
                      <TabsTrigger 
                        value={tab.id}
                        className="pr-8 data-[state=active]:bg-primary/10"
                      >
                        <Code2 className="h-3 w-3 mr-1.5" />
                        {tab.name}
                        {tab.isDirty && (
                          <span className="ml-1 w-1.5 h-1.5 bg-primary rounded-full" />
                        )}
                      </TabsTrigger>
                      {tabs.length > 1 && (
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            closeTab(tab.id);
                          }}
                          className="absolute right-1 top-1/2 -translate-y-1/2 p-0.5 rounded hover:bg-muted/50"
                        >
                          <X className="h-3 w-3" />
                        </button>
                      )}
                    </motion.div>
                  ))}
                </AnimatePresence>
              </TabsList>
              
              <Tooltip>
                <TooltipTrigger asChild>
                  <Button
                    variant="ghost"
                    size="icon"
                    onClick={addNewTab}
                    className="h-9 w-9"
                  >
                    <Plus className="h-4 w-4" />
                  </Button>
                </TooltipTrigger>
                <TooltipContent>New Query Tab</TooltipContent>
              </Tooltip>
            </div>
          </Tabs>
        </CardHeader>
        
        <CardContent className="flex-1 p-4">
          <div className="h-full rounded-lg overflow-hidden border glass">
            <CodeMirror
              value={activeQuery?.query || ''}
              height="100%"
              extensions={[sql()]}
              onChange={updateQuery}
              onKeyDown={handleKeyDown}
              theme={theme === 'dark' ? oneDark : lightTheme}
              className="h-full"
              placeholder="Write your SQL query here..."
            />
          </div>
          
          {/* Quick actions bar */}
          <motion.div 
            className="mt-4 flex items-center gap-4 text-xs text-muted-foreground"
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.2 }}
          >
            <button className="flex items-center gap-1 hover:text-primary transition-colors">
              <History className="h-3 w-3" />
              Query History
            </button>
            <button className="flex items-center gap-1 hover:text-primary transition-colors">
              <Sparkles className="h-3 w-3" />
              AI Assistant
            </button>
            <button className="flex items-center gap-1 hover:text-primary transition-colors">
              <Download className="h-3 w-3" />
              Export Results
            </button>
            <div className="ml-auto flex items-center gap-3">
              <span>Line 1, Col 1</span>
              <span>•</span>
              <span>SQL</span>
            </div>
          </motion.div>
        </CardContent>
      </Card>
    </TooltipProvider>
  );
}