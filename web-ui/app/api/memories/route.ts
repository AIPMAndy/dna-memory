import Database from 'better-sqlite3'
import { NextResponse } from 'next/server'
import path from 'path'

const DB_PATH = path.join(process.cwd(), '..', 'memory', 'memory.db')

interface Memory {
  id: number
  content: string
  type: string
  tags: string
  weight: number
  short_term: number
  long_term: number
  created: number
  updated: number
  accessed: number
  access_count: number
}

export async function GET(request: Request) {
  try {
    const { searchParams } = new URL(request.url)
    const limit = parseInt(searchParams.get('limit') || '50')
    const offset = parseInt(searchParams.get('offset') || '0')
    const type = searchParams.get('type')

    // Check if database exists
    const fs = require('fs')
    if (!fs.existsSync(DB_PATH)) {
      return NextResponse.json({
        memories: [],
        total: 0,
        limit,
        offset,
        message: '数据库未初始化。请先运行: python3 scripts/evolve.py stats'
      })
    }

    const db = new Database(DB_PATH, { readonly: true })

    let query = `
      SELECT id, content, type, tags, weight, short_term, long_term,
             created, updated, accessed, access_count
      FROM memory
    `
    const params: any[] = []

    if (type) {
      query += ' WHERE type = ?'
      params.push(type)
    }

    query += ' ORDER BY updated DESC LIMIT ? OFFSET ?'
    params.push(limit, offset)

    const memories = db.prepare(query).all(...params) as Memory[]

    // Get total count
    let countQuery = 'SELECT COUNT(*) as total FROM memory'
    if (type) {
      countQuery += ' WHERE type = ?'
    }
    const countParams = type ? [type] : []
    const { total } = db.prepare(countQuery).get(...countParams) as { total: number }

    db.close()

    return NextResponse.json({
      memories: memories.map(m => ({
        ...m,
        layer: m.long_term ? '长期' : m.short_term ? '短期' : '工作',
        created_date: new Date(m.created * 1000).toISOString(),
        updated_date: new Date(m.updated * 1000).toISOString(),
      })),
      total,
      limit,
      offset
    })
  } catch (error) {
    console.error('Error fetching memories:', error)
    return NextResponse.json(
      {
        error: 'Failed to fetch memories',
        message: String(error)
      },
      { status: 500 }
    )
  }
}
