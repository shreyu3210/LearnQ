import React from 'react';
import type { ReactNode } from 'react';

interface InputProps extends React.InputHTMLAttributes<HTMLInputElement> {
  label?: string;
  icon?: ReactNode;
}

const Input: React.FC<InputProps> = ({ label, icon, className, id, ...props }) => {
  return (
    <div className="mb-3">
      {label && (
        <label htmlFor={id} className="form-label form-label-custom">
          {label}
        </label>
      )}
      <div className="input-group">
        {icon && (
          <span className="input-group-text border-end-0 auth-input-icon">
            {icon}
          </span>
        )}
        <input
          id={id}
          className={`form-control form-control-custom ${icon ? 'border-start-0' : ''} ${className || ''}`}
          {...props}
        />
      </div>
    </div>
  );
};

export default Input;
