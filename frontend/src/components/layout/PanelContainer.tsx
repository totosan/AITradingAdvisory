import { cn } from "@/lib/utils";

interface PanelContainerProps {
  title: string;
  children: React.ReactNode;
  className?: string;
  headerActions?: React.ReactNode;
}

export function PanelContainer({
  title,
  children,
  className,
  headerActions,
}: PanelContainerProps) {
  return (
    <div className={cn("panel flex flex-col h-full", className)}>
      <div className="panel-header">
        <h2 className="panel-title">{title}</h2>
        {headerActions && <div className="flex items-center gap-2">{headerActions}</div>}
      </div>
      <div className="panel-content flex-1 min-h-0">{children}</div>
    </div>
  );
}
