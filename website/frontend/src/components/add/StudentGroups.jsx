import React, { useState, useEffect, useCallback } from "react";

export default function StudentGroups() {
    const [lines, setLines] = useState([]);
    const [isDragging, setIsDragging] = useState(false);
    const [loading, setLoading] = useState(false);
    const [message, setMessage] = useState("");
    const [groupPools, setGroupPools] = useState([]);
    const [selectedPool, setSelectedPool] = useState("");
    const [newPoolName, setNewPoolName] = useState("");

    // Fetch StudentGroupPools from the backend
    useEffect(() => {
        const fetchGroupPools = async () => {
            try {
                const res = await fetch("/api/student-group-pools/");
                const data = await res.json();
                if (res.ok) {
                    setGroupPools(data);
                } else {
                    console.error("Failed to fetch student group pools:", data.error);
                }
            } catch (error) {
                console.error("Error fetching student group pools:", error);
            }
        };

        fetchGroupPools();
    }, []);

    const handleFile = (file) => {
        if (file.type !== "text/plain") {
            alert("Please upload a .txt file");
            return;
        }

        const reader = new FileReader();
        reader.onload = (e) => {
            const text = e.target.result;
            const linesArray = text.split(/\r?\n/).filter((line) => line.trim() !== "");
            const parsedLines = linesArray.map((line) => line.split(","));
            setLines(parsedLines);
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
        if (!selectedPool) return alert("Please select a student group pool!");
        if (lines.length === 0) return alert("No lines to send!");

        try {
            setLoading(true);
            setMessage("");

            const csrftoken = document.cookie
                .split("; ")
                .find((row) => row.startsWith("csrftoken="))
                ?.split("=")[1];

            const res = await fetch("/api/student-groups/", {
                method: "POST",
                headers: { "Content-Type": "application/json", "X-CSRFToken": csrftoken },
                body: JSON.stringify({ student_groups: lines, pool_id: selectedPool }),
            });

            const data = await res.json();

            if (res.ok) {
                setMessage(`✅ Uploaded ${data.length} student groups successfully!`);
                setLines([]); // Clear the lines after successful upload
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

    const handleAddPool = async () => {
        if (!newPoolName.trim()) return alert("Please enter a name for the new student group pool!");

        try {
            setLoading(true);
            setMessage("");

            const csrftoken = document.cookie
                .split("; ")
                .find((row) => row.startsWith("csrftoken="))
                ?.split("=")[1];

            const res = await fetch("/api/student-group-pools/", {
                method: "POST",
                headers: { "Content-Type": "application/json", "X-CSRFToken": csrftoken },
                body: JSON.stringify({ name: newPoolName }),
            });

            const data = await res.json();

            if (res.ok) {
                setMessage(`✅ Created new student group pool: ${data.name}`);
                setGroupPools((prev) => [...prev, data]); // Add the new pool to the list
                setNewPoolName(""); // Clear the input field
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
            {/* Student Group Pool Selection */}
            <div className="w-full max-w-xl">
                <label htmlFor="group-pool" className="block text-gray-700 font-medium mb-2">
                    Select a Student Group Pool:
                </label>
                <select
                    id="group-pool"
                    value={selectedPool}
                    onChange={(e) => setSelectedPool(e.target.value)}
                    className="w-full border border-gray-300 rounded-lg p-2"
                >
                    <option value="">-- Select a Pool --</option>
                    {groupPools.map((pool) => (
                        <option key={pool.id} value={pool.id}>
                            {pool.name}
                        </option>
                    ))}
                </select>
            </div>

            {/* Add New Student Group Pool */}
            <div className="w-full max-w-xl">
                <label htmlFor="new-pool" className="block text-gray-700 font-medium mb-2">
                    Add a New Student Group Pool:
                </label>
                <div className="flex gap-2">
                    <input
                        id="new-pool"
                        type="text"
                        value={newPoolName}
                        onChange={(e) => setNewPoolName(e.target.value)}
                        placeholder="Enter pool name"
                        className="flex-1 border border-gray-300 rounded-lg p-2"
                    />
                    <button
                        onClick={handleAddPool}
                        disabled={loading}
                        className="px-4 py-2 bg-green-600 text-white rounded-lg font-semibold hover:bg-green-700"
                    >
                        Add Pool
                    </button>
                </div>
            </div>

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
                                {line.join(", ")}
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