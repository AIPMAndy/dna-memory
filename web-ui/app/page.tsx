import Link from 'next/link'

export default function HomePage() {
  return (
    <div className="min-h-screen bg-gradient-to-br from-primary-50 via-white to-secondary-50">
      <div className="container mx-auto px-4 py-16">
        {/* Header */}
        <header className="text-center mb-16">
          <h1 className="text-6xl font-bold mb-4 bg-gradient-to-r from-primary-600 to-secondary-600 bg-clip-text text-transparent">
            🧬 DNA Memory
          </h1>
          <p className="text-2xl text-gray-600 mb-8">
            让 AI 像人脑一样学习、记忆与进化
          </p>
          <div className="flex justify-center gap-4">
            <Link
              href="/timeline"
              className="px-8 py-3 bg-primary-600 text-white rounded-lg hover:bg-primary-700 transition-colors shadow-lg"
            >
              查看记忆时间线
            </Link>
            <Link
              href="/stats"
              className="px-8 py-3 bg-white text-primary-600 border-2 border-primary-600 rounded-lg hover:bg-primary-50 transition-colors"
            >
              统计数据
            </Link>
          </div>
        </header>

        {/* Features Grid */}
        <div className="grid md:grid-cols-3 gap-8 mb-16">
          <FeatureCard
            icon="🎯"
            title="自动采集"
            description="零配置自动识别对话中的偏好、决策和知识点"
          />
          <FeatureCard
            icon="🔍"
            title="智能搜索"
            description="全文搜索 + 多维度排序，快速找到相关记忆"
          />
          <FeatureCard
            icon="🧠"
            title="三层架构"
            description="工作记忆 → 短期记忆 → 长期记忆，模拟人脑机制"
          />
          <FeatureCard
            icon="📊"
            title="记忆图谱"
            description="可视化记忆关系网络，发现隐藏关联"
          />
          <FeatureCard
            icon="⚡"
            title="自动强化"
            description="高频使用自动提权，长期不用自动衰减"
          />
          <FeatureCard
            icon="🔐"
            title="本地优先"
            description="SQLite 本地存储，零重依赖，隐私安全"
          />
        </div>

        {/* Stats Preview */}
        <StatsPreview />
      </div>
    </div>
  )
}

function FeatureCard({ icon, title, description }: { icon: string; title: string; description: string }) {
  return (
    <div className="bg-white rounded-xl p-6 shadow-lg hover:shadow-xl transition-shadow">
      <div className="text-4xl mb-3">{icon}</div>
      <h3 className="text-xl font-bold mb-2 text-gray-800">{title}</h3>
      <p className="text-gray-600">{description}</p>
    </div>
  )
}

async function StatsPreview() {
  try {
    const res = await fetch(`http://localhost:3456/api/stats`, {
      cache: 'no-store',
      next: { revalidate: 0 }
    })

    if (!res.ok) {
      throw new Error('Failed to fetch stats')
    }

    const stats = await res.json()

    return (
      <div className="bg-white rounded-xl shadow-lg p-8">
        <h2 className="text-2xl font-bold mb-6 text-center text-gray-800">📈 实时统计</h2>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-6">
          <StatItem label="总记忆" value={stats.total} />
          <StatItem label="短期记忆" value={stats.short_term} />
          <StatItem label="长期记忆" value={stats.long_term} />
          <StatItem label="平均权重" value={stats.avg_weight.toFixed(2)} />
        </div>
      </div>
    )
  } catch (error) {
    return (
      <div className="bg-white rounded-xl shadow-lg p-8">
        <p className="text-center text-gray-500">
          启动 Web UI 后查看统计数据
        </p>
      </div>
    )
  }
}

function StatItem({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="text-center">
      <div className="text-3xl font-bold text-primary-600 mb-1">{value}</div>
      <div className="text-sm text-gray-600">{label}</div>
    </div>
  )
}
