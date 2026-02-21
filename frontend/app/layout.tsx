import './globals.css'
import type { Metadata } from 'next'

export const metadata: Metadata = {
  title: 'RepoMind AI',
  description: 'Analyze GitHub repositories with AI',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en" className="dark">
      <body className="bg-[#0f0f0f] text-[#f5f5f5]">{children}</body>
    </html>
  )
}
