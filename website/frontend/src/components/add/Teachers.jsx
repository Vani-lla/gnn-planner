import React, { useState, useEffect, useCallback } from "react";
import styles from "../../styles/Teachers.module.css";

export default function Teachers() {
    const [rows, setRows] = useState([]); // unified existing + new
    const [isDragging, setIsDragging] = useState(false);
    const [loading, setLoading] = useState(false);
    const [message, setMessage] = useState("");
    const [teacherPools, setTeacherPools] = useState([]);
    const [selectedPool, setSelectedPool] = useState("");
    const [newPoolName, setNewPoolName] = useState("");
    const [subjectPools, setSubjectPools] = useState([]);
    const [selectedSubjectPool, setSelectedSubjectPool] = useState("");
    const [subjectsInPool, setSubjectsInPool] = useState([]);

    useEffect(() => {
        (async () => {
            try {
                const r = await fetch("/api/teacher-pools/");
                const d = await r.json();
                if (r.ok) setTeacherPools(d);
            } catch { }
        })();
    }, []);

    useEffect(() => {
        (async () => {
            try {
                const r = await fetch("/api/subject-pools/");
                const d = await r.json();
                if (r.ok) setSubjectPools(d);
            } catch { }
        })();
    }, []);

    useEffect(() => {
        const fetchSubjects = async () => {
            if (!selectedSubjectPool) {
                setSubjectsInPool([]);
                setRows([]);
                return;
            }
            try {
                const r = await fetch(`/api/subjects/?pool_id=${selectedSubjectPool}`);
                const d = await r.json();
                setSubjectsInPool(r.ok ? d : []);
            } catch {
                setSubjectsInPool([]);
            }
        };
        fetchSubjects();
    }, [selectedSubjectPool]);

    useEffect(() => {
        if (!selectedPool || !selectedSubjectPool) {
            setRows([]);
            return;
        }
        const fetchTeachers = async () => {
            try {
                const r = await fetch(`/api/teachers/?pool_id=${selectedPool}`);
                const d = await r.json();
                if (r.ok) {
                    const mapped = d.map(t => ({
                        id: t.id,
                        name: t.name,
                        subjectIds: (t.teached_subjects || t.subjects || []).map(s =>
                            typeof s === "number" ? s : s.id
                        ),
                    }));
                    setRows(mapped);
                } else {
                    setRows([]);
                }
            } catch {
                setRows([]);
            }
        };
        fetchTeachers();
    }, [selectedPool, selectedSubjectPool]);

    const parseSelectedOptions = (e) =>
        Array.from(e.target.selectedOptions)
            .map(o => Number(o.value))
            .filter(v => Number.isFinite(v));

    const handleFile = (file) => {
        if (!file || file.type !== "text/plain") {
            alert("Upload a .txt file");
            return;
        }
        if (!selectedSubjectPool) {
            alert("Select a subject pool first");
            return;
        }
        const byName = new Map(subjectsInPool.map(s => [s.name.trim().toLowerCase(), s.id]));
        const reader = new FileReader();
        reader.onload = (e) => {
            const lines = e.target.result
                .split(/\r?\n/)
                .map(l => l.trim())
                .filter(Boolean);
            const parsed = lines.map(line => {
                const parts = line.split(",").map(p => p.trim()).filter(Boolean);
                const name = parts[0] || "";
                const subjectIds = parts.slice(1)
                    .map(n => byName.get(n.toLowerCase()))
                    .filter(id => typeof id === "number");
                return { name, subjectIds };
            });
            setRows(prev => {
                const existing = prev.filter(r => r.id);
                return [...existing, ...parsed.filter(p => p.name)];
            });
        };
        reader.readAsText(file);
    };

    const handleDrop = useCallback((e) => {
        e.preventDefault();
        setIsDragging(false);
        const f = e.dataTransfer.files[0];
        if (f) handleFile(f);
    }, []);

    const handleAddPool = async () => {
        if (!newPoolName.trim()) return;
        try {
            setLoading(true);
            setMessage("");
            const csrftoken = document.cookie.split("; ").find(r => r.startsWith("csrftoken="))?.split("=")[1];
            const r = await fetch("/api/teacher-pools/", {
                method: "POST",
                headers: { "Content-Type": "application/json", "X-CSRFToken": csrftoken },
                body: JSON.stringify({ name: newPoolName }),
            });
            const d = await r.json();
            if (r.ok) {
                setTeacherPools(p => [...p, d]);
                setNewPoolName("");
                setMessage("✅ Pool created");
            } else setMessage("❌ Failed to create pool");
        } catch {
            setMessage("❌ Network error");
        } finally {
            setLoading(false);
        }
    };

    const handleAddRow = () => {
        setRows(prev => [...prev, { name: "", subjectIds: [] }]);
    };

    const handleDeleteRow = async (index) => {
        const row = rows[index];
        // If it's a persisted teacher -> DELETE from backend
        if (row?.id) {
            try {
                setLoading(true);
                setMessage("");
                const csrftoken = document.cookie
                    .split("; ")
                    .find((r) => r.startsWith("csrftoken="))
                    ?.split("=")[1];

                const res = await fetch(`/api/teachers/${row.id}/`, {
                    method: "DELETE",
                    headers: { "X-CSRFToken": csrftoken },
                });

                if (!res.ok) {
                    const err = await res.json().catch(() => ({}));
                    throw new Error(err.error || "Failed to delete teacher");
                }

                setRows((prev) => prev.filter((_, i) => i !== index));
                setMessage("✅ Deleted teacher");
            } catch (e) {
                setMessage("❌ " + e.message);
            } finally {
                setLoading(false);
            }
        } else {
            // Local-only row
            setRows((prev) => prev.filter((_, i) => i !== index));
        }
    };

    const handleSaveAll = async () => {
        if (!selectedPool || !selectedSubjectPool) {
            alert("Select pools first");
            return;
        }
        const cleaned = rows.filter(r => r.name.trim() !== "");
        if (cleaned.length === 0) {
            alert("No data to save");
            return;
        }
        const newOnes = cleaned.filter(r => !r.id);
        const existing = cleaned.filter(r => r.id);

        setLoading(true);
        setMessage("");
        const csrftoken = document.cookie.split("; ").find(r => r.startsWith("csrftoken="))?.split("=")[1];

        try {
            // Create new teachers (bulk)
            if (newOnes.length) {
                const createPayload = {
                    teachers: newOnes.map(t => ({
                        name: t.name,
                        subjects: t.subjectIds,
                    })),
                    pool_id: selectedPool,
                };
                const cr = await fetch("/api/teachers/", {
                    method: "POST",
                    headers: { "Content-Type": "application/json", "X-CSRFToken": csrftoken },
                    body: JSON.stringify(createPayload),
                });
                if (!cr.ok) {
                    const err = await cr.json().catch(() => ({}));
                    throw new Error("Create failed: " + (err.error || cr.status));
                }
            }

            // Update existing
            for (const t of existing) {
                const ur = await fetch(`/api/teachers/${t.id}/`, {
                    method: "PATCH",
                    headers: { "Content-Type": "application/json", "X-CSRFToken": csrftoken },
                    body: JSON.stringify({
                        name: t.name,
                        subjects: t.subjectIds,
                        pool: [Number(selectedPool)],
                    }),
                });
                if (!ur.ok) {
                    const err = await ur.json().catch(() => ({}));
                    throw new Error(`Update failed (${t.name}): ${err.error || ur.status}`);
                }
            }

            // Refresh
            const ref = await fetch(`/api/teachers/?pool_id=${selectedPool}`);
            if (ref.ok) {
                const d = await ref.json();
                const mapped = d.map(t => ({
                    id: t.id,
                    name: t.name,
                    subjectIds: (t.teached_subjects || t.subjects || []).map(s =>
                        typeof s === "number" ? s : s.id
                    ),
                }));
                setRows(mapped);
            }
            setMessage("✅ Saved");
        } catch (e) {
            setMessage("❌ " + e.message);
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className={styles.teachersView}>
            <div className={styles.teachersSelectors}>
                <select
                    className={styles.teachersSelect}
                    value={selectedPool}
                    onChange={(e) => setSelectedPool(e.target.value)}
                >
                    <option value="">-- Select Teacher Pool --</option>
                    {teacherPools.map(p => <option key={p.id} value={p.id}>{p.name}</option>)}
                </select>
                <select
                    className={styles.teachersSelect}
                    value={selectedSubjectPool}
                    onChange={(e) => setSelectedSubjectPool(e.target.value)}
                >
                    <option value="">-- Select Subject Pool --</option>
                    {subjectPools.map(p => <option key={p.id} value={p.id}>{p.name}</option>)}
                </select>
                <div className={styles.inlineFlex}>
                    <input
                        type="text"
                        value={newPoolName}
                        onChange={(e) => setNewPoolName(e.target.value)}
                        placeholder="New teacher pool name"
                        className={styles.teachersSelect}
                    />
                    <button
                        onClick={handleAddPool}
                        disabled={loading}
                        className={styles.button}
                    >
                        {loading ? "Creating..." : "Add Pool"}
                    </button>
                </div>
            </div>

            <div
                onDrop={handleDrop}
                onDragOver={(e) => { e.preventDefault(); setIsDragging(true); }}
                onDragLeave={() => setIsDragging(false)}
                className={`${styles.dropZone} ${isDragging ? styles.dragging : ""}`}
            >
                <p>{isDragging ? "Drop .txt file here" : "Upload / Drag .txt (Teacher,Subject,...)"}</p>
                <input
                    type="file"
                    accept=".txt"
                    onChange={(e) => handleFile(e.target.files[0])}
                    className={styles.hiddenFileInput}
                    disabled={!selectedSubjectPool}
                />
            </div>

            <div className={styles.teachersGrid}>
                <div className={styles.teachersGridHeader}>
                    <div className={styles.teachersGridCell}>Teacher Name</div>
                    <div className={styles.teachersGridCell}>Subjects (multi-select)</div>
                    <div className={styles.teachersGridCell}>Actions</div>
                </div>
                <div className={styles.teachersGridBody}>
                    {rows.length === 0 && (
                        <div className={styles.teachersGridRow}>
                            <div className={styles.teachersGridCell} style={{ opacity: 0.6 }}>
                                No rows. Add or upload.
                            </div>
                            <div className={styles.teachersGridCell} />
                            <div className={styles.teachersGridCell} />
                        </div>
                    )}
                    {rows.map((r, i) => (
                        <div className={styles.teachersGridRow} key={r.id ? `e-${r.id}` : `n-${i}`}>
                            <div className={styles.teachersGridCell}>
                                <input
                                    type="text"
                                    value={r.name}
                                    onChange={(e) => {
                                        const next = [...rows];
                                        next[i] = { ...next[i], name: e.target.value };
                                        setRows(next);
                                    }}
                                    className={styles.teachersSelect}
                                    placeholder="Teacher name"
                                />
                            </div>
                            <div className={styles.teachersGridCell}>
                                <select
                                    className={styles.teachersSelect}
                                    multiple
                                    value={r.subjectIds}
                                    disabled={!selectedSubjectPool}
                                    onChange={(e) => {
                                        const next = [...rows];
                                        next[i] = { ...next[i], subjectIds: parseSelectedOptions(e) };
                                        setRows(next);
                                    }}
                                >
                                    {subjectsInPool.map(s => (
                                        <option key={s.id} value={s.id}>{s.name}</option>
                                    ))}
                                </select>
                            </div>
                            <div className={styles.teachersGridCell}>
                                <button
                                    onClick={() => handleDeleteRow(i)}
                                    className={styles.deleteButton}
                                    title="Delete Teacher"
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
                        disabled={!selectedSubjectPool}
                    >
                        + Add Row
                    </button>
                    <button
                        type="button"
                        onClick={handleSaveAll}
                        className={styles.button}
                        disabled={loading || !selectedPool || !selectedSubjectPool || rows.length === 0}
                    >
                        {loading ? "Saving..." : "Save All"}
                    </button>
                </div>
            </div>

            {message && <p className={styles.message}>{message}</p>}
        </div>
    );
}