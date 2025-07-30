import type { Metadata } from 'next';
import { Inter } from 'next/font/google';
import './globals.css';
import { CinchDBProvider } from './lib/cinchdb-context';
import { ThemeProvider } from './lib/theme-provider';
import { Toaster } from 'sonner';

const inter = Inter({ subsets: ['latin'] });

export const metadata: Metadata = {
  title: 'CinchDB',
  description: 'Git-like SQLite database management',
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body className={inter.className}>
        <ThemeProvider
          defaultTheme="system"
        >
          <CinchDBProvider>
            {children}
            <Toaster 
              position="bottom-right" 
              toastOptions={{
                className: 'glass',
              }}
            />
          </CinchDBProvider>
        </ThemeProvider>
      </body>
    </html>
  );
}