import React from 'react';
import './App.css';
import MaskDetector from './MaskDetector'; // <-- 1. Import your component

function App() {
  return (
    <div className="App">
      <header className="App-header">
        <h1>Intelligent Visual Monitoring System - IntelMon</h1>
        <MaskDetector /> {/* <-- 2. Add your component here */}
      </header>
    </div>
  );
}

export default App;
