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
          <div className="absolute inset-0 bg-gradient-to-br from-background via-background to-muted/20">
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