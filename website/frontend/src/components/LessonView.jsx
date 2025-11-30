import React, { useState, useEffect } from "react";
import styles from "../styles/LessonView.module.css";

export default function LessonView() {
    const [plans, setPlans] = useState([]);
    const [selectedPlan, setSelectedPlan] = useState("");
    const [studentGroups, setStudentGroups] = useState([]);
    const [teachers, setTeachers] = useState([]);
    const [lessons, setLessons] = useState([]);
    const [filteredLessons, setFilteredLessons] = useState([]);
    const [selectedGroup, setSelectedGroup] = useState("");
    const [selectedTeacher, setSelectedTeacher] = useState("");
    const [showTeacher, setshowTeacher] = useState(true);

    // Mapping of day names to integers
    const dayMapping = {
        "Monday": 0,
        "Tuesday": 1,
        "Wednesday": 2,
        "Thursday": 3,
        "Friday": 4,
    };

    // Fetch plans
    useEffect(() => {
        const fetchPlans = async () => {
            try {
                const plansRes = await fetch("/api/plans/");
                const plansData = await plansRes.json();
                console.log("Fetched Plans:", plansData); // Log response
                setPlans(plansData);
            } catch (error) {
                console.error("Error fetching plans:", error);
            }
        };

        fetchPlans();
    }, []);

    // Fetch plan details and lessons when a plan is selected
    useEffect(() => {
        const fetchPlanDetailsAndLessons = async () => {
            if (!selectedPlan) return;

            try {
                // Fetch plan details (teachers and student groups)
                const planDetailsRes = await fetch(`/api/plans/${selectedPlan}/details/`);
                const planDetailsData = await planDetailsRes.json();
                console.log("Fetched Plan Details:", planDetailsData); // Log response
                setTeachers(planDetailsData.teachers);
                setStudentGroups(planDetailsData.student_groups);

                // Fetch lessons for the selected plan
                const lessonsRes = await fetch(`/api/plans/${selectedPlan}/lessons/`);
                const lessonsData = await lessonsRes.json();
                console.log("Fetched Lessons:", lessonsData); // Log response
                setLessons(lessonsData);
                setFilteredLessons([]); // Clear filtered lessons initially
            } catch (error) {
                console.error("Error fetching plan details or lessons:", error);
            }
        };

        fetchPlanDetailsAndLessons();
    }, [selectedPlan]);

    // Filter lessons based on selected student group or teacher
    useEffect(() => {
        if (!selectedGroup && !selectedTeacher) {
            setFilteredLessons([]); // Clear filtered lessons if no group or teacher is selected
            return;
        }

        let filtered = lessons;

        if (selectedGroup) {
            filtered = filtered.filter(
                (lesson) => lesson.group.id === parseInt(selectedGroup)
            );
            console.log(`Filtered Lessons by Group (${selectedGroup}):`, filtered); // Log filtering
        }

        if (selectedTeacher) {
            filtered = filtered.filter(
                (lesson) => lesson.teacher.id === parseInt(selectedTeacher)
            );
            console.log(`Filtered Lessons by Teacher (${selectedTeacher}):`, filtered); // Log filtering
        }

        setFilteredLessons(filtered);
    }, [selectedGroup, selectedTeacher, lessons]);

    // Handle group selection
    const handleGroupSelect = (groupId) => {
        console.log(`Selected Group: ${groupId}`); // Log group selection
        setSelectedGroup(groupId);
        setSelectedTeacher(""); // Deselect teacher
        setshowTeacher(true);
    };

    // Handle teacher selection
    const handleTeacherSelect = (teacherId) => {
        console.log(`Selected Teacher: ${teacherId}`); // Log teacher selection
        setSelectedTeacher(teacherId);
        setSelectedGroup(""); // Deselect group
        setshowTeacher(false);
    };

    return (
        <div className={styles.lessonView}>
            {/* === Selectors === */}
            <div className={styles.lessonSelectors}>
                <select
                    className={styles.lessonSelect}
                    value={selectedPlan}
                    onChange={(e) => setSelectedPlan(e.target.value)}
                >
                    <option value="">Select Plan</option>
                    {plans.map((plan) => (
                        <option key={plan.id} value={plan.id}>
                            {plan.name}
                        </option>
                    ))}
                </select>

                <select
                    className={styles.lessonSelect}
                    value={selectedGroup}
                    onChange={(e) => handleGroupSelect(e.target.value)}
                >
                    <option value="">Select Group</option>
                    {studentGroups.map((group) => (
                        <option key={group.id} value={group.id}>
                            {group.name}
                        </option>
                    ))}
                </select>

                <select
                    className={styles.lessonSelect}
                    value={selectedTeacher}
                    onChange={(e) => handleTeacherSelect(e.target.value)}
                >
                    <option value="">Select Teacher</option>
                    {teachers.map((teacher) => (
                        <option key={teacher.id} value={teacher.id}>
                            {teacher.name}
                        </option>
                    ))}
                </select>
            </div>

            {/* === Lesson Grid === */}
            <div className={styles.lessonGrid}>
                {/* Grid Header */}
                <div className={styles.lessonGridHeader}>
                    <div className={styles.lessonGridCell}>Time Slot</div>
                    <div className={styles.lessonGridCell}>Monday</div>
                    <div className={styles.lessonGridCell}>Tuesday</div>
                    <div className={styles.lessonGridCell}>Wednesday</div>
                    <div className={styles.lessonGridCell}>Thursday</div>
                    <div className={styles.lessonGridCell}>Friday</div>
                </div>

                {/* Grid Body */}
                <div className={styles.lessonGridBody}>
                    {Array.from({ length: 13 }, (_, hour) => {
                        const lessonsInRow = filteredLessons.filter(
                            (lesson) => lesson.hour === hour
                        );

                        if (lessonsInRow.length === 0) return null;

                        return (
                            <div className={styles.lessonGridRow} key={hour}>
                                {/* Time Slot Column */}
                                <div className={styles.lessonGridCell}>{hour+1}</div>

                                {/* Days Columns */}
                                {["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"].map((day) => (
                                    <div className={styles.lessonGridCell} key={day}>
                                        {lessonsInRow
                                            .filter((lesson) => lesson.day === dayMapping[day])
                                            .map((lesson, index) => (
                                                <div key={index} className={styles.lessonCard}>
                                                    <div className={styles.lessonTitle}>{lesson.subject.name}</div>
                                                    <div className={styles.lessonMeta}>
                                                        <span>{showTeacher ? lesson.teacher.name: lesson.group.name}</span>
                                                        <span>{lesson.room.name}</span>
                                                    </div>
                                                </div>
                                            ))}
                                    </div>
                                ))}
                            </div>
                        );
                    })}
                </div>
            </div>
        </div>
    );

}