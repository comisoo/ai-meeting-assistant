const dropZone = document.getElementById('drop-zone');
const fileInput = document.getElementById('file-input');
const processBtn = document.getElementById('process-btn');
const statusSection = document.getElementById('processing-status');
<<<<<<< HEAD
const templateSelect = document.getElementById('template-select');
const resultsSection = document.getElementById('results-section');
=======
>>>>>>> 6a9b581612307d82b4c1a68e19cc9ebcf61d1f9d
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

<<<<<<< HEAD
// Processing Logic
processBtn.addEventListener('click', async () => {
    if (!selectedFile) return;

    statusSection.classList.remove('hidden');
    resultsSection.innerHTML = ''; // reset previous
    resultsSection.classList.add('hidden');
    processBtn.disabled = true;

    const steps = document.querySelectorAll('.step');
    steps.forEach(step => {
        step.style.color = '#818cf8';
        step.innerHTML = step.innerHTML.replace(' ✅', '').replace(' ❌', '').replace(' (Pending)', '');
    });

    try {
        const formData = new FormData();
        formData.append("file", selectedFile);
        formData.append("template", templateSelect.value);

        steps[0].style.color = '#f8fafc';
        steps[0].innerHTML += ' (Pending)';

        const response = await fetch("http://localhost:8000/api/process-audio", {
            method: 'POST',
            body: formData
        });

        steps.forEach(step => {
            step.style.color = '#f8fafc';
            if(!step.innerHTML.includes('✅')) step.innerHTML = step.innerHTML.split(' (')[0] + ' ✅';
        });

        if (!response.ok) {
            const err = await response.json();
            throw new Error(err.detail || 'Server error occurred');
        }

        const data = await response.json();
        renderResults(data);

    } catch (error) {
        console.error(error);
        alert(`Error: ${error.message}`);
        steps.forEach(step => {
            step.style.color = '#f87171'; // red
        });
    } finally {
        processBtn.disabled = false;
    }
});

function renderResults(data) {
    const summaryHTML = marked.parse(data.summary || 'No summary generated.');
    
    let actionItemsHTML = '';
    if (data.action_items && data.action_items.length > 0) {
        actionItemsHTML = data.action_items.map(item => `
            <div style="background: rgba(255,255,255,0.05); padding: 1rem; border-radius: 8px; margin-bottom: 0.5rem; border: 1px solid rgba(255,255,255,0.1);">
                <strong>Task:</strong> ${item.task} <br/>
                <span style="color: #c084fc;">👤 Assignee: ${item.assignee}</span> | 
                <span style="color: #fb923c;">🗓 Deadline: ${item.deadline}</span>
            </div>
        `).join('');
    } else {
        actionItemsHTML = '<p style="color: #94a3b8;">No specific action items found.</p>';
    }

    resultsSection.innerHTML = `
        <div class="glass-panel" style="text-align: left;">
            <h2 style="margin-top: 0; color: #c084fc; font-weight: 600;">📝 Meeting Summary</h2>
            <div style="line-height: 1.6;">${summaryHTML}</div>
            
            <h2 style="color: #818cf8; margin-top: 2rem; font-weight: 600;">🎯 Action Items</h2>
            ${actionItemsHTML}

            <h3 style="margin-top: 2rem; border-top: 1px solid rgba(255,255,255,0.1); padding-top: 1rem; font-size: 1rem; color: #94a3b8; cursor: pointer;" onclick="document.getElementById('raw-transcript').classList.toggle('hidden')">
                (Click to Toggle) View Code-Switched Cleaned Transcript
            </h3>
            <div id="raw-transcript" class="hidden" style="white-space: pre-wrap; font-size: 0.9em; line-height: 1.5; color: #cbd5e1; background: rgba(0,0,0,0.2); padding: 1rem; border-radius: 8px; margin-top: 0.5rem;">${data.cleaned_transcript}</div>
        </div>
    `;
    resultsSection.classList.remove('hidden');
}
=======
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
>>>>>>> 6a9b581612307d82b4c1a68e19cc9ebcf61d1f9d
