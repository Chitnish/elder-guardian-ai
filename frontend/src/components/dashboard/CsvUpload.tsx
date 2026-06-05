"use client";

import { uploadCsv } from "@/lib/api";
import type { UploadResponse } from "@/types";
import { UploadCloud } from "lucide-react";
import { useRef, useState } from "react";

interface CsvUploadProps {
  userId: string;
  onUploadComplete: (result: UploadResponse) => void;
}

export function CsvUpload({ userId, onUploadComplete }: CsvUploadProps) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [isDragging, setIsDragging] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleFile(file: File) {
    if (!file.name.toLowerCase().endsWith(".csv")) {
      setError("Please select a CSV file");
      return;
    }

    setError(null);
    setIsUploading(true);

    try {
      const result = await uploadCsv(file, userId);
      onUploadComplete(result);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Upload failed");
    } finally {
      setIsUploading(false);
    }
  }

  function handleDrop(e: React.DragEvent<HTMLDivElement>) {
    e.preventDefault();
    setIsDragging(false);

    const file = e.dataTransfer.files[0];
    if (file) {
      void handleFile(file);
    }
  }

  function handleChange(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (file) {
      void handleFile(file);
    }
    e.target.value = "";
  }

  return (
    <div>
      <div
        className={`border-2 border-dashed rounded-lg p-12 text-center cursor-pointer ${
          isDragging
            ? "border-blue-400 bg-blue-50"
            : "border-slate-300"
        }`}
        onClick={() => inputRef.current?.click()}
        onDragOver={(e) => {
          e.preventDefault();
          setIsDragging(true);
        }}
        onDragLeave={() => setIsDragging(false)}
        onDrop={handleDrop}
      >
        {isUploading ? (
          <div className="flex flex-col items-center gap-3">
            <div className="h-8 w-8 animate-spin rounded-full border-4 border-slate-300 border-t-blue-500" />
            <p className="text-slate-600">Analyzing transactions...</p>
          </div>
        ) : (
          <>
            <UploadCloud className="mx-auto h-12 w-12 text-slate-400" />
            <p className="mt-4 font-medium text-slate-700">
              Drop your CSV here or click to browse
            </p>
            <p className="mt-1 text-sm text-slate-500">
              Requires columns: date, amount, payee
            </p>
          </>
        )}
        <input
          ref={inputRef}
          type="file"
          accept=".csv"
          className="hidden"
          onChange={handleChange}
        />
      </div>
      {error && <p className="mt-2 text-sm text-red-600">{error}</p>}
    </div>
  );
}
