import Link from 'next/link'
import { formatDistanceToNow } from 'date-fns'
import { zhCN } from 'date-fns/locale'

interface Memory {
  id: number
  content: string
  type: string
  tags: string
  weight: number
  layer: string
  created_date: string
  updated_date: string
  access_count: number
}

export default async function TimelinePage() {
  const res = await fetch('http://localhost:3456/api/memories?limit=100', {
    cache: 'no-store',
  })

  if (!res.ok) {
    return <ErrorView />
  }

  const data = await res.json()
  const memories: Memory[] = data.memories

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white shadow-sm border-b">
        <div className="container mx-auto px-4 py-4 flex items-center justify-between">
          <div className="flex items-center gap-4">
            <Link href="/" className="text-2xl font-bold text-primary-600">
              🧬 DNA Memory
            </Link>
            <span className="text-gray-400">|</span>
            <h1 className="text-xl text-gray-700">记忆时间线</h1>
          </div>
          <div className="flex gap-2">
            <Link
              href="/stats"
              className="px-4 py-2 text-gray-600 hover:text-gray-900 transition-colors"
            >
              统计
            </Link>
            <Link
              href="/graph"
              className="px-4 py-2 text-gray-600 hover:text-gray-900 transition-colors"
            >
              图谱
            </Link>
          </div>
        </div>
      </header>

      {/* Timeline Content */}
      <div className="container mx-auto px-4 py-8">
        <div className="mb-6 flex items-center justify-between">
          <p className="text-gray-600">
            共 {data.total} 条记忆，显示最近 {memories.length} 条
          </p>
          <TypeFilter />
        </div>

        {/* Timeline */}
        <div className="space-y-4">
          {memories.map((memory) => (
            <MemoryCard key={memory.id} memory={memory} />
          ))}
        </div>
      </div>
    </div>
  )
}

function MemoryCard({ memory }: { memory: Memory }) {
  const typeColors: Record<string, string> = {
    preference: 'bg-purple-100 text-purple-800',
    error: 'bg-red-100 text-red-800',
    insight: 'bg-blue-100 text-blue-800',
    skill: 'bg-green-100 text-green-800',
    fact: 'bg-gray-100 text-gray-800',
    pattern: 'bg-yellow-100 text-yellow-800',
  }

  const layerColors: Record<string, string> = {
    '工作': 'bg-gray-200 text-gray-700',
    '短期': 'bg-blue-200 text-blue-800',
    '长期': 'bg-green-200 text-green-800',
  }

  return (
    <div className="bg-white rounded-lg shadow-sm hover:shadow-md transition-shadow p-6 border border-gray-200">
      <div className="flex items-start justify-between mb-3">
        <div className="flex gap-2">
          <span className={`px-2 py-1 rounded text-xs font-medium ${typeColors[memory.type] || typeColors.fact}`}>
            {memory.type}
          </span>
          <span className={`px-2 py-1 rounded text-xs font-medium ${layerColors[memory.layer]}`}>
            {memory.layer}
          </span>
          <span className="px-2 py-1 rounded text-xs font-medium bg-orange-100 text-orange-800">
            ⭐ {memory.weight.toFixed(2)}
          </span>
        </div>
        <span className="text-xs text-gray-500">
          访问 {memory.access_count} 次
        </span>
      </div>

      <p className="text-gray-800 mb-3 leading-relaxed">{memory.content}</p>

      {memory.tags && (
        <div className="flex gap-2 mb-3 flex-wrap">
          {memory.tags.split(',').map((tag, i) => (
            <span key={i} className="px-2 py-1 bg-gray-100 text-gray-600 rounded text-xs">
              #{tag.trim()}
            </span>
          ))}
        </div>
      )}

      <div className="text-xs text-gray-500">
        创建于 {formatDistanceToNow(new Date(memory.created_date), { addSuffix: true, locale: zhCN })}
      </div>
    </div>
  )
}

function TypeFilter() {
  return (
    <div className="flex gap-2">
      <button className="px-3 py-1 bg-primary-600 text-white rounded text-sm">
        全部
      </button>
      <button className="px-3 py-1 bg-gray-200 text-gray-700 rounded text-sm hover:bg-gray-300">
        偏好
      </button>
      <button className="px-3 py-1 bg-gray-200 text-gray-700 rounded text-sm hover:bg-gray-300">
        错误
      </button>
      <button className="px-3 py-1 bg-gray-200 text-gray-700 rounded text-sm hover:bg-gray-300">
        洞察
      </button>
    </div>
  )
}

function ErrorView() {
  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50">
      <div className="text-center">
        <h1 className="text-2xl font-bold text-gray-800 mb-4">⚠️ 无法加载记忆</h1>
        <p className="text-gray-600 mb-6">请确保 DNA Memory 数据库存在</p>
        <Link
          href="/"
          className="px-6 py-3 bg-primary-600 text-white rounded-lg hover:bg-primary-700 transition-colors"
        >
          返回首页
        </Link>
      </div>
    </div>
  )
}
