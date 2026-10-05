import type { ButtonHTMLAttributes } from "react";

interface Props extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: "primary" | "ghost" | "danger" | "success";
  size?: "sm" | "md";
}

const VARIANTS: Record<string, string> = {
  primary: "bg-accent text-accent-ink hover:brightness-110",
  ghost: "border border-line text-ink hover:bg-raised",
  danger: "text-bad hover:underline",
  success: "border border-ok text-ok hover:bg-raised",
};

const SIZES: Record<string, string> = {
  sm: "px-2.5 py-1 text-xs",
  md: "px-4 py-1.5 text-sm",
};

export default function Button({
  variant = "primary",
  size = "md",
  className = "",
  ...rest
}: Props) {
  return (
    <button
      className={`rounded-md font-medium disabled:opacity-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent ${VARIANTS[variant]} ${SIZES[size]} ${className}`}
      {...rest}
    />
  );
}
