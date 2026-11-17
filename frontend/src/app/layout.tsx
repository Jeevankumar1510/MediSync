import './globals.css';
import type { Metadata } from 'next';
import { AppLayout } from '@/components/layout/AppLayout';

export const metadata: Metadata = {
  title: 'MediSync AI - Healthcare Data Integration & RAG Platform',
  description: 'Enterprise FHIR R4 Integration, Asynchronous ETL Synchronization, AI Field Mapping, and Grounded Clinical Assistant.',
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className="antialiased selection:bg-teal-500 selection:text-white">
        <AppLayout>{children}</AppLayout>
      </body>
    </html>
  );
}
