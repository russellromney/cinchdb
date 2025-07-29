import type { Metadata } from 'next';
import { Inter } from 'next/font/google';
import './globals.css';
import { CinchDBProvider } from './lib/cinchdb-context';

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
    <html lang="en">
      <body className={inter.className}>
        <CinchDBProvider>
          {children}
        </CinchDBProvider>
      </body>
    </html>
  );
}