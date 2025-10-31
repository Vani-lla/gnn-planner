import React, { useState, useEffect } from "react";

export default function RunEvolutionaryProcess() {
    const [generations, setGenerations] = useState("");
    const [requirementSets, setRequirementSets] = useState([]);
    const [selectedSet, setSelectedSet] = useState("");
    const [message, setMessage] = useState("");
    const [loading, setLoading] = useState(false);

    // Fetch Requirement Sets from the backend
    useEffect(() => {
        const fetchRequirementSets = async () => {
            try {
                const res = await fetch("/api/requirement-sets/");
                const data = await res.json();
                if (res.ok) {
                    setRequirementSets(data);
                } else {
                    console.error("Failed to fetch requirement sets:", data.error);
                }
            } catch (error) {
                console.error("Error fetching requirement sets:", error);
            }
        };

        fetchRequirementSets();
    }, []);

    const handleSubmit = async () => {
        if (!generations || isNaN(generations) || generations <= 0) {
            alert("Please enter a valid positive integer for generations.");
            return;
        }

        if (!selectedSet) {
            alert("Please select a requirement set.");
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
                setMessage(`❌ Error: ${data.error || "Unknown error"}`);
            }
        } catch (error) {
            console.error("Error:", error);
            setMessage("❌ Network error");
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="flex flex-col items-center gap-6 p-6">
            <h1 className="text-2xl font-bold">Run Evolutionary Process</h1>

            {/* Requirement Set Selection */}
            <div className="w-full max-w-md">
                <label htmlFor="requirement-set" className="block text-gray-700 font-medium mb-2">
                    Select Requirement Set:
                </label>
                <select
                    id="requirement-set"
                    value={selectedSet}
                    onChange={(e) => setSelectedSet(e.target.value)}
                    className="w-full border border-gray-300 rounded-lg p-2"
                >
                    <option value="">-- Select a Set --</option>
                    {requirementSets.map((set) => (
                        <option key={set.id} value={set.id}>
                            {set.name}
                        </option>
                    ))}
                </select>
            </div>

            {/* Generations Input */}
            <div className="w-full max-w-md">
                <label htmlFor="generations" className="block text-gray-700 font-medium mb-2">
                    Enter Number of Generations:
                </label>
                <input
                    id="generations"
                    type="number"
                    value={generations}
                    onChange={(e) => setGenerations(e.target.value)}
                    placeholder="Enter a positive integer"
                    className="w-full border border-gray-300 rounded-lg p-2"
                />
            </div>

            {/* Submit Button */}
            <button
                onClick={handleSubmit}
                disabled={loading}
                className={`px-6 py-2 rounded-lg text-white font-semibold ${loading ? "bg-gray-400" : "bg-blue-600 hover:bg-blue-700"
                    }`}
            >
                {loading ? "Processing..." : "Run Process"}
            </button>

            {/* Message Display */}
            {message && <p className="text-center text-gray-700">{message}</p>}
        </div>
    );
}