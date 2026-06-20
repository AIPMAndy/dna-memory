import './globals.css'
import type { Metadata } from 'next'

export const metadata: Metadata = {
  title: 'DNA Memory - 个人知识助手',
  description: '让 AI 记住你的每一个想法、偏好和决策',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="zh-CN">
      <body>{children}</body>
    </html>
  )
}
