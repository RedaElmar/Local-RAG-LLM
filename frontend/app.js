// Modern ChatGPT-like UI, local backend integration
try {
  console.log('App.js loaded successfully');

  // Basic element selection
  const chatArea = document.getElementById('chat-area');
  const chatForm = document.getElementById('chat-form');
  const userInput = document.getElementById('user-input');
  const sendBtn = document.getElementById('send-btn');
  const themeToggleBtn = document.getElementById('theme-toggle-btn');
  const clearChatBtn = document.getElementById('clear-chat');
  const modelSelect = document.getElementById('model-select');
  const modeQuick = document.getElementById('mode-quick');
  const modeTeam = document.getElementById('mode-team');
  const charCount = document.getElementById('char-count');

  // File management elements
  const fileCount = document.getElementById('file-count');
  const totalSize = document.getElementById('total-size');
  const fileList = document.getElementById('file-list');
  const uploadModal = document.getElementById('upload-modal');
  const rebuildModal = document.getElementById('rebuild-modal');
  const fileInput = document.getElementById('file-input');
  const uploadArea = document.getElementById('upload-area');
  const uploadProgress = document.getElementById('upload-progress');
  const progressFill = document.getElementById('progress-fill');
  const progressPercentage = document.getElementById('progress-percentage');
  const uploadedFiles = document.getElementById('uploaded-files');
  const processFilesBtn = document.getElementById('process-files-btn');

  console.log('Elements found:', {
    chatArea: !!chatArea,
    chatForm: !!chatForm,
    userInput: !!userInput,
    sendBtn: !!sendBtn,
    modeQuick: !!modeQuick,
    modeTeam: !!modeTeam,
    themeToggleBtn: !!themeToggleBtn,
    fileCount: !!fileCount,
    fileList: !!fileList
  });

  // Add markdown rendering for bot answers
  const script = document.createElement('script');
  script.src = 'https://cdn.jsdelivr.net/npm/marked/marked.min.js';
  document.head.appendChild(script);

  // File management state
  let uploadedFilesList = [];
  let rebuildTimer = null;

  // Theme management
  let currentTheme = localStorage.getItem('theme') || 'auto';
  
  function setTheme(theme) {
    currentTheme = theme;
    localStorage.setItem('theme', theme);
    
    // Remove existing theme classes
    document.documentElement.removeAttribute('data-theme');
    
    if (theme === 'auto') {
      // Auto theme based on system preference
      const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
      document.documentElement.setAttribute('data-theme', prefersDark ? 'dark' : 'light');
    } else {
      document.documentElement.setAttribute('data-theme', theme);
    }
    
    // Update theme toggle button
    updateThemeToggleUI();
  }
  
  function updateThemeToggleUI() {
    if (themeToggleBtn) {
      const themes = ['auto', 'light', 'dark'];
      const currentIndex = themes.indexOf(currentTheme);
      const nextTheme = themes[(currentIndex + 1) % themes.length];
      
      const themeIcons = {
        'auto': 'auto_awesome',
        'light': 'light_mode',
        'dark': 'dark_mode'
      };
      
      const themeLabels = {
        'auto': 'Auto',
        'light': 'Light',
        'dark': 'Dark'
      };
      
      themeToggleBtn.setAttribute('data-theme', nextTheme);
      themeToggleBtn.innerHTML = `
        <span class="material-symbols-rounded">${themeIcons[currentTheme]}</span>
        <span class="toggle-label">${themeLabels[currentTheme]}</span>
      `;
    }
  }
  
  // Initialize theme
  setTheme(currentTheme);
  
  // Theme toggle click handler
  if (themeToggleBtn) {
    themeToggleBtn.onclick = () => {
      const themes = ['auto', 'light', 'dark'];
      const currentIndex = themes.indexOf(currentTheme);
      const nextTheme = themes[(currentIndex + 1) % themes.length];
      setTheme(nextTheme);
    };
  }
  
  // Listen for system theme changes
  window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', (e) => {
    if (currentTheme === 'auto') {
      setTheme('auto');
    }
  });

  function formatDate(timestamp) {
    if (!timestamp) return 'Unknown date';
    
    // Handle both string and numeric timestamps
    let date;
    if (typeof timestamp === 'number') {
      // Convert Unix timestamp to Date object
      date = new Date(timestamp * 1000);
    } else {
      // Try to parse as string
      date = new Date(timestamp);
    }
    
    // Check if date is valid
    if (isNaN(date.getTime())) {
      return 'Invalid date';
    }
    
    return date.toLocaleDateString();
  }

  // File management functions - Make globally accessible
  window.deleteFile = async function(filename) {
    if (!confirm(`Are you sure you want to delete "${filename}"?`)) return;
    
    try {
      console.log(`Deleting file: ${filename}`);
      const response = await fetch(`/api/files/${encodeURIComponent(filename)}`, {
        method: 'DELETE'
      });
      
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }
      
      const data = await response.json();
      console.log('Delete response:', data);
      
      if (data.success) {
        showNotification(`File "${filename}" deleted successfully`, 'success');
        await refreshFileList(); // Wait for refresh to complete
      } else {
        throw new Error(data.error || 'Delete failed');
      }
    } catch (error) {
      console.error('Error deleting file:', error);
      showNotification(`Failed to delete "${filename}": ${error.message}`, 'error');
    }
  };

  // File upload handling
  function setupFileUpload() {
    if (!fileInput || !uploadArea) {
      console.warn('File upload elements not found');
      return;
    }

    console.log('Setting up file upload...');

    // File input change
    fileInput.addEventListener('change', handleFileSelect);

    // Drag and drop
    uploadArea.addEventListener('dragover', handleDragOver);
    uploadArea.addEventListener('dragleave', handleDragLeave);
    uploadArea.addEventListener('drop', handleDrop);
    uploadArea.addEventListener('click', () => fileInput.click());
    
    console.log('File upload setup completed');
  }

  function handleFileSelect(event) {
    const files = Array.from(event.target.files);
    console.log('Files selected:', files.map(f => f.name));
    addFilesToList(files);
  }

  function handleDragOver(event) {
    event.preventDefault();
    uploadArea.classList.add('dragover');
  }

  function handleDragLeave(event) {
    event.preventDefault();
    uploadArea.classList.remove('dragover');
  }

  function handleDrop(event) {
    event.preventDefault();
    uploadArea.classList.remove('dragover');
    
    const files = Array.from(event.dataTransfer.files);
    console.log('Files dropped:', files.map(f => f.name));
    addFilesToList(files);
  }

  function addFilesToList(files) {
    files.forEach(file => {
      if (isValidFileType(file)) {
        uploadedFilesList.push(file);
        renderUploadedFile(file);
      } else {
        showNotification(`Invalid file type: ${file.name}`, 'warning');
      }
    });
    
    if (processFilesBtn) {
      processFilesBtn.disabled = uploadedFilesList.length === 0;
    }
  }

  function isValidFileType(file) {
    const validTypes = [
      'application/pdf',
      'text/plain',
      'application/msword',
      'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
      'text/markdown'
    ];
    return validTypes.includes(file.type) || file.name.match(/\.(pdf|txt|doc|docx|md)$/i);
  }

  function renderUploadedFile(file) {
    if (!uploadedFiles) return;
    
    const fileItem = document.createElement('div');
    fileItem.className = 'uploaded-file-item';
    fileItem.innerHTML = `
      <div class="uploaded-file-icon">
        <span class="material-symbols-rounded">${getFileIcon(file.name)}</span>
      </div>
      <div class="uploaded-file-info">
        <div class="uploaded-file-name">${file.name}</div>
        <div class="uploaded-file-size">${formatFileSize(file.size)}</div>
      </div>
      <div class="uploaded-file-status">Ready to upload</div>
    `;
    uploadedFiles.appendChild(fileItem);
  }

  // Make function globally accessible for onclick handlers
  window.processUploadedFiles = async function() {
    if (uploadedFilesList.length === 0) return;
    
    console.log('Processing uploaded files...');
    
    if (processFilesBtn) processFilesBtn.disabled = true;
    if (uploadProgress) uploadProgress.style.display = 'block';
    
    let uploadedCount = 0;
    const totalFiles = uploadedFilesList.length;
    
    for (const file of uploadedFilesList) {
      try {
        console.log(`Uploading file: ${file.name}`);
        await uploadFile(file);
        uploadedCount++;
        
        // Update progress
        if (progressFill && progressPercentage) {
          const progress = (uploadedCount / totalFiles) * 100;
          progressFill.style.width = `${progress}%`;
          progressPercentage.textContent = `${Math.round(progress)}%`;
        }
        
        // Update file status
        updateFileStatus(file.name, 'Uploaded successfully');
        
      } catch (error) {
        console.error('Error uploading file:', error);
        updateFileStatus(file.name, 'Upload failed');
      }
    }
    
    // Wait a moment then close modal and refresh
    setTimeout(async () => {
      closeFileUpload();
      await refreshFileList(); // Wait for refresh
      showNotification(`${uploadedCount} files uploaded successfully`, 'success');
    }, 2000);
  };

  async function uploadFile(file) {
    console.log(`Starting upload for: ${file.name}`);
    
    const formData = new FormData();
    formData.append('file', file);
    
    const response = await fetch('/api/upload', {
      method: 'POST',
      body: formData
    });
    
    if (!response.ok) {
      const errorText = await response.text();
      throw new Error(`Upload failed: ${response.status} ${response.statusText} - ${errorText}`);
    }
    
    const data = await response.json();
    console.log('Upload response:', data);
    
    if (!data.success) {
      throw new Error(data.error || data.message || 'Upload failed');
    }
    
    return data;
  }

  function updateFileStatus(filename, status) {
    if (!uploadedFiles) return;
    
    const fileItems = uploadedFiles.querySelectorAll('.uploaded-file-item');
    fileItems.forEach(item => {
      const nameElement = item.querySelector('.uploaded-file-name');
      if (nameElement && nameElement.textContent === filename) {
        const statusElement = item.querySelector('.uploaded-file-status');
        if (statusElement) {
          statusElement.textContent = status;
          statusElement.style.color = status.includes('success') ? 'var(--accent-success)' : 'var(--primary-red)';
        }
      }
    });
  }

  // File Management Functions - Make globally accessible
  window.openFileUpload = function() {
    if (!uploadModal) {
      console.error('Upload modal not found');
      return;
    }
    uploadModal.classList.add('active');
    uploadedFilesList = [];
    if (uploadedFiles) uploadedFiles.innerHTML = '';
    if (processFilesBtn) processFilesBtn.disabled = true;
    if (uploadProgress) uploadProgress.style.display = 'none';
  };

  window.closeFileUpload = function() {
    if (!uploadModal) return;
    uploadModal.classList.remove('active');
    uploadedFilesList = [];
  };

  window.refreshFileList = function() {
    return fetchFileList();
  };

  async function fetchFileList() {
    try {
      console.log('Fetching file list...');
      const response = await fetch('/api/files');
      
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }
      
      const data = await response.json();
      console.log('File list response:', data);
      
      if (data.success) {
        updateFileStats(data.files);
        renderFileList(data.files);
      } else {
        console.error('Failed to fetch files:', data.error);
        showNotification('Failed to fetch files', 'error');
      }
    } catch (error) {
      console.error('Error fetching files:', error);
      showNotification(`Error fetching files: ${error.message}`, 'error');
      // Show fallback data
      updateFileStats([]);
      renderFileList([]);
    }
  }

  function updateFileStats(files) {
    if (fileCount && totalSize) {
      fileCount.textContent = files.length;
      
      const totalBytes = files.reduce((sum, file) => sum + (file.size || 0), 0);
      const totalMB = (totalBytes / (1024 * 1024)).toFixed(1);
      totalSize.textContent = `${totalMB} MB`;
    }
  }

  function renderFileList(files) {
    if (!fileList) {
      console.warn('File list element not found');
      return;
    }
    
    if (files.length === 0) {
      fileList.innerHTML = `
        <div class="file-item">
          <div class="file-icon">
            <span class="material-symbols-rounded">folder_open</span>
          </div>
          <div class="file-info">
            <div class="file-name">No files found</div>
            <div class="file-meta">Upload documents to get started</div>
          </div>
        </div>
      `;
      return;
    }

    fileList.innerHTML = files.map(file => `
      <div class="file-item">
        <div class="file-icon">
          <span class="material-symbols-rounded">${getFileIcon(file.name)}</span>
        </div>
        <div class="file-info">
          <div class="file-name" title="${file.name}">${file.name}</div>
          <div class="file-meta">${formatFileSize(file.size)} • ${formatDate(file.modified)}</div>
        </div>
        <div class="file-actions-menu">
          <button class="file-action-menu-btn" onclick="deleteFile('${file.name}')" title="Delete file">
            <span class="material-symbols-rounded">delete</span>
          </button>
        </div>
      </div>
    `).join('');
  }

  function getFileIcon(filename) {
    const ext = filename.split('.').pop().toLowerCase();
    const iconMap = {
      'pdf': 'picture_as_pdf',
      'txt': 'article',
      'doc': 'description',
      'docx': 'description',
      'md': 'article',
      'jpg': 'image',
      'jpeg': 'image',
      'png': 'image',
      'gif': 'image'
    };
    return iconMap[ext] || 'insert_drive_file';
  }

  function formatFileSize(bytes) {
    if (!bytes) return 'Unknown size';
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(1024));
    return `${(bytes / Math.pow(1024, i)).toFixed(1)} ${sizes[i]}`;
  }

  // Knowledge base rebuilding - Make globally accessible
  window.rebuildKnowledgeBase = async function() {
    console.log('Starting knowledge base rebuild...');
    
    if (!rebuildModal) {
      console.error('Rebuild modal not found');
      return;
    }
    
    rebuildModal.classList.add('active');
    startRebuildProgress();
    
    try {
      const response = await fetch('/api/rebuild', {
        method: 'POST'
      });
      
      if (!response.ok) {
        const errorText = await response.text();
        throw new Error(`HTTP ${response.status}: ${response.statusText} - ${errorText}`);
      }
      
      const data = await response.json();
      console.log('Rebuild response:', data);
      
      if (data.success) {
        completeRebuildProgress();
        setTimeout(async () => {
          rebuildModal.classList.remove('active');
          await refreshFileList(); // Wait for refresh
          showNotification('Knowledge base rebuilt successfully', 'success');
        }, 2000);
      } else {
        throw new Error(data.error || data.message || 'Rebuild failed');
      }
    } catch (error) {
      console.error('Error rebuilding knowledge base:', error);
      showNotification(`Failed to rebuild knowledge base: ${error.message}`, 'error');
      rebuildModal.classList.remove('active');
    }
  };

  function startRebuildProgress() {
    const steps = document.querySelectorAll('.rebuild-step');
    steps.forEach(step => {
      step.classList.remove('active', 'completed');
    });
    
    // Start timer
    const startTime = Date.now();
    rebuildTimer = setInterval(() => {
      const elapsed = Math.floor((Date.now() - startTime) / 1000);
      const timerElement = document.getElementById('rebuild-timer');
      if (timerElement) {
        timerElement.textContent = `${elapsed}s`;
      }
    }, 1000);
    
    // Simulate progress
    setTimeout(() => updateRebuildStep(1, 'completed', 'Files scanned successfully'), 1000);
    setTimeout(() => updateRebuildStep(2, 'active', 'Extracting text content...'), 2000);
    setTimeout(() => updateRebuildStep(2, 'completed', 'Text extraction completed'), 4000);
    setTimeout(() => updateRebuildStep(3, 'active', 'Building search index...'), 5000);
    setTimeout(() => updateRebuildStep(3, 'completed', 'Index built successfully'), 7000);
    setTimeout(() => updateRebuildStep(4, 'active', 'Finalizing...'), 8000);
  }

  function updateRebuildStep(stepNumber, status, details = '') {
    const stepElement = document.getElementById(`rebuild-step-${stepNumber}`);
    if (stepElement) {
      stepElement.classList.remove('active', 'completed');
      stepElement.classList.add(status);
      
      const statusElement = stepElement.querySelector('.step-status');
      if (statusElement) {
        statusElement.textContent = details;
      }
    }
  }

  function completeRebuildProgress() {
    updateRebuildStep(4, 'completed', 'Rebuild completed successfully');
    if (rebuildTimer) {
      clearInterval(rebuildTimer);
      rebuildTimer = null;
    }
  }

  // Notification system
  function showNotification(message, type = 'info') {
    const notification = document.createElement('div');
    notification.className = `notification notification-${type}`;
    notification.innerHTML = `
      <span class="notification-icon">
        <span class="material-symbols-rounded">
          ${type === 'success' ? 'check_circle' : type === 'error' ? 'error' : type === 'warning' ? 'warning' : 'info'}
        </span>
      </span>
      <span class="notification-message">${message}</span>
      <button class="notification-close" onclick="this.parentElement.remove()">
        <span class="material-symbols-rounded">close</span>
      </button>
    `;
    
    document.body.appendChild(notification);
    
    // Auto-remove after 5 seconds
    setTimeout(() => {
      if (notification.parentElement) {
        notification.remove();
      }
    }, 5000);
  }

  // Helper: create message element
  function createMessage(text, sender, sources=[]) {
    const msgDiv = document.createElement('div');
    msgDiv.className = `message ${sender}`;
    const avatar = document.createElement('div');
    avatar.className = 'avatar';
    if (sender === 'user') {
      avatar.innerHTML = '<span class="material-symbols-rounded">person</span>';
    } else {
      avatar.innerHTML = '<span class="material-symbols-rounded">psychology</span>';
    }
    const bubble = document.createElement('div');
    bubble.className = `bubble ${sender}`;
    if (sender === 'bot') {
      // Render markdown for bot answers
      bubble.innerHTML = window.marked ? marked.parse(text) : text;
    } else {
      bubble.textContent = text;
    }
    // If bot and sources exist, add sources below answer
    if (sender === 'bot' && sources && sources.length > 0) {
      const srcDiv = document.createElement('div');
      srcDiv.className = 'sources';
      srcDiv.innerHTML = '<span class="material-symbols-rounded" style="font-size:1.1em;vertical-align:middle;">link</span> Sources: ' +
        sources.map(src => {
          if (src && src !== 'Unknown') {
            const safeSrc = encodeURIComponent(src);
            return `<a class="source-chip" href="/static/docs/${safeSrc}" target="_blank" title="Open document">${src}</a>`;
          } else {
            return `<span class="source-chip">Unknown</span>`;
          }
        }).join(' ');
      bubble.appendChild(document.createElement('br'));
      bubble.appendChild(srcDiv);
    }
    msgDiv.appendChild(avatar);
    msgDiv.appendChild(bubble);
    return msgDiv;
  }

  // Helper: show multi-agent pipeline progress
  function showPipelineProgress() {
    const msgDiv = document.createElement('div');
    msgDiv.className = 'message bot';
    msgDiv.id = 'pipeline-progress';
    const avatar = document.createElement('div');
    avatar.className = 'avatar';
    avatar.innerHTML = '<span class="material-symbols-rounded">psychology</span>';
    const bubble = document.createElement('div');
    bubble.className = 'bubble bot';
    
    const progressHtml = `
      <div class="pipeline-progress">
        <h4>🤖 Multi-Agent Research Pipeline in Progress...</h4>
        <div class="agent-status-container">
          <div class="agent-step" id="step-1">
            <span class="agent-icon">🔍</span>
            <span class="agent-name">Decomposer Agent</span>
            <span class="agent-status-text">⏳ Starting analysis...</span>
          </div>
          <div class="agent-step" id="step-2">
            <span class="agent-icon">🔬</span>
            <span class="agent-name">Critique Agent</span>
            <span class="agent-status-text">⏸️ Waiting for breakdown...</span>
          </div>
          <div class="agent-step" id="step-3">
            <span class="agent-icon">🧠</span>
            <span class="agent-name">Synthesis Agent</span>
            <span class="agent-status-text">⏸️ Waiting for critique...</span>
          </div>
          <div class="agent-step" id="step-4">
            <span class="agent-icon">📝</span>
            <span class="agent-name">Report Formatter</span>
            <span class="agent-status-text">⏸️ Waiting for synthesis...</span>
          </div>
        </div>
        <div class="pipeline-note">
          <small>This process involves multiple AI agents working together to create a comprehensive research report. Each agent has a specific role in analyzing, critiquing, and synthesizing information from your knowledge base.</small>
        </div>
        <div class="pipeline-timer">
          <small>⏱️ Processing time: <span id="pipeline-timer">0s</span></small>
        </div>
      </div>
    `;
    
    bubble.innerHTML = progressHtml;
    msgDiv.appendChild(avatar);
    msgDiv.appendChild(bubble);
    chatArea.appendChild(msgDiv);
    chatArea.scrollTop = chatArea.scrollHeight;
    
    // Start timer
    startPipelineTimer();
    
    console.log('Pipeline progress displayed');
  }

  // Helper: start pipeline timer
  function startPipelineTimer() {
    const startTime = Date.now();
    const timerElement = document.getElementById('pipeline-timer');
    
    if (timerElement) {
      const timer = setInterval(() => {
        const elapsed = Math.floor((Date.now() - startTime) / 1000);
        timerElement.textContent = `${elapsed}s`;
      }, 1000);
      
      // Store timer ID for cleanup
      window.pipelineTimer = timer;
    }
  }

  // Helper: stop pipeline timer
  function stopPipelineTimer() {
    if (window.pipelineTimer) {
      clearInterval(window.pipelineTimer);
      window.pipelineTimer = null;
    }
  }

  // Helper: update pipeline progress
  function updatePipelineStep(stepNumber, status, details = '') {
    const stepElement = document.getElementById(`step-${stepNumber}`);
    console.log(`Updating step ${stepNumber}:`, status, details, 'Element found:', !!stepElement);
    
    if (stepElement) {
      const statusElement = stepElement.querySelector('.agent-status-text');
      if (statusElement) {
        if (status === 'working') {
          statusElement.innerHTML = '⏳ ' + details;
          stepElement.classList.add('active');
          console.log(`Step ${stepNumber} marked as working`);
        } else if (status === 'completed') {
          statusElement.innerHTML = '✅ ' + details;
          stepElement.classList.add('completed');
          console.log(`Step ${stepNumber} marked as completed`);
        }
      } else {
        console.error(`Status element not found for step ${stepNumber}`);
      }
    } else {
      console.error(`Step element ${stepNumber} not found`);
    }
  }

  // Helper: remove pipeline progress
  function removePipelineProgress() {
    const progress = document.getElementById('pipeline-progress');
    if (progress) progress.remove();
    stopPipelineTimer(); // Stop timer when progress is removed
  }

  // Character count functionality
  function updateCharCount() {
    if (charCount && userInput) {
      const count = userInput.value.length;
      charCount.textContent = count;
      
      // Change color based on length
      if (count > 1000) {
        charCount.style.color = 'var(--primary-red)';
      } else if (count > 500) {
        charCount.style.color = 'var(--accent-warning)';
      } else {
        charCount.style.color = 'var(--text-muted)';
      }
    }
  }

  // Fetch available Ollama models from local server
  async function fetchModels() {
    try {
      const res = await fetch('http://localhost:11434/api/tags');
      const data = await res.json();
      if (data && data.models) {
        console.log('Available models from Ollama:', data.models.map(m => m.name));
        modelSelect.innerHTML = '';
        let defaultModelFound = false;
        
        // First, add gemma34b as the default if it exists
        data.models.forEach(m => {
          const opt = document.createElement('option');
          opt.value = m.name;
          opt.textContent = m.name;
          if (m.name === 'gemma34b') {
            opt.selected = true;
            defaultModelFound = true;
            console.log('✅ Found gemma34b, setting as default');
          }
          modelSelect.appendChild(opt);
        });
        
        // If gemma34b wasn't found, add it as the first option and select it
        if (!defaultModelFound) {
          console.log('⚠️ gemma34b not found in Ollama models, adding as default option');
          const defaultOpt = document.createElement('option');
          defaultOpt.value = 'gemma34b';
          defaultOpt.textContent = 'Gemma 34B (Default)';
          defaultOpt.selected = true;
          modelSelect.insertBefore(defaultOpt, modelSelect.firstChild);
        }
        
        console.log('Final model select value:', modelSelect.value);
      }
    } catch {
      // fallback: add default
      modelSelect.innerHTML = '<option value="gemma34b" selected>Gemma 34B (Default)</option>';
    }
  }

  // Initialize models on load
  fetchModels();
  
  // Global function for manual refresh
  window.refreshModels = function() {
    console.log('🔄 Manual model refresh requested');
    fetchModels();
  };
  
  // Also set a fallback default after a short delay to ensure it's set
  setTimeout(() => {
    if (modelSelect.value !== 'gemma34b') {
      console.log('🔄 Setting fallback default model to gemma34b');
      modelSelect.value = 'gemma34b';
    }
  }, 1000);
  
  // Force refresh models and set default after page load
  window.addEventListener('load', () => {
    setTimeout(() => {
      console.log('🔄 Page loaded, ensuring gemma34b is selected');
      if (modelSelect.value !== 'gemma34b') {
        modelSelect.value = 'gemma34b';
        console.log('✅ Forced gemma34b selection');
      }
    }, 500);
  });

  // Chat handling
  async function handleSend(e) {
    e.preventDefault();
    const text = userInput.value.trim();
    if (!text) return;
    
    chatArea.appendChild(createMessage(text, 'user'));
    chatArea.scrollTop = chatArea.scrollHeight;
    userInput.value = '';
    updateCharCount();
    
    if (currentMode === 'team') {
      // Show pipeline progress for team mode
      showPipelineProgress();
      
      // Start with first step working
      updatePipelineStep(1, 'working', 'Breaking down your query into research components...');
    }
    
    try {
      const res = await fetch('/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query: text, model: modelSelect.value, mode: currentMode })
      });
      const data = await res.json();
      
      if (currentMode === 'team') {
        // Update progress based on actual response
        console.log('Team mode response:', data);
        
        if (data.debug_steps && data.debug_steps.length >= 4) {
          console.log('Debug steps found:', data.debug_steps.length);
          
          // Show realistic progress with delays
          setTimeout(() => {
            updatePipelineStep(1, 'completed', 'Query decomposed into research components');
            updatePipelineStep(2, 'working', 'Critically reviewing the breakdown...');
          }, 2000);
          
          setTimeout(() => {
            updatePipelineStep(2, 'completed', 'Breakdown reviewed and improved');
            updatePipelineStep(3, 'working', 'Synthesizing information...');
          }, 4000);
          
          setTimeout(() => {
            updatePipelineStep(3, 'completed', 'Information synthesized');
            updatePipelineStep(4, 'working', 'Formatting final report...');
          }, 6000);
          
          setTimeout(() => {
            updatePipelineStep(4, 'completed', 'Report formatted and ready');
            
            // Wait a moment to show completion, then show final result
            setTimeout(() => {
              removePipelineProgress();
              // Show only the final synthesized answer
              chatArea.appendChild(createMessage(data.answer, 'bot', data.sources));
              
              // Add PDF export button for the final report
              if (data.answer) {
                const pdfBtn = document.createElement('button');
                pdfBtn.textContent = '📄 Download Full Report as PDF';
                pdfBtn.className = 'pdf-btn';
                pdfBtn.onclick = () => {
                  console.log('PDF export clicked, markdown length:', data.answer.length);
                  exportMarkdownToPDF(data.answer);
                };
                chatArea.appendChild(pdfBtn);
                console.log('PDF button added to chat');
              }
              chatArea.scrollTop = chatArea.scrollHeight;
            }, 1000);
          }, 8000);
          
        } else {
          console.log('Debug steps not found or insufficient, fallback mode');
          // Fallback if debug_steps not available
          removePipelineProgress();
          chatArea.appendChild(createMessage(data.answer, 'bot', data.sources));
          if (data.answer) {
            const pdfBtn = document.createElement('button');
            pdfBtn.textContent = '📄 Download Full Report as PDF';
            pdfBtn.className = 'pdf-btn';
            pdfBtn.onclick = () => {
              console.log('PDF export clicked (fallback), markdown length:', data.answer.length);
              exportMarkdownToPDF(data.answer);
            };
            chatArea.appendChild(pdfBtn);
            console.log('PDF button added to chat (fallback)');
          }
          chatArea.scrollTop = chatArea.scrollHeight;
        }
      } else {
        // Quick mode - simple response
        chatArea.appendChild(createMessage(data.answer, 'bot', data.sources));
        chatArea.scrollTop = chatArea.scrollHeight;
      }
    } catch (error) {
      if (currentMode === 'team') {
        removePipelineProgress();
      }
      chatArea.appendChild(createMessage('Error: Could not get response.', 'bot'));
      chatArea.scrollTop = chatArea.scrollHeight;
    }
  }

  // Improved PDF export utility for markdown
  function exportMarkdownToPDF(markdown) {
    try {
      // Convert markdown to HTML
      const html = window.marked ? marked.parse(markdown) : markdown;
      
      // Create a properly formatted HTML document
      const fullHtml = `
        <!DOCTYPE html>
        <html lang="en">
        <head>
          <meta charset="UTF-8">
          <meta name="viewport" content="width=device-width, initial-scale=1.0">
          <title>Research Report</title>
          <style>
            body {
              font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
              line-height: 1.6;
              color: #333;
              max-width: 800px;
              margin: 0 auto;
              padding: 20px;
              background: white;
            }
            h1, h2, h3, h4, h5, h6 {
              color: #2c3e50;
              margin-top: 30px;
              margin-bottom: 15px;
            }
            h1 { font-size: 2.5em; border-bottom: 3px solid #2563eb; padding-bottom: 10px; }
            h2 { font-size: 2em; border-bottom: 2px solid #ecf0f1; padding-bottom: 8px; }
            h3 { font-size: 1.5em; color: #34495e; }
            h4 { font-size: 1.3em; color: #7f8c8d; }
            p { margin-bottom: 15px; text-align: justify; }
            ul, ol { margin-bottom: 15px; padding-left: 30px; }
            li { margin-bottom: 8px; }
            strong, b { color: #2c3e50; }
            em, i { color: #7f8c8d; }
            code { background: #f8f9fa; padding: 2px 6px; border-radius: 4px; font-family: 'Courier New', monospace; }
            pre { background: #f8f9fa; padding: 15px; border-radius: 8px; overflow-x: auto; }
            blockquote { border-left: 4px solid #2563eb; padding-left: 20px; margin: 20px 0; font-style: italic; color: #7f8c8d; }
            table { border-collapse: collapse; width: 100%; margin: 20px 0; }
            th, td { border: 1px solid #ddd; padding: 12px; text-align: left; }
            th { background-color: #f8f9fa; font-weight: bold; }
            .page-break { page-break-before: always; }
            @media print {
              body { margin: 0; padding: 15px; }
              h1, h2, h3, h4, h5, h6 { page-break-after: avoid; }
              p, li { page-break-inside: avoid; }
            }
          </style>
        </head>
        <body>
          ${html}
        </body>
        </html>
      `;
      
      // Create a new window with the formatted content
      const win = window.open('', '_blank');
      win.document.write(fullHtml);
      win.document.close();
      
      // Wait for content to load, then print
      setTimeout(() => {
        win.print();
      }, 500);
      
    } catch (error) {
      console.error('Error generating PDF:', error);
      alert('Error generating PDF. Please try again.');
    }
  }

  // Mode toggle functionality
  let currentMode = localStorage.getItem('chat-mode') || 'quick';

  function updateModeUI() {
    if (modeQuick && modeTeam) {
      if (currentMode === 'quick') {
        modeQuick.classList.add('mode-active');
        modeTeam.classList.remove('mode-active');
      } else {
        modeTeam.classList.add('mode-active');
        modeQuick.classList.remove('mode-active');
      }
    }
  }

  if (modeQuick && modeTeam) {
    updateModeUI();
    modeQuick.onclick = () => {
      currentMode = 'quick';
      localStorage.setItem('chat-mode', currentMode);
      updateModeUI();
    };
    modeTeam.onclick = () => {
      currentMode = 'team';
      localStorage.setItem('chat-mode', currentMode);
      updateModeUI();
    };
  }

  // Attach chat form handler
  if (chatForm && userInput && sendBtn) {
    chatForm.onsubmit = handleSend;
    sendBtn.onclick = handleSend;
    
    console.log('Chat form handlers attached');
  } else {
    console.error('Chat elements not found');
  }

  // Conversation management
  let conversations = JSON.parse(localStorage.getItem('conversations') || '[]');
  let currentConvId = localStorage.getItem('current-conv-id') || null;

  function saveConversations() {
    localStorage.setItem('conversations', JSON.stringify(conversations));
    localStorage.setItem('current-conv-id', currentConvId);
  }

  // Make conversation functions globally accessible
  window.createNewConversation = function() {
    const id = Date.now().toString();
    // Add welcome message as the first message in every new conversation
    const welcomeMsg = createMessage(
      "Welcome! I am the research assistant of Ai movement research center. My job is to help you find information by searching our private collection of local documents, securely and completely offline. How can I assist your research today?",
      'bot',
      []
    );
    const tempDiv = document.createElement('div');
    tempDiv.appendChild(welcomeMsg);
    const conv = { id, title: `Conversation ${conversations.length + 1}`, messages: tempDiv.innerHTML, created: new Date().toLocaleString() };
    conversations.push(conv);
    currentConvId = id;
    chatArea.innerHTML = conv.messages;
    saveConversations();
    renderSidebar();
  };

  function switchConversation(id) {
    const conv = conversations.find(c => c.id === id);
    if (conv) {
      currentConvId = id;
      chatArea.innerHTML = conv.messages;
      saveConversations();
      renderSidebar();
    }
  }

  function saveCurrentConversation() {
    const conv = conversations.find(c => c.id === currentConvId);
    if (conv) {
      conv.messages = chatArea.innerHTML;
      saveConversations();
    }
  }

  // Sidebar rendering
  function renderSidebar() {
    let sidebar = document.getElementById('sidebar');
    let conversationsList = document.getElementById('conversations-list');
    
    if (sidebar && conversationsList) {
      conversationsList.innerHTML = conversations.map(conv => `
        <div class="conversation-item ${conv.id === currentConvId ? 'active' : ''}" data-conv-id="${conv.id}">
          <div class="conversation-content" onclick="switchConversation('${conv.id}')">
            <div class="conversation-title">${conv.title}</div>
            <div class="conversation-date">${conv.created}</div>
          </div>
          <button class="delete-conversation-btn" onclick="deleteConversation('${conv.id}', event)" title="Delete conversation">
            <span class="material-symbols-rounded">close</span>
          </button>
        </div>
      `).join('');
    }
  }

  // Delete conversation function
  function deleteConversation(convId, event) {
    event.stopPropagation(); // Prevent triggering conversation switch
    
    if (confirm('Are you sure you want to delete this conversation? This action cannot be undone.')) {
      // Remove from conversations array
      const convIndex = conversations.findIndex(c => c.id === convId);
      if (convIndex !== -1) {
        conversations.splice(convIndex, 1);
        
        // If we deleted the current conversation, switch to another one
        if (convId === currentConvId) {
          if (conversations.length > 0) {
            currentConvId = conversations[0].id;
            chatArea.innerHTML = conversations[0].messages;
          } else {
            // No conversations left, create a new one
            createNewConversation();
            return; // Early return since createNewConversation calls renderSidebar
          }
        }
        
        // Save and re-render
        saveConversations();
        renderSidebar();
      }
    }
  }

  // Mobile sidebar toggle
  const sidebarToggle = document.getElementById('sidebar-toggle');
  const sidebar = document.getElementById('sidebar');
  
  if (sidebarToggle && sidebar) {
    sidebarToggle.onclick = () => {
      sidebar.classList.toggle('open');
    };
    
    // Close sidebar when clicking outside on mobile
    document.addEventListener('click', (e) => {
      if (window.innerWidth <= 768 && 
          !sidebar.contains(e.target) && 
          !sidebarToggle.contains(e.target)) {
        sidebar.classList.remove('open');
      }
    });
  }

  // Initialize sidebar
  renderSidebar();

  // Load chat history
  function loadChatHistory() {
    if (conversations.length === 0) {
      createNewConversation();
    } else {
      switchConversation(currentConvId || conversations[0].id);
    }
  }

  // Load chat history on page load
  loadChatHistory();

  // Clear chat functionality
  if (clearChatBtn) {
    clearChatBtn.onclick = () => {
      if (confirm('Clear all chat messages?')) {
        chatArea.innerHTML = '';
        // Remove current conversation if empty
        const convIdx = conversations.findIndex(c => c.id === currentConvId);
        if (convIdx !== -1) {
          conversations.splice(convIdx, 1);
          // Switch to another conversation or create new if none left
          if (conversations.length > 0) {
            currentConvId = conversations[0].id;
            chatArea.innerHTML = conversations[0].messages;
          } else {
            createNewConversation();
          }
          saveConversations();
          renderSidebar();
        }
      }
    };
  }

  // Auto-grow textarea and character count
  if (userInput) {
    userInput.addEventListener('input', () => {
      userInput.style.height = 'auto';
      userInput.style.height = userInput.scrollHeight + 'px';
      updateCharCount();
    });
    
    // Submit on Enter (without Shift)
    userInput.addEventListener('keydown', e => {
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        sendBtn.click();
      }
    });
  }
  
  // Save after every message
  const origCreateMessage = createMessage;
  createMessage = function(...args) {
    const msg = origCreateMessage.apply(this, args);
    setTimeout(() => {
      saveCurrentConversation();
    }, 0);
    return msg;
  };

  // Initialize file management
  setupFileUpload();
  fetchFileList();

  console.log('App.js initialization completed successfully');

} catch (error) {
  console.error('Error in app.js:', error);
}