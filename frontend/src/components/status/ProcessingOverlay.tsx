"use client";

import { useState, useEffect, useRef } from "react";
import { ProgressBar } from "@/components/ui/ProgressBar";
import { ProgressSteps } from "./ProgressSteps";
import { Spinner } from "@/components/ui/Spinner";
import { Button } from "@/components/ui/Button";

interface ProcessingOverlayProps {
  step: number;
  progress: number;
  message?: string;
  onCancel?: () => void;
}

function formatElapsed(seconds: number): string {
  const m = Math.floor(seconds / 60);
  const s = seconds % 60;
  if (m > 0) return `${m}m ${s}s`;
  return `${s}s`;
}

export function ProcessingOverlay({ step, progress, message, onCancel }: ProcessingOverlayProps) {
  const [elapsed, setElapsed] = useState(0);
  const startRef = useRef(Date.now());

  useEffect(() => {
    startRef.current = Date.now();
    setElapsed(0);
    const timer = setInterval(() => {
      setElapsed(Math.floor((Date.now() - startRef.current) / 1000));
    }, 1000);
    return () => clearInterval(timer);
  }, []);

  return (
    <div className="fixed inset-0 z-40 flex items-center justify-center bg-black/70">
      <div className="bg-gray-900 border border-gray-800 rounded-2xl p-8 w-full max-w-lg text-center space-y-6">
        <Spinner size={40} className="mx-auto" />
        <h3 className="text-lg font-semibold text-gray-100">Processing your video</h3>
        <ProgressSteps currentStep={step} />
        <ProgressBar value={progress} />
        <div className="space-y-1">
          {message && <p className="text-sm text-gray-400">{message}</p>}
          <p className="text-xs text-gray-600">Elapsed: {formatElapsed(elapsed)}</p>
        </div>
        {onCancel && (
          <Button variant="ghost" size="sm" onClick={onCancel}>
            Cancel
          </Button>
        )}
      </div>
    </div>
  );
}
