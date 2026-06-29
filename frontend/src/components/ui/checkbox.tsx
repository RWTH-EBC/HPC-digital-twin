import * as React from "react";

interface CheckboxProps extends React.InputHTMLAttributes<HTMLInputElement> {
  checked?: boolean;
  onCheckedChange?: (checked: boolean) => void;
  label?: string;
}

const Checkbox = React.forwardRef<HTMLInputElement, CheckboxProps>(
  ({ checked, onCheckedChange, className, label, ...props }, ref) => {
    return (
      <div className="flex items-center">
        <input
          type="checkbox"
          ref={ref}
          checked={checked}
          onChange={(e) => onCheckedChange?.(e.target.checked)}
          className={`
            h-4 w-4 
            rounded 
            border-gray-300 
            text-blue-600 
            focus:ring-2 
            focus:ring-blue-500 
            focus:ring-offset-2
            cursor-pointer
            ${className}
          `}
          {...props}
        />
        {label && (
          <label className="ml-2 text-sm text-gray-700">{label}</label>
        )}
      </div>
    );
  }
);

Checkbox.displayName = "Checkbox";

export { Checkbox };