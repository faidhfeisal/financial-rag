import * as React from "react"

const Badge = React.forwardRef(({ className, variant = "default", ...props }, ref) => {
  const variants = {
    default: "bg-primary text-primary-foreground",
    secondary: "bg-secondary text-secondary-foreground",
    destructive: "bg-destructive text-destructive-foreground",
    outline: "border border-input bg-background hover:bg-accent hover:text-accent-foreground"
  }

  return (
    <div
      ref={ref}
      className={`
        inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-semibold transition-colors
        ${variants[variant] || variants.default}
        ${className}`}
      {...props}
    />
  )
})
Badge.displayName = "Badge"

export { Badge }