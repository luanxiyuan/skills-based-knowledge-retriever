import * as React from "react"
import { ChevronDown } from "lucide-react"

import { cn } from "@/lib/utils"

interface CollapsibleProps {
  title: string;
  children: React.ReactNode;
  defaultOpen?: boolean;
  className?: string;
}

export function Collapsible({ title, children, defaultOpen = false, className }: CollapsibleProps) {
  const [isOpen, setIsOpen] = React.useState(defaultOpen)

  return (
    <div className={cn("border border-[var(--color-border)] rounded-lg overflow-hidden", className)}>
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="w-full flex items-center justify-between p-3 bg-[var(--color-muted)] hover:bg-[var(--color-accent)] transition-colors"
      >
        <span className="text-sm font-medium text-[var(--color-foreground)]">{title}</span>
        <ChevronDown
          className={cn(
            "w-4 h-4 text-[var(--color-muted-foreground)] transition-transform",
            isOpen && "rotate-180"
          )}
        />
      </button>
      {isOpen && (
        <div className="p-3 bg-[var(--color-background)] border-t border-[var(--color-border)]">
          {children}
        </div>
      )}
    </div>
  )
}
