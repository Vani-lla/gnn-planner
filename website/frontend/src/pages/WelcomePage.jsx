import React from 'react';
import { Link } from 'react-router-dom';
import "../styles/WelcomePage.css"

export default function WelcomePage() {
    return (
        <div className="welcome-container">
            <h1 className="welcome-title">Welcome to the Timetable Generator</h1>
            <p className="welcome-subtitle">Choose an option to get started:</p>
            <div className="welcome-buttons">
                <Link to="/plan" className="welcome-button">View Plans</Link>
                <Link to="/add/generation" className="welcome-button">Generate a New Plan</Link>
                <Link to="/add/requirements" className="welcome-button">Upload Hour Requirements</Link>
            </div>
        </div>
    );
}