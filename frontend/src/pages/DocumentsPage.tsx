import { useCallback, useEffect, useRef, useState } from 'react'

import {

  Alert, Box, Button, Chip, CircularProgress, FormControl, IconButton, InputLabel,

  List, ListItem, ListItemSecondaryAction, ListItemText, MenuItem, Paper, Select,

  Table, TableBody, TableCell, TableHead, TableRow, TextField, Typography,

} from '@mui/material'

import CloudUploadIcon from '@mui/icons-material/CloudUpload'

import DeleteIcon from '@mui/icons-material/Delete'

import RefreshIcon from '@mui/icons-material/Refresh'

import ReplayIcon from '@mui/icons-material/Replay'

import CloseIcon from '@mui/icons-material/Close'

import {

  deleteDocument, getDocumentCategories, listDocuments, reindexDocument, uploadDocument,

  type DocumentItem,

} from '../api/client'

import PageChrome from '../components/PageChrome'



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



const CATEGORY_LABELS: Record<string, string> = {

  general: 'General',

  ventas: 'Ventas',

  productos: 'Productos',

  operaciones: 'Operaciones',

  politicas: 'Políticas',

  finanzas: 'Finanzas',

  soporte: 'Soporte técnico',

}



interface PendingFile {

  id: string

  file: File

}



export default function DocumentsPage() {

  const [docs, setDocs] = useState<DocumentItem[]>([])

  const [loading, setLoading] = useState(true)

  const [uploading, setUploading] = useState(false)

  const [dragOver, setDragOver] = useState(false)

  const [error, setError] = useState('')

  const [category, setCategory] = useState('general')

  const [description, setDescription] = useState('')

  const [pendingFiles, setPendingFiles] = useState<PendingFile[]>([])

  const [categories, setCategories] = useState<Array<{ key: string; label: string }>>([

    { key: 'general', label: 'General' },

  ])

  const fileInputRef = useRef<HTMLInputElement>(null)



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

    getDocumentCategories().then(setCategories).catch(() => {})

    const interval = setInterval(loadDocs, 5000)

    return () => clearInterval(interval)

  }, [loadDocs])



  const addFilesToQueue = (files: FileList | null) => {

    if (!files?.length) return

    setError('')

    const items = Array.from(files).map((file) => ({

      id: crypto.randomUUID(),

      file,

    }))

    setPendingFiles((prev) => [...prev, ...items])

    if (fileInputRef.current) fileInputRef.current.value = ''

  }



  const removePending = (id: string) => {

    setPendingFiles((prev) => prev.filter((p) => p.id !== id))

  }



  const handleUpload = async () => {

    if (!pendingFiles.length || uploading) return

    setUploading(true)

    setError('')

    try {

      for (const { file } of pendingFiles) {

        await uploadDocument(file, category, description)

      }

      setPendingFiles([])

      setDescription('')

      await loadDocs()

    } catch {

      setError('Error al subir uno o más archivos')

    } finally {

      setUploading(false)

    }

  }



  const handleReindex = async (id: string) => {

    setError('')

    try {

      await reindexDocument(id)

      await loadDocs()

    } catch {

      setError('No se pudo reindexar el documento')

    }

  }



  const handleDelete = async (id: string) => {

    if (!confirm('¿Eliminar este documento?')) return

    await deleteDocument(id)

    await loadDocs()

  }



  const formatSize = (bytes: number) => {

    if (bytes < 1024) return `${bytes} B`

    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`

    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`

  }



  return (

    <PageChrome
      title="Base de conocimiento"
      description="Selecciona archivos y confirma con el botón Subir"
      actions={(
        <IconButton onClick={loadDocs} disabled={loading}>
          <RefreshIcon />
        </IconButton>
      )}
    >



      {error && <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>}



      <Paper variant="outlined" sx={{ p: 2, mb: 2 }}>

        <Box sx={{ display: 'flex', gap: 2, flexWrap: 'wrap', mb: 2 }}>

          <FormControl size="small" sx={{ minWidth: 180 }}>

            <InputLabel>Categoría</InputLabel>

            <Select label="Categoría" value={category} onChange={(e) => setCategory(e.target.value)}>

              {categories.map((c) => (

                <MenuItem key={c.key} value={c.key}>{c.label}</MenuItem>

              ))}

            </Select>

          </FormControl>

          <TextField

            size="small"

            label="Descripción (opcional)"

            value={description}

            onChange={(e) => setDescription(e.target.value)}

            sx={{ flex: 1, minWidth: 200 }}

            placeholder="Ej: Ventas Q1 2025"

          />

        </Box>



        <Paper

          variant="outlined"

          onDragOver={(e) => { e.preventDefault(); setDragOver(true) }}

          onDragLeave={() => setDragOver(false)}

          onDrop={(e) => {

            e.preventDefault()

            setDragOver(false)

            addFilesToQueue(e.dataTransfer.files)

          }}

          sx={{

            p: 4,

            textAlign: 'center',

            borderStyle: 'dashed',

            borderWidth: 2,

            borderColor: dragOver ? 'primary.main' : 'divider',

            bgcolor: dragOver ? 'action.hover' : 'background.paper',

            cursor: 'pointer',

            mb: 2,

          }}

          onClick={() => fileInputRef.current?.click()}

        >

          <input

            ref={fileInputRef}

            type="file"

            hidden

            multiple

            accept=".pdf,.docx,.txt,.md,.csv,.xlsx,.xlsm"

            onChange={(e) => addFilesToQueue(e.target.files)}

          />

          <CloudUploadIcon sx={{ fontSize: 48, color: 'text.secondary', mb: 1 }} />

          <Typography>Arrastra archivos aquí o haz clic para seleccionar</Typography>

          <Typography variant="caption" color="text.secondary">

            PDF, DOCX, TXT, CSV, XLSX — máximo 20 MB por archivo

          </Typography>

        </Paper>



        {pendingFiles.length > 0 && (

          <Box sx={{ mb: 2 }}>

            <Typography variant="subtitle2" sx={{ mb: 1, fontWeight: 700 }}>

              Archivos listos para subir ({pendingFiles.length})

            </Typography>

            <List dense disablePadding>

              {pendingFiles.map(({ id, file }) => (

                <ListItem key={id} sx={{ bgcolor: '#f8fafc', mb: 0.5, borderRadius: 1 }}>

                  <ListItemText

                    primary={file.name}

                    secondary={formatSize(file.size)}

                  />

                  <ListItemSecondaryAction>

                    <IconButton edge="end" size="small" onClick={() => removePending(id)}>

                      <CloseIcon fontSize="small" />

                    </IconButton>

                  </ListItemSecondaryAction>

                </ListItem>

              ))}

            </List>

          </Box>

        )}



        <Box sx={{ display: 'flex', gap: 1, justifyContent: 'flex-end' }}>

          {pendingFiles.length > 0 && (

            <Button

              variant="outlined"

              color="inherit"

              onClick={() => setPendingFiles([])}

              disabled={uploading}

            >

              Limpiar lista

            </Button>

          )}

          <Button

            variant="contained"

            startIcon={uploading ? <CircularProgress size={18} color="inherit" /> : <CloudUploadIcon />}

            onClick={handleUpload}

            disabled={uploading || pendingFiles.length === 0}

            sx={{ bgcolor: '#1a365d', '&:hover': { bgcolor: '#153050' } }}

          >

            {uploading ? 'Subiendo...' : pendingFiles.length === 0
              ? 'Subir archivos'
              : `Subir ${pendingFiles.length} archivo${pendingFiles.length !== 1 ? 's' : ''}`}

          </Button>

        </Box>

      </Paper>



      {loading && docs.length === 0 ? (

        <Box sx={{ textAlign: 'center', py: 4 }}><CircularProgress /></Box>

      ) : (

        <Paper elevation={1}>

          <Table>

            <TableHead>

              <TableRow>

                <TableCell>Archivo</TableCell>

                <TableCell>Categoría</TableCell>

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

                      No hay documentos indexados aún

                    </Typography>

                  </TableCell>

                </TableRow>

              ) : (

                docs.map((doc) => (

                  <TableRow key={doc.id}>

                    <TableCell>

                      {doc.filename}

                      {doc.description && (

                        <Typography variant="caption" color="text.secondary" sx={{ display: 'block' }}>

                          {doc.description}

                        </Typography>

                      )}

                    </TableCell>

                    <TableCell>

                      <Chip

                        label={CATEGORY_LABELS[doc.category] ?? doc.category}

                        size="small"

                        variant="outlined"

                      />

                    </TableCell>

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

                      {(doc.status === 'pending' || doc.status === 'failed') && (

                        <IconButton

                          size="small"

                          color="primary"

                          title="Reindexar"

                          onClick={() => handleReindex(doc.id)}

                        >

                          <ReplayIcon />

                        </IconButton>

                      )}

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

    </PageChrome>

  )

}


