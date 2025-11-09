import React, { useState, useEffect, useCallback } from "react";
import styles from "../../styles/Subjects.module.css";

export default function Subjects() {
    const [subjectPools, setSubjectPools] = useState([]);
    const [selectedPool, setSelectedPool] = useState("");
    const [subjects, setSubjects] = useState([]);
    const [newPoolName, setNewPoolName] = useState("");
    const [message, setMessage] = useState("");
    const [loading, setLoading] = useState(false);
    const [isDragging, setIsDragging] = useState(false);

    // Fetch subject pools on component mount
    useEffect(() => {
        const fetchSubjectPools = async () => {
            try {
                const res = await fetch("/api/subject-pools/");
                const data = await res.json();
                if (res.ok) {
                    setSubjectPools(data);
                } else {
                    console.error("Failed to fetch subject pools:", data.error);
                }
            } catch (error) {
                console.error("Error fetching subject pools:", error);
            }
        };

        fetchSubjectPools();
    }, []);

    // Fetch subjects for the selected pool
    useEffect(() => {
        const fetchSubjects = async () => {
            if (!selectedPool) {
                setSubjects([]);
                return;
            }

            try {
                const res = await fetch(`/api/subjects/?pool_id=${selectedPool}`);
                const data = await res.json();
                if (res.ok) {
                    setSubjects(data); // removed automatic empty row
                } else {
                    console.error("Failed to fetch subjects:", data.error);
                }
            } catch (error) {
                console.error("Error fetching subjects:", error);
            }
        };

        fetchSubjects();
    }, [selectedPool]);

    // Handle subject name change
    const handleSubjectChange = (index, value) => {
        setSubjects((prev) => {
            const next = [...prev];
            next[index] = { ...next[index], name: value };
            return next;
        });
    };

    const handleAddRow = () => {
        setSubjects((prev) => [...prev, { name: "", id: null }]);
    };

    // Delete a subject
    const handleDeleteSubject = async (index) => {
        const subjectToDelete = subjects[index];

        // If the subject has an ID, send a DELETE request to the backend
        if (subjectToDelete.id) {
            try {
                const csrftoken = document.cookie
                    .split("; ")
                    .find((row) => row.startsWith("csrftoken="))
                    ?.split("=")[1];

                const res = await fetch(`/api/subjects/${subjectToDelete.id}/`, {
                    method: "DELETE",
                    headers: { "X-CSRFToken": csrftoken },
                });

                if (!res.ok) {
                    const data = await res.json();
                    console.error(`Failed to delete subject: ${data.error || "Unknown error"}`);
                    return;
                }
            } catch (error) {
                console.error("Error deleting subject:", error);
                return;
            }
        }

        // Remove the subject from the list
        setSubjects((prev) => prev.filter((_, i) => i !== index));
    };

    // Save subjects to the backend
    const handleSaveAll = async () => {
        if (!selectedPool) return alert("Please select a subject pool!");

        const subjectsToSave = subjects.filter((s) => s.name.trim() !== "");
        if (subjectsToSave.length === 0) return alert("No subjects to save.");

        try {
            setLoading(true);
            setMessage("");

            const csrftoken = document.cookie
                .split("; ")
                .find((row) => row.startsWith("csrftoken="))
                ?.split("=")[1];

            const res = await fetch("/api/subjects/", {
                method: "POST",
                headers: { "Content-Type": "application/json", "X-CSRFToken": csrftoken },
                body: JSON.stringify({
                    subjects: subjectsToSave.map((s) => s.name),
                    pool_id: selectedPool,
                }),
            });

            const data = await res.json();

            if (res.ok) {
                setMessage("✅ Subjects saved successfully!");
                setSubjects(data); // refresh (no extra empty row)
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

    // Create a new subject pool
    const handleCreatePool = async () => {
        if (!newPoolName.trim()) return alert("Please enter a name for the new subject pool!");

        try {
            setLoading(true);
            setMessage("");

            const csrftoken = document.cookie
                .split("; ")
                .find((row) => row.startsWith("csrftoken="))
                ?.split("=")[1];

            const res = await fetch("/api/subject-pools/", {
                method: "POST",
                headers: { "Content-Type": "application/json", "X-CSRFToken": csrftoken },
                body: JSON.stringify({ name: newPoolName }),
            });

            const data = await res.json();

            if (res.ok) {
                setMessage(`✅ Created new subject pool: ${data.name}`);
                setSubjectPools((prev) => [...prev, data]); // Add the new pool to the list
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

    // Handle file upload
    const handleFile = (file) => {
        if (file.type !== "text/plain") {
            alert("Please upload a .txt file");
            return;
        }

        const reader = new FileReader();
        reader.onload = (e) => {
            const text = e.target.result;
            const linesArray = text.split(/\r?\n/).filter((line) => line.trim() !== "");
            const parsedSubjects = linesArray.map((line) => ({ name: line, id: null }));
            setSubjects((prev) => [...prev, ...parsedSubjects]);
        };
        reader.readAsText(file);
    };

    const handleDrop = useCallback((event) => {
        event.preventDefault();
        setIsDragging(false);
        const file = event.dataTransfer.files[0];
        if (file) handleFile(file);
    }, []);

    return (
        <div className={styles.subjectsView}>
            {/* Row 1: selectors + create pool */}
            <div className={styles.subjectsSelectors}>
                <select
                    className={styles.subjectsSelect}
                    value={selectedPool}
                    onChange={(e) => setSelectedPool(e.target.value)}
                >
                    <option value="">Select Subject Pool</option>
                    {subjectPools.map((pool) => (
                        <option key={pool.id} value={pool.id}>
                            {pool.name}
                        </option>
                    ))}
                </select>
                <div className={styles.inlineFlex}>
                    <input
                        type="text"
                        value={newPoolName}
                        onChange={(e) => setNewPoolName(e.target.value)}
                        placeholder="New subject pool name"
                        className={styles.subjectsSelect}
                    />
                    <button
                        onClick={handleCreatePool}
                        disabled={loading}
                        className={styles.button}
                    >
                        {loading ? "Creating..." : "Add Pool"}
                    </button>
                </div>
            </div>

            {/* Row 2: drag & drop zone */}
            <div
                onDrop={handleDrop}
                onDragOver={(e) => {
                    e.preventDefault();
                    setIsDragging(true);
                }}
                onDragLeave={() => setIsDragging(false)}
                className={`${styles.dropZone} ${isDragging ? styles.dragging : ""}`}
            >
                <p>{isDragging ? "Drop .txt file here" : "Upload / Drag .txt (one subject per line)"}</p>
                <input
                    type="file"
                    accept=".txt"
                    onChange={(e) => handleFile(e.target.files[0])}
                    className={styles.hiddenFileInput}
                />
            </div>

            {/* Grid */}
            <div className={styles.subjectsGrid}>
                <div className={styles.subjectsGridHeader}>
                    <div className={styles.subjectsGridCell}>Subject Name</div>
                    <div className={styles.subjectsGridCell}>Actions</div>
                </div>
                <div className={styles.subjectsGridBody}>
                    {subjects.length === 0 && (
                        <div className={styles.subjectsGridRow}>
                            <div className={styles.subjectsGridCell} style={{ opacity: 0.6 }}>
                                No rows. Add or upload.
                            </div>
                            <div className={styles.subjectsGridCell} />
                        </div>
                    )}
                    {subjects.map((subject, index) => (
                        <div
                            className={styles.subjectsGridRow}
                            key={subject.id ? `e-${subject.id}` : `n-${index}`}
                        >
                            <div className={styles.subjectsGridCell}>
                                <input
                                    type="text"
                                    value={subject.name}
                                    onChange={(e) => handleSubjectChange(index, e.target.value)}
                                    className={styles.subjectsSelect}
                                    placeholder="Subject name"
                                />
                            </div>
                            <div className={styles.subjectsGridCell}>
                                <button
                                    onClick={() => handleDeleteSubject(index)}
                                    className={styles.deleteButton}
                                    title="Delete Subject"
                                >
                                    ✖
                                </button>
                            </div>
                        </div>
                    ))}
                </div>
                <div className={styles.actionRow}>
                    <button
                        type="button"
                        onClick={handleAddRow}
                        className={styles.button}
                        disabled={!selectedPool}
                    >
                        + Add Row
                    </button>
                    <button
                        type="button"
                        onClick={handleSaveAll}
                        className={styles.button}
                        disabled={
                            loading ||
                            !selectedPool ||
                            subjects.filter((s) => s.name.trim() !== "").length === 0
                        }
                    >
                        {loading ? "Saving..." : "Save All"}
                    </button>
                </div>
            </div>

            {message && <p className={styles.message}>{message}</p>}
        </div>
    );
}