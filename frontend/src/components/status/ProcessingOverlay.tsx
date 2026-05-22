"use client";

import { ProgressBar } from "@/components/ui/ProgressBar";
import { ProgressSteps } from "./ProgressSteps";
import { Spinner } from "@/components/ui/Spinner";

interface ProcessingOverlayProps {
  step: number;
  progress: number;
  message?: string;
}

export function ProcessingOverlay({ step, progress, message }: ProcessingOverlayProps) {
  return (
    <div className="fixed inset-0 z-40 flex items-center justify-center bg-black/70">
      <div className="bg-gray-900 border border-gray-800 rounded-2xl p-8 w-full max-w-lg text-center space-y-6">
        <Spinner size={40} className="mx-auto" />
        <h3 className="text-lg font-semibold text-gray-100">Processing your video</h3>
        <ProgressSteps currentStep={step} />
        <ProgressBar value={progress} />
        {message && <p className="text-sm text-gray-400">{message}</p>}
      </div>
    </div>
  );
}
