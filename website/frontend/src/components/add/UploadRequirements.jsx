import React, { useState } from "react";

export default function UploadRequirements() {
    const [file, setFile] = useState(null); // State to store the selected file
    const [message, setMessage] = useState(""); // State to store the upload status message
    const [loading, setLoading] = useState(false); // State to indicate loading status

    // Function to get the CSRF token from cookies
    const getCSRFToken = () => {
        const cookieValue = document.cookie
            .split("; ")
            .find((row) => row.startsWith("csrftoken="))
            ?.split("=")[1];
        return cookieValue || "";
    };

    // Handle file selection
    const handleFileChange = (e) => {
        setFile(e.target.files[0]);
    };

    // Handle file upload
    const handleUpload = async () => {
        if (!file) {
            alert("Please select a file to upload.");
            return;
        }

        const formData = new FormData();
        formData.append("file", file);

        try {
            setLoading(true);
            setMessage("");

            const res = await fetch("/api/upload-requirements/", {
                method: "POST",
                headers: {
                    "X-CSRFToken": getCSRFToken(), // Include the CSRF token in the headers
                },
                body: formData,
            });

            const data = await res.json();
            if (res.ok) {
                setMessage(`✅ ${data.message} (RequirementSet ID: ${data.req_set_id})`);
            } else {
                setMessage(`❌ Error: ${data.error}`);
            }
        } catch (error) {
            console.error("Error uploading file:", error);
            setMessage("❌ Network error");
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="upload-container">
            <h1>Upload Requirements CSV</h1>
            <input
                type="file"
                accept=".csv"
                onChange={handleFileChange}
                className="file-input"
            />
            <button
                onClick={handleUpload}
                disabled={loading}
                className={`upload-button ${loading ? "loading" : ""}`}
            >
                {loading ? "Uploading..." : "Upload"}
            </button>
            {message && <p className="upload-message">{message}</p>}
        </div>
    );
}