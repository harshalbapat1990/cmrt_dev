
import alertIconUrl from '../../assets/icons/emergency_home.svg';

type FieldErrorProps = {
  message?: string | null;
  className?: string;
};

export default function FieldError({ message, className = '' }: FieldErrorProps) {
  if (!message) return null;
  return (
    <div
      role="alert"
      aria-live="assertive"
      className={`mb-2 mt-1 flex items-center gap-1.5 text-sm text-danger ${className}`}
    >
      <img src={alertIconUrl} alt="" width={20} height={20} aria-hidden="true" />
      <span>{message}</span>
    </div>
  );
}
