import React, { useState, useEffect } from "react";
import "../styles/PlanLessons.css";

export default function PlanLessons() {
    const [plans, setPlans] = useState([]);
    const [selectedPlan, setSelectedPlan] = useState("");
    const [lessons, setLessons] = useState([]);
    const [filteredLessons, setFilteredLessons] = useState({});
    const [studentGroups, setStudentGroups] = useState([]);
    const [selectedGroup, setSelectedGroup] = useState("");
    const [loading, setLoading] = useState(false);

    // Fetch all plans
    useEffect(() => {
        const fetchPlans = async () => {
            try {
                const res = await fetch("/api/plans/");
                const data = await res.json();
                if (res.ok) {
                    setPlans(data);
                } else {
                    console.error("Failed to fetch plans:", data.error);
                }
            } catch (error) {
                console.error("Error fetching plans:", error);
            }
        };

        fetchPlans();
    }, []);

    // Fetch lessons for the selected plan
    const fetchLessons = async (planId) => {
        setLoading(true);
        try {
            const res = await fetch(`/api/plans/${planId}/lessons/`);
            const data = await res.json();
            if (res.ok) {
                setLessons(data);
                extractStudentGroups(data); // Extract student groups from lessons
            } else {
                console.error("Failed to fetch lessons:", data.error);
            }
        } catch (error) {
            console.error("Error fetching lessons:", error);
        } finally {
            setLoading(false);
        }
    };

    // Extract unique student groups from lessons
    const extractStudentGroups = (lessons) => {
        const groups = [...new Set(lessons.map((lesson) => lesson.group.name))];
        setStudentGroups(groups);
        if (groups.length > 0) {
            setSelectedGroup(groups[0]); // Default to the first group
            groupLessonsByStudentGroup(lessons, groups[0]);
        }
    };

    // Handle plan selection
    const handlePlanChange = (e) => {
        const planId = e.target.value;
        setSelectedPlan(planId);
        if (planId) {
            fetchLessons(planId);
        } else {
            setLessons([]);
            setFilteredLessons({});
        }
    };

    // Handle student group selection
    const handleGroupChange = (e) => {
        const groupName = e.target.value;
        setSelectedGroup(groupName);
        groupLessonsByStudentGroup(lessons, groupName);
    };

    // Group lessons by student group and organize them into a grid
    const groupLessonsByStudentGroup = (lessons, groupName) => {
        const groupLessons = lessons.filter((lesson) => lesson.group.name === groupName);
        const grid = {};

        const dayMap = {
            0: "Monday",
            1: "Tuesday",
            2: "Wednesday",
            3: "Thursday",
            4: "Friday",
        };

        groupLessons.forEach((lesson) => {
            const dayName = dayMap[lesson.day];
            if (!grid[dayName]) {
                grid[dayName] = {};
            }
            if (!grid[dayName][lesson.hour]) {
                grid[dayName][lesson.hour] = [];
            }
            grid[dayName][lesson.hour].push(lesson); // Store multiple lessons in an array
        });

        // Ensure React detects the state change
        setFilteredLessons({ ...grid });
    };

    return (
        <div className="plan-lessons-container">
            <h1>Plan Lessons</h1>

            {/* Plan Selection */}
            <div className="form-group">
                <label htmlFor="plan-select">Select Plan:</label>
                <select id="plan-select" value={selectedPlan} onChange={handlePlanChange}>
                    <option value="">-- Select a Plan --</option>
                    {plans.map((plan) => (
                        <option key={plan.id} value={plan.id}>
                            {plan.name}
                        </option>
                    ))}
                </select>
            </div>

            {/* Student Group Selection */}
            {studentGroups.length > 0 && (
                <div className="form-group">
                    <label htmlFor="group-select">Select Student Group:</label>
                    <select id="group-select" value={selectedGroup} onChange={handleGroupChange}>
                        {studentGroups.map((group) => (
                            <option key={group} value={group}>
                                {group}
                            </option>
                        ))}
                    </select>
                </div>
            )}

            {/* Lessons Grid */}
            {loading ? (
                <p>Loading lessons...</p>
            ) : (
                <div className="lessons-grid">
                    <table>
                        <thead>
                            <tr>
                                <th>Time Slot</th>
                                <th>Monday</th>
                                <th>Tuesday</th>
                                <th>Wednesday</th>
                                <th>Thursday</th>
                                <th>Friday</th>
                            </tr>
                        </thead>
                        <tbody>
                            {Array.from({ length: 12 }, (_, hour) => (
                                <tr key={hour}>
                                    <td>{hour + 1}</td>
                                    {["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"].map((day) => (
                                        <td key={day}>
                                            {filteredLessons[day]?.[hour + 1] ? (
                                                <div className="lesson-cell">
                                                    {filteredLessons[day][hour + 1].map((lesson, index) => (
                                                        <div key={index} className="lesson-item">
                                                            <strong>{lesson.subject.name}</strong>
                                                            <br />
                                                            {lesson.teacher.name}
                                                            <br />
                                                            {lesson.room.name}
                                                        </div>
                                                    ))}
                                                </div>
                                            ) : (
                                                "-"
                                            )}
                                        </td>
                                    ))}
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
            )}
        </div>
    );
}