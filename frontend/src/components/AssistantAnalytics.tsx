import { useState } from 'react'
import {
  Box, Button, Collapse, Paper, Table, TableBody, TableCell, TableHead, TableRow, Typography,
} from '@mui/material'
import BarChartIcon from '@mui/icons-material/BarChart'
import ExpandLessIcon from '@mui/icons-material/ExpandLess'
import ExpandMoreIcon from '@mui/icons-material/ExpandMore'
import TrendingDownIcon from '@mui/icons-material/TrendingDown'
import TrendingFlatIcon from '@mui/icons-material/TrendingFlat'
import TrendingUpIcon from '@mui/icons-material/TrendingUp'
import {
  Bar, BarChart, CartesianGrid, Cell, Legend, Line, LineChart,
  Pie, PieChart, ResponsiveContainer, Tooltip, XAxis, YAxis,
} from 'recharts'
import type { AnalyticsPayload } from '../api/client'
import Reveal from './Reveal'

const REVEAL_STEP_MS = 90

const CHART_COLORS = ['#1a365d', '#2d6a9f', '#3182ce', '#4299e1', '#63b3ed', '#90cdf4']
const PIE_COLORS = ['#1a365d', '#c53030', '#2d6a9f', '#d69e2e', '#38a169', '#805ad5']

function formatValue(value: number, format: string): string {
  if (format === 'clp') {
    if (Math.abs(value) >= 1_000_000) return `$${(value / 1_000_000).toFixed(1)}M`
    if (Math.abs(value) >= 1_000) return `$${(value / 1_000).toFixed(0)}K`
    return `$${value.toLocaleString('es-CL')}`
  }
  if (format === 'pct') return `${value.toFixed(1)}%`
  return value.toLocaleString('es-CL')
}

export function hasVisualAnalytics(analytics: AnalyticsPayload): boolean {
  return analytics.charts.length > 0 || analytics.tables.length > 0
}

export function userAskedForCharts(text: string): boolean {
  return /gr[aá]fic|visual|desglose|detalle(s)?\s+(en|con)\s+(gr[aá]fic|visual)|mu[eé]strame|muestra(me)?\s+(el|los)\s+gr[aá]fic/i.test(text)
}

export function userAskedForLineChart(text: string): boolean {
  return /lineal|tendencia|evoluci[oó]n|curva/i.test(text)
}

function splitCharts(charts: AnalyticsPayload['charts']) {
  const primary = charts.filter((c) => !c.optional)
  const optional = charts.filter((c) => c.optional)
  return { primary, optional }
}

export function AssistantComparison({ comparisons }: { comparisons: AnalyticsPayload['comparisons'] }) {
  if (!comparisons.length) return null

  return (
    <Reveal delay={60}>
      <Box sx={{ display: 'flex', gap: 1.5, flexWrap: 'wrap', mt: 2, pt: 2, borderTop: '1px solid', borderColor: 'divider' }}>
        {comparisons.map((c, i) => {
          const up = c.change_pct > 0
          const flat = Math.abs(c.change_pct) < 0.5
          const Icon = flat ? TrendingFlatIcon : up ? TrendingUpIcon : TrendingDownIcon
          const color = flat ? 'text.secondary' : up ? 'success.main' : 'error.main'
          return (
            <Paper key={i} variant="outlined" sx={{ p: 1.5, minWidth: 200, flex: '1 1 200px' }}>
              <Typography variant="caption" color="text.secondary" sx={{ fontWeight: 600 }}>
                {c.label}
              </Typography>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5, mt: 0.5 }}>
                <Icon sx={{ fontSize: 20, color }} />
                <Typography variant="h6" sx={{ fontWeight: 700, color }}>
                  {c.unit === 'clp' && c.value_a > 0 && c.value_b > 0
                    ? `${c.change_pct > 0 ? '+' : ''}${c.change_pct.toFixed(1)}%`
                    : `${c.change_pct.toFixed(1)}%`}
                </Typography>
              </Box>
              {c.unit === 'clp' && c.value_a > 0 && (
                <Typography variant="body2" color="text.secondary" sx={{ mt: 0.5 }}>
                  {c.period_a}: {formatValue(c.value_a, 'clp')} → {c.period_b}: {formatValue(c.value_b, 'clp')}
                </Typography>
              )}
            </Paper>
          )
        })}
      </Box>
    </Reveal>
  )
}

function AnalyticsChart({ chart }: { chart: AnalyticsPayload['charts'][0] }) {
  if (chart.chart_type === 'pie') {
    const data = chart.labels.map((label, i) => ({
      name: label,
      value: chart.datasets[0]?.values[i] ?? 0,
    }))
    const total = data.reduce((sum, item) => sum + item.value, 0)
    const renderPieLabel = ({
      name,
      value,
    }: {
      name?: string
      value?: number
    }) => {
      if (!name || value == null || total <= 0) return ''
      const pct = ((value / total) * 100).toFixed(0)
      return `${name} · ${formatValue(value, chart.value_format)} (${pct}%)`
    }

    return (
      <Box sx={{ width: '100%', height: 340, minHeight: 340 }}>
        <ResponsiveContainer width="100%" height="100%">
          <PieChart margin={{ top: 28, right: 32, left: 32, bottom: 12 }}>
            <Pie
              data={data}
              dataKey="value"
              nameKey="name"
              cx="50%"
              cy="46%"
              innerRadius={58}
              outerRadius={92}
              paddingAngle={2}
              label={renderPieLabel}
              labelLine={{ stroke: '#718096', strokeWidth: 1 }}
              isAnimationActive
              animationDuration={700}
              animationEasing="linear"
            >
              {data.map((_, i) => (
                <Cell key={i} fill={PIE_COLORS[i % PIE_COLORS.length]} />
              ))}
            </Pie>
            <Tooltip formatter={(v: number) => formatValue(v, chart.value_format)} />
            <Legend verticalAlign="bottom" wrapperStyle={{ paddingTop: 12 }} />
          </PieChart>
        </ResponsiveContainer>
      </Box>
    )
  }

  const data = chart.labels.map((label, i) => {
    const row: Record<string, string | number> = { label }
    chart.datasets.forEach((ds) => {
      row[ds.label] = ds.values[i] ?? 0
    })
    return row
  })

  const ChartComponent = chart.chart_type === 'line' ? LineChart : BarChart

  return (
    <Box sx={{ width: '100%', height: 300, minHeight: 300 }}>
      <ResponsiveContainer width="100%" height="100%">
        <ChartComponent data={data} margin={{ top: 12, right: 16, left: 4, bottom: 8 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
          <XAxis
            dataKey="label"
            tick={{ fontSize: 11 }}
            angle={chart.labels.some((l) => l.length > 12) ? -28 : 0}
            textAnchor={chart.labels.some((l) => l.length > 12) ? 'end' : 'middle'}
            height={chart.labels.some((l) => l.length > 12) ? 72 : 32}
            interval={0}
            tickFormatter={(v: string) => (v.length > 20 ? `${v.slice(0, 18)}…` : v)}
          />
          <YAxis tickFormatter={(v) => formatValue(Number(v), chart.value_format)} tick={{ fontSize: 11 }} width={72} />
          <Tooltip formatter={(v: number) => formatValue(v, chart.value_format)} />
          <Legend />
          {chart.datasets.map((ds, i) =>
            chart.chart_type === 'line' ? (
              <Line
                key={ds.label}
                type="monotone"
                dataKey={ds.label}
                stroke={CHART_COLORS[i % CHART_COLORS.length]}
                strokeWidth={2}
                dot={{ r: 4 }}
                isAnimationActive
                animationDuration={700}
                animationEasing="linear"
              />
            ) : (
              <Bar
                key={ds.label}
                dataKey={ds.label}
                fill={CHART_COLORS[i % CHART_COLORS.length]}
                radius={[4, 4, 0, 0]}
                isAnimationActive
                animationDuration={700}
                animationEasing="linear"
              />
            ),
          )}
        </ChartComponent>
      </ResponsiveContainer>
    </Box>
  )
}

function AnalyticsTable({ table }: { table: AnalyticsPayload['tables'][0] }) {
  return (
    <Box sx={{ overflowX: 'auto', mb: 2 }}>
      <Table size="small">
        <TableHead>
          <TableRow sx={{ bgcolor: '#f7fafc' }}>
            {table.columns.map((col) => (
              <TableCell key={col} sx={{ fontWeight: 700 }}>{col}</TableCell>
            ))}
          </TableRow>
        </TableHead>
        <TableBody>
          {table.rows.map((row, i) => (
            <TableRow key={i} hover>
              {row.map((cell, j) => (
                <TableCell key={j}>{cell}</TableCell>
              ))}
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </Box>
  )
}

export function AssistantChartsPanel({
  analytics,
  showOptional = false,
  userQuestion = '',
}: {
  analytics: AnalyticsPayload
  showOptional?: boolean
  userQuestion?: string
}) {
  if (!hasVisualAnalytics(analytics)) return null

  const { primary, optional } = splitCharts(analytics.charts)
  const chartsToShow = showOptional || userAskedForLineChart(userQuestion)
    ? [...primary, ...optional]
    : primary

  let revealIndex = 0
  const nextDelay = () => {
    const delay = revealIndex * REVEAL_STEP_MS
    revealIndex += 1
    return delay
  }

  return (
    <Box sx={{ mt: 1.5 }}>
      <Reveal delay={nextDelay()}>
        <Typography variant="caption" color="primary" sx={{ fontWeight: 700, mb: 1.5, display: 'block' }}>
          Detalle visual
        </Typography>
      </Reveal>

      {chartsToShow.map((chart) => (
        <Reveal key={chart.id} delay={nextDelay()}>
          <Paper variant="outlined" sx={{ p: 2, mb: 2, bgcolor: '#fafbfc', overflow: 'visible' }}>
            <Typography variant="subtitle2" sx={{ fontWeight: 700, mb: 1.5 }}>
              {chart.title}
            </Typography>
            <AnalyticsChart chart={chart} />
          </Paper>
        </Reveal>
      ))}

      {analytics.tables.map((table) => (
        <Reveal key={table.id} delay={nextDelay()}>
          <Paper variant="outlined" sx={{ p: 2, mb: 2, bgcolor: '#fafbfc' }}>
            <Typography variant="subtitle2" sx={{ fontWeight: 700, mb: 1 }}>
              {table.title}
            </Typography>
            <AnalyticsTable table={table} />
          </Paper>
        </Reveal>
      ))}
    </Box>
  )
}

interface AssistantAnalyticsProps {
  analytics: AnalyticsPayload
  chartsExpanded: boolean
  onToggleCharts: () => void
  streaming?: boolean
  userQuestion?: string
}

export default function AssistantAnalytics({
  analytics,
  chartsExpanded,
  onToggleCharts,
  streaming = false,
  userQuestion = '',
}: AssistantAnalyticsProps) {
  const hasCharts = hasVisualAnalytics(analytics)
  const hasComparisons = analytics.comparisons.length > 0
  const { optional } = splitCharts(analytics.charts)
  const [showOptional, setShowOptional] = useState(userAskedForLineChart(userQuestion))

  if (!hasCharts && !hasComparisons) return null

  return (
    <>
      {hasCharts && !streaming && (
        <Box sx={{ mt: 1.5 }}>
          <Button
            size="small"
            variant="outlined"
            startIcon={chartsExpanded ? <ExpandLessIcon /> : <BarChartIcon />}
            endIcon={chartsExpanded ? undefined : <ExpandMoreIcon />}
            onClick={onToggleCharts}
            sx={{ textTransform: 'none', borderColor: '#1a365d', color: '#1a365d' }}
          >
            {chartsExpanded ? 'Ocultar gráficos y tablas' : 'Ver gráficos y tablas'}
          </Button>
          <Collapse in={chartsExpanded} unmountOnExit>
            <AssistantChartsPanel
              analytics={analytics}
              showOptional={showOptional}
              userQuestion={userQuestion}
            />
            {optional.length > 0 && !showOptional && (
              <Button
                size="small"
                variant="text"
                onClick={() => setShowOptional(true)}
                sx={{ textTransform: 'none', color: '#1a365d', mt: 0.5 }}
              >
                Ver gráfico de tendencia (lineal)
              </Button>
            )}
            {optional.length > 0 && showOptional && (
              <Button
                size="small"
                variant="text"
                onClick={() => setShowOptional(false)}
                sx={{ textTransform: 'none', color: 'text.secondary', mt: 0.5 }}
              >
                Ocultar gráfico lineal
              </Button>
            )}
          </Collapse>
        </Box>
      )}

      {hasComparisons && !streaming && (
        <AssistantComparison comparisons={analytics.comparisons} />
      )}
    </>
  )
}
