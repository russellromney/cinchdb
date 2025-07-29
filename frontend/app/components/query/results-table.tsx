'use client';

import { Download } from 'lucide-react';
import type { QueryResult } from '@cinchdb/client';

interface ResultsTableProps {
  results: QueryResult | null;
  error: string | null;
}

export function ResultsTable({ results, error }: ResultsTableProps) {
  const downloadCSV = () => {
    if (!results || !results.data || results.data.length === 0) return;

    const headers = Object.keys(results.data[0]);
    const csvContent = [
      headers.join(','),
      ...results.data.map(row => 
        headers.map(header => {
          const value = row[header];
          // Escape values containing commas or quotes
          if (typeof value === 'string' && (value.includes(',') || value.includes('"'))) {
            return `"${value.replace(/"/g, '""')}"`;
          }
          return value;
        }).join(',')
      )
    ].join('\n');

    const blob = new Blob([csvContent], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `query_results_${new Date().toISOString()}.csv`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  if (error) {
    return (
      <div className="mt-4 p-4 bg-red-50 border border-red-200 rounded-md">
        <h3 className="text-sm font-medium text-red-800">Error</h3>
        <p className="mt-1 text-sm text-red-700">{error}</p>
      </div>
    );
  }

  if (!results) {
    return (
      <div className="mt-4 p-8 text-center text-gray-500">
        <p>Execute a query to see results</p>
      </div>
    );
  }

  if (!results.data || results.data.length === 0) {
    return (
      <div className="mt-4 p-8 text-center text-gray-500">
        <p>Query returned no results</p>
      </div>
    );
  }

  const headers = Object.keys(results.data[0]);

  return (
    <div className="mt-4">
      <div className="flex items-center justify-between mb-2">
        <h3 className="text-sm font-medium text-gray-700">
          Results ({results.row_count} rows)
        </h3>
        <button
          onClick={downloadCSV}
          className="flex items-center space-x-1 text-sm text-gray-600 hover:text-gray-900"
        >
          <Download className="w-4 h-4" />
          <span>Export CSV</span>
        </button>
      </div>

      <div className="overflow-x-auto border border-gray-200 rounded-md">
        <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-gray-50">
            <tr>
              {headers.map((header) => (
                <th
                  key={header}
                  className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider"
                >
                  {header}
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-gray-200">
            {results.data.map((row, i) => (
              <tr key={i} className="hover:bg-gray-50">
                {headers.map((header) => (
                  <td
                    key={header}
                    className="px-6 py-4 whitespace-nowrap text-sm text-gray-900"
                  >
                    {row[header] === null ? (
                      <span className="text-gray-400 italic">NULL</span>
                    ) : (
                      String(row[header])
                    )}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}