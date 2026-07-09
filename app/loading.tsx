"use client"

import Image from "next/image"
import { motion } from "framer-motion"

export default function Loading() {
  return (
    <div className="fixed inset-0 z-[100] flex flex-col items-center justify-center bg-background/90 backdrop-blur-sm">
      <motion.div
        animate={{ 
          scale: [1, 1.15, 1],
          filter: [
            "drop-shadow(0 0 15px rgba(255,69,0,0.3))", 
            "drop-shadow(0 0 45px rgba(255,69,0,0.9))", 
            "drop-shadow(0 0 15px rgba(255,69,0,0.3))"
          ]
        }}
        transition={{ 
          duration: 1.2, 
          repeat: Infinity, 
          ease: "easeInOut" 
        }}
        className="relative h-32 w-32 mb-6"
      >
        <Image 
          src="/logo-full.png" 
          alt="Loading Ignition..." 
          fill 
          className="object-contain scale-125"
          priority
        />
      </motion.div>
      <motion.div
        animate={{ opacity: [0.5, 1, 0.5] }}
        transition={{ duration: 1.2, repeat: Infinity, ease: "easeInOut" }}
      >
        <span className="text-xl font-bold tracking-tight text-transparent bg-clip-text bg-gradient-to-r from-primary to-blue-400">
          IGNITING...
        </span>
      </motion.div>
    </div>
  )
}
