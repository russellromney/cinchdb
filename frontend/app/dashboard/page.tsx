'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { QueryEditor } from '../components/query/query-editor';
import { ResultsTable } from '../components/query/results-table';
import { useCinchDB } from '../lib/cinchdb-context';
import type { QueryResult } from '@cinchdb/client';

export default function Dashboard() {
  const router = useRouter();
  const { connected } = useCinchDB();
  const [results, setResults] = useState<QueryResult | null>(null);
  const [error, setError] = useState<string>('');

  useEffect(() => {
    if (!connected) {
      router.push('/');
    }
  }, [connected, router]);

  if (!connected) {
    return null;
  }

  return (
    <div className="h-full flex flex-col">
      <div className="flex-1 flex flex-col gap-6 p-6 overflow-hidden">
        <div className="flex-shrink-0">
          <QueryEditor 
            onResults={setResults} 
            onError={setError}
          />
        </div>
        <div className="flex-1 overflow-y-auto scrollbar-thin">
          <ResultsTable 
            results={results} 
            error={error}
          />
        </div>
      </div>
    </div>
  );
}