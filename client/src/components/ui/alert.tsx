import * as React from "react";
import { cn } from "../../lib/utils";

export interface AlertProps extends React.HTMLAttributes<HTMLDivElement> {
  variant?: "success" | "error" | "info" | "warning";
  title?: string;
  description?: string;
  onClose?: () => void;
}

const variantStyles = {
  success: "bg-green-50 border-green-400 text-green-700",
  error: "bg-red-50 border-red-400 text-red-700",
  info: "bg-blue-50 border-blue-400 text-blue-700",
  warning: "bg-yellow-50 border-yellow-400 text-yellow-700",
};

const iconMap = {
  success: (
    <svg className="w-5 h-5 text-green-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M5 13l4 4L19 7" /></svg>
  ),
  error: (
    <svg className="w-5 h-5 text-red-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M6 18L18 6M6 6l12 12" /></svg>
  ),
  info: (
    <svg className="w-5 h-5 text-blue-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M13 16h-1v-4h-1m1-4h.01" /></svg>
  ),
  warning: (
    <svg className="w-5 h-5 text-yellow-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 8v4m0 4h.01M21 12A9 9 0 113 12a9 9 0 0118 0z" /></svg>
  ),
};

export const Alert = React.forwardRef<HTMLDivElement, AlertProps>(
  ({ variant = "info", title, description, onClose, className, ...props }, ref) => {
    return (
      <div
        ref={ref}
        className={cn(
          "border-l-4 p-4 rounded-lg flex items-start gap-3 relative",
          variantStyles[variant],
          className
        )}
        role="alert"
        {...props}
      >
        <div className="mt-1">{iconMap[variant]}</div>
        <div className="flex-1">
          {title && <div className="font-semibold mb-1">{title}</div>}
          {description && <div className="text-sm">{description}</div>}
        </div>
        {onClose && (
          <button
            onClick={onClose}
            className="absolute top-2 right-2 text-gray-400 hover:text-gray-600 focus:outline-none"
            aria-label="Cerrar alerta"
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M6 18L18 6M6 6l12 12" /></svg>
          </button>
        )}
      </div>
    );
  }
);
Alert.displayName = "Alert"; 