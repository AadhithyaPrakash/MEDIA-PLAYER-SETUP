let mediaList = [];
let currentIndex = -1;

async function fetchMediaList() {
    try {
        const response = await fetch('/media');
        const contentType = response.headers.get('content-type');

        if (contentType && contentType.includes('application/json')) {
            mediaList = await response.json();
            renderMediaList();
        } else {
            throw new Error('Server did not return JSON');
        }
    } catch (error) {
        document.getElementById('media-list').innerHTML =
            `<p class="loading-message">Error loading media: ${error.message}</p>`;
    }
}

function renderMediaList(filter = 'all') {
    const listContainer = document.getElementById('media-list');
    listContainer.innerHTML = '';

    const filteredList = filter === 'all'
        ? mediaList
        : mediaList.filter(item => item.type === filter);

    if (filteredList.length === 0) {
        listContainer.innerHTML = '<p class="loading-message">No media files found.</p>';
        return;
    }

    filteredList.forEach((media, index) => {
        const item = document.createElement('div');
        item.classList.add('media-item');
        item.innerHTML = `
            <div class="media-icon">${media.type === 'audio' ? '🎵' : '🎥'}</div>
            <div class="media-details">
                <div class="media-name">${media.name}</div>
                <div class="media-type">${media.type}</div>
            </div>
        `;
        item.addEventListener('click', () => playMedia(index));
        listContainer.appendChild(item);
    });
}

function playMedia(index) {
    currentIndex = index;
    const media = mediaList[index];
    const audioPlayer = document.getElementById('audio-player');
    const videoPlayer = document.getElementById('video-player');

    if (media.type === 'audio') {
        videoPlayer.style.display = 'none';
        audioPlayer.style.display = 'block';
        audioPlayer.src = media.url;
        audioPlayer.play();
    } else {
        audioPlayer.style.display = 'none';
        videoPlayer.style.display = 'block';
        videoPlayer.src = media.url;
        videoPlayer.play();
    }

    document.getElementById('now-playing-title').textContent = media.name;

    document.querySelectorAll('.media-item').forEach(item => item.classList.remove('active'));
    document.querySelectorAll('.media-item')[index].classList.add('active');
}

document.querySelectorAll('.filter-btn').forEach(btn => {
    btn.addEventListener('click', () => {
        document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        renderMediaList(btn.dataset.filter);
    });
});

document.getElementById('volume-slider').addEventListener('input', (e) => {
    const audio = document.getElementById('audio-player');
    const video = document.getElementById('video-player');
    if (audio.style.display === 'block') audio.volume = e.target.value;
    if (video.style.display === 'block') video.volume = e.target.value;
});

document.getElementById('play-btn').addEventListener('click', () => {
    const audio = document.getElementById('audio-player');
    const video = document.getElementById('video-player');
    if (audio.style.display === 'block') audio.paused ? audio.play() : audio.pause();
    if (video.style.display === 'block') video.paused ? video.play() : video.pause();
});

document.getElementById('prev-btn').addEventListener('click', () => {
    if (currentIndex > 0) playMedia(currentIndex - 1);
});

document.getElementById('next-btn').addEventListener('click', () => {
    if (currentIndex < mediaList.length - 1) playMedia(currentIndex + 1);
});

fetchMediaList();
