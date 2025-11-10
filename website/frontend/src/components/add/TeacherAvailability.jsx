import React, { useEffect, useMemo, useState, useCallback } from "react";
import styles from "../../styles/TeacherAvailability.module.css";

export default function TeacherAvailability() {
    const [teacherPools, setTeacherPools] = useState([]);
    const [requirementSets, setRequirementSets] = useState([]);
    const [selectedRequirementSet, setSelectedRequirementSet] = useState("");
    const [teacherPoolId, setTeacherPoolId] = useState("");
    const [teachers, setTeachers] = useState([]);
    const [availability, setAvailability] = useState({}); // { [teacherId]: { "0": true, ..., "4": true } }
    const [isDragging, setIsDragging] = useState(false);
    const [loading, setLoading] = useState(false);
    const [message, setMessage] = useState("");

    // CSRF
    const csrftoken = useMemo(
        () => document.cookie.split("; ").find((r) => r.startsWith("csrftoken="))?.split("=")[1],
        []
    );

    // Load pools and req sets
    useEffect(() => {
        (async () => {
            try {
                const [tpRes, rsRes] = await Promise.all([
                    fetch("/api/teacher-pools/"),
                    fetch("/api/requirement-sets/"),
                ]);
                if (tpRes.ok) setTeacherPools(await tpRes.json());
                if (rsRes.ok) setRequirementSets(await rsRes.json());
            } catch { /* noop */ }
        })();
    }, []);

    // When req set changes, fetch its teacher pool, teachers, and existing availability
    useEffect(() => {
        const load = async () => {
            if (!selectedRequirementSet) {
                setTeacherPoolId("");
                setTeachers([]);
                setAvailability({});
                return;
            }
            try {
                // Requirement set detail -> get teacher_pool id
                const rsRes = await fetch(`/api/requirement-sets/${selectedRequirementSet}/`);
                const rs = await rsRes.json();
                if (!rsRes.ok) throw new Error("Failed to load requirement set");
                const tPoolId = String(rs.teacher_pool || "");
                setTeacherPoolId(tPoolId);

                // Teachers in that pool
                if (tPoolId) {
                    const tRes = await fetch(`/api/teachers/?pool_id=${tPoolId}`);
                    const tData = await tRes.json();
                    const list = tRes.ok ? tData : [];
                    setTeachers(list);

                    // Existing availability for this req set
                    const aRes = await fetch(`/api/teacher-availability/?req_set=${selectedRequirementSet}`);
                    const aData = aRes.ok ? await aRes.json() : [];
                    const byTeacher = new Map(
                        (Array.isArray(aData) ? aData : []).map((rec) => [rec.teacher, rec.availability])
                    );

                    // Default true for all days; override with existing if present
                    const init = list.reduce((acc, t) => {
                        const existing = byTeacher.get(t.id);
                        acc[t.id] = existing
                            ? existing
                            : { "0": true, "1": true, "2": true, "3": true, "4": true };
                        return acc;
                    }, {});
                    setAvailability(init);
                } else {
                    setTeachers([]);
                    setAvailability({});
                }
            } catch {
                setTeachers([]);
                setAvailability({});
            }
        };
        load();
    }, [selectedRequirementSet]);

    const toggle = (teacherId, dayKey) => {
        setAvailability((prev) => ({
            ...prev,
            [teacherId]: { ...prev[teacherId], [dayKey]: !prev[teacherId]?.[dayKey] },
        }));
    };

    const save = async () => {
        if (!selectedRequirementSet) {
            alert("Select a Requirement Set first");
            return;
        }
        try {
            setLoading(true);
            setMessage("");
            const res = await fetch("/api/teacher-availability/", {
                method: "POST",
                headers: { "Content-Type": "application/json", "X-CSRFToken": csrftoken },
                body: JSON.stringify({
                    req_set_id: Number(selectedRequirementSet),
                    availability,
                }),
            });
            const data = await res.json();
            setMessage(res.ok ? "✅ Availability saved" : `❌ ${data.error || "Save failed"}`);
        } catch {
            setMessage("❌ Network error");
        } finally {
            setLoading(false);
        }
    };

    // Drag & drop + upload .txt: "teacher_name,1,1,1,0,0"
    const handleFile = (file) => {
        if (!file) return;
        if (!file.name.endsWith(".txt")) {
            alert("Upload a .txt file");
            return;
        }
        const byName = new Map(teachers.map((t) => [t.name.trim().toLowerCase(), t.id]));
        const reader = new FileReader();
        reader.onload = (e) => {
            const lines = String(e.target.result || "")
                .split(/\r?\n/)
                .map((l) => l.trim())
                .filter(Boolean);
            setAvailability((prev) => {
                const next = { ...prev };
                for (const line of lines) {
                    const parts = line.split(",").map((p) => p.trim());
                    if (!parts.length) continue;
                    const name = (parts[0] || "").toLowerCase();
                    const id = byName.get(name);
                    if (!id) continue; // ignore teachers not in pool
                    const vals = parts.slice(1, 6); // 5 days
                    const obj = { "0": true, "1": true, "2": true, "3": true, "4": true };
                    vals.forEach((v, i) => {
                        obj[String(i)] = v === "1";
                    });
                    next[id] = obj;
                }
                return next;
            });
        };
        reader.readAsText(file);
    };

    const onDrop = useCallback((e) => {
        e.preventDefault();
        setIsDragging(false);
        const f = e.dataTransfer.files[0];
        if (f) handleFile(f);
    }, [teachers]);

    const poolName = teacherPools.find((p) => String(p.id) === String(teacherPoolId))?.name || "-";

    return (
        <div className={styles.availabilityView}>
            <div className={styles.availabilitySelectors}>
                <select
                    className={styles.availabilitySelect}
                    value={selectedRequirementSet}
                    onChange={(e) => setSelectedRequirementSet(e.target.value)}
                >
                    <option value="">-- Select Requirement Set --</option>
                    {requirementSets.map((rs) => (
                        <option key={rs.id} value={rs.id}>{rs.name}</option>
                    ))}
                </select>
                <div className={styles.inlineFlex}>
                    <span className={styles.poolBadge}>Teacher Pool: <b>{poolName}</b></span>
                </div>
            </div>

            <div
                onDrop={onDrop}
                onDragOver={(e) => { e.preventDefault(); setIsDragging(true); }}
                onDragLeave={() => setIsDragging(false)}
                className={`${styles.dropZone} ${isDragging ? styles.dragging : ""}`}
            >
                <p>{isDragging ? "Drop .txt here" : "Upload / Drag .txt (teacher,1,1,1,0,0)"}</p>
                <input
                    type="file"
                    accept=".txt"
                    onChange={(e) => handleFile(e.target.files[0])}
                    className={styles.hiddenFileInput}
                    disabled={!selectedRequirementSet}
                />
            </div>

            <div className={styles.gridCard}>
                <div className={styles.gridHeader} style={{ gridTemplateColumns: "4fr repeat(5, 1fr)" }}>
                    <div className={`${styles.cell} ${styles.firstCol}`}>Teacher</div>
                    <div className={styles.cell}>Day 1</div>
                    <div className={styles.cell}>Day 2</div>
                    <div className={styles.cell}>Day 3</div>
                    <div className={styles.cell}>Day 4</div>
                    <div className={styles.cell}>Day 5</div>
                </div>
                <div className={styles.gridBody}>
                    {teachers.length === 0 ? (
                        <div className={styles.placeholder}>Select a Requirement Set to load teachers.</div>
                    ) : teachers.map((t) => (
                        <div key={t.id} className={styles.gridRow} style={{ gridTemplateColumns: "4fr repeat(5, 1fr)" }}>
                            <div className={`${styles.cell} ${styles.firstCol}`}>{t.name}</div>
                            {["0","1","2","3","4"].map((d) => (
                                <div key={d} className={styles.cell}>
                                    <input
                                        type="checkbox"
                                        checked={availability[t.id]?.[d] ?? true}
                                        onChange={() => toggle(t.id, d)}
                                    />
                                </div>
                            ))}
                        </div>
                    ))}
                </div>
                <div className={styles.actionRow}>
                    <button
                        className={styles.button}
                        onClick={save}
                        disabled={loading || !selectedRequirementSet || teachers.length === 0}
                    >
                        {loading ? "Saving..." : "Save Availability"}
                    </button>
                </div>
            </div>

            {message && <p className={styles.message}>{message}</p>}
        </div>
    );
}