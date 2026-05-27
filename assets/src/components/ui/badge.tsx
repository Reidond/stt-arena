import { cn } from "@/lib/utils";

type BadgeProps = React.HTMLAttributes<HTMLSpanElement> & {
  variant?: "default" | "success" | "warning" | "error" | "muted";
};

export function Badge({
  className,
  variant = "default",
  ...props
}: BadgeProps) {
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium",
        variant === "default" && "bg-zinc-800 text-zinc-300",
        variant === "success" && "bg-emerald-950 text-emerald-400",
        variant === "warning" && "bg-amber-950 text-amber-400",
        variant === "error" && "bg-red-950 text-red-400",
        variant === "muted" && "bg-zinc-900 text-zinc-500",
        className,
      )}
      {...props}
    />
  );
}
