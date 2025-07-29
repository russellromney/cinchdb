'use client';

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { ApiKeyForm } from './components/auth/api-key-form';
import { useCinchDB } from './lib/cinchdb-context';

export default function Home() {
  const router = useRouter();
  const { connected, connect } = useCinchDB();

  useEffect(() => {
    // Check for stored credentials
    const storedApiKey = localStorage.getItem('cinchdb_api_key');
    const storedApiUrl = localStorage.getItem('cinchdb_api_url');
    
    if (storedApiKey) {
      connect(storedApiKey, storedApiUrl || undefined);
    }
  }, [connect]);

  useEffect(() => {
    if (connected) {
      router.push('/dashboard');
    }
  }, [connected, router]);

  return <ApiKeyForm />;
}