const express = require('express');
const bodyParser = require('body-parser');
const dotenv = require('dotenv');
dotenv.config();

const app = express();
const port = process.env.PORT || 3000;
const AIzaSyBuLDbPhS5QddaZaETco_-MUtngmGSscH8 = process.env.AIzaSyBuLDbPhS5QddaZaETco_-MUtngmGSscH8;

const isValidYoutubeUrl = (url) => {
    const youtubeRegex = /(https?:\/\/)?(www\.)?(youtube|youtu|youtube-nocookie)\.(com|be)\/.+/;
    return youtubeRegex.test(url);
};

app.use(bodyParser.json());

app.post('/convert', async (req, res) => {
    const { url } = req.body;
    if (!url || !isValidYoutubeUrl(url)) {
        return res.status(400).json({ success: false, message: "Invalid URL" });
    }

    // Extract video ID
    const videoId = url.includes('v=') ? url.split('v=')[1] : url.split('/').pop();

    // Example conversion logic (You should implement actual conversion)
    const downloadUrl = `https://youtube.com/download/${videoId}.mp4`;

    res.json({ success: true, downloadUrl, videoId });
});

app.listen(port, () => {
    console.log(`Server is running on port ${port}`);
});

