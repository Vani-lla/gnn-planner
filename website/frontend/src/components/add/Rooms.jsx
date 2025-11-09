import React, { useState, useEffect, useCallback } from "react";
import styles from "../../styles/Rooms.module.css";

export default function Rooms() {
    const [rows, setRows] = useState([]);            // unified existing + new rooms
    const [isDragging, setIsDragging] = useState(false);
    const [loading, setLoading] = useState(false);
    const [message, setMessage] = useState("");

    const [roomPools, setRoomPools] = useState([]);
    const [selectedRoomPool, setSelectedRoomPool] = useState("");
    const [newPoolName, setNewPoolName] = useState("");

    const [subjectPools, setSubjectPools] = useState([]);
    const [selectedSubjectPool, setSelectedSubjectPool] = useState("");
    const [subjectsInPool, setSubjectsInPool] = useState([]);

    // Fetch pools
    useEffect(() => {
        (async () => {
            try {
                const [roomPoolsRes, subjectPoolsRes] = await Promise.all([
                    fetch("/api/room-pools/"),
                    fetch("/api/subject-pools/"),
                ]);
                const rp = await roomPoolsRes.json();
                const sp = await subjectPoolsRes.json();
                if (roomPoolsRes.ok) setRoomPools(rp);
                if (subjectPoolsRes.ok) setSubjectPools(sp);
            } catch {}
        })();
    }, []);

    // Fetch subjects for selected subject pool
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

    // Fetch existing rooms when both pools selected
    useEffect(() => {
        const fetchRooms = async () => {
            if (!selectedRoomPool || !selectedSubjectPool) {
                setRows([]);
                return;
            }
            try {
                const r = await fetch(`/api/rooms/?pool_id=${selectedRoomPool}`);
                const d = await r.json();
                if (!r.ok) {
                    setRows([]);
                    return;
                }
                // Map rooms to rows: assume compatible_subjects is array of {id,name} or ids
                const mapped = d.map(room => ({
                    id: room.id,
                    name: room.name,
                    subjectIds: (room.compatible_subjects || []).map(s =>
                        typeof s === "number" ? s : s.id
                    ),
                }));
                setRows(mapped);
            } catch {
                setRows([]);
            }
        };
        fetchRooms();
    }, [selectedRoomPool, selectedSubjectPool]);

    const parseSelectedOptions = (e) =>
        Array.from(e.target.selectedOptions)
            .map(o => Number(o.value))
            .filter(v => Number.isFinite(v));

    // Drag & drop file: RoomName,SubjectA,SubjectB,...
    const handleFile = (file) => {
        if (!file || file.type !== "text/plain") {
            alert("Upload a .txt file");
            return;
        }
        if (!selectedSubjectPool) {
            alert("Select a subject pool first");
            return;
        }
        const byName = new Map(subjectsInPool.map(s => [s.name.trim().toLowerCase(), s]));
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
                    .filter(Boolean)
                    .map(s => s.id);
                return { name, subjectIds };
            }).filter(p => p.name);
            setRows(prev => {
                const existing = prev.filter(r => r.id);
                return [...existing, ...parsed];
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
            const r = await fetch("/api/room-pools/", {
                method: "POST",
                headers: { "Content-Type": "application/json", "X-CSRFToken": csrftoken },
                body: JSON.stringify({ name: newPoolName }),
            });
            const d = await r.json();
            if (r.ok) {
                setRoomPools(p => [...p, d]);
                setNewPoolName("");
                setMessage("✅ Room pool created");
            } else setMessage("❌ Failed to create room pool");
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
        if (row?.id) {
            try {
                setLoading(true);
                setMessage("");
                const csrftoken = document.cookie.split("; ").find(r => r.startsWith("csrftoken="))?.split("=")[1];
                const res = await fetch(`/api/rooms/${row.id}/`, {
                    method: "DELETE",
                    headers: { "X-CSRFToken": csrftoken },
                });
                if (!res.ok) {
                    const err = await res.json().catch(() => ({}));
                    throw new Error(err.error || "Failed to delete room");
                }
                setRows(prev => prev.filter((_, i) => i !== index));
                setMessage("✅ Deleted room");
            } catch (e) {
                setMessage("❌ " + e.message);
            } finally {
                setLoading(false);
            }
        } else {
            setRows(prev => prev.filter((_, i) => i !== index));
        }
    };

    const handleSaveAll = async () => {
        if (!selectedRoomPool || !selectedSubjectPool) {
            alert("Select both pools first");
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
            // Create new rooms via bulk create endpoint (requires names not IDs)
            if (newOnes.length) {
                const idToName = new Map(subjectsInPool.map(s => [s.id, s.name]));
                const roomsPayload = newOnes.map(r => [
                    r.name,
                    ...r.subjectIds.map(id => idToName.get(id)).filter(Boolean),
                ]);
                const cr = await fetch("/api/rooms/", {
                    method: "POST",
                    headers: { "Content-Type": "application/json", "X-CSRFToken": csrftoken },
                    body: JSON.stringify({
                        rooms: roomsPayload,
                        room_pool_id: selectedRoomPool,
                        subject_pool_id: selectedSubjectPool,
                    }),
                });
                if (!cr.ok) {
                    const err = await cr.json().catch(() => ({}));
                    throw new Error("Create failed: " + (err.error || cr.status));
                }
            }

            // Update existing rooms (PATCH each)
            for (const r of existing) {
                const ur = await fetch(`/api/rooms/${r.id}/`, {
                    method: "PATCH",
                    headers: { "Content-Type": "application/json", "X-CSRFToken": csrftoken },
                    body: JSON.stringify({
                        name: r.name,
                        compatible_subjects: r.subjectIds, // expecting serializer to accept IDs
                        pool: Number(selectedRoomPool),
                    }),
                });
                if (!ur.ok) {
                    const err = await ur.json().catch(() => ({}));
                    throw new Error(`Update failed (${r.name}): ${err.error || ur.status}`);
                }
            }

            // Refresh rooms
            const ref = await fetch(`/api/rooms/?pool_id=${selectedRoomPool}`);
            if (ref.ok) {
                const d = await ref.json();
                const mapped = d.map(room => ({
                    id: room.id,
                    name: room.name,
                    subjectIds: (room.compatible_subjects || []).map(s =>
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
        <div className={styles.roomsView}>
            <div className={styles.roomsSelectors}>
                <select
                    className={styles.roomsSelect}
                    value={selectedRoomPool}
                    onChange={(e) => setSelectedRoomPool(e.target.value)}
                >
                    <option value="">-- Select Room Pool --</option>
                    {roomPools.map(p => <option key={p.id} value={p.id}>{p.name}</option>)}
                </select>
                <select
                    className={styles.roomsSelect}
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
                        placeholder="New room pool name"
                        className={styles.roomsSelect}
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
                <p>{isDragging ? "Drop .txt file here" : "Upload / Drag .txt (Room,Subject,...)"}</p>
                <input
                    type="file"
                    accept=".txt"
                    onChange={(e) => handleFile(e.target.files[0])}
                    className={styles.hiddenFileInput}
                    disabled={!selectedSubjectPool}
                />
            </div>

            <div className={styles.roomsGrid}>
                <div className={styles.roomsGridHeader}>
                    <div className={styles.roomsGridCell}>Room Name</div>
                    <div className={styles.roomsGridCell}>Compatible Subjects (multi-select)</div>
                    <div className={styles.roomsGridCell}>Actions</div>
                </div>
                <div className={styles.roomsGridBody}>
                    {rows.length === 0 && (
                        <div className={styles.roomsGridRow}>
                            <div className={styles.roomsGridCell} style={{ opacity: 0.6 }}>
                                No rows. Add or upload.
                            </div>
                            <div className={styles.roomsGridCell} />
                            <div className={styles.roomsGridCell} />
                        </div>
                    )}
                    {rows.map((r, i) => (
                        <div className={styles.roomsGridRow} key={r.id ? `e-${r.id}` : `n-${i}`}>
                            <div className={styles.roomsGridCell}>
                                <input
                                    type="text"
                                    value={r.name}
                                    onChange={(e) => {
                                        const next = [...rows];
                                        next[i] = { ...next[i], name: e.target.value };
                                        setRows(next);
                                    }}
                                    className={styles.roomsSelect}
                                    placeholder="Room name"
                                />
                            </div>
                            <div className={styles.roomsGridCell}>
                                <select
                                    className={styles.roomsSelect}
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
                            <div className={styles.roomsGridCell}>
                                <button
                                    onClick={() => handleDeleteRow(i)}
                                    className={styles.deleteButton}
                                    title="Delete Room"
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
                        disabled={loading || !selectedRoomPool || !selectedSubjectPool || rows.length === 0}
                    >
                        {loading ? "Saving..." : "Save All"}
                    </button>
                </div>
            </div>

            {message && <p className={styles.message}>{message}</p>}
        </div>
    );
}