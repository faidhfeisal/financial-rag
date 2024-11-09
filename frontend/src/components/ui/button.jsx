import * as React from "react"

const Button = React.forwardRef(({ className, variant = "default", size = "default", children, ...props }, ref) => (
  <button
    ref={ref}
    className={`inline-flex items-center justify-center rounded-md font-medium transition-colors 
    focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring disabled:pointer-events-none disabled:opacity-50
    ${variant === "outline" ? "border border-input bg-background hover:bg-accent hover:text-accent-foreground" : ""}
    ${size === "sm" ? "h-9 px-3 text-sm" : "h-10 px-4 py-2"}
    ${className}`}
    {...props}
  >
    {children}
  </button>
))
Button.displayName = "Button"

export { Button }