import { Check } from "lucide-react";

const steps = ["Upload", "Transcribe", "Analyze", "Ready"];

interface ProgressStepsProps {
  currentStep: number;
}

export function ProgressSteps({ currentStep }: ProgressStepsProps) {
  return (
    <div className="flex items-center justify-center gap-2">
      {steps.map((step, i) => (
        <div key={step} className="flex items-center gap-2">
          <div
            className={`w-7 h-7 rounded-full flex items-center justify-center text-xs font-medium
              ${i < currentStep ? "bg-green-600 text-white" : i === currentStep ? "bg-blue-600 text-white" : "bg-gray-800 text-gray-500"}`}
          >
            {i < currentStep ? <Check size={14} /> : i + 1}
          </div>
          <span className={`text-sm ${i <= currentStep ? "text-gray-200" : "text-gray-600"}`}>{step}</span>
          {i < steps.length - 1 && <div className={`w-8 h-px ${i < currentStep ? "bg-green-600" : "bg-gray-800"}`} />}
        </div>
      ))}
    </div>
  );
}
