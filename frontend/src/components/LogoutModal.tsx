import { AlertIcon } from './ItplusIcons'

interface LogoutModalProps {
  open: boolean
  onCancel: () => void
  onConfirm: () => void
}

export default function LogoutModal({ open, onCancel, onConfirm }: LogoutModalProps) {
  return (
    <div
      className={`modal-overlay${open ? ' visible' : ''}`}
      onClick={(e) => { if (e.target === e.currentTarget) onCancel() }}
      role="presentation"
    >
      <div className="modal-box" role="dialog" aria-modal="true" aria-labelledby="logout-title">
        <div className="modal-icon">
          <AlertIcon />
        </div>
        <h3 id="logout-title">¿Cerrar sesión?</h3>
        <p>Tendrás que iniciar sesión nuevamente para volver a usar ITPlus.</p>
        <div className="modal-actions">
          <button type="button" className="btn-ghost" onClick={onCancel}>Cancelar</button>
          <button type="button" className="btn-danger" onClick={onConfirm}>Cerrar sesión</button>
        </div>
      </div>
    </div>
  )
}
