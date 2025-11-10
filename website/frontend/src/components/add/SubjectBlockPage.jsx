import React, { useState, useEffect, useMemo } from "react";
import styles from "../../styles/SubjectBlocks.module.css";

export default function SubjectBlockPage() {
    const [reqSets, setReqSets] = useState([]);
    const [selectedReqSet, setSelectedReqSet] = useState("");
    const [subjectPoolName, setSubjectPoolName] = useState("-");
    const [groupPoolName, setGroupPoolName] = useState("-");
    const [subjects, setSubjects] = useState([]);
    const [studentGroups, setStudentGroups] = useState([]);
    const [subjectBlocks, setSubjectBlocks] = useState([]);
    const [message, setMessage] = useState("");

    const csrftoken = useMemo(
        () => document.cookie.split("; ").find(r => r.startsWith("csrftoken="))?.split("=")[1],
        []
    );

    useEffect(() => {
        (async () => {
            try {
                const res = await fetch("/api/requirement-sets/");
                if (res.ok) setReqSets(await res.json());
            } catch {}
        })();
    }, []);

    useEffect(() => {
        const loadForReqSet = async () => {
            if (!selectedReqSet) {
                setSubjectBlocks([]);
                setSubjects([]);
                setStudentGroups([]);
                setSubjectPoolName("-");
                setGroupPoolName("-");
                return;
            }
            try {
                const rsRes = await fetch(`/api/requirement-sets/${selectedReqSet}/`);
                if (rsRes.ok) {
                    const rs = await rsRes.json();
                    if (rs.subject_pool) {
                        // fetch subject pool name
                        const spRes = await fetch(`/api/subject-pools/${rs.subject_pool}/`);
                        if (spRes.ok) setSubjectPoolName((await spRes.json()).name);
                        const subjRes = await fetch(`/api/subjects/?pool_id=${rs.subject_pool}`);
                        if (subjRes.ok) setSubjects(await subjRes.json());
                    }
                    if (rs.group_pool) {
                        const gpRes = await fetch(`/api/student-group-pools/${rs.group_pool}/`);
                        if (gpRes.ok) setGroupPoolName((await gpRes.json()).name);
                        const grpRes = await fetch(`/api/student-groups/?pool_id=${rs.group_pool}`);
                        if (grpRes.ok) setStudentGroups(await grpRes.json());
                    }
                }
            } catch {}
            try {
                const blocksRes = await fetch(`/api/subject-blocks/?req_set=${selectedReqSet}`);
                if (blocksRes.ok) setSubjectBlocks(await blocksRes.json());
            } catch {}
        };
        loadForReqSet();
    }, [selectedReqSet]);

    const handleAddBlock = () => {
        if (!selectedReqSet) {
            setMessage("❌ Select a Requirement Set first");
            return;
        }
        setSubjectBlocks(prev => [
            ...prev,
            {
                id: null,
                req_set: Number(selectedReqSet),
                numbers: {},
                groups: [],
                power_block: false,
                max_number: 0
            }
        ]);
    };

    const handleDeleteBlock = async (blockId, index) => {
        if (blockId) {
            try {
                const res = await fetch(`/api/subject-blocks/${blockId}/`, {
                    method: "DELETE",
                    headers: { "X-CSRFToken": csrftoken }
                });
                if (!res.ok) {
                    setMessage("❌ Delete failed");
                    return;
                }
            } catch {
                setMessage("❌ Network error");
                return;
            }
        }
        setSubjectBlocks(prev => prev.filter((_, i) => i !== index));
    };

    const toggleGroup = (blockIndex, groupId) => {
        setSubjectBlocks(prev => {
            const next = [...prev];
            const b = next[blockIndex];
            const set = new Set(b.groups.map(g => String(g)));
            if (set.has(String(groupId))) set.delete(String(groupId));
            else set.add(String(groupId));
            b.groups = Array.from(set);
            next[blockIndex] = { ...b };
            return next;
        });
    };

    const updateNumber = (blockIndex, subjectId, val) => {
        setSubjectBlocks(prev => {
            const next = [...prev];
            const b = next[blockIndex];
            const numbers = { ...(b.numbers || {}) };
            if (val === "" || Number(val) === 0) {
                delete numbers[subjectId];
            } else {
                numbers[subjectId] = Number(val);
            }
            b.numbers = numbers;
            next[blockIndex] = { ...b };
            return next;
        });
    };

    const togglePower = (blockIndex) => {
        setSubjectBlocks(prev => {
            const next = [...prev];
            next[blockIndex].power_block = !next[blockIndex].power_block;
            return next;
        });
    };

    const updateMaxNumber = (blockIndex, val) => {
        setSubjectBlocks(prev => {
            const next = [...prev];
            next[blockIndex].max_number = Math.max(0, Number(val) || 0);
            return next;
        });
    };

    const handleSave = async () => {
        if (!selectedReqSet) {
            setMessage("❌ Select a Requirement Set first");
            return;
        }
        try {
            const payload = subjectBlocks.map(b => ({
                id: b.id,
                req_set: b.req_set,
                numbers: b.numbers,
                groups: b.groups.map(g => Number(g)),
                power_block: b.power_block,
                max_number: b.max_number
            }));
            const res = await fetch("/api/subject-blocks/", {
                method: "POST",
                headers: { "Content-Type": "application/json", "X-CSRFToken": csrftoken },
                body: JSON.stringify(payload)
            });
            const data = await res.json();
            if (res.ok) {
                setMessage("✅ Saved");
                const reload = await fetch(`/api/subject-blocks/?req_set=${selectedReqSet}`);
                if (reload.ok) setSubjectBlocks(await reload.json());
            } else {
                setMessage(`❌ ${data.error || "Save failed"}`);
            }
        } catch {
            setMessage("❌ Network error");
        }
    };

    // Split subjects into two columns
    const splitSubjects = () => {
        const mid = Math.ceil(subjects.length / 2);
        return [subjects.slice(0, mid), subjects.slice(mid)];
    };

    return (
        <div className={styles.blocksView}>
            <div className={styles.blocksSelectors}>
                <select
                    className={styles.blocksSelect}
                    value={selectedReqSet}
                    onChange={e => setSelectedReqSet(e.target.value)}
                >
                    <option value="">-- Requirement Set --</option>
                    {reqSets.map(r => <option key={r.id} value={r.id}>{r.name}</option>)}
                </select>
                <div className={styles.infoBadge}>Subject Pool: <b>{subjectPoolName}</b></div>
                <div className={styles.infoBadge}>Group Pool: <b>{groupPoolName}</b></div>
            </div>

            <div className={styles.blocksContainer}>
                {(!selectedReqSet) && (
                    <div className={styles.placeholder}>Select a Requirement Set to begin.</div>
                )}
                {selectedReqSet && subjectBlocks.length === 0 && (
                    <div className={styles.placeholder}>No blocks. Add one.</div>
                )}
                {subjectBlocks.map((block, idx) => {
                    const [colA, colB] = splitSubjects();
                    return (
                        <div key={block.id ?? `new-${idx}`} className={styles.blockCard}>
                            <div className={styles.blockHeader}>
                                <div className={styles.blockTitle}>Block {idx + 1}</div>
                                <div className={styles.blockControls}>
                                    <label className={styles.inline}>
                                        <input
                                            type="checkbox"
                                            checked={block.power_block}
                                            onChange={() => togglePower(idx)}
                                        /> Power
                                    </label>
                                    <label className={styles.inline}>
                                        Max:
                                        <input
                                            type="number"
                                            min="0"
                                            className={styles.smallInput}
                                            value={block.max_number}
                                            onChange={e => updateMaxNumber(idx, e.target.value)}
                                        />
                                    </label>
                                </div>
                                <button
                                    type="button"
                                    className={styles.deleteButton}
                                    onClick={() => handleDeleteBlock(block.id, idx)}
                                    title="Delete block"
                                >
                                    ✖
                                </button>
                            </div>

                            <div className={styles.blockGrid}>
                                {/* Column 1 */}
                                <div className={styles.subjectColumn}>
                                    <div className={styles.subjectColumnHeader}>Subjects</div>
                                    {colA.map(s => (
                                        <div key={s.id} className={styles.subjectRow}>
                                            <span className={styles.subjectName}>{s.name}</span>
                                            <input
                                                type="number"
                                                min="0"
                                                className={styles.numInput}
                                                value={block.numbers?.[s.id] ?? ""}
                                                onChange={e => updateNumber(idx, s.id, e.target.value)}
                                            />
                                        </div>
                                    ))}
                                </div>
                                {/* Column 2 */}
                                <div className={styles.subjectColumn}>
                                    <div className={styles.subjectColumnHeader}>Subjects</div>
                                    {colB.map(s => (
                                        <div key={s.id} className={styles.subjectRow}>
                                            <span className={styles.subjectName}>{s.name}</span>
                                            <input
                                                type="number"
                                                min="0"
                                                className={styles.numInput}
                                                value={block.numbers?.[s.id] ?? ""}
                                                onChange={e => updateNumber(idx, s.id, e.target.value)}
                                            />
                                        </div>
                                    ))}
                                </div>
                                {/* Column 3 Groups */}
                                <div className={styles.groupsColumn}>
                                    <div className={styles.groupsHeader}>Applicable Groups</div>
                                    <div className={styles.groupsList}>
                                        {studentGroups.map(g => {
                                            const checked = block.groups.map(String).includes(String(g.id));
                                            return (
                                                <label key={g.id} className={styles.groupItem}>
                                                    <input
                                                        type="checkbox"
                                                        checked={checked}
                                                        onChange={() => toggleGroup(idx, g.id)}
                                                    />
                                                    <span>{g.name}</span>
                                                </label>
                                            );
                                        })}
                                    </div>
                                </div>
                            </div>
                        </div>
                    );
                })}
            </div>

            <div className={styles.actionRow}>
                <button className={styles.button} onClick={handleAddBlock} disabled={!selectedReqSet}>+ Add Block</button>
                <button
                    className={styles.button}
                    onClick={handleSave}
                    disabled={!selectedReqSet || subjectBlocks.length === 0}
                >
                    Save All
                </button>
            </div>

            {message && <p className={styles.message}>{message}</p>}
        </div>
    );
}