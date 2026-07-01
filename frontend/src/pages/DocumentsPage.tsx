import { useCallback, useEffect, useState } from 'react'
import {
  Alert, Box, Chip, CircularProgress, IconButton, Paper,
  Table, TableBody, TableCell, TableHead, TableRow, Typography,
} from '@mui/material'
import CloudUploadIcon from '@mui/icons-material/CloudUpload'
import DeleteIcon from '@mui/icons-material/Delete'
import RefreshIcon from '@mui/icons-material/Refresh'
import { deleteDocument, listDocuments, uploadDocument, type DocumentItem } from '../api/client'

const STATUS_COLORS: Record<string, 'default' | 'warning' | 'success' | 'error' | 'info'> = {
  pending: 'default',
  processing: 'info',
  ready: 'success',
  failed: 'error',
}

const STATUS_LABELS: Record<string, string> = {
  pending: 'Pendiente',
  processing: 'Procesando',
  ready: 'Listo',
  failed: 'Error',
}

export default function DocumentsPage() {
  const [docs, setDocs] = useState<DocumentItem[]>([])
  const [loading, setLoading] = useState(true)
  const [uploading, setUploading] = useState(false)
  const [dragOver, setDragOver] = useState(false)
  const [error, setError] = useState('')

  const loadDocs = useCallback(async () => {
    setLoading(true)
    try {
      const data = await listDocuments()
      setDocs(data)
    } catch {
      setError('No se pudieron cargar los documentos')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    loadDocs()
    const interval = setInterval(loadDocs, 5000)
    return () => clearInterval(interval)
  }, [loadDocs])

  const handleFiles = async (files: FileList | null) => {
    if (!files?.length) return
    setUploading(true)
    setError('')
    try {
      for (const file of Array.from(files)) {
        await uploadDocument(file)
      }
      await loadDocs()
    } catch {
      setError('Error al subir el archivo')
    } finally {
      setUploading(false)
    }
  }

  const handleDelete = async (id: string) => {
    if (!confirm('¿Eliminar este documento?')) return
    await deleteDocument(id)
    await loadDocs()
  }

  return (
    <Box>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
        <Typography variant="h5" sx={{ fontWeight: 700 }}>
          Documentos
        </Typography>
        <IconButton onClick={loadDocs} disabled={loading}>
          <RefreshIcon />
        </IconButton>
      </Box>

      {error && <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>}

      <Paper
        variant="outlined"
        onDragOver={(e) => { e.preventDefault(); setDragOver(true) }}
        onDragLeave={() => setDragOver(false)}
        onDrop={(e) => { e.preventDefault(); setDragOver(false); handleFiles(e.dataTransfer.files) }}
        sx={{
          p: 4,
          mb: 3,
          textAlign: 'center',
          borderStyle: 'dashed',
          borderWidth: 2,
          borderColor: dragOver ? 'primary.main' : 'divider',
          bgcolor: dragOver ? 'action.hover' : 'background.paper',
          cursor: 'pointer',
        }}
        onClick={() => document.getElementById('file-input')?.click()}
      >
        <input
          id="file-input"
          type="file"
          hidden
          multiple
          accept=".pdf,.docx,.txt,.md,.csv"
          onChange={(e) => handleFiles(e.target.files)}
        />
        {uploading ? (
          <CircularProgress />
        ) : (
          <>
            <CloudUploadIcon sx={{ fontSize: 48, color: 'text.secondary', mb: 1 }} />
            <Typography>Arrastra archivos aquí o haz clic para seleccionar</Typography>
            <Typography variant="caption" color="text.secondary">
              PDF, DOCX, TXT — máximo 20 MB
            </Typography>
          </>
        )}
      </Paper>

      {loading && docs.length === 0 ? (
        <Box sx={{ textAlign: 'center', py: 4 }}><CircularProgress /></Box>
      ) : (
        <Paper elevation={1}>
          <Table>
            <TableHead>
              <TableRow>
                <TableCell>Archivo</TableCell>
                <TableCell>Tipo</TableCell>
                <TableCell>Estado</TableCell>
                <TableCell>Fecha</TableCell>
                <TableCell align="right">Acciones</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {docs.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={5} align="center">
                    <Typography color="text.secondary" sx={{ py: 2 }}>
                      No hay documentos cargados
                    </Typography>
                  </TableCell>
                </TableRow>
              ) : (
                docs.map((doc) => (
                  <TableRow key={doc.id}>
                    <TableCell>{doc.filename}</TableCell>
                    <TableCell>{doc.mime_type}</TableCell>
                    <TableCell>
                      <Chip
                        label={STATUS_LABELS[doc.status] ?? doc.status}
                        color={STATUS_COLORS[doc.status] ?? 'default'}
                        size="small"
                      />
                      {doc.error_message && (
                        <Typography variant="caption" color="error" sx={{ display: 'block' }}>
                          {doc.error_message}
                        </Typography>
                      )}
                    </TableCell>
                    <TableCell>
                      {new Date(doc.created_at).toLocaleString('es-CL')}
                    </TableCell>
                    <TableCell align="right">
                      <IconButton size="small" color="error" onClick={() => handleDelete(doc.id)}>
                        <DeleteIcon />
                      </IconButton>
                    </TableCell>
                  </TableRow>
                ))
              )}
            </TableBody>
          </Table>
        </Paper>
      )}
    </Box>
  )
}
