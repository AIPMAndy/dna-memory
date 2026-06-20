import Link from 'next/link'

export default function GraphPage() {
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
            <h1 className="text-xl text-gray-700">记忆图谱</h1>
          </div>
          <div className="flex gap-2">
            <Link
              href="/timeline"
              className="px-4 py-2 text-gray-600 hover:text-gray-900 transition-colors"
            >
              时间线
            </Link>
            <Link
              href="/stats"
              className="px-4 py-2 text-gray-600 hover:text-gray-900 transition-colors"
            >
              统计
            </Link>
          </div>
        </div>
      </header>

      {/* Graph Content */}
      <div className="container mx-auto px-4 py-8">
        <div className="bg-white rounded-lg shadow-sm p-8 border border-gray-200 text-center">
          <div className="text-6xl mb-4">🚧</div>
          <h2 className="text-2xl font-bold text-gray-800 mb-4">记忆图谱功能开发中</h2>
          <p className="text-gray-600 mb-6">
            即将支持 D3.js 可视化记忆关联网络
          </p>
          <div className="space-y-2 text-left max-w-md mx-auto">
            <FeatureItem text="节点：每条记忆" />
            <FeatureItem text="边：记忆之间的关联关系" />
            <FeatureItem text="交互：点击节点查看详情" />
            <FeatureItem text="缩放：拖拽调整视图" />
            <FeatureItem text="过滤：按类型/层级筛选" />
          </div>
          <div className="mt-8">
            <Link
              href="/timeline"
              className="px-6 py-3 bg-primary-600 text-white rounded-lg hover:bg-primary-700 transition-colors inline-block"
            >
              查看时间线
            </Link>
          </div>
        </div>
      </div>
    </div>
  )
}

function FeatureItem({ text }: { text: string }) {
  return (
    <div className="flex items-center gap-2">
      <span className="text-green-500">✓</span>
      <span className="text-gray-700">{text}</span>
    </div>
  )
}
