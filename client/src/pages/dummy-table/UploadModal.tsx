import React, { useEffect, useRef, useState } from "react";

export type UploadModalProps<T> = {
    open: boolean;
    onClose: () => void;
    parseFile: (file: File) => Promise<T[]>;
    validateRows: (rows: T[]) => Promise<{ validRows: T[]; errors: string[] }>;
    onSuccess: (rows: T[]) => Promise<void> | void;
    title?: string;
    maxSizeMB?: number;
    accept?: string;
};

function ProgressBar({ value }: { value: number }) {
    return (
        <div className="w-full bg-neutral-200 rounded h-2">
            <div
                className="bg-primary h-2 rounded"
                style={{ width: `${Math.max(0, Math.min(100, value))}%` }}
            />
        </div>
    );
}

export function UploadModal<T>({
    open,
    onClose,
    parseFile,
    validateRows,
    onSuccess,
    maxSizeMB = 50,
    accept = ".csv,.xlsx",
}: UploadModalProps<T>) {
    const fileInputRef = useRef<HTMLInputElement>(null);
    const [file, setFile] = useState<File | null>(null);
    const [stage, setStage] = useState<"idle" | "parsing" | "validating" | "uploading" | "done" | "error">("idle");
    const [progress, setProgress] = useState(0);
    const [errors, setErrors] = useState<string[]>([]);

    useEffect(() => {
        if (!open) {
            setFile(null);
            setErrors([]);
            setStage("idle");
            setProgress(0);
        }
    }, [open]);

    const pickFile = () => fileInputRef.current?.click();

    const onFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
        const f = e.target.files?.[0] || null;
        e.target.value = "";
        if (!f) return;

        if (f.size > maxSizeMB * 1024 * 1024) {
            setErrors([`File too large. Max size is ${maxSizeMB} MB.`]);
            setStage("error");
            return;
        }
        setFile(f);
        setErrors([]);
        setStage("idle");
    };

    const upload = async (e?: React.MouseEvent<HTMLButtonElement>) => {
        e?.preventDefault();
        if (!file) return;

        try {
            setStage("parsing");
            setProgress(20);

            const parsed = await parseFile(file);

            setStage("validating");
            setProgress(50);

            const { validRows, errors } = await validateRows(parsed);
            if (errors.length) {
                setErrors(errors);
                setStage("error");
                setProgress(0);
                return;
            }

            setStage("uploading");
            setProgress(80);

            await onSuccess(validRows);

            setProgress(100);
            setStage("done");

            setTimeout(onClose, 600);
        } catch (err: any) {
            setErrors([err?.message || "Upload failed"]);
            setStage("error");
            setProgress(0);
        }
    };

    if (!open) return null;

    return (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
            <div className="bg-white rounded shadow-lg p-6 w-full max-w-xl">
                <h3 className="text-xl font-semibold mb-4">Upload file</h3>
                <div className="rounded bg-amber-50 text-amber-900 border border-amber-200 px-3 py-2 mb-3">
                    <span className="font-medium">Uploading a file will overwrite the existing data</span>
                </div>

                <p className="text-sm text-gray-600 mb-4">
                    Max file size is 50 MB. Only <b>.xlsx</b> and <b>.csv</b> files are supported.
                </p>

                <button type="button" className="px-3 py-2 border cursor-pointer rounded" onClick={pickFile}>
                    Add file
                </button>
                {file && (
                    <div className="mt-3 text-sm">
                        <div className="mb-2 text-gray-800">{file.name}</div>
                        {(stage === "parsing" ||
                            stage === "validating" ||
                            stage === "uploading" ||
                            stage === "done") && <ProgressBar value={progress} />}
                    </div>
                )}
                <input ref={fileInputRef} type="file" accept={accept} onChange={onFileChange} style={{ display: "none" }} />

                {errors.length > 0 && (
                    <div className="mt-4 text-sm text-red-600">
                        <ul className="list-disc pl-5">
                            {errors.map((e, i) => <li key={`error-${i}`}>{e}</li>)}
                        </ul>
                    </div>
                )}

                <div className="flex justify-end gap-3 mt-6">
                    <button type="button" className="px-4 py-2 rounded border cursor-pointer" onClick={onClose}>
                        Cancel
                    </button>
                    <button type="button"
                        className={`px-4 py-2 text-white cursor-pointer rounded ${file ? "bg-primary" : "bg-gray-300"}`}
                        disabled={!file}
                        onClick={(e) => upload(e)}
                    >
                        Upload
                    </button>
                </div>
            </div>
        </div>
    );
}