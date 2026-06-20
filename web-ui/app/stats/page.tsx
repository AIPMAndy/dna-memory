import Link from 'next/link'

export default async function StatsPage() {
  const res = await fetch('http://localhost:3456/api/stats', {
    cache: 'no-store',
  })

  if (!res.ok) {
    return <ErrorView />
  }

  const stats = await res.json()

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
            <h1 className="text-xl text-gray-700">统计数据</h1>
          </div>
          <div className="flex gap-2">
            <Link
              href="/timeline"
              className="px-4 py-2 text-gray-600 hover:text-gray-900 transition-colors"
            >
              时间线
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

      {/* Stats Content */}
      <div className="container mx-auto px-4 py-8">
        {/* Overview Cards */}
        <div className="grid md:grid-cols-4 gap-6 mb-8">
          <StatCard
            label="总记忆数"
            value={stats.total}
            icon="🧠"
            color="primary"
          />
          <StatCard
            label="短期记忆"
            value={stats.short_term}
            icon="⚡"
            color="blue"
          />
          <StatCard
            label="长期记忆"
            value={stats.long_term}
            icon="💎"
            color="green"
          />
          <StatCard
            label="平均权重"
            value={stats.avg_weight.toFixed(2)}
            icon="⭐"
            color="orange"
          />
        </div>

        <div className="grid md:grid-cols-2 gap-8">
          {/* Type Distribution */}
          <div className="bg-white rounded-lg shadow-sm p-6 border border-gray-200">
            <h2 className="text-xl font-bold mb-4 text-gray-800">📊 类型分布</h2>
            <div className="space-y-3">
              {stats.type_distribution.map((item: any) => (
                <TypeDistributionBar
                  key={item.type}
                  type={item.type}
                  count={item.count}
                  total={stats.total}
                />
              ))}
            </div>
          </div>

          {/* Operations */}
          <div className="bg-white rounded-lg shadow-sm p-6 border border-gray-200">
            <h2 className="text-xl font-bold mb-4 text-gray-800">🔄 操作统计</h2>
            <div className="space-y-3">
              {Object.entries(stats.operations).map(([op, count]) => (
                <OperationRow key={op} operation={op} count={count as number} />
              ))}
            </div>
          </div>
        </div>

        {/* Capacity Usage */}
        <div className="bg-white rounded-lg shadow-sm p-6 border border-gray-200 mt-8">
          <h2 className="text-xl font-bold mb-4 text-gray-800">💾 容量使用</h2>
          <div className="mb-2 flex justify-between text-sm text-gray-600">
            <span>{stats.capacity_usage}</span>
            <span>{stats.usage_percent}%</span>
          </div>
          <div className="w-full bg-gray-200 rounded-full h-4">
            <div
              className="bg-gradient-to-r from-primary-500 to-secondary-500 h-4 rounded-full transition-all"
              style={{ width: `${stats.usage_percent}%` }}
            />
          </div>
          <p className="text-sm text-gray-500 mt-2">
            {stats.usage_percent < 50
              ? '✅ 容量充足'
              : stats.usage_percent < 80
              ? '⚠️ 建议定期清理'
              : '🔴 容量紧张，建议立即清理'}
          </p>
        </div>
      </div>
    </div>
  )
}

function StatCard({
  label,
  value,
  icon,
  color,
}: {
  label: string
  value: string | number
  icon: string
  color: string
}) {
  const colorClasses: Record<string, string> = {
    primary: 'from-primary-500 to-primary-600',
    blue: 'from-blue-500 to-blue-600',
    green: 'from-green-500 to-green-600',
    orange: 'from-orange-500 to-orange-600',
  }

  return (
    <div className="bg-white rounded-lg shadow-sm p-6 border border-gray-200">
      <div className="flex items-center justify-between mb-2">
        <span className="text-3xl">{icon}</span>
        <span className={`text-3xl font-bold bg-gradient-to-r ${colorClasses[color]} bg-clip-text text-transparent`}>
          {value}
        </span>
      </div>
      <p className="text-sm text-gray-600">{label}</p>
    </div>
  )
}

function TypeDistributionBar({
  type,
  count,
  total,
}: {
  type: string
  count: number
  total: number
}) {
  const percentage = (count / total) * 100
  const typeLabels: Record<string, string> = {
    preference: '偏好',
    error: '错误',
    insight: '洞察',
    skill: '技能',
    fact: '事实',
    pattern: '模式',
  }

  return (
    <div>
      <div className="flex justify-between text-sm mb-1">
        <span className="text-gray-700">{typeLabels[type] || type}</span>
        <span className="text-gray-600">{count} ({percentage.toFixed(1)}%)</span>
      </div>
      <div className="w-full bg-gray-200 rounded-full h-2">
        <div
          className="bg-primary-500 h-2 rounded-full transition-all"
          style={{ width: `${percentage}%` }}
        />
      </div>
    </div>
  )
}

function OperationRow({ operation, count }: { operation: string; count: number }) {
  const opLabels: Record<string, string> = {
    remember: '记录',
    recall: '召回',
    reflect: '反思',
    decay: '衰减',
    promote: '晋升',
    forget: '遗忘',
  }

  return (
    <div className="flex justify-between items-center py-2 border-b border-gray-100 last:border-0">
      <span className="text-gray-700">{opLabels[operation] || operation}</span>
      <span className="font-semibold text-gray-900">{count}</span>
    </div>
  )
}

function ErrorView() {
  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50">
      <div className="text-center">
        <h1 className="text-2xl font-bold text-gray-800 mb-4">⚠️ 无法加载统计数据</h1>
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
