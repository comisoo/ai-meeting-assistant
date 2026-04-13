const dropZone = document.getElementById('drop-zone');
const fileInput = document.getElementById('file-input');
const processBtn = document.getElementById('process-btn');
const statusSection = document.getElementById('processing-status');
let selectedFile = null;

// Event Listeners for Drag and Drop
dropZone.addEventListener('click', () => fileInput.click());

dropZone.addEventListener('dragover', (e) => {
    e.preventDefault();
    dropZone.classList.add('dragover');
});

dropZone.addEventListener('dragleave', () => {
    dropZone.classList.remove('dragover');
});

dropZone.addEventListener('drop', (e) => {
    e.preventDefault();
    dropZone.classList.remove('dragover');
    if (e.dataTransfer.files.length) {
        selectedFile = e.dataTransfer.files[0];
        updateDropZoneUI();
    }
});

fileInput.addEventListener('change', (e) => {
    if (e.target.files.length) {
        selectedFile = e.target.files[0];
        updateDropZoneUI();
    }
});

function updateDropZoneUI() {
    if (selectedFile) {
        dropZone.innerHTML = `<div class="icon">✅</div><p>${selectedFile.name}</p>`;
        processBtn.disabled = false;
    }
}

// Processing Mock
processBtn.addEventListener('click', async () => {
    statusSection.classList.remove('hidden');
    // Here you would do actual API calls to FastAPI
    // const formData = new FormData();
    // formData.append("file", selectedFile);
    // fetch("http://localhost:8000/api/process-audio", { method: 'POST', body: formData }) ...

    const steps = document.querySelectorAll('.step');
    for (let step of steps) {
        step.style.color = '#818cf8';
        await new Promise(r => setTimeout(r, 1000));
        step.style.color = '#f8fafc';
        step.innerHTML += ' ✅';
    }
    
    alert('Processing complete! Results UI pending backend integration.');
});
