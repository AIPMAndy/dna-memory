import Database from 'better-sqlite3'
import { NextResponse } from 'next/server'
import path from 'path'

const DB_PATH = path.join(process.cwd(), '..', 'memory', 'memory.db')

export async function GET() {
  try {
    // Check if database exists
    const fs = require('fs')
    if (!fs.existsSync(DB_PATH)) {
      return NextResponse.json({
        total: 0,
        short_term: 0,
        long_term: 0,
        relations: 0,
        avg_weight: 0,
        capacity_usage: '0/10000',
        usage_percent: 0,
        type_distribution: [],
        operations: {},
        message: '数据库未初始化。请先运行: python3 scripts/evolve.py stats'
      })
    }

    const db = new Database(DB_PATH, { readonly: true })

    // Get total counts
    const totalRow = db.prepare('SELECT COUNT(*) as total FROM memory').get() as { total: number }
    const shortTermRow = db.prepare('SELECT COUNT(*) as count FROM memory WHERE short_term = 1').get() as { count: number }
    const longTermRow = db.prepare('SELECT COUNT(*) as count FROM memory WHERE long_term = 1').get() as { count: number }
    const relationsRow = db.prepare('SELECT COUNT(*) as count FROM memory_relations').get() as { count: number }

    // Get average weight
    const avgWeightRow = db.prepare('SELECT AVG(weight) as avg FROM memory').get() as { avg: number }

    // Get type distribution
    const typeDistribution = db.prepare(`
      SELECT type, COUNT(*) as count
      FROM memory
      GROUP BY type
      ORDER BY count DESC
    `).all() as Array<{ type: string; count: number }>

    // Get recent operations
    const recentOps = db.prepare(`
      SELECT operation, COUNT(*) as count
      FROM operations
      GROUP BY operation
      ORDER BY count DESC
      LIMIT 5
    `).all() as Array<{ operation: string; count: number }>

    db.close()

    return NextResponse.json({
      total: totalRow.total,
      short_term: shortTermRow.count,
      long_term: longTermRow.count,
      relations: relationsRow.count,
      avg_weight: avgWeightRow.avg || 0,
      capacity_usage: `${totalRow.total}/10000`,
      usage_percent: Math.round((totalRow.total / 10000) * 100),
      type_distribution: typeDistribution,
      operations: recentOps.reduce((acc, op) => {
        acc[op.operation] = op.count
        return acc
      }, {} as Record<string, number>)
    })
  } catch (error) {
    console.error('Error fetching stats:', error)
    return NextResponse.json(
      {
        error: 'Failed to fetch stats',
        message: String(error)
      },
      { status: 500 }
    )
  }
}
