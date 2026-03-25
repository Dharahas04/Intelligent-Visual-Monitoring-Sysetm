const express = require('express');
const axios = require('axios');
const cors = require('cors');

const app = express();
const PORT = 3001; // We will run the backend on port 3001

// Middleware to parse JSON. Increased limit for base64 images.
app.use(express.json({ limit: '10mb' }));
app.use(cors()); // Use cors middleware

// This is our proxy endpoint.
// React will send requests here.
app.post('/api/detect', async (req, res) => {
    try {
        // We take the image from the request...
        const { image } = req.body;
        if (!image) {
            return res.status(400).json({ error: 'No image data provided' });
        }

        // ...and forward it to our Python AI service.
        // This is a server-to-server request, so no browser CORS issues.
        const pythonApiResponse = await axios.post('http://localhost:5001/detect', {
            image: image
        });

        // We send the result from the Python service back to our React app.
        res.json(pythonApiResponse.data);

    } catch (error) {
        console.error('Error in proxy to AI service:', error.message);
        res.status(500).json({ error: 'Failed to communicate with AI service' });
    }
});

app.listen(PORT, () => {
    console.log(`Backend proxy server is running on http://localhost:${PORT}`);
});
