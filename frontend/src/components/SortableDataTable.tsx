// Tabla reutilizable: columna N°, orden por encabezado y selector de orden.
/* eslint-disable @typescript-eslint/no-explicit-any */
import { useMemo, useState } from 'react'
import {
  Box, Button, Table, TableBody, TableCell, TableContainer, TableHead, TableRow,
  Paper, Alert, TableSortLabel, FormControl, InputLabel, Select, MenuItem, Typography,
} from '@mui/material'
import type { SxProps, Theme } from '@mui/material/styles'
import { Download } from '@mui/icons-material'

export type ExportColumn = { key: string; label: string }

export type SortDir = 'asc' | 'desc'

export type SortableColumn<T = Record<string, unknown>> = {
  key: string
  label: string
  align?: 'left' | 'right' | 'center'
  /** Por defecto true; false en columnas de acciones o decorativas. */
  sortable?: boolean
  sortValue?: (row: T) => string | number | null | undefined
  render?: (value: unknown, row: T, index: number) => React.ReactNode
}

export type SortableDataTableProps<T = Record<string, unknown>> = {
  rows: T[]
  columns: SortableColumn<T>[]
  exportName?: string
  exportColumns?: ExportColumn[]
  rowKey?: (row: T, index: number) => string | number
  getRowSx?: (row: T) => SxProps<Theme> | undefined
  /** Si se entrega, la fila completa es clickeable (cursor pointer + onClick). */
  onRowClick?: (row: T) => void
  enumerate?: boolean
  enumLabel?: string
  defaultSort?: { key: string; dir: SortDir }
  maxHeight?: number | string
  headerBg?: string
  emptyMessage?: string
  dense?: boolean
  showSortSelector?: boolean
}

function compareValues(a: unknown, b: unknown, dir: SortDir): number {
  const mul = dir === 'asc' ? 1 : -1
  if (a == null && b == null) return 0
  if (a == null) return 1 * mul
  if (b == null) return -1 * mul
  if (typeof a === 'number' && typeof b === 'number' && !Number.isNaN(a) && !Number.isNaN(b)) {
    return (a - b) * mul
  }
  const sa = String(a).trim().toLowerCase()
  const sb = String(b).trim().toLowerCase()
  const na = Number(sa.replace(/[^\d.-]/g, ''))
  const nb = Number(sb.replace(/[^\d.-]/g, ''))
  if (sa !== '' && sb !== '' && !Number.isNaN(na) && !Number.isNaN(nb) && /^\d/.test(sa) && /^\d/.test(sb)) {
    return (na - nb) * mul
  }
  return sa.localeCompare(sb, 'es', { sensitivity: 'base' }) * mul
}

function isSortable<T>(col: SortableColumn<T>): boolean {
  return col.sortable !== false && !col.key.startsWith('_')
}

export function SortableDataTable<T extends Record<string, any>>({
  rows,
  columns,
  exportName,
  exportColumns: _exportColumns,
  rowKey,
  getRowSx,
  onRowClick,
  enumerate = true,
  enumLabel = 'N°',
  defaultSort,
  maxHeight = 440,
  headerBg = 'primary.main',
  emptyMessage = 'No hay filas para mostrar.',
  dense = true,
  showSortSelector = false,
}: SortableDataTableProps<T>) {
  const sortableColumns = useMemo(() => columns.filter(isSortable), [columns])
  const firstSortKey = defaultSort?.key ?? sortableColumns[0]?.key ?? ''

  const [sortKey, setSortKey] = useState(firstSortKey)
  const [sortDir, setSortDir] = useState<SortDir>(defaultSort?.dir ?? 'asc')

  const sortedRows = useMemo(() => {
    if (!sortKey) return rows
    const col = columns.find((c) => c.key === sortKey)
    if (!col || !isSortable(col)) return rows
    return [...rows].sort((ra, rb) => {
      const va = col.sortValue ? col.sortValue(ra) : ra[col.key]
      const vb = col.sortValue ? col.sortValue(rb) : rb[col.key]
      return compareValues(va, vb, sortDir)
    })
  }, [rows, sortKey, sortDir, columns])

  const handleSort = (key: string) => {
    const col = columns.find((c) => c.key === key)
    if (!col || !isSortable(col)) return
    if (sortKey === key) {
      setSortDir((d) => (d === 'asc' ? 'desc' : 'asc'))
    } else {
      setSortKey(key)
      setSortDir('asc')
    }
  }

  if (!rows.length) {
    return <Alert severity="info" sx={{ borderRadius: 2 }}>{emptyMessage}</Alert>
  }

  const headerCellSx = {
    bgcolor: headerBg,
    color: '#fff',
    fontWeight: 700,
    whiteSpace: 'nowrap' as const,
    fontSize: dense ? 12 : 13,
  }

  return (
    <Box>
      <Box sx={{ display: 'flex', justifyContent: 'flex-end', alignItems: 'center', flexWrap: 'wrap', gap: 1, mb: exportName ? 1 : 0 }}>
        {showSortSelector && sortableColumns.length > 1 && (
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, flexWrap: 'wrap' }}>
            <Typography variant="caption" color="text.secondary">Ordenar por:</Typography>
            <FormControl size="small" sx={{ minWidth: 160 }}>
              <InputLabel>Columna</InputLabel>
              <Select
                label="Columna"
                value={sortKey}
                onChange={(e) => setSortKey(String(e.target.value))}
              >
                {sortableColumns.map((c) => (
                  <MenuItem key={c.key} value={c.key}>{c.label}</MenuItem>
                ))}
              </Select>
            </FormControl>
            <FormControl size="small" sx={{ minWidth: 120 }}>
              <InputLabel>Dirección</InputLabel>
              <Select
                label="Dirección"
                value={sortDir}
                onChange={(e) => setSortDir(e.target.value as SortDir)}
              >
                <MenuItem value="asc">Ascendente (A→Z)</MenuItem>
                <MenuItem value="desc">Descendente (Z→A)</MenuItem>
              </Select>
            </FormControl>
            <Typography variant="caption" color="text.disabled">
              {sortedRows.length} fila(s)
            </Typography>
          </Box>
        )}
        {exportName && (
          <Button size="small" startIcon={<Download />} disabled title="Exportación no configurada">
            Exportar Excel
          </Button>
        )}
      </Box>

      <TableContainer component={Paper} variant="outlined" sx={{ borderRadius: 2, maxHeight }}>
        <Table size={dense ? 'small' : 'medium'} stickyHeader>
          <TableHead>
            <TableRow>
              {enumerate && (
                <TableCell align="center" sx={{ ...headerCellSx, width: 48, minWidth: 48 }}>
                  {enumLabel}
                </TableCell>
              )}
              {columns.map((c) => (
                <TableCell key={c.key} align={c.align} sx={headerCellSx}>
                  {isSortable(c) ? (
                    <TableSortLabel
                      active={sortKey === c.key}
                      direction={sortKey === c.key ? sortDir : 'asc'}
                      onClick={() => handleSort(c.key)}
                      sx={{
                        color: 'inherit !important',
                        '& .MuiTableSortLabel-icon': { color: 'inherit !important', opacity: sortKey === c.key ? 1 : 0.5 },
                      }}
                    >
                      {c.label}
                    </TableSortLabel>
                  ) : (
                    c.label
                  )}
                </TableCell>
              ))}
            </TableRow>
          </TableHead>
          <TableBody>
            {sortedRows.map((row, i) => (
              <TableRow
                key={rowKey ? rowKey(row, i) : row.id ?? i}
                hover
                onClick={onRowClick ? () => onRowClick(row) : undefined}
                sx={[
                  onRowClick ? { cursor: 'pointer' } : false,
                  getRowSx?.(row) as any,
                ]}
              >
                {enumerate && (
                  <TableCell align="center" sx={{ fontWeight: 600, color: 'text.secondary', fontSize: 12 }}>
                    {i + 1}
                  </TableCell>
                )}
                {columns.map((c) => (
                  <TableCell key={c.key} align={c.align} sx={{ fontSize: dense ? 12.5 : 14, whiteSpace: 'nowrap' }}>
                    {c.render ? c.render(row[c.key], row, i) : (row[c.key] ?? '—')}
                  </TableCell>
                ))}
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </TableContainer>
    </Box>
  )
}
