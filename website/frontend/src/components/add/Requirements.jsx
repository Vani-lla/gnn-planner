import React, { useEffect, useMemo, useState, useCallback } from "react";
import styles from "../../styles/Requirements.module.css";

export default function Requirements() {
    const [teacherPools, setTeacherPools] = useState([]);
    const [subjectPools, setSubjectPools] = useState([]);
    const [groupPools, setGroupPools] = useState([]);
    const [reqSets, setReqSets] = useState([]);

    const [selectedTeacherPool, setSelectedTeacherPool] = useState("");
    const [selectedSubjectPool, setSelectedSubjectPool] = useState("");
    const [selectedGroupPool, setSelectedGroupPool] = useState("");
    const [selectedReqSet, setSelectedReqSet] = useState("");
    const [newReqSetName, setNewReqSetName] = useState("");

    const [grid, setGrid] = useState(null); // { req_set, teachers, groups, subjects, requirements }
    const [updatedRequirements, setUpdatedRequirements] = useState([]);
    const [loading, setLoading] = useState(false);
    const [message, setMessage] = useState("");
    const [isDragging, setIsDragging] = useState(false);

    // Load pools and req sets
    useEffect(() => {
        (async () => {
            try {
                const [tp, sp, gp, rs] = await Promise.all([
                    fetch("/api/teacher-pools/"),
                    fetch("/api/subject-pools/"),
                    fetch("/api/student-group-pools/"),
                    fetch("/api/requirement-sets/"),
                ]);
                const [tpd, spd, gpd, rsd] = await Promise.all([tp.json(), sp.json(), gp.json(), rs.json()]);
                if (tp.ok) setTeacherPools(tpd);
                if (sp.ok) setSubjectPools(spd);
                if (gp.ok) setGroupPools(gpd);
                if (rs.ok) setReqSets(rsd);
            } catch { /* noop */ }
        })();
    }, []);

    // Helper: CSRF
    const csrftoken = useMemo(
        () => document.cookie.split("; ").find(r => r.startsWith("csrftoken="))?.split("=")[1],
        []
    );

    // Selecting existing req set should auto-fill pools and fetch grid
    useEffect(() => {
        const loadReqSet = async (id) => {
            if (!id) {
                setGrid(null);
                return;
            }
            try {
                const res = await fetch(`/api/requirement-sets/${id}/`);
                const data = await res.json();
                if (res.ok) {
                    // Auto-fill pools
                    setSelectedTeacherPool(String(data.teacher_pool || ""));
                    setSelectedSubjectPool(String(data.subject_pool || ""));
                    setSelectedGroupPool(String(data.group_pool || ""));

                    // Fetch grid for this req_set
                    const gRes = await fetch(`/api/requirements/grid/?req_set_id=${id}`);
                    const gData = await gRes.json();
                    if (gRes.ok) {
                        // Backend returns either a single object or array; normalize
                        const picked = Array.isArray(gData) ? (gData[0] || null) : gData;
                        setGrid(picked);
                    } else {
                        setGrid(null);
                    }
                }
            } catch {
                setGrid(null);
            }
        };
        loadReqSet(selectedReqSet);
        setUpdatedRequirements([]);
    }, [selectedReqSet]);

    // Create a new Requirement Set using selected pools
    const handleCreateReqSet = async () => {
        if (!newReqSetName.trim()) return alert("Enter requirement set name");
        if (!selectedTeacherPool || !selectedSubjectPool || !selectedGroupPool) {
            return alert("Select Teacher, Subject and Group pools first");
        }
        try {
            setLoading(true);
            setMessage("");
            const res = await fetch("/api/requirement-sets/", {
                method: "POST",
                headers: { "Content-Type": "application/json", "X-CSRFToken": csrftoken },
                body: JSON.stringify({
                    name: newReqSetName.trim(),
                    teacher_pool: Number(selectedTeacherPool),
                    subject_pool: Number(selectedSubjectPool),
                    group_pool: Number(selectedGroupPool),
                    room_pool: null,
                }),
            });
            const data = await res.json();
            if (res.ok) {
                setReqSets(prev => [...prev, data]);
                setSelectedReqSet(String(data.id));
                setNewReqSetName("");
                setMessage("✅ Requirement set created");
            } else {
                setMessage(`❌ ${data.error || "Failed to create requirement set"}`);
            }
        } catch {
            setMessage("❌ Network error");
        } finally {
            setLoading(false);
        }
    };

    // Track cell changes
    const handleCellChange = (reqSetId, teacherId, groupId, subjectId, value) => {
        const hours = Number.isFinite(parseInt(value, 10)) ? parseInt(value, 10) : 0;
        setUpdatedRequirements(prev => {
            const idx = prev.findIndex(
                r => r.req_set === reqSetId && r.teacher === teacherId && r.group === groupId && r.subject === subjectId
            );
            if (idx >= 0) {
                const next = [...prev];
                next[idx] = { ...next[idx], hours };
                return next;
            }
            return [...prev, { req_set: reqSetId, teacher: teacherId, group: groupId, subject: subjectId, hours }];
        });
    };

    const handleSave = async () => {
        if (!selectedReqSet) {
            alert("Select or create a requirement set first");
            return;
        }
        if (updatedRequirements.length === 0) {
            alert("No changes to save");
            return;
        }
        try {
            setLoading(true);
            setMessage("");
            const res = await fetch("/api/requirements/", {
                method: "POST",
                headers: { "Content-Type": "application/json", "X-CSRFToken": csrftoken },
                body: JSON.stringify(updatedRequirements),
            });
            if (!res.ok) {
                const err = await res.json().catch(() => ({}));
                throw new Error(err.error || "Save failed");
            }
            setUpdatedRequirements([]);
            setMessage("✅ Requirements saved");
            // Refresh grid
            const gRes = await fetch(`/api/requirements/grid/?req_set_id=${selectedReqSet}`);
            const gData = await gRes.json();
            const picked = Array.isArray(gData) ? (gData[0] || null) : gData;
            setGrid(picked);
        } catch (e) {
            setMessage("❌ " + e.message);
        } finally {
            setLoading(false);
        }
    };

    const handleImportResponse = async (res) => {
        const data = await res.json();
        if (res.ok) {
            setMessage(`✅ Imported CSV: ${data.requirements_processed} requirements`);
            // If a new set was created select it
            if (!selectedReqSet) {
                setSelectedReqSet(String(data.requirement_set_id));
            } else {
                // Refresh grid
                const gRes = await fetch(`/api/requirements/grid/?req_set_id=${selectedReqSet || data.requirement_set_id}`);
                const gData = await gRes.json();
                const picked = Array.isArray(gData) ? (gData[0] || null) : gData;
                setGrid(picked);
            }
        } else {
            setMessage(`❌ ${data.error || "Import failed"}`);
        }
    };

    const uploadCsv = async (file) => {
        if (!file) return;
        if (!selectedTeacherPool || !selectedSubjectPool || !selectedGroupPool) {
            alert("Select all pools before importing");
            return;
        }
        const form = new FormData();
        form.append("file", file);
        form.append("teacher_pool_id", selectedTeacherPool);
        form.append("subject_pool_id", selectedSubjectPool);
        form.append("group_pool_id", selectedGroupPool);
        if (selectedReqSet) form.append("req_set_id", selectedReqSet);
        else if (newReqSetName.trim()) form.append("new_req_set_name", newReqSetName.trim());

        try {
            setLoading(true);
            setMessage("");
            const res = await fetch("/api/requirements/import-csv/", {
                method: "POST",
                headers: { "X-CSRFToken": csrftoken },
                body: form,
            });
            await handleImportResponse(res);
        } catch {
            setMessage("❌ Network error");
        } finally {
            setLoading(false);
        }
    };

    const handleFile = (file) => {
        if (!file) return;
        if (!file.name.endsWith(".csv")) {
            alert("Upload a .csv file");
            return;
        }
        uploadCsv(file);
    };

    const handleDrop = useCallback((e) => {
        e.preventDefault();
        setIsDragging(false);
        const file = e.dataTransfer.files[0];
        handleFile(file);
    }, [selectedTeacherPool, selectedSubjectPool, selectedGroupPool, selectedReqSet, newReqSetName]);

    // Helper to read existing hours
    const getExistingHours = (teacherId, groupId, subjectId) => {
        if (!grid) return 0;
        const existing = grid.requirements?.find(
            r => r.teacher === teacherId && r.group === groupId && r.subject === subjectId
        );
        return existing ? Number(existing.hours) || 0 : 0;
    };

    // Effective hours = updated (if present) else existing
    const getEffectiveHours = (teacherId, groupId, subjectId) => {
        const upd = updatedRequirements.find(
            r => r.teacher === teacherId && r.group === groupId && r.subject === subjectId
        );
        return upd ? Number(upd.hours) || 0 : getExistingHours(teacherId, groupId, subjectId);
    };

    // Subject sums per group across all teachers
    const getSubjectGroupSum = (subjectId, groupId) => {
        const teacherIds = grid?.teachers
            ?.filter(t => (t.subjects || []).some(s => s.id === subjectId))
            .map(t => t.id) || [];
        return teacherIds.reduce((sum, tId) => sum + getEffectiveHours(tId, groupId, subjectId), 0);
    };

    const poolsDisabled = Boolean(selectedReqSet);

    return (
        <div className={styles.requirementsView}>
            {/* Selectors */}
            <div className={styles.requirementsSelectors}>
                <select
                    className={styles.requirementsSelect}
                    value={selectedReqSet}
                    onChange={(e) => setSelectedReqSet(e.target.value)}
                >
                    <option value="">Select Requirement Set</option>
                    {reqSets.map(rs => (
                        <option key={rs.id} value={rs.id}>{rs.name}</option>
                    ))}
                </select>

                <select
                    className={styles.requirementsSelect}
                    value={selectedTeacherPool}
                    onChange={(e) => setSelectedTeacherPool(e.target.value)}
                    disabled={poolsDisabled}
                >
                    <option value="">Teacher Pool</option>
                    {teacherPools.map(p => <option key={p.id} value={p.id}>{p.name}</option>)}
                </select>

                <select
                    className={styles.requirementsSelect}
                    value={selectedSubjectPool}
                    onChange={(e) => setSelectedSubjectPool(e.target.value)}
                    disabled={poolsDisabled}
                >
                    <option value="">Subject Pool</option>
                    {subjectPools.map(p => <option key={p.id} value={p.id}>{p.name}</option>)}
                </select>

                <select
                    className={styles.requirementsSelect}
                    value={selectedGroupPool}
                    onChange={(e) => setSelectedGroupPool(e.target.value)}
                    disabled={poolsDisabled}
                >
                    <option value="">Student Group Pool</option>
                    {groupPools.map(p => <option key={p.id} value={p.id}>{p.name}</option>)}
                </select>

                <div className={styles.inlineFlex}>
                    <input
                        type="text"
                        value={newReqSetName}
                        onChange={(e) => setNewReqSetName(e.target.value)}
                        placeholder="New requirement set name"
                        className={styles.requirementsSelect}
                        disabled={loading}
                    />
                    <button
                        className={styles.button}
                        onClick={handleCreateReqSet}
                        disabled={
                            loading ||
                            !selectedTeacherPool ||
                            !selectedSubjectPool ||
                            !selectedGroupPool ||
                            !newReqSetName.trim()
                        }
                    >
                        {loading ? "Creating..." : "Create Set"}
                    </button>
                </div>
            </div>

            <div
                onDrop={handleDrop}
                onDragOver={(e) => { e.preventDefault(); setIsDragging(true); }}
                onDragLeave={() => setIsDragging(false)}
                className={`${styles.dropZone} ${isDragging ? styles.dragging : ""}`}
            >
                <p>
                    {isDragging
                        ? "Drop requirements CSV here"
                        : "Drag / click to upload requirements CSV (first 2 rows = groups)"}
                </p>
                <input
                    type="file"
                    accept=".csv"
                    onChange={(e) => handleFile(e.target.files[0])}
                    className={styles.hiddenFileInput}
                />
            </div>

            {/* Grid */}
            <div className={styles.gridCard}>
                {!selectedReqSet ? (
                    <div className={styles.placeholder}>Select or create a Requirement Set to begin.</div>
                ) : !grid ? (
                    <div className={styles.placeholder}>Loading grid...</div>
                ) : (
                    <div className={styles.gridWrapper}>
                        {/* Sticky header */}
                        <div
                            className={styles.gridHeader}
                            style={{ gridTemplateColumns: `220px repeat(${grid.groups.length}, 84px)` }}
                        >
                            <div className={`${styles.cell} ${styles.firstCol}`}>Subject / Teacher</div>
                            {grid.groups.map(g => (
                                <div key={g.id} className={`${styles.cell} ${styles.groupCol}`}>{g.name}</div>
                            ))}
                        </div>

                        {/* Body */}
                        <div className={styles.gridBody}>
                            {grid.subjects.map(subject => (
                                <React.Fragment key={subject.id}>
                                    {/* Subject summary row with sums */}
                                    <div
                                        className={`${styles.gridRow} ${styles.subjectRow}`}
                                        style={{ gridTemplateColumns: `220px repeat(${grid.groups.length}, 84px)` }}
                                    >
                                        <div className={`${styles.cell} ${styles.firstCol} ${styles.subjectTitle}`}>
                                            {subject.name}
                                        </div>
                                        {grid.groups.map(g => (
                                            <div key={`sum-${subject.id}-${g.id}`} className={`${styles.cell} ${styles.groupCol}`}>
                                                {getSubjectGroupSum(subject.id, g.id)}
                                            </div>
                                        ))}
                                    </div>

                                    {/* Teacher rows */}
                                    {grid.teachers
                                        .filter(t => (t.subjects || []).some(s => s.id === subject.id))
                                        .map(t => (
                                            <div
                                                key={`${t.id}-${subject.id}`}
                                                className={styles.gridRow}
                                                style={{ gridTemplateColumns: `220px repeat(${grid.groups.length}, 84px)` }}
                                            >
                                                <div className={`${styles.cell} ${styles.firstCol}`}>{t.name}</div>
                                                {grid.groups.map(g => (
                                                    <div
                                                        key={`${t.id}-${g.id}-${subject.id}`}
                                                        className={`${styles.cell} ${styles.groupCol}`}
                                                    >
                                                        <input
                                                            type="number"
                                                            min="0"
                                                            className={styles.hoursInput}
                                                            defaultValue={getExistingHours(t.id, g.id, subject.id) || ""}
                                                            onChange={(e) =>
                                                                handleCellChange(
                                                                    grid.req_set.id,
                                                                    t.id,
                                                                    g.id,
                                                                    subject.id,
                                                                    e.target.value
                                                                )
                                                            }
                                                        />
                                                    </div>
                                                ))}
                                            </div>
                                        ))}
                                </React.Fragment>
                            ))}
                        </div>
                    </div>
                )}
                <div className={styles.actionRow}>
                    <button
                        className={styles.button}
                        onClick={handleSave}
                        disabled={loading || !selectedReqSet || updatedRequirements.length === 0}
                    >
                        {loading ? "Saving..." : "Save Changes"}
                    </button>
                </div>
            </div>

            {message && <p className={styles.message}>{message}</p>}
        </div>
    );
}