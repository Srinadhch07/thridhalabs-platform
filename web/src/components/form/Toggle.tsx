/** Toggle switch for boolean settings. */

export interface ToggleProps {
  id: string
  label: string
  checked: boolean
  description?: string
  disabled?: boolean
  onChange?: (checked: boolean) => void
  className?: string
}

export function Toggle({ id, label, description, checked, disabled, onChange, className = '' }: ToggleProps) {
  return (
    <label className={`toggle${className ? ` ${className}` : ''}`}>
      <input
        id={id}
        type="checkbox"
        checked={checked}
        disabled={disabled}
        onChange={(event) => onChange?.(event.target.checked)}
        className="toggle__input"
      />
      <span className="toggle__track" aria-hidden="true">
        <span className="toggle__thumb" aria-hidden="true" />
      </span>
      <span className="toggle__text">
        <span className="toggle__label">{label}</span>
        {description ? <span className="toggle__description">{description}</span> : null}
      </span>
    </label>
  )
}