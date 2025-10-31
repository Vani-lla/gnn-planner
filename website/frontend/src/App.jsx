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
import { Background } from './components/Background';
import PlanLessons from './components/PlanLessons';

function App() {

    return (
        <BrowserRouter>
            <div className='global-bg-pattern' />
            <Routes>
                <Route path="/add/teachers" element={<Teachers />} />
                <Route path="/add/rooms" element={<Rooms />} />
                <Route path="/add/subjects" element={<Subjects />} />
                <Route path="/add/classes" element={<StudentGroups />} />
                <Route path="/add/requirements" element={<Requirements />} />
                <Route path="/add/upload-requirements" element={<UploadRequirements />} />
                <Route path="/add/generation" element={<RunEvolutionaryProcess />} />
                <Route path="/add/plan" element={<PlanLessons />} />
                <Route path="/" element={<h1>xD</h1>} />
            </Routes>
        </BrowserRouter>
    )
}

export default App
