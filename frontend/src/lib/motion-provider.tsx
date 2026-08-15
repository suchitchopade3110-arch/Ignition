"use client"

import { MotionConfig } from "framer-motion"

/**
 * Applies the viewer's motion preference to every framer-motion component.
 *
 * CSS `prefers-reduced-motion` rules cannot reach framer-motion, which drives
 * transforms imperatively via inline styles. `reducedMotion="user"` makes the
 * library honour the OS setting itself, reducing transform and layout
 * animations to instant while leaving opacity fades intact.
 */
export function MotionProvider({ children }: { children: React.ReactNode }) {
  return <MotionConfig reducedMotion="user">{children}</MotionConfig>
}
