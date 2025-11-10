import React, { useState, useEffect } from "react";
import styles from "../../styles/Requirements.module.css";

export default function RunEvolutionaryProcess() {
    const [generations, setGenerations] = useState("");
    const [requirementSets, setRequirementSets] = useState([]);
    const [selectedSet, setSelectedSet] = useState("");
    const [message, setMessage] = useState("");
    const [loading, setLoading] = useState(false);

    useEffect(() => {
        const fetchRequirementSets = async () => {
            try {
                const res = await fetch("/api/requirement-sets/");
                const data = await res.json();
                if (res.ok) setRequirementSets(data);
            } catch {
                // noop
            }
        };
        fetchRequirementSets();
    }, []);

    const handleSubmit = async () => {
        if (!generations || isNaN(generations) || Number(generations) <= 0) {
            setMessage("❌ Enter a positive integer for generations.");
            return;
        }
        if (!selectedSet) {
            setMessage("❌ Select a requirement set.");
            return;
        }

        try {
            setLoading(true);
            setMessage("");

            const csrftoken = document.cookie
                .split("; ")
                .find((row) => row.startsWith("csrftoken="))
                ?.split("=")[1];

            const res = await fetch("/api/run-evolutionary-process/", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    "X-CSRFToken": csrftoken,
                },
                body: JSON.stringify({
                    generations: parseInt(generations, 10),
                    req_set_id: selectedSet,
                }),
            });
            const data = await res.json();
            if (res.ok) {
                setMessage(`✅ ${data.message}`);
            } else {
                setMessage(`❌ ${data.error || "Unknown error"}`);
            }
        } catch {
            setMessage("❌ Network error");
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className={styles.requirementsView}>
            <h2 className={styles.placeholder}>Run Evolutionary Process</h2>

            <div className={styles.requirementsSelectors}>
                <select
                    className={styles.requirementsSelect}
                    value={selectedSet}
                    onChange={(e) => setSelectedSet(e.target.value)}
                >
                    <option value="">Select Requirement Set</option>
                    {requirementSets.map((set) => (
                        <option key={set.id} value={set.id}>
                            {set.name}
                        </option>
                    ))}
                </select>

                <input
                    type="number"
                    min="1"
                    step="1"
                    value={generations}
                    onChange={(e) => setGenerations(e.target.value)}
                    placeholder="Number of generations"
                    className={styles.requirementsSelect}
                />

                <button
                    className={styles.button}
                    onClick={handleSubmit}
                    disabled={loading || !selectedSet || !generations}
                >
                    {loading ? "Processing..." : "Run Process"}
                </button>
            </div>

            {message && <p className={styles.message}>{message}</p>}
        </div>
    );
}