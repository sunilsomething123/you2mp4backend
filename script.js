document.getElementById('download-form').addEventListener('submit', async (event) => {
    event.preventDefault();

    const url = document.getElementById('url').value;
    const resolution = document.getElementById('resolution').value;
    const messageDiv = document.getElementById('message');
    const videoPreviewDiv = document.getElementById('video-preview');
    const videoElement = document.getElementById('video');
    const historyList = document.getElementById('history-list');

    messageDiv.textContent = 'Processing...';
    messageDiv.classList.remove('hidden');
    videoPreviewDiv.classList.add('hidden');

    try {
        const response = await fetch('https://you2-mp4.onrender.com/download', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ url, resolution }),
        });

        const data = await response.json();

        if (data.status === 'success') {
            messageDiv.textContent = 'Download ready!';

            videoElement.src = data.preview;
            videoPreviewDiv.classList.remove('hidden');

            const downloadLink = document.createElement('a');
            downloadLink.href = data.file;
            downloadLink.textContent = `Download (${resolution})`;
            downloadLink.target = '_blank';

            const historyItem = document.createElement('li');
            historyItem.appendChild(downloadLink);
            historyList.appendChild(historyItem);

            document.getElementById('download-history').classList.remove('hidden');
        } else {
            messageDiv.textContent = data.message;
        }
    } catch (error) {
        messageDiv.textContent = 'An error occurred. Please try again.';
    }
});

// Fetch resolutions and populate the dropdown
document.getElementById('url').addEventListener('input', async () => {
    const url = document.getElementById('url').value;
    const resolutionSelect = document.getElementById('resolution');

    if (url) {
        try {
            const response = await fetch('YOUR_BACKEND_URL/get_resolutions', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ url }),
            });

            const data = await response.json();

            resolutionSelect.innerHTML = '';
            data.resolutions.forEach(resolution => {
                const option = document.createElement('option');
                option.value = resolution;
                option.textContent = resolution;
                resolutionSelect.appendChild(option);
            });
        } catch (error) {
            console.error('Error fetching resolutions:', error);
        }
    }
});

// Social Media Sharing
function shareOnSocialMedia(platform, url) {
    let shareUrl = '';

    switch (platform) {
        case 'facebook':
            shareUrl = `https://www.facebook.com/sharer/sharer.php?u=${encodeURIComponent(url)}`;
            break;
        case 'twitter':
            shareUrl = `https://twitter.com/intent/tweet?url=${encodeURIComponent(url)}`;
            break;
        case 'whatsapp':
            shareUrl = `https://api.whatsapp.com/send?text=${encodeURIComponent(url)}`;
            break;
        case 'instagram':
            shareUrl = `https://www.instagram.com/?url=${encodeURIComponent(url)}`;
            break;
    }

    window.open(shareUrl, '_blank');
}

// Add event listeners for social media buttons
document.getElementById('facebook-share').addEventListener('click', () => shareOnSocialMedia('facebook', window.location.href));
document.getElementById('twitter-share').addEventListener('click', () => shareOnSocialMedia('twitter', window.location.href));
document.getElementById('whatsapp-share').addEventListener('click', () => shareOnSocialMedia('whatsapp', window.location.href));
document.getElementById('instagram-share').addEventListener('click', () => shareOnSocialMedia('instagram', window.location.href));
