import React, { useState, useEffect } from "react";

export default function TeacherAvailability() {
    const [teacherPools, setTeacherPools] = useState([]);
    const [requirementSets, setRequirementSets] = useState([]);
    const [selectedTeacherPool, setSelectedTeacherPool] = useState("");
    const [selectedRequirementSet, setSelectedRequirementSet] = useState("");
    const [teachers, setTeachers] = useState([]);
    const [availability, setAvailability] = useState({});
    const [message, setMessage] = useState("");

    // Fetch Teacher Pools and Requirement Sets
    useEffect(() => {
        const fetchData = async () => {
            try {
                const [teacherPoolsRes, requirementSetsRes] = await Promise.all([
                    fetch("/api/teacher-pools/"),
                    fetch("/api/requirement-sets/"),
                ]);

                const teacherPoolsData = await teacherPoolsRes.json();
                const requirementSetsData = await requirementSetsRes.json();

                setTeacherPools(teacherPoolsData);
                setRequirementSets(requirementSetsData);
            } catch (error) {
                console.error("Error fetching data:", error);
            }
        };

        fetchData();
    }, []);

    // Fetch Teachers when a Teacher Pool is selected
    useEffect(() => {
        if (!selectedTeacherPool) return;

        const fetchTeachers = async () => {
            try {
                const res = await fetch(`/api/teachers/?pool=${selectedTeacherPool}`);
                const data = await res.json();
                setTeachers(data);

                // Set default availability to true for all days
                const initialAvailability = data.reduce((acc, teacher) => {
                    acc[teacher.id] = { 0: true, 1: true, 2: true, 3: true, 4: true };
                    return acc;
                }, {});
                setAvailability(initialAvailability);
            } catch (error) {
                console.error("Error fetching teachers:", error);
            }
        };

        fetchTeachers();
    }, [selectedTeacherPool]);

    const handleCheckboxChange = (teacherId, day) => {
        setAvailability((prev) => ({
            ...prev,
            [teacherId]: {
                ...prev[teacherId],
                [day]: !prev[teacherId][day],
            },
        }));
    };

    const handleSave = async () => {
        if (!selectedRequirementSet) {
            alert("Please select a Requirement Set!");
            return;
        }

        try {
            const csrftoken = document.cookie
                .split("; ")
                .find((row) => row.startsWith("csrftoken="))
                ?.split("=")[1];
                
            const res = await fetch("/api/teacher-availability/", {
                method: "POST",
                headers: { "Content-Type": "application/json", "X-CSRFToken": csrftoken },
                body: JSON.stringify({
                    req_set_id: selectedRequirementSet,
                    availability: availability,
                }),
            });

            const data = await res.json();
            if (res.ok) {
                setMessage("✅ Availability saved successfully!");
            } else {
                setMessage(`❌ Error: ${data.error || "Unknown error"}`);
            }
        } catch (error) {
            console.error("Error saving availability:", error);
            setMessage("❌ Network error");
        }
    };

    return (
        <div className="flex flex-col items-center gap-6 p-6">
            <h1 className="text-2xl font-bold">Teacher Availability</h1>

            {/* Teacher Pool Selection */}
            <div className="w-full max-w-xl">
                <label className="block text-gray-700 font-medium mb-2">
                    Select a Teacher Pool:
                </label>
                <select
                    value={selectedTeacherPool}
                    onChange={(e) => setSelectedTeacherPool(e.target.value)}
                    className="w-full border border-gray-300 rounded-lg p-2"
                >
                    <option value="">-- Select a Pool --</option>
                    {teacherPools.map((pool) => (
                        <option key={pool.id} value={pool.id}>
                            {pool.name}
                        </option>
                    ))}
                </select>
            </div>

            {/* Requirement Set Selection */}
            <div className="w-full max-w-xl">
                <label className="block text-gray-700 font-medium mb-2">
                    Select a Requirement Set:
                </label>
                <select
                    value={selectedRequirementSet}
                    onChange={(e) => setSelectedRequirementSet(e.target.value)}
                    className="w-full border border-gray-300 rounded-lg p-2"
                >
                    <option value="">-- Select a Requirement Set --</option>
                    {requirementSets.map((reqSet) => (
                        <option key={reqSet.id} value={reqSet.id}>
                            {reqSet.name}
                        </option>
                    ))}
                </select>
            </div>

            {/* Teacher Availability Table */}
            {teachers.length > 0 && (
                <div className="w-full max-w-4xl border border-gray-300 rounded-lg shadow-sm overflow-hidden">
                    <table className="w-full table-auto">
                        <thead>
                            <tr className="bg-gray-100">
                                <th className="px-4 py-2">Teacher</th>
                                {[...Array(5).keys()].map((day) => (
                                    <th key={day} className="px-4 py-2">
                                        Day {day + 1}
                                    </th>
                                ))}
                            </tr>
                        </thead>
                        <tbody>
                            {teachers.map((teacher) => (
                                <tr key={teacher.id}>
                                    <td className="border px-4 py-2">{teacher.name}</td>
                                    {[...Array(5).keys()].map((day) => (
                                        <td key={day} className="border px-4 py-2 text-center">
                                            <input
                                                type="checkbox"
                                                checked={availability[teacher.id]?.[day] || false}
                                                onChange={() => handleCheckboxChange(teacher.id, day)}
                                            />
                                        </td>
                                    ))}
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
            )}

            {/* Save Button */}
            <button
                onClick={handleSave}
                className="px-6 py-2 bg-blue-600 text-white rounded-lg font-semibold hover:bg-blue-700"
            >
                Save Availability
            </button>

            {message && <p className="text-center text-gray-700">{message}</p>}
        </div>
    );
}