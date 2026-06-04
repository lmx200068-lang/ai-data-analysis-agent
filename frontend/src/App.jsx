import { useCallback, useEffect, useMemo, useState } from 'react'
import './App.css'

const DEFAULT_API_BASE_URL = 'http://127.0.0.1:8000'
const DEFAULT_CSV_PATH = 'SuperMarket Analysis.csv'
const DEFAULT_SQLITE_PATH = 'supermarket_demo.db'

const CSV_PROMPTS = [
  '这个超市的核心业务指标怎么样？',
  '按 Product line 分析业务表现',
  '不同 City 的销售表现如何？',
  '每天 Sales 趋势如何？',
  'Sales 和哪些字段相关性最高？',
  '帮我整体分析一下这个超市销售数据',
]

const SQLITE_PROMPTS = [
  '这个数据库有哪些表？',
  'supermarket_sales 表有哪些字段？',
  '预览 supermarket_sales 表前 5 行',
  '哪个城市销售额最高？',
  '按 Product line 统计总销售额并排序',
  '不同 Payment 的订单数和总销售额是多少？',
]

function App() {
  const [apiBaseUrl, setApiBaseUrl] = useState(DEFAULT_API_BASE_URL)
  const [backendStatus, setBackendStatus] = useState('checking')
  const [sourceKind, setSourceKind] = useState('csv')
  const [csvMode, setCsvMode] = useState('local')
  const [csvPath, setCsvPath] = useState(DEFAULT_CSV_PATH)
  const [sqlitePath, setSqlitePath] = useState(DEFAULT_SQLITE_PATH)
  const [uploadFile, setUploadFile] = useState(null)
  const [source, setSource] = useState(null)
  const [selectedTable, setSelectedTable] = useState('')
  const [tableSchema, setTableSchema] = useState(null)
  const [tablePreview, setTablePreview] = useState(null)
  const [messages, setMessages] = useState([])
  const [question, setQuestion] = useState('')
  const [loading, setLoading] = useState(false)
  const [notice, setNotice] = useState('')

  const apiRoot = useMemo(() => apiBaseUrl.trim().replace(/\/$/, ''), [apiBaseUrl])
  const prompts = source?.kind === 'sqlite' ? SQLITE_PROMPTS : CSV_PROMPTS

  const apiRequest = useCallback(
    async (path, options = {}) => {
      const response = await fetch(`${apiRoot}${path}`, options)
      const data = await response.json().catch(() => null)

      if (!response.ok) {
        const detail = data?.detail || response.statusText
        throw new Error(typeof detail === 'string' ? detail : JSON.stringify(detail))
      }

      return data
    },
    [apiRoot],
  )

  const checkBackend = useCallback(async () => {
    setBackendStatus('checking')

    try {
      await apiRequest('/health')
      setBackendStatus('online')
    } catch {
      setBackendStatus('offline')
    }
  }, [apiRequest])

  const loadTableDetails = useCallback(
    async (tableName) => {
      if (!source?.id || source.kind !== 'sqlite' || !tableName) return

      try {
        const encodedTable = encodeURIComponent(tableName)
        const schema = await apiRequest(`/databases/${source.id}/tables/${encodedTable}/schema`)
        const preview = await apiRequest(`/databases/${source.id}/tables/${encodedTable}/preview?limit=20`)
        setTableSchema(schema.table_schema)
        setTablePreview(preview.preview)
      } catch (error) {
        setNotice(`读取表信息失败：${error.message}`)
      }
    },
    [apiRequest, source],
  )

  useEffect(() => {
    checkBackend()
  }, [checkBackend])

  useEffect(() => {
    if (source?.kind === 'sqlite' && source.tables?.length) {
      setSelectedTable(source.tables[0])
      return
    }

    setSelectedTable('')
    setTableSchema(null)
    setTablePreview(null)
  }, [source])

  useEffect(() => {
    if (source?.kind === 'sqlite' && selectedTable) {
      loadTableDetails(selectedTable)
    }
  }, [loadTableDetails, selectedTable, source])

  function resetConversation() {
    setMessages([])
    setQuestion('')
  }

  async function loadLocalCsv() {
    setLoading(true)
    setNotice('')

    try {
      const summary = await apiRequest('/datasets/load-local', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ path: csvPath }),
      })

      setSource({ kind: 'csv', id: summary.dataset_id, label: summary.filename, summary })
      resetConversation()
      setNotice('CSV 已加载')
    } catch (error) {
      setNotice(`加载失败：${error.message}`)
    } finally {
      setLoading(false)
    }
  }

  async function uploadCsv() {
    if (!uploadFile) {
      setNotice('请先选择 CSV 文件')
      return
    }

    setLoading(true)
    setNotice('')

    try {
      const formData = new FormData()
      formData.append('file', uploadFile)

      const summary = await apiRequest('/datasets/upload', {
        method: 'POST',
        body: formData,
      })

      setSource({ kind: 'csv', id: summary.dataset_id, label: summary.filename, summary })
      resetConversation()
      setNotice('CSV 已上传并加载')
    } catch (error) {
      setNotice(`上传失败：${error.message}`)
    } finally {
      setLoading(false)
    }
  }

  async function connectSqlite() {
    setLoading(true)
    setNotice('')

    try {
      const summary = await apiRequest('/databases/connect-sqlite', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ path: sqlitePath }),
      })

      setSource({ kind: 'sqlite', id: summary.database_id, label: summary.filename, tables: summary.tables })
      resetConversation()
      setNotice('SQLite 已连接')
    } catch (error) {
      setNotice(`连接失败：${error.message}`)
    } finally {
      setLoading(false)
    }
  }

  async function sendQuestion(text) {
    const trimmed = text.trim()
    if (!trimmed || !source || loading) return

    setMessages((current) => [...current, { role: 'user', content: trimmed }])
    setQuestion('')
    setLoading(true)
    setNotice('')

    try {
      const payload =
        source.kind === 'csv'
          ? await apiRequest('/chat', {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({ dataset_id: source.id, question: trimmed }),
            })
          : await apiRequest(`/databases/${source.id}/chat`, {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({ database_id: source.id, question: trimmed }),
            })

      setMessages((current) => [
        ...current,
        {
          role: 'assistant',
          content: payload.answer,
          charts: payload.charts || [],
          toolCalls: payload.tool_calls || [],
        },
      ])
    } catch (error) {
      setMessages((current) => [
        ...current,
        {
          role: 'assistant',
          content: `运行出错：${error.message}`,
          charts: [],
          toolCalls: [],
        },
      ])
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand">
          <div className="brand-mark">DA</div>
          <div>
            <h1>Data Agent</h1>
            <p>多源数据分析工作台</p>
          </div>
        </div>

        <section className="sidebar-section">
          <div className="section-title">后端服务</div>
          <label className="field-label" htmlFor="api-url">
            FastAPI 地址
          </label>
          <input
            id="api-url"
            value={apiBaseUrl}
            onChange={(event) => setApiBaseUrl(event.target.value)}
            className="text-input"
          />
          <div className={`status-pill ${backendStatus}`}>
            <span></span>
            {backendStatus === 'online' ? '已连接' : backendStatus === 'checking' ? '检查中' : '未连接'}
          </div>
        </section>

        <section className="sidebar-section">
          <div className="section-title">数据源</div>
          <div className="segmented">
            <button type="button" className={sourceKind === 'csv' ? 'active' : ''} onClick={() => setSourceKind('csv')}>
              CSV
            </button>
            <button
              type="button"
              className={sourceKind === 'sqlite' ? 'active' : ''}
              onClick={() => setSourceKind('sqlite')}
            >
              SQLite
            </button>
          </div>

          {sourceKind === 'csv' && (
            <div className="source-form">
              <div className="segmented compact">
                <button type="button" className={csvMode === 'local' ? 'active' : ''} onClick={() => setCsvMode('local')}>
                  本地路径
                </button>
                <button type="button" className={csvMode === 'upload' ? 'active' : ''} onClick={() => setCsvMode('upload')}>
                  上传文件
                </button>
              </div>

              {csvMode === 'local' ? (
                <>
                  <label className="field-label" htmlFor="csv-path">
                    CSV 路径
                  </label>
                  <textarea
                    id="csv-path"
                    rows="3"
                    value={csvPath}
                    onChange={(event) => setCsvPath(event.target.value)}
                    className="text-area"
                  />
                  <button type="button" className="primary-button" onClick={loadLocalCsv} disabled={loading}>
                    加载 CSV
                  </button>
                </>
              ) : (
                <>
                  <label className="file-drop">
                    <input type="file" accept=".csv" onChange={(event) => setUploadFile(event.target.files?.[0] || null)} />
                    <span>{uploadFile ? uploadFile.name : '选择 CSV 文件'}</span>
                  </label>
                  <button type="button" className="primary-button" onClick={uploadCsv} disabled={loading}>
                    上传并加载
                  </button>
                </>
              )}
            </div>
          )}

          {sourceKind === 'sqlite' && (
            <div className="source-form">
              <label className="field-label" htmlFor="sqlite-path">
                SQLite 路径
              </label>
              <textarea
                id="sqlite-path"
                rows="3"
                value={sqlitePath}
                onChange={(event) => setSqlitePath(event.target.value)}
                className="text-area"
              />
              <button type="button" className="primary-button" onClick={connectSqlite} disabled={loading}>
                连接 SQLite
              </button>
            </div>
          )}

          {notice && <div className="notice">{notice}</div>}
        </section>

        {source && (
          <section className="sidebar-section">
            <div className="section-title">当前数据源</div>
            <div className="source-card">
              <span className="source-type">{source.kind.toUpperCase()}</span>
              <strong>{source.label}</strong>
              <small>{source.id}</small>
            </div>
            <button type="button" className="secondary-button" onClick={resetConversation}>
              清空对话
            </button>
          </section>
        )}
      </aside>

      <main className="workspace">
        <header className="topbar">
          <div>
            <p className="eyebrow">FastAPI + LangChain + React</p>
            <h2>多源数据分析 Agent</h2>
          </div>
          <div className="topbar-actions">
            <span>{source ? `当前：${source.label}` : '尚未加载数据源'}</span>
          </div>
        </header>

        {!source ? (
          <div className="empty-state">
            <h3>选择一个数据源开始分析</h3>
            <p>左侧可以加载 CSV 文件，或连接本地 SQLite 数据库。前端只负责交互，真实分析由 FastAPI 后端和 Agent 工具完成。</p>
          </div>
        ) : (
          <div className="content-grid">
            <section className="data-panel">
              <SourcePanel
                source={source}
                selectedTable={selectedTable}
                setSelectedTable={setSelectedTable}
                tableSchema={tableSchema}
                tablePreview={tablePreview}
              />
            </section>

            <section className="chat-panel">
              <div className="panel-heading">
                <h3>对话分析</h3>
                {loading && <span className="loading-text">分析中...</span>}
              </div>

              <div className="prompt-grid">
                {prompts.map((prompt) => (
                  <button type="button" key={prompt} onClick={() => sendQuestion(prompt)} disabled={loading}>
                    {prompt}
                  </button>
                ))}
              </div>

              <div className="message-list">
                {messages.map((message, index) => (
                  <Message key={`${message.role}-${index}`} message={message} />
                ))}
              </div>

              <form
                className="chat-input-row"
                onSubmit={(event) => {
                  event.preventDefault()
                  sendQuestion(question)
                }}
              >
                <input
                  value={question}
                  onChange={(event) => setQuestion(event.target.value)}
                  placeholder="输入你的数据分析问题"
                  disabled={loading}
                />
                <button type="submit" disabled={loading || !question.trim()}>
                  发送
                </button>
              </form>
            </section>
          </div>
        )}
      </main>
    </div>
  )
}

function SourcePanel({ source, selectedTable, setSelectedTable, tableSchema, tablePreview }) {
  if (source.kind === 'csv') {
    const summary = source.summary
    const numericColumns = summary.numeric_columns || []
    const categoricalColumns = summary.categorical_columns || []

    return (
      <>
        <div className="metric-row">
          <Metric label="Rows" value={summary.rows} />
          <Metric label="Columns" value={summary.columns.length} />
          <Metric label="Numeric" value={numericColumns.length} />
        </div>

        <DataSection title="数据预览">
          <DataTable rows={summary.preview} />
        </DataSection>

        <DataSection title="字段信息">
          <FieldList label="全部字段" values={summary.columns} />
          <FieldList label="数值字段" values={numericColumns} />
          <FieldList label="类别字段" values={categoricalColumns} />
        </DataSection>
      </>
    )
  }

  return (
    <>
      <div className="metric-row">
        <Metric label="Tables" value={source.tables.length} />
        <Metric label="Database" value={source.label} />
      </div>

      <DataSection title="数据表">
        <select className="table-select" value={selectedTable} onChange={(event) => setSelectedTable(event.target.value)}>
          {source.tables.map((table) => (
            <option key={table} value={table}>
              {table}
            </option>
          ))}
        </select>
      </DataSection>

      <DataSection title="表预览">
        <DataTable rows={tablePreview?.rows || []} />
      </DataSection>

      <DataSection title="表结构">
        <DataTable rows={tableSchema?.columns || []} />
      </DataSection>
    </>
  )
}

function Message({ message }) {
  return (
    <article className={`message ${message.role}`}>
      <div className="message-role">{message.role === 'user' ? '你' : 'Agent'}</div>
      <div className="message-body">
        <TextBlock text={message.content} />
        <ChartRenderer charts={message.charts || []} />
        <ToolCalls toolCalls={message.toolCalls || []} />
      </div>
    </article>
  )
}

function TextBlock({ text }) {
  return (
    <div className="text-block">
      {String(text || '')
        .split('\n')
        .filter(Boolean)
        .map((line, index) => (
          <p key={`${line}-${index}`}>{renderInlineMarkdown(line)}</p>
        ))}
    </div>
  )
}

function renderInlineMarkdown(line) {
  const parts = line.split(/(\*\*[^*]+\*\*)/g)

  return parts.map((part, index) => {
    if (part.startsWith('**') && part.endsWith('**')) {
      return <strong key={index}>{part.slice(2, -2)}</strong>
    }

    return <span key={index}>{part}</span>
  })
}

function ChartRenderer({ charts }) {
  if (!charts?.length) return null

  return (
    <div className="chart-stack">
      {charts.map((chart, index) => {
        if (chart.type === 'metric') return <MetricChart key={index} chart={chart} />
        if (chart.type === 'bar') return <BarChart key={index} chart={chart} />
        if (chart.type === 'line') return <LineChart key={index} chart={chart} />
        if (chart.type === 'table') {
          return (
            <DataSection key={index} title={chart.title}>
              <DataTable rows={chart.data || []} />
            </DataSection>
          )
        }

        return null
      })}
    </div>
  )
}

function MetricChart({ chart }) {
  return (
    <DataSection title={chart.title}>
      <div className="metric-row chart-metrics">
        {(chart.data || []).map((item) => (
          <Metric key={item.label} label={item.label} value={item.value} />
        ))}
      </div>
    </DataSection>
  )
}

function BarChart({ chart }) {
  const rows = chart.data || []
  if (!rows.length) return null

  const maxValue = Math.max(...rows.map((row) => Math.abs(Number(row[chart.y]) || 0)), 1)

  return (
    <DataSection title={chart.title}>
      <div className="bar-chart">
        {rows.map((row, index) => {
          const value = Number(row[chart.y]) || 0
          const height = Math.max((Math.abs(value) / maxValue) * 180, 4)

          return (
            <div className="bar-item" key={`${row[chart.x]}-${index}`}>
              <div className="bar-value">{formatNumber(value)}</div>
              <div className="bar-track">
                <div className="bar-fill" style={{ height: `${height}px` }}></div>
              </div>
              <div className="bar-label" title={String(row[chart.x])}>
                {String(row[chart.x])}
              </div>
            </div>
          )
        })}
      </div>
    </DataSection>
  )
}

function LineChart({ chart }) {
  const rows = chart.data || []
  if (!rows.length) return null

  const width = 680
  const height = 240
  const padding = 28
  const values = rows.map((row) => Number(row[chart.y]) || 0)
  const min = Math.min(...values)
  const max = Math.max(...values)
  const span = max - min || 1

  const points = rows.map((row, index) => {
    const x = padding + (index / Math.max(rows.length - 1, 1)) * (width - padding * 2)
    const y = height - padding - ((Number(row[chart.y]) - min) / span) * (height - padding * 2)
    return { x, y, label: row[chart.x] }
  })

  const pointString = points.map((point) => `${point.x},${point.y}`).join(' ')

  return (
    <DataSection title={chart.title}>
      <div className="line-chart">
        <svg viewBox={`0 0 ${width} ${height}`} role="img" aria-label={chart.title}>
          <line x1={padding} y1={height - padding} x2={width - padding} y2={height - padding} className="axis" />
          <line x1={padding} y1={padding} x2={padding} y2={height - padding} className="axis" />
          <polyline points={pointString} className="line" fill="none" />
          {points.map((point, index) => (
            <circle key={`${point.label}-${index}`} cx={point.x} cy={point.y} r="3" className="point" />
          ))}
        </svg>
        <div className="line-summary">
          <span>最小值 {formatNumber(min)}</span>
          <span>最大值 {formatNumber(max)}</span>
        </div>
      </div>
    </DataSection>
  )
}

function ToolCalls({ toolCalls }) {
  if (!toolCalls.length) return null

  return (
    <details className="tool-details">
      <summary>工具调用</summary>
      {toolCalls.map((tool, index) => (
        <div className="tool-call" key={`${tool.name}-${index}`}>
          <strong>{tool.name}</strong>
          <pre>{JSON.stringify({ args: tool.args, result: tool.result }, null, 2)}</pre>
        </div>
      ))}
    </details>
  )
}

function DataSection({ title, children }) {
  return (
    <section className="data-section">
      <h4>{title}</h4>
      {children}
    </section>
  )
}

function DataTable({ rows }) {
  if (!rows?.length) return <div className="muted">暂无数据</div>

  const columns = Object.keys(rows[0])

  return (
    <div className="table-wrap">
      <table>
        <thead>
          <tr>
            {columns.map((column) => (
              <th key={column}>{column}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, index) => (
            <tr key={index}>
              {columns.map((column) => (
                <td key={column}>{formatCell(row[column])}</td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

function FieldList({ label, values }) {
  return (
    <div className="field-list">
      <strong>{label}</strong>
      <p>{values?.length ? values.join(', ') : '无'}</p>
    </div>
  )
}

function Metric({ label, value }) {
  return (
    <div className="metric">
      <span>{label}</span>
      <strong>{formatNumber(value)}</strong>
    </div>
  )
}

function formatCell(value) {
  if (typeof value === 'number') return formatNumber(value)
  if (value === null || value === undefined) return ''
  return String(value)
}

function formatNumber(value) {
  if (typeof value !== 'number') return String(value)

  return value.toLocaleString('zh-CN', {
    maximumFractionDigits: 2,
  })
}

export default App
