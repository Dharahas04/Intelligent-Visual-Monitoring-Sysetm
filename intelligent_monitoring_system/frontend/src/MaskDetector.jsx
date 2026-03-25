// A simplified example for your React component

import React, { useRef, useEffect } from 'react';
import Webcam from 'react-webcam';
import axios from 'axios';

const MaskDetector = () => {
    const webcamRef = useRef(null);
    const canvasRef = useRef(null);

    const drawResults = (results) => {
        const video = webcamRef.current.video;
        const canvas = canvasRef.current;
        const ctx = canvas.getContext('2d');
        
        // Set canvas dimensions to match video
        canvas.width = video.videoWidth;
        canvas.height = video.videoHeight;
        
        // Clear previous drawings
        ctx.clearRect(0, 0, canvas.width, canvas.height);

        results.forEach(result => {
            const [startX, startY, endX, endY] = result.box;
            const label = `${result.label} (${(result.confidence * 100).toFixed(2)}%)`;
            const color = result.label === 'Mask' ? 'green' : 'red';
            
            // Draw the box
            ctx.strokeStyle = color;
            ctx.lineWidth = 4;
            ctx.strokeRect(startX, startY, endX - startX, endY - startY);
            
            // Draw the label background
            ctx.fillStyle = color;
            ctx.font = '18px Arial';
            const textWidth = ctx.measureText(label).width;
            ctx.fillRect(startX, startY - 25, textWidth + 10, 25);
            
            // Draw the label text
            ctx.fillStyle = 'white';
            ctx.fillText(label, startX + 5, startY - 5);
        });
    };

    useEffect(() => {
        const interval = setInterval(async () => {
            if (webcamRef.current) {
                const imageSrc = webcamRef.current.getScreenshot();
                if (imageSrc) {
                    // Send image to Flask API (remove data:image/jpeg;base64,)
                    const base64Image = imageSrc.split(',')[1];
                    // const response = await axios.post('http://localhost:5001/detect', {
                    //     image: base64Image
                    // });
                    const response = await axios.post('/api/detect', { // <-- CHANGE THIS URL
    image: base64Image
}, {
   timeout: 3000 // Increased timeout slightly
});
                    // Draw the results on the canvas
                    drawResults(response.data);
                }
            }
        }, 200); // Send a frame every 200ms

        return () => clearInterval(interval);
    }, []);

    return (
        <div style={{ position: 'relative', width: '640px', height: '480px' }}>
            <Webcam
                ref={webcamRef}
                screenshotFormat="image/jpeg"
                style={{ position: 'absolute', left: 0, top: 0, zIndex: 1 }}
            />
            <canvas
                ref={canvasRef}
                style={{ position: 'absolute', left: 0, top: 0, zIndex: 2 }}
            />
        </div>
    );
};

export default MaskDetector;