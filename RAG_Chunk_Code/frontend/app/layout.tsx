import type { Metadata } from 'next';
import './globals.css';

export const metadata: Metadata = {
  title: 'Product Wisdom Hub',
  description: 'AI-powered Product Knowledge Assistant - Learn from top product leaders',
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className="dark">
      <body>{children}</body>
    </html>
  );
}
