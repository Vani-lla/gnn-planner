import React, { useState, useEffect } from "react";
import "../../styles/Requirements.css";

export default function Requirements() {
    const [gridData, setGridData] = useState(null); // Use `null` to differentiate between loading and empty data
    const [updatedRequirements, setUpdatedRequirements] = useState([]);

    useEffect(() => {
        const fetchGridData = async () => {
            try {
                const res = await fetch(`/api/requirements/grid/`);
                const data = await res.json();
                setGridData(data); // Set the data, even if it's an empty list
            } catch (error) {
                console.error("Error fetching grid data:", error);
                setGridData([]); // Set an empty array to stop loading in case of an error
            }
        };

        fetchGridData();
    }, []);

    const handleCellChange = (reqSetId, teacherId, groupId, subjectId, value) => {
        const hours = parseInt(value, 10) || 0;
        const existing = updatedRequirements.find(
            (req) =>
                req.req_set === reqSetId &&
                req.teacher === teacherId &&
                req.group === groupId &&
                req.subject === subjectId
        );

        if (existing) {
            existing.hours = hours;
        } else {
            setUpdatedRequirements((prev) => [
                ...prev,
                { req_set: reqSetId, teacher: teacherId, group: groupId, subject: subjectId, hours },
            ]);
        }
    };

    const handleSave = async () => {
        const csrftoken = document.cookie
            .split("; ")
            .find((row) => row.startsWith("csrftoken="))
            ?.split("=")[1];

        try {
            const res = await fetch("/api/requirements/", {
                method: "POST",
                headers: { "Content-Type": "application/json", "X-CSRFToken": csrftoken },
                body: JSON.stringify(updatedRequirements),
            });

            if (res.ok) {
                alert("Requirements updated successfully!");
                setUpdatedRequirements([]);
            } else {
                alert("Failed to update requirements.");
            }
        } catch (error) {
            console.error("Error saving requirements:", error);
        }
    };

    // Render a loading message only while `gridData` is null
    if (gridData === null) return <div>Loading...</div>;

    return (
        <div className="requirements-container">
            <div className="requirements-header">
                <h1>Requirements Grid</h1>
                <button onClick={handleSave}>Save Changes</button>
            </div>
            {gridData.length === 0 ? (
                <div>No data available.</div>
            ) : (
                gridData.map((reqSet) => (
                    <div key={reqSet.req_set.id} className="requirements-grid-container">
                        <h2>{reqSet.req_set.name}</h2>
                        <table className="requirements-grid">
                            <thead>
                                <tr>
                                    <th>Subject / Teacher</th>
                                    {reqSet.groups.map((group) => (
                                        <th key={group.id}>{group.name}</th>
                                    ))}
                                </tr>
                            </thead>
                            <tbody>
                                {reqSet.subjects.map((subject) => (
                                    <React.Fragment key={subject.id}>
                                        {/* Master row for the subject */}
                                        <tr className="subject-row">
                                            <td colSpan={reqSet.groups.length + 1}>
                                                <strong>{subject.name}</strong>
                                            </td>
                                        </tr>
                                        {/* Rows for teachers under this subject */}
                                        {reqSet.teachers
                                            .filter((teacher) =>
                                                (teacher.subjects || []).some((taughtSubject) => taughtSubject.id === subject.id)
                                            )
                                            .map((teacher) => (
                                                <tr key={`${teacher.id}-${subject.id}`}>
                                                    <td>{teacher.name}</td>
                                                    {reqSet.groups.map((group) => {
                                                        const existingRequirement =
                                                            reqSet.requirements.find(
                                                                (req) =>
                                                                    req.teacher === teacher.id &&
                                                                    req.group === group.id &&
                                                                    req.subject === subject.id
                                                            );

                                                        return (
                                                            <td
                                                                key={`${teacher.id}-${group.id}-${subject.id}`}
                                                            >
                                                                <input
                                                                    type="number"
                                                                    defaultValue={
                                                                        existingRequirement
                                                                            ? existingRequirement.hours
                                                                            : ""
                                                                    }
                                                                    onChange={(e) =>
                                                                        handleCellChange(
                                                                            reqSet.req_set.id,
                                                                            teacher.id,
                                                                            group.id,
                                                                            subject.id,
                                                                            e.target.value
                                                                        )
                                                                    }
                                                                />
                                                            </td>
                                                        );
                                                    })}
                                                </tr>
                                            ))}
                                    </React.Fragment>
                                ))}
                            </tbody>
                        </table>
                    </div>
                ))
            )}
        </div>
    );
}