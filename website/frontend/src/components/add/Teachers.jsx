import React, { useState, useCallback } from "react";

export default function TextFileGrid() {
    const [lines, setLines] = useState([]);
    const [isDragging, setIsDragging] = useState(false);
    const [loading, setLoading] = useState(false);
    const [message, setMessage] = useState("");

    const handleFile = (file) => {
        if (file.type !== "text/plain") {
            alert("Please upload a .txt file");
            return;
        }

        const reader = new FileReader();
        reader.onload = (e) => {
            const text = e.target.result;
            const linesArray = text.split(/\r?\n/).filter((line) => line.trim() !== "");
            setLines(linesArray);
        };
        reader.readAsText(file);
    };

    const handleDrop = useCallback((event) => {
        event.preventDefault();
        setIsDragging(false);
        const file = event.dataTransfer.files[0];
        if (file) handleFile(file);
    }, []);

    const handleUpload = async () => {
        if (lines.length === 0) return alert("No lines to send!");

        try {
            setLoading(true);
            setMessage("");

            const csrftoken = document.cookie
                .split("; ")
                .find((row) => row.startsWith("csrftoken="))
                ?.split("=")[1];

            const res = await fetch("/api/teachers/upload", {
                method: "POST",
                headers: { "Content-Type": "application/json", "X-CSRFToken": csrftoken },
                body: JSON.stringify({ lines }),
            });

            const data = await res.json();

            if (res.ok) {
                setMessage(`✅ Uploaded ${data.length} teachers successfully!`);
            } else {
                setMessage(`❌ Error: ${data.error || "Unknown error"}`);
            }
        } catch (error) {
            console.error(error);
            setMessage("❌ Network error");
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="flex flex-col items-center gap-6 p-6">
            {/* Drop Zone */}
            <div
                onDrop={handleDrop}
                onDragOver={(e) => {
                    e.preventDefault();
                    setIsDragging(true);
                }}
                onDragLeave={() => setIsDragging(false)}
                className={`w-full max-w-xl h-40 flex items-center justify-center border-4 border-dashed rounded-2xl transition-all ${isDragging ? "border-blue-500 bg-blue-50" : "border-gray-300"
                    }`}
            >
                <p className="text-gray-600 text-center">
                    {isDragging ? "Drop your .txt file here" : "Drag & drop a .txt file here"}
                </p>
                <input
                    type="file"
                    accept=".txt"
                    onChange={(e) => handleFile(e.target.files[0])}
                    className="absolute opacity-0 w-full h-full cursor-pointer"
                />
            </div>

            {/* Grid Display */}
            {lines.length > 0 && (
                <div className="w-full max-w-xl border border-gray-300 rounded-xl shadow-sm overflow-hidden">
                    <div className="grid grid-cols-1 divide-y divide-gray-200">
                        {lines.map((line, index) => (
                            <div
                                key={index}
                                className="p-3 hover:bg-gray-50 text-gray-800 font-mono text-sm"
                            >
                                {line}
                            </div>
                        ))}
                    </div>
                </div>
            )}

            {/* Upload Button */}
            {lines.length > 0 && (
                <button
                    onClick={handleUpload}
                    disabled={loading}
                    className={`px-6 py-2 rounded-lg text-white font-semibold ${loading ? "bg-gray-400" : "bg-blue-600 hover:bg-blue-700"
                        }`}
                >
                    {loading ? "Uploading..." : "Send to Backend"}
                </button>
            )}

            {message && <p className="text-center text-gray-700">{message}</p>}
        </div>
    );
}
