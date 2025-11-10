import React from "react";
import { Link, useLocation } from "react-router-dom";
import "../styles/Navigation.css";

export default function Navigation() {
    const location = useLocation();

    // Map routes to page titles
    const pageTitles = {
        "/": "Welcome",
        "/plan": "Lesson View",
        "/add/generation": "Generate a New Plan",
        "/add/subjects": "Add Subjects",
        "/add/teachers": "Add Teachers",
        "/add/rooms": "Add Rooms",
        "/add/classes": "Add Classes",
        "/add/requirements": "Add Hour Requirements",
        "/add/availability": "Add Teacher Availability",
    };

    // Get the current page title based on the route
    const currentPage = pageTitles[location.pathname] || "Page";

    return (
        <nav className="navigation-container">
            <div className="navigation-title">GEL Scheduler</div>
            <div className="navigation-current-page">{currentPage}</div>
            <ul className="navigation-links">
                <li>
                    <Link to="/" className="navigation-link">Home</Link>
                </li>
                <li>
                    <Link to="/plan" className="navigation-link">View Plans</Link>
                </li>
                <li>
                    <Link to="/add/generation" className="navigation-link">Generate a New Plan</Link>
                </li>
                <li className="dropdown">
                    <span className="navigation-link dropdown-toggle">Upload Requirements</span>
                    <ul className="dropdown-menu">
                        <li><Link to="/add/subjects" className="dropdown-item">Add Subjects</Link></li>
                        <li><Link to="/add/teachers" className="dropdown-item">Add Teachers</Link></li>
                        <li><Link to="/add/rooms" className="dropdown-item">Add Rooms</Link></li>
                        <li><Link to="/add/classes" className="dropdown-item">Add Classes</Link></li>
                        <li><Link to="/add/requirements" className="dropdown-item">Add Hours</Link></li>
                        <li><Link to="/add/availability" className="dropdown-item">Add Availability</Link></li>
                        <li><Link to="/add/requirements/7" className="dropdown-item">Requirement 7</Link></li>
                        <li><Link to="/add/requirements/8" className="dropdown-item">Requirement 8</Link></li>
                    </ul>
                </li>
            </ul>
        </nav>
    );
}