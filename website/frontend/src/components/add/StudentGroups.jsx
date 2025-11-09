import React, { useState, useEffect, useCallback } from "react";
import styles from "../../styles/StudentGroups.module.css";

export default function StudentGroups() {
    const [groupPools, setGroupPools] = useState([]);
    const [selectedPool, setSelectedPool] = useState("");
    const [groups, setGroups] = useState([]);
    const [newPoolName, setNewPoolName] = useState("");
    const [message, setMessage] = useState("");
    const [loading, setLoading] = useState(false);
    const [isDragging, setIsDragging] = useState(false);

    // Fetch pools
    useEffect(() => {
        const fetchGroupPools = async () => {
            try {
                const res = await fetch("/api/student-group-pools/");
                const data = await res.json();
                if (res.ok) setGroupPools(data);
            } catch (e) {
                console.error(e);
            }
        };
        fetchGroupPools();
    }, []);

    // Fetch groups when pool selected
    useEffect(() => {
        const fetchGroups = async () => {
            if (!selectedPool) {
                setGroups([]);
                return;
            }
            try {
                const res = await fetch(`/api/student-groups/?pool_id=${selectedPool}`);
                const data = await res.json();
                if (res.ok) {
                    // Normalize to {id, name, desc}
                    setGroups(data.map(g => ({ id: g.id, name: g.name, desc: g.desc || "" })));
                } else {
                    console.error("Failed to fetch groups");
                }
            } catch (e) {
                console.error(e);
            }
        };
        fetchGroups();
    }, [selectedPool]);

    const csrftoken = document.cookie
        .split("; ")
        .find((row) => row.startsWith("csrftoken="))
        ?.split("=")[1];

    // Add new pool
    const handleAddPool = async () => {
        if (!newPoolName.trim()) return alert("Enter pool name");
        try {
            setLoading(true);
            setMessage("");
            const res = await fetch("/api/student-group-pools/", {
                method: "POST",
                headers: { "Content-Type": "application/json", "X-CSRFToken": csrftoken },
                body: JSON.stringify({ name: newPoolName }),
            });
            const data = await res.json();
            if (res.ok) {
                setGroupPools(prev => [...prev, data]);
                setNewPoolName("");
                setMessage(`✅ Created pool: ${data.name}`);
            } else {
                setMessage(`❌ ${data.error || "Error"}`);
            }
        } catch {
            setMessage("❌ Network error");
        } finally {
            setLoading(false);
        }
    };

    // Handle manual edits
    const handleChange = (index, field, value) => {
        setGroups(prev => {
            const next = [...prev];
            next[index] = { ...next[index], [field]: value };
            return next;
        });
    };

    const handleAddRow = () => {
        if (!selectedPool) return;
        setGroups(prev => [...prev, { id: null, name: "", desc: "" }]);
    };

    const handleDelete = async (index) => {
        const g = groups[index];
        if (g.id) {
            try {
                const res = await fetch(`/api/student-groups/${g.id}/`, {
                    method: "DELETE",
                    headers: { "X-CSRFToken": csrftoken },
                });
                if (!res.ok) {
                    const data = await res.json();
                    console.error("Delete failed", data);
                    return;
                }
            } catch (e) {
                console.error(e);
                return;
            }
        }
        setGroups(prev => prev.filter((_, i) => i !== index));
    };

    // Save all new (id == null) or edited (only new bulk creation supported)
    const handleSaveAll = async () => {
        if (!selectedPool) return alert("Select pool");
        const toCreate = groups.filter(g => !g.id && g.name.trim() !== "");
        if (toCreate.length === 0) return alert("No new groups to save");
        try {
            setLoading(true);
            setMessage("");
            const payload = {
                pool_id: selectedPool,
                student_groups: toCreate.map(g => [g.name.trim(), g.desc.trim() || null]),
            };
            const res = await fetch("/api/student-groups/", {
                method: "POST",
                headers: { "Content-Type": "application/json", "X-CSRFToken": csrftoken },
                body: JSON.stringify(payload),
            });
            const data = await res.json();
            if (res.ok) {
                setMessage(`✅ Saved ${data.length} groups`);
                // Refresh list
                const listRes = await fetch(`/api/student-groups/?pool_id=${selectedPool}`);
                const listData = await listRes.json();
                if (listRes.ok) {
                    setGroups(listData.map(g => ({ id: g.id, name: g.name, desc: g.desc || "" })));
                }
            } else {
                setMessage(`❌ ${data.error || "Error"}`);
            }
        } catch {
            setMessage("❌ Network error");
        } finally {
            setLoading(false);
        }
    };

    // Drag & drop file
    const handleFile = (file) => {
        if (!file || file.type !== "text/plain") {
            alert("Upload a .txt file");
            return;
        }
        const reader = new FileReader();
        reader.onload = (e) => {
            const text = e.target.result;
            const lines = text.split(/\r?\n/).filter(l => l.trim() !== "");
            // Each line: name[,desc]
            const parsed = lines.map(line => {
                const parts = line.split(",").map(p => p.trim());
                return { id: null, name: parts[0] || "", desc: parts[1] || "" };
            });
            setGroups(prev => [...prev, ...parsed]);
        };
        reader.readAsText(file);
    };

    const handleDrop = useCallback((e) => {
        e.preventDefault();
        setIsDragging(false);
        const file = e.dataTransfer.files[0];
        if (file) handleFile(file);
    }, []);

    return (
        <div className={styles.groupsView}>
            <div className={styles.groupsSelectors}>
                <select
                    className={styles.groupsSelect}
                    value={selectedPool}
                    onChange={(e) => setSelectedPool(e.target.value)}
                >
                    <option value="">Select Group Pool</option>
                    {groupPools.map(pool => (
                        <option key={pool.id} value={pool.id}>{pool.name}</option>
                    ))}
                </select>
                <div className={styles.inlineFlex}>
                    <input
                        type="text"
                        value={newPoolName}
                        onChange={(e) => setNewPoolName(e.target.value)}
                        placeholder="New group pool name"
                        className={styles.groupsSelect}
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
                <p>{isDragging ? "Drop .txt file here" : "Upload / Drag .txt (name[,desc])"}</p>
                <input
                    type="file"
                    accept=".txt"
                    onChange={(e) => handleFile(e.target.files[0])}
                    className={styles.hiddenFileInput}
                />
            </div>

            <div className={styles.groupsGrid}>
                <div className={styles.groupsGridHeader}>
                    <div className={styles.groupsGridCell}>Group Name</div>
                    <div className={styles.groupsGridCell}>Description</div>
                    <div className={styles.groupsGridCell}>Actions</div>
                </div>
                <div className={styles.groupsGridBody}>
                    {groups.length === 0 && (
                        <div className={styles.groupsGridRow}>
                            <div className={styles.groupsGridCell} style={{ opacity: 0.6 }}>No rows. Add or upload.</div>
                            <div className={styles.groupsGridCell} />
                            <div className={styles.groupsGridCell} />
                        </div>
                    )}
                    {groups.map((g, i) => (
                        <div
                            className={styles.groupsGridRow}
                            key={g.id ? `e-${g.id}` : `n-${i}`}
                        >
                            <div className={styles.groupsGridCell}>
                                <input
                                    type="text"
                                    value={g.name}
                                    onChange={(e) => handleChange(i, "name", e.target.value)}
                                    className={styles.groupsSelect}
                                    placeholder="Group name"
                                />
                            </div>
                            <div className={styles.groupsGridCell}>
                                <input
                                    type="text"
                                    value={g.desc}
                                    onChange={(e) => handleChange(i, "desc", e.target.value)}
                                    className={styles.groupsSelect}
                                    placeholder="Description (optional)"
                                />
                            </div>
                            <div className={styles.groupsGridCell}>
                                <button
                                    onClick={() => handleDelete(i)}
                                    className={styles.deleteButton}
                                    title="Delete Group"
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
                            groups.filter(g => !g.id && g.name.trim() !== "").length === 0
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