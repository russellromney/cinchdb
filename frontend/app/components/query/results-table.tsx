'use client';

import { useState, useMemo } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { 
  Download, 
  AlertCircle, 
  Database, 
  FileText,
  Copy,
  CheckCircle,
  ChevronLeft,
  ChevronRight,
  ChevronsLeft,
  ChevronsRight,
  ArrowUpDown,
  ArrowUp,
  ArrowDown,
  FileSpreadsheet,
  FileJson,
  Table as TableIcon,
  Sparkles,
  Search,
  Filter,
  X
} from 'lucide-react';
import type { QueryResult } from '@cinchdb/client';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader } from '@/components/ui/card';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from '@/components/ui/tooltip';
import { toast } from 'sonner';

interface ResultsTableProps {
  results: QueryResult | null;
  error: string | null;
}

type SortDirection = 'asc' | 'desc' | null;

export function ResultsTable({ results, error }: ResultsTableProps) {
  const [currentPage, setCurrentPage] = useState(1);
  const [pageSize, setPageSize] = useState(25);
  const [searchQuery, setSearchQuery] = useState('');
  const [sortColumn, setSortColumn] = useState<string | null>(null);
  const [sortDirection, setSortDirection] = useState<SortDirection>(null);
  const [copiedCell, setCopiedCell] = useState<string | null>(null);

  // Filter and sort data
  const processedData = useMemo(() => {
    if (!results?.data) return [];
    
    let data = [...results.data];
    
    // Filter by search
    if (searchQuery) {
      data = data.filter(row => 
        Object.values(row).some(value => 
          String(value).toLowerCase().includes(searchQuery.toLowerCase())
        )
      );
    }
    
    // Sort
    if (sortColumn && sortDirection) {
      data.sort((a, b) => {
        const aVal = a[sortColumn];
        const bVal = b[sortColumn];
        
        if (aVal === null) return 1;
        if (bVal === null) return -1;
        
        const comparison = aVal < bVal ? -1 : aVal > bVal ? 1 : 0;
        return sortDirection === 'asc' ? comparison : -comparison;
      });
    }
    
    return data;
  }, [results?.data, searchQuery, sortColumn, sortDirection]);

  // Pagination
  const totalPages = Math.ceil(processedData.length / pageSize);
  const startIndex = (currentPage - 1) * pageSize;
  const endIndex = startIndex + pageSize;
  const currentData = processedData.slice(startIndex, endIndex);

  const handleSort = (column: string) => {
    if (sortColumn === column) {
      setSortDirection(
        sortDirection === 'asc' ? 'desc' : sortDirection === 'desc' ? null : 'asc'
      );
      if (sortDirection === 'desc') setSortColumn(null);
    } else {
      setSortColumn(column);
      setSortDirection('asc');
    }
  };

  const copyCell = async (value: any) => {
    const text = value === null ? 'NULL' : String(value);
    await navigator.clipboard.writeText(text);
    setCopiedCell(text);
    toast.success('Value copied to clipboard');
    setTimeout(() => setCopiedCell(null), 2000);
  };

  const downloadData = (format: 'csv' | 'json') => {
    if (!processedData.length) return;

    let content: string;
    let mimeType: string;
    let extension: string;

    if (format === 'csv') {
      const headers = Object.keys(processedData[0]);
      content = [
        headers.join(','),
        ...processedData.map(row => 
          headers.map(header => {
            const value = row[header];
            if (value === null) return '';
            if (typeof value === 'string' && (value.includes(',') || value.includes('"'))) {
              return `"${value.replace(/"/g, '""')}"`;
            }
            return value;
          }).join(',')
        )
      ].join('\n');
      mimeType = 'text/csv';
      extension = 'csv';
    } else {
      content = JSON.stringify(processedData, null, 2);
      mimeType = 'application/json';
      extension = 'json';
    }

    const blob = new Blob([content], { type: mimeType });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `query_results_${new Date().toISOString()}.${extension}`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
    
    toast.success(`Downloaded as ${extension.toUpperCase()}`);
  };

  if (error) {
    return (
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.3 }}
      >
        <Card className="mt-4 glass border-0 shadow-xl">
          <CardContent className="pt-6">
            <Alert variant="destructive" className="glass border-red-500/20">
              <AlertCircle className="h-4 w-4" />
              <AlertTitle>Query Error</AlertTitle>
              <AlertDescription className="mt-2 font-mono text-sm">
                {error}
              </AlertDescription>
            </Alert>
          </CardContent>
        </Card>
      </motion.div>
    );
  }

  if (!results) {
    return (
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ duration: 0.5 }}
      >
        <Card className="mt-4 glass border-0 shadow-xl">
          <CardContent className="flex flex-col items-center justify-center py-20">
            <motion.div
              initial={{ scale: 0.8 }}
              animate={{ scale: 1 }}
              transition={{ duration: 0.5, delay: 0.2 }}
            >
              <div className="w-20 h-20 rounded-2xl gradient-secondary flex items-center justify-center mb-4">
                <Database className="h-10 w-10 text-white" />
              </div>
            </motion.div>
            <h3 className="text-lg font-semibold mb-2">No Results Yet</h3>
            <p className="text-muted-foreground">Execute a query to see results</p>
          </CardContent>
        </Card>
      </motion.div>
    );
  }

  if (!results.data || results.data.length === 0) {
    return (
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.3 }}
      >
        <Card className="mt-4 glass border-0 shadow-xl">
          <CardContent className="flex flex-col items-center justify-center py-20">
            <motion.div
              initial={{ rotate: -10 }}
              animate={{ rotate: 0 }}
              transition={{ type: "spring", stiffness: 200 }}
            >
              <FileText className="h-16 w-16 text-muted-foreground mb-4" />
            </motion.div>
            <h3 className="text-lg font-semibold mb-2">Empty Result Set</h3>
            <p className="text-muted-foreground">Query completed but returned no rows</p>
          </CardContent>
        </Card>
      </motion.div>
    );
  }

  const headers = Object.keys(results.data[0]);

  return (
    <TooltipProvider>
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.3 }}
      >
        <Card className="mt-4 glass border-0 shadow-xl">
          <CardHeader className="pb-3">
            <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4">
              <div className="flex items-center gap-3">
                <motion.div
                  className="flex items-center gap-2"
                  initial={{ opacity: 0, x: -20 }}
                  animate={{ opacity: 1, x: 0 }}
                >
                  <div className="p-2 rounded-lg gradient-success">
                    <TableIcon className="h-5 w-5 text-white" />
                  </div>
                  <h3 className="text-lg font-semibold">Results</h3>
                </motion.div>
                
                <div className="flex items-center gap-2">
                  <Badge variant="secondary" className="glass">
                    {processedData.length} {processedData.length === 1 ? 'row' : 'rows'}
                  </Badge>
                  {searchQuery && (
                    <Badge variant="outline" className="glass">
                      Filtered
                    </Badge>
                  )}
                </div>
              </div>
              
              <div className="flex items-center gap-2">
                {/* Search */}
                <div className="relative">
                  <Search className="absolute left-2 top-2.5 h-4 w-4 text-muted-foreground" />
                  <Input
                    placeholder="Search results..."
                    value={searchQuery}
                    onChange={(e) => {
                      setSearchQuery(e.target.value);
                      setCurrentPage(1);
                    }}
                    className="h-9 w-[200px] pl-8 pr-8 glass border-0"
                  />
                  {searchQuery && (
                    <button
                      onClick={() => {
                        setSearchQuery('');
                        setCurrentPage(1);
                      }}
                      className="absolute right-2 top-2.5 text-muted-foreground hover:text-foreground"
                    >
                      <X className="h-4 w-4" />
                    </button>
                  )}
                </div>
                
                {/* Export */}
                <DropdownMenu>
                  <DropdownMenuTrigger asChild>
                    <Button variant="outline" size="sm" className="glass">
                      <Download className="mr-2 h-4 w-4" />
                      Export
                    </Button>
                  </DropdownMenuTrigger>
                  <DropdownMenuContent align="end" className="glass">
                    <DropdownMenuItem onClick={() => downloadData('csv')}>
                      <FileSpreadsheet className="mr-2 h-4 w-4" />
                      Export as CSV
                    </DropdownMenuItem>
                    <DropdownMenuItem onClick={() => downloadData('json')}>
                      <FileJson className="mr-2 h-4 w-4" />
                      Export as JSON
                    </DropdownMenuItem>
                  </DropdownMenuContent>
                </DropdownMenu>
              </div>
            </div>
          </CardHeader>
          
          <CardContent className="p-0">
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="border-b bg-muted/30">
                    {headers.map((header) => (
                      <th
                        key={header}
                        className="px-4 py-3 text-left text-xs font-medium text-muted-foreground uppercase tracking-wider cursor-pointer hover:bg-muted/50 transition-colors"
                        onClick={() => handleSort(header)}
                      >
                        <div className="flex items-center gap-2">
                          {header}
                          <div className="flex flex-col">
                            {sortColumn === header ? (
                              sortDirection === 'asc' ? (
                                <ArrowUp className="h-3 w-3 text-primary" />
                              ) : sortDirection === 'desc' ? (
                                <ArrowDown className="h-3 w-3 text-primary" />
                              ) : (
                                <ArrowUpDown className="h-3 w-3 opacity-50" />
                              )
                            ) : (
                              <ArrowUpDown className="h-3 w-3 opacity-50" />
                            )}
                          </div>
                        </div>
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  <AnimatePresence mode="wait">
                    {currentData.map((row, i) => (
                      <motion.tr
                        key={`${currentPage}-${i}`}
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        exit={{ opacity: 0 }}
                        transition={{ duration: 0.2, delay: i * 0.02 }}
                        className="border-b transition-colors hover:bg-muted/30 group"
                      >
                        {headers.map((header) => (
                          <td
                            key={header}
                            className="px-4 py-3 text-sm relative"
                            onClick={() => copyCell(row[header])}
                          >
                            <div className="flex items-center gap-2 cursor-pointer">
                              {row[header] === null ? (
                                <span className="text-muted-foreground italic">NULL</span>
                              ) : (
                                <span className="font-mono">{String(row[header])}</span>
                              )}
                              <Tooltip>
                                <TooltipTrigger asChild>
                                  <button className="opacity-0 group-hover:opacity-100 transition-opacity">
                                    {copiedCell === String(row[header]) ? (
                                      <CheckCircle className="h-3 w-3 text-green-500" />
                                    ) : (
                                      <Copy className="h-3 w-3 text-muted-foreground" />
                                    )}
                                  </button>
                                </TooltipTrigger>
                                <TooltipContent>Click to copy</TooltipContent>
                              </Tooltip>
                            </div>
                          </td>
                        ))}
                      </motion.tr>
                    ))}
                  </AnimatePresence>
                </tbody>
              </table>
            </div>
            
            {/* Pagination */}
            {totalPages > 1 && (
              <div className="flex items-center justify-between px-4 py-3 border-t">
                <div className="flex items-center gap-2 text-sm text-muted-foreground">
                  <span>
                    Showing {startIndex + 1} to {Math.min(endIndex, processedData.length)} of {processedData.length} results
                  </span>
                </div>
                
                <div className="flex items-center gap-2">
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => setCurrentPage(1)}
                    disabled={currentPage === 1}
                    className="glass"
                  >
                    <ChevronsLeft className="h-4 w-4" />
                  </Button>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => setCurrentPage(currentPage - 1)}
                    disabled={currentPage === 1}
                    className="glass"
                  >
                    <ChevronLeft className="h-4 w-4" />
                  </Button>
                  
                  <div className="flex items-center gap-1">
                    <Input
                      type="number"
                      min={1}
                      max={totalPages}
                      value={currentPage}
                      onChange={(e) => {
                        const page = parseInt(e.target.value) || 1;
                        setCurrentPage(Math.min(Math.max(1, page), totalPages));
                      }}
                      className="w-16 h-8 text-center glass border-0"
                    />
                    <span className="text-sm text-muted-foreground">of {totalPages}</span>
                  </div>
                  
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => setCurrentPage(currentPage + 1)}
                    disabled={currentPage === totalPages}
                    className="glass"
                  >
                    <ChevronRight className="h-4 w-4" />
                  </Button>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => setCurrentPage(totalPages)}
                    disabled={currentPage === totalPages}
                    className="glass"
                  >
                    <ChevronsRight className="h-4 w-4" />
                  </Button>
                </div>
              </div>
            )}
          </CardContent>
        </Card>
      </motion.div>
    </TooltipProvider>
  );
}