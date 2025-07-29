'use client';

import { useState } from 'react';
import CodeMirror from '@uiw/react-codemirror';
import { sql } from '@codemirror/lang-sql';
import { Play, Trash2, Loader2 } from 'lucide-react';
import { useCinchDB } from '@/app/lib/cinchdb-context';
import type { QueryResult } from '@cinchdb/client';

interface QueryEditorProps {
  onResults: (results: QueryResult) => void;
  onError: (error: string) => void;
}

export function QueryEditor({ onResults, onError }: QueryEditorProps) {
  const { client } = useCinchDB();
  const [query, setQuery] = useState('SELECT * FROM sqlite_master WHERE type = "table";');
  const [executing, setExecuting] = useState(false);

  const executeQuery = async () => {
    if (!client || !query.trim()) return;

    setExecuting(true);
    onError('');

    try {
      const result = await client.query(query);
      onResults(result);
    } catch (err) {
      onError(err instanceof Error ? err.message : 'Query execution failed');
    } finally {
      setExecuting(false);
    }
  };

  const clearQuery = () => {
    setQuery('');
    onResults({ columns: [], rows: [], row_count: 0, data: [] });
    onError('');
  };

  return (
    <div className="flex flex-col h-full">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-lg font-semibold">Query Editor</h2>
        <div className="flex items-center space-x-2">
          <button
            onClick={executeQuery}
            disabled={executing || !query.trim()}
            className="flex items-center space-x-2 px-4 py-2 bg-primary text-primary-foreground rounded-md hover:bg-primary/90 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {executing ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin" />
                <span>Executing...</span>
              </>
            ) : (
              <>
                <Play className="w-4 h-4" />
                <span>Execute</span>
              </>
            )}
          </button>
          <button
            onClick={clearQuery}
            className="flex items-center space-x-2 px-4 py-2 border border-gray-300 rounded-md hover:bg-gray-50"
          >
            <Trash2 className="w-4 h-4" />
            <span>Clear</span>
          </button>
        </div>
      </div>

      <div className="flex-1 border border-gray-300 rounded-md overflow-hidden">
        <CodeMirror
          value={query}
          height="200px"
          extensions={[sql()]}
          onChange={(value) => setQuery(value)}
          theme={undefined}
          className="text-sm"
        />
      </div>
    </div>
  );
}