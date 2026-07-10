"use client"

import { useState, useEffect } from "react"

export type ToastType = "default" | "success" | "error" | "warning" | "info"

export interface Toast {
  id: string
  title?: string
  description?: string
  type?: ToastType
  duration?: number
}

type ToastOmitId = Omit<Toast, "id">

let memoryState: Toast[] = []
let listeners: React.Dispatch<React.SetStateAction<Toast[]>>[] = []

function dispatch() {
  listeners.forEach((listener) => listener([...memoryState]))
}

export const toast = (props: ToastOmitId) => {
  const id = Math.random().toString(36).slice(2, 9)
  const newToast = { ...props, id, type: props.type || "default", duration: props.duration || 5000 }
  memoryState = [...memoryState, newToast]
  dispatch()

  if (newToast.duration !== Infinity) {
    setTimeout(() => {
      dismissToast(id)
    }, newToast.duration)
  }
  
  return id
}

export const dismissToast = (id: string) => {
  memoryState = memoryState.filter((t) => t.id !== id)
  dispatch()
}

export function useToast() {
  const [toasts, setToasts] = useState<Toast[]>(memoryState)

  useEffect(() => {
    listeners.push(setToasts)
    return () => {
      listeners = listeners.filter((l) => l !== setToasts)
    }
  }, [])

  return {
    toasts,
    toast,
    dismiss: dismissToast,
  }
}
