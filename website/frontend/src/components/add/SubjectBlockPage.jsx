import React, { useState, useEffect } from "react";
import "../../styles/SubjectBlockPage.css";

export default function SubjectBlockPage() {
    const [reqSets, setReqSets] = useState([]);
    const [groupPools, setGroupPools] = useState([]);
    const [subjectPools, setSubjectPools] = useState([]);
    const [selectedReqSet, setSelectedReqSet] = useState("");
    const [selectedGroupPool, setSelectedGroupPool] = useState("");
    const [selectedSubjectPool, setSelectedSubjectPool] = useState("");
    const [subjects, setSubjects] = useState([]);
    const [studentGroups, setStudentGroups] = useState([]);
    const [subjectBlocks, setSubjectBlocks] = useState([]);
    const [message, setMessage] = useState("");

    // Fetch initial data
    useEffect(() => {
        const fetchData = async () => {
            try {
                const [reqSetsRes, groupPoolsRes, subjectPoolsRes] = await Promise.all([
                    fetch("/api/requirement-sets/"),
                    fetch("/api/student-group-pools/"),
                    fetch("/api/subject-pools/"),
                ]);

                setReqSets(await reqSetsRes.json());
                setGroupPools(await groupPoolsRes.json());
                setSubjectPools(await subjectPoolsRes.json());
            } catch (error) {
                console.error("Error fetching data:", error);
            }
        };

        fetchData();
    }, []);

    // Fetch subjects and student groups when pools are selected
    useEffect(() => {
        if (!selectedGroupPool || !selectedSubjectPool) return;

        const fetchDetails = async () => {
            try {
                const [subjectsRes, groupsRes] = await Promise.all([
                    fetch(`/api/subjects/?pool=${selectedSubjectPool}`),
                    fetch(`/api/student-groups/?pool=${selectedGroupPool}`),
                ]);

                setSubjects(await subjectsRes.json());
                setStudentGroups(await groupsRes.json());
            } catch (error) {
                console.error("Error fetching details:", error);
            }
        };

        fetchDetails();
    }, [selectedGroupPool, selectedSubjectPool]);

    // Fetch existing SubjectBlocks
    useEffect(() => {
        if (!selectedReqSet) return;

        const fetchSubjectBlocks = async () => {
            try {
                const res = await fetch(`/api/subject-blocks/?req_set=${selectedReqSet}`);
                setSubjectBlocks(await res.json());
            } catch (error) {
                console.error("Error fetching subject blocks:", error);
            }
        };

        fetchSubjectBlocks();
    }, [selectedReqSet]);

    const handleAddBlock = () => {
        setSubjectBlocks((prev) => [
            ...prev,
            { id: null, req_set: selectedReqSet, subjects: [], groups: [], numbers: {} },
        ]);
    };

    const handleDeleteBlock = async (blockId, index) => {
        if (blockId) {
            // If the block has an ID, send a DELETE request to the backend
            try {
                const csrftoken = document.cookie
                    .split("; ")
                    .find((row) => row.startsWith("csrftoken="))
                    ?.split("=")[1];

                const res = await fetch(`/api/subject-blocks/${blockId}/`, {
                    method: "DELETE",
                    headers: { "X-CSRFToken": csrftoken },
                });

                if (res.ok) {
                    setMessage("✅ SubjectBlock deleted successfully!");
                } else {
                    setMessage("❌ Failed to delete SubjectBlock.");
                    return;
                }
            } catch (error) {
                console.error("Error deleting SubjectBlock:", error);
                setMessage("❌ Network error while deleting.");
                return;
            }
        }

        // Remove the block locally
        setSubjectBlocks((prev) => prev.filter((_, i) => i !== index));
    };

    const handleSave = async () => {
        try {
            const csrftoken = document.cookie
                .split("; ")
                .find((row) => row.startsWith("csrftoken="))
                ?.split("=")[1];

            // Ensure subject IDs in numbers are integers
            const sanitizedBlocks = subjectBlocks.map((block) => ({
                ...block,
                req_set: parseInt(block.req_set, 10),
                numbers: Object.fromEntries(
                    Object.entries(block.numbers).map(([key, value]) => [parseInt(key, 10), value])
                ),
            }));

            const res = await fetch("/api/subject-blocks/", {
                method: "POST",
                headers: { "Content-Type": "application/json", "X-CSRFToken": csrftoken },
                body: JSON.stringify(sanitizedBlocks),
            });

            const data = await res.json();
            if (res.ok) {
                setMessage("✅ SubjectBlocks saved successfully!");
            } else {
                setMessage(`❌ Error: ${data.error || "Unknown error"}`);
            }
        } catch (error) {
            console.error("Error saving subject blocks:", error);
            setMessage("❌ Network error");
        }
    };

    return (
        <div className="container">
            <h1>Manage Subject Blocks</h1>

            {/* Dropdowns for selection */}
            <div className="select-container">
                <select
                    value={selectedReqSet}
                    onChange={(e) => setSelectedReqSet(e.target.value)}
                >
                    <option value="">-- Select Requirement Set --</option>
                    {reqSets.map((reqSet) => (
                        <option key={reqSet.id} value={reqSet.id}>
                            {reqSet.name}
                        </option>
                    ))}
                </select>

                <select
                    value={selectedGroupPool}
                    onChange={(e) => setSelectedGroupPool(e.target.value)}
                >
                    <option value="">-- Select Group Pool --</option>
                    {groupPools.map((pool) => (
                        <option key={pool.id} value={pool.id}>
                            {pool.name}
                        </option>
                    ))}
                </select>

                <select
                    value={selectedSubjectPool}
                    onChange={(e) => setSelectedSubjectPool(e.target.value)}
                >
                    <option value="">-- Select Subject Pool --</option>
                    {subjectPools.map((pool) => (
                        <option key={pool.id} value={pool.id}>
                            {pool.name}
                        </option>
                    ))}
                </select>
            </div>

            {/* SubjectBlocks */}
            {subjectBlocks.map((block, index) => (
                <div key={index} className="subject-block">
                    <h2>SubjectBlock {index + 1}</h2>
                    <div className="grid">
                        {subjects.map((subject) => (
                            <div key={subject.id} className="grid-item">
                                <span>{subject.name}</span>
                                <input
                                    type="number"
                                    min="0"
                                    value={block.numbers[subject.id] || ""}
                                    onChange={(e) => {
                                        const value = parseInt(e.target.value, 10) || 0;
                                        setSubjectBlocks((prev) => {
                                            const updated = [...prev];
                                            updated[index].numbers[subject.id] = value;
                                            return updated;
                                        });
                                    }}
                                />
                            </div>
                        ))}
                    </div>
                    <div className="group-selection">
                        <label>Applicable Groups:</label>
                        <select
                            multiple
                            value={block.groups}
                            onChange={(e) => {
                                const selected = Array.from(e.target.selectedOptions).map(
                                    (option) => parseInt(option.value, 10)
                                );
                                setSubjectBlocks((prev) => {
                                    const updated = [...prev];
                                    updated[index].groups = selected;
                                    return updated;
                                });
                            }}
                        >
                            {studentGroups.map((group) => (
                                <option key={group.id} value={group.id}>
                                    {group.name}
                                </option>
                            ))}
                        </select>
                    </div>
                    <button
                        className="delete-button"
                        onClick={() => handleDeleteBlock(block.id, index)}
                    >
                        Delete
                    </button>
                </div>
            ))}

            <button className="add-button" onClick={handleAddBlock}>
                Add SubjectBlock
            </button>
            <button className="save-button" onClick={handleSave}>
                Save All
            </button>

            {message && <p className="message">{message}</p>}
        </div>
    );
}