import * as React from "react"

const Alert = React.forwardRef(({ className, variant = "default", ...props }, ref) => (
  <div
    ref={ref}
    role="alert"
    className={`
      rounded-lg border p-4
      ${variant === "destructive" ? 
        "border-red-500/50 text-red-600 dark:border-red-500 dark:text-red-500" : 
        "border-gray-200 text-gray-800 dark:border-gray-800 dark:text-gray-200"}
      ${className}`}
    {...props}
  />
))
Alert.displayName = "Alert"

const AlertDescription = React.forwardRef(({ className, ...props }, ref) => (
  <div
    ref={ref}
    className={`text-sm [&_p]:leading-relaxed ${className}`}
    {...props}
  />
))
AlertDescription.displayName = "AlertDescription"

export { Alert, AlertDescription }