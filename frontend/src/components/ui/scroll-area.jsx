import * as React from "react"

const ScrollArea = React.forwardRef(({ className, children, ...props }, ref) => {
  return (
    <div
      ref={ref}
      className={`relative overflow-auto ${className}`}
      {...props}
    >
      <div className="h-full w-full">
        {children}
      </div>
      <div className="absolute right-0 top-0 h-full w-2 bg-transparent">
        <div className="rounded-full bg-gray-200 opacity-0 transition-opacity hover:opacity-100" />
      </div>
    </div>
  )
})
ScrollArea.displayName = "ScrollArea"

export { ScrollArea }