import React from 'react'
import { BrowserRouter, Routes, Route, Link } from 'react-router-dom';
import './styles/main.css'
import Teachers from './components/add/Teachers';
import Subjects from './components/add/Subjects';
import Rooms from './components/add/Rooms';
import StudentGroups from './components/add/StudentGroups';
import Requirements from './components/add/Requirements';
import UploadRequirements from './components/add/UploadRequirements';
import RunEvolutionaryProcess from './components/add/RunEvolutionaryProcess';
import LessonView from './components/LessonView';
import TeacherAvailability from './components/add/TeacherAvailability';
import SubjectBlockPage from './components/add/SubjectBlockPage';
import WelcomePage from './pages/WelcomePage';
import Navigation from './components/Navigation';

function App() {

    return (
        <BrowserRouter>
            <div className='global-bg-pattern' />
            <Routes>
                <Route path="/" element={<WelcomePage />} />
                <Route
                    path="*"
                    element={
                        <>
                            <Navigation />
                            <Routes>
                                <Route path="/plan" element={<LessonView />} />
                                <Route path="/add/teachers" element={<Teachers />} />
                                <Route path="/add/availability" element={<TeacherAvailability />} />
                                <Route path="/add/rooms" element={<Rooms />} />
                                <Route path="/add/subjects" element={<Subjects />} />
                                <Route path="/add/classes" element={<StudentGroups />} />
                                <Route path="/add/blocks" element={<SubjectBlockPage />} />
                                <Route path="/add/requirements" element={<Requirements />} />
                                <Route path="/add/upload-requirements" element={<UploadRequirements />} />
                                <Route path="/add/generation" element={<RunEvolutionaryProcess />} />
                            </Routes>
                        </>
                    }
                />
            </Routes>
        </BrowserRouter>
    )
}

export default App
