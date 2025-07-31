'use client';

import { Header } from '../components/layout/header';
import { Sidebar } from '../components/layout/sidebar';
import { CommandPalette } from '../components/command-palette';

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <div className="h-screen flex flex-col bg-background">
      <Header />
      <div className="flex-1 flex overflow-hidden">
        <Sidebar />
        <main className="flex-1 overflow-y-auto relative">
          {/* Background pattern */}
          <div className="absolute inset-0" style={{
            background: 'linear-gradient(to bottom right, hsl(var(--background)), hsl(var(--background)), hsl(var(--muted) / 0.2))'
          }}>
            <div className="absolute inset-0 bg-grid-slate-900/[0.04] dark:bg-grid-slate-100/[0.02]" />
          </div>
          <div className="relative z-10 h-full">
            {children}
          </div>
        </main>
      </div>
      <CommandPalette />
    </div>
  );
}