const themeToggle = document.getElementById('themeToggle');
const themeIcon = document.getElementById('themeIcon');
const body = document.body;

const savedTheme = localStorage.getItem('theme') || 'dark';
body.setAttribute('data-theme', savedTheme);
themeIcon.textContent = savedTheme === 'dark' ? '🌙' : '☀️';

themeToggle.addEventListener('click', () => {
    const currentTheme = body.getAttribute('data-theme');
    const newTheme = currentTheme === 'dark' ? 'light' : 'dark';

    body.setAttribute('data-theme', newTheme);
    themeIcon.textContent = newTheme === 'dark' ? '🌙' : '☀️';
    localStorage.setItem('theme', newTheme);
});

const fileInput = document.getElementById('fileInput');
const fileUpload = document.getElementById('fileUpload');
const selectedFiles = document.getElementById('selectedFiles');
const errorMessage = document.getElementById('errorMessage');
let uploadedFiles = [];


function validateFile(file) {
    const maxSize = 10 * 1024 * 1024;
    const allowedTypes = ['application/pdf', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'];

    if (!allowedTypes.includes(file.type)) {
        return 'Only PDF and DOCX files are allowed';
    }

    if (file.size > maxSize) {
        return 'File size must be less than 10MB';
    }

    return null;
}

function formatFileSize(bytes) {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

function displayFiles() {
    selectedFiles.innerHTML = '';
    uploadedFiles.forEach((file, index) => {
        const fileItem = document.createElement('div');
        fileItem.className = 'file-item';
        fileItem.innerHTML = `
                    <div class="file-info">
                        <span>📄</span>
                        <div>
                            <div class="filename">${file.name}</div>
                            <div class="file-size">${formatFileSize(file.size)}</div>
                        </div>
                    </div>
                    <button type="button" class="remove-file" onclick="removeFile(${index})">
                        ✕
                    </button>
                `;
        selectedFiles.appendChild(fileItem);
    });
}

window.removeFile = function (index) {
    uploadedFiles.splice(index, 1);
    displayFiles();
    errorMessage.style.display = 'none';
}

function handleFiles(files) {
    const newFiles = Array.from(files);
    let hasError = false;
    let errorText = '';

    newFiles.forEach(file => {
        const error = validateFile(file);
        if (error) {
            hasError = true;
            errorText += `${file.name}: ${error}\n`;
        } else {
            const isDuplicate = uploadedFiles.some(existingFile =>
                existingFile.name === file.name && existingFile.size === file.size
            );
            if (!isDuplicate) {
                uploadedFiles.push(file);
            }
        }
    });

    if (hasError) {
        errorMessage.textContent = errorText;
        errorMessage.style.display = 'block';
    } else {
        errorMessage.style.display = 'none';
    }

    displayFiles();
}

fileUpload.addEventListener('click', () => fileInput.click());

fileInput.addEventListener('change', (e) => {
    handleFiles(e.target.files);
});
fileUpload.addEventListener('dragover', (e) => {
    e.preventDefault();
    fileUpload.classList.add('dragover');
});

fileUpload.addEventListener('dragleave', () => {
    fileUpload.classList.remove('dragover');
});

fileUpload.addEventListener('drop', (e) => {
    e.preventDefault();
    fileUpload.classList.remove('dragover');
    handleFiles(e.dataTransfer.files);
});

const rankingForm = document.getElementById('rankingForm');
const mainForm = document.getElementById('mainForm');
const loadingState = document.getElementById('loadingState');
const resultsSection = document.getElementById('resultsSection');
const submitBtn = document.getElementById('submitBtn');
const API_BASE_URL = "/api";

rankingForm.addEventListener('submit', async (e) => {
    e.preventDefault();

    const jobDescription = document.getElementById('jobDescription').value;

    if (uploadedFiles.length === 0) {
        errorMessage.textContent = 'Please select at least one resume file';
        errorMessage.style.display = 'block';
        return;
    }

    mainForm.style.display = 'none';
    loadingState.style.display = 'block';
    errorMessage.style.display = 'none';

    try {
        const formData = new FormData();
        formData.append('job_description', jobDescription);

        uploadedFiles.forEach(file => {
            formData.append('resumes', file);
        });

        const response = await fetch(`${API_BASE_URL}/rank`, {
            method: 'POST',
            body: formData
        });

        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.detail || 'API request failed');
        }

        const apiData = await response.json();

        displayResults(apiData);

    } catch (error) {
        console.error('Error:', error);
        errorMessage.textContent = `Error: ${error.message || 'Failed to process resumes'}`;
        errorMessage.style.display = 'block';
        loadingState.style.display = 'none';
        mainForm.style.display = 'block';
    }
});

function displayResults(apiData) {
    const jobTitle = document.getElementById('jobDescription').value.split('\n')[0].substring(0, 50);
    document.getElementById('jobTitle').textContent = jobTitle + (document.getElementById('jobDescription').value.split('\n')[0].length > 50 ? '...' : '');

    const candidatesList = document.getElementById('candidatesList');
    candidatesList.innerHTML = '';

    apiData.results.forEach(candidate => {
        const row = document.createElement('div');
        row.className = 'candidate-row';

        const rankBadge = candidate.rank === 1 ? 'rank-badge top' : 'rank-badge';
        const rankIcon = candidate.rank === 1 ? '🏆' : candidate.rank;

        row.innerHTML = `
                    <div class="${rankBadge}">
                        ${rankIcon}
                    </div>
                    <div>
                        <div class="filename">${candidate.filename}</div>
                    </div>
                    <div class="score-container">
                        <div class="score-value">${candidate.grand_score}%</div>
                        <div class="score-bar">
                            <div class="score-fill" style="width: ${candidate.grand_score}%"></div>
                        </div>
                    </div>
                    <div>
                        <div class="tech-stack">
                            ${candidate.tech_stack && candidate.tech_stack.length > 0
                ? candidate.tech_stack.map(tech => `<span class="tech-tag">${tech}</span>`).join('')
                : '<span class="no-tech">No tech stack detected</span>'}
                        </div>
                    </div>
                `;
        candidatesList.appendChild(row);
    });

    window.apiData = apiData;

    loadingState.style.display = 'none';
    resultsSection.style.display = 'block';
}


document.getElementById('backBtn').addEventListener('click', () => {
    resultsSection.style.display = 'none';
    mainForm.style.display = 'block';
    uploadedFiles = [];
    document.getElementById('selectedFiles').innerHTML = '';
    document.getElementById('jobDescription').value = '';
    errorMessage.style.display = 'none';
});

document.getElementById('downloadBtn').addEventListener('click', async () => {
    if (!window.apiData || !window.apiData.report_url) {
        errorMessage.textContent = 'No report available for download.';
        errorMessage.style.display = 'block';
        return;
    }

    try {

        const response = await fetch(`${window.apiData.report_url}`);

        if (!response.ok) {
            throw new Error('Failed to download report');
        }
        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `resume_report_${new Date().toISOString().replace(/:/g, '-').replace(/\..+/, '')}.csv`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        window.URL.revokeObjectURL(url);

    } catch (error) {
        console.error('Download error:', error);
        errorMessage.textContent = `Error: ${error.message || 'Failed to download report'}`;
        errorMessage.style.display = 'block';
    }
});