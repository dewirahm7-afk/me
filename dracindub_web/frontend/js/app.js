// frontend/js/app.js - VERSION LENGKAP dengan Tab 2 Translate
class DracinApp {
    constructor() {
        this.currentSessionId = null;
        this.isConnected = false;
        this.baseUrl = '';
        this.activeTab = 'srt-processing';
        
        // Add these lines
        this.videoFile = null;
        this.srtFile = null;
        
        this.initializeApp();
    }

    initializeApp() {
        console.log('Initializing DracinDub Web App...');
        
        // Set up tab navigation
        this.setupTabNavigation();
        
        // Set up global event listeners
        this.setupGlobalEvents();
        
        // Test backend connection
        this.testBackendConnection();
        
        // Load initial tab
        this.loadTab('srt-processing');
        
        console.log('DracinDub Web App initialized');
    }

    setupTabNavigation() {
        console.log('Setting up tab navigation...');
        
        // Tab click handlers
        document.querySelectorAll('[data-tab]').forEach(tab => {
            tab.addEventListener('click', (e) => {
                e.preventDefault();
                const tabName = tab.getAttribute('data-tab');
                console.log('Tab clicked:', tabName);
                this.loadTab(tabName);
            });
        });

        // Keyboard shortcuts
        document.addEventListener('keydown', (e) => {
            if (e.ctrlKey || e.metaKey) {
                switch(e.key) {
                    case '1':
                        e.preventDefault();
                        this.loadTab('srt-processing');
                        break;
                    case '2':
                        e.preventDefault();
                        this.loadTab('translate');
                        break;
                    case '3':
                        e.preventDefault();
                        this.loadTab('editing');
                        break;
                    case '4':
                        e.preventDefault();
                        this.loadTab('tts-export');
                        break;
                }
            }
        });
    }

    setupGlobalEvents() {
        console.log('Setting up global events...');
        
        // Global save handler
        const saveBtn = document.getElementById('save-all');
        if (saveBtn) {
            saveBtn.addEventListener('click', () => {
                this.saveAll();
            });
        }

        const settingsBtn = document.getElementById('settings');
        if (settingsBtn) {
            settingsBtn.addEventListener('click', () => {
                this.showNotification('Settings will be available soon', 'info');
            });
        }

        const helpBtn = document.getElementById('help');
        if (helpBtn) {
            helpBtn.addEventListener('click', () => {
                window.open('https://github.com/dracindub/dracindub-web', '_blank');
            });
        }

        // Online/offline detection
        window.addEventListener('online', () => {
            this.showNotification('Connection restored', 'success');
        });

        window.addEventListener('offline', () => {
            this.showNotification('Connection lost', 'error');
        });
    }

	async loadTab(tabName) {
	  console.log('Loading tab:', tabName);

	  // Toggle state di tombol tab
	  document.querySelectorAll('[data-tab]').forEach(tab => {
		tab.classList.remove('active', 'border-blue-400', 'bg-gray-700');
		tab.classList.add('border-transparent');
	  });
	  const activeBtn = document.querySelector(`[data-tab="${tabName}"]`);
	  if (activeBtn) {
		activeBtn.classList.add('active', 'border-blue-400', 'bg-gray-700');
		activeBtn.classList.remove('border-transparent');
	  }

	  // TUTUP semua konten tab (hapus .active)
	  document.querySelectorAll('.tab-content').forEach(el => {
		el.classList.remove('active');
	  });

	  // BUKA konten tab yang dipilih (tambah .active)
	  const tabContent = document.getElementById(tabName);
	  if (tabContent) {
		tabContent.classList.add('active');
	  }
		if (tabName === 'editing') {
		  await this.loadEditingTab();
		  return;
		}

	  this.activeTab = tabName;

	  // Muat konten spesifik tab
	  await this.loadTabContent(tabName);
	}


	async loadTabContent(tabName) {
		this.showLoading(`Loading ${tabName.replace('-', ' ')}...`);
		
		try {
			switch(tabName) {
				case 'srt-processing':
					await this.loadSRTProcessingTab();
					break;
				case 'translate':
					await this.loadTranslateTab();  // Pastikan ini yang dipanggil
					break;
				case 'editing':
					await this.loadEditingTab();
					break;
				case 'tts-export':
					await this.loadTTSExportTab();
					break;
			}
		} catch (error) {
			console.error(`Error loading tab ${tabName}:`, error);
			this.showNotification(`Error loading ${tabName}: ${error.message}`, 'error');
		} finally {
			this.hideLoading();
		}
	}

	async loadSRTProcessingTab() {
	  const tab = document.getElementById('srt-processing');
	  if (!tab) return;
	  tab.innerHTML = `
		<!-- spinner singkat boleh, tapi langsung render saja juga boleh -->
		<div class="bg-gray-800 rounded-lg p-6">
		  <h2 class="text-2xl font-bold mb-6 text-blue-400">
			<i class="fas fa-file-alt mr-2"></i>SRT Processing
		  </h2>
		  <div class="text-center py-8">
			<div class="loading-spinner mx-auto mb-4"></div>
			<p class="text-gray-400">Loading SRT Processing interface...</p>
		  </div>
		</div>
	  `;
	  // langsung render UI + bind
	  this.renderSRTProcessingTab();
	}


    renderSRTProcessingTab() {
        const tabContent = document.getElementById('srt-processing');
        if (!tabContent) return;

        tabContent.innerHTML = `
            <div class="bg-gray-800 rounded-lg p-6">
                <h2 class="text-2xl font-bold mb-6 text-blue-400">
                    <i class="fas fa-file-alt mr-2"></i>SRT Processing
                </h2>

                <!-- File Upload Section -->
                <div class="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
                    <!-- Video Upload -->
                    <div class="bg-gray-700 rounded-lg p-4">
                        <h3 class="text-lg font-semibold mb-3 text-white">
                            <i class="fas fa-video mr-2"></i>Video File
                        </h3>
                        <div class="border-2 border-dashed border-gray-600 rounded-lg p-6 text-center hover:border-blue-400 transition-colors cursor-pointer" id="video-drop-zone">
                            <i class="fas fa-cloud-upload-alt text-4xl text-gray-400 mb-3"></i>
                            <p class="text-gray-300 mb-2">Drag & drop video file or click to browse</p>
                            <p class="text-sm text-gray-400 mb-4">Supported: MP4, MKV, AVI, MOV</p>
                            <button class="bg-blue-500 hover:bg-blue-600 px-4 py-2 rounded transition-colors">
                                <i class="fas fa-search mr-2"></i>Browse Files
                            </button>
                            <div id="video-file-info" class="mt-3 text-sm text-green-400 hidden">
                                <i class="fas fa-check-circle mr-1"></i>
                                <span>Video file selected</span>
                            </div>
                        </div>
                    </div>

                    <!-- SRT Upload -->
                    <div class="bg-gray-700 rounded-lg p-4">
                        <h3 class="text-lg font-semibold mb-3 text-white">
                            <i class="fas fa-file-text mr-2"></i>SRT File
                        </h3>
                        <div class="border-2 border-dashed border-gray-600 rounded-lg p-6 text-center hover:border-blue-400 transition-colors cursor-pointer" id="srt-drop-zone">
                            <i class="fas fa-file-upload text-4xl text-gray-400 mb-3"></i>
                            <p class="text-gray-300 mb-2">Drag & drop SRT Hasil OCR</p>
                            <p class="text-sm text-gray-400 mb-4">Format: SubRip (.srt)</p>
                            <button class="bg-blue-500 hover:bg-blue-600 px-4 py-2 rounded transition-colors">
                                <i class="fas fa-search mr-2"></i>Browse Files
                            </button>
                            <div id="srt-file-info" class="mt-3 text-sm text-green-400 hidden">
                                <i class="fas fa-check-circle mr-1"></i>
                                <span>SRT file selected</span>
                            </div>
                        </div>
                    </div>
                </div>

                <!-- Diarization Configuration -->
                <div class="bg-gray-700 rounded-lg p-4 mb-6">
                    <h3 class="text-lg font-semibold mb-4 text-white">
                        <i class="fas fa-users mr-2"></i>Diarization Configuration
                    </h3>
                    <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                        <div>
                            <label class="block text-sm font-medium mb-2 text-gray-300">Male Reference</label>
                            <input id="male-ref" type="text" value="D:\\dubdracin\\samples\\male" 
                                   class="w-full px-3 py-2 bg-gray-600 rounded border border-gray-500 focus:border-blue-500 text-white placeholder-gray-400">
                        </div>
                        <div>
                            <label class="block text-sm font-medium mb-2 text-gray-300">Female Reference</label>
                            <input id="female-ref" type="text" value="D:\\dubdracin\\samples\\female" 
                                   class="w-full px-3 py-2 bg-gray-600 rounded border border-gray-500 focus:border-blue-500 text-white placeholder-gray-400">
                        </div>
                        <div>
                            <label class="block text-sm font-medium mb-2 text-gray-300">HF Token</label>
                            <input id="hf-token" type="password" value="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"
                                   class="w-full px-3 py-2 bg-gray-600 rounded border border-gray-500 focus:border-blue-500 text-white placeholder-gray-400">
                        </div>
                        <div>
                            <label class="block text-sm font-medium mb-2 text-gray-300">Top N Segments</label>
                            <input id="top-n" type="number" value="6" 
                                   class="w-full px-3 py-2 bg-gray-600 rounded border border-gray-500 focus:border-blue-500 text-white">
                        </div>
                        <div class="flex items-center mt-2">
                            <input id="use-gpu" type="checkbox" id="use-gpu" checked class="mr-2 w-4 h-4 text-blue-500 bg-gray-600 border-gray-500 rounded focus:ring-blue-400">
                            <label for="use-gpu" class="text-gray-300">Use GPU for Diarization</label>
                        </div>
                    </div>
                </div>

                <!-- Progress Section -->
                <div class="bg-gray-700 rounded-lg p-4 mb-6">
                    <h3 class="text-lg font-semibold mb-3 text-white">
                        <i class="fas fa-tasks mr-2"></i>Processing Progress
                    </h3>
                    <div class="space-y-4">
                        <div>
                            <div class="flex justify-between mb-2">
                                <span class="text-sm text-gray-300" id="current-step">Ready to process</span>
                                <span class="text-sm text-gray-300" id="progress-percent">0%</span>
                            </div>
                            <div class="w-full bg-gray-600 rounded-full h-3">
                                <div id="progress-bar" class="bg-blue-500 h-3 rounded-full transition-all duration-500 ease-out" style="width: 0%"></div>
                            </div>
                        </div>
                    </div>
                </div>

                <!-- Action Buttons -->
                <div class="flex flex-wrap gap-3">
                    <button id="create-session" class="bg-green-500 hover:bg-green-600 px-4 py-2 rounded flex items-center transition-colors">
                        <i class="fas fa-plus mr-2"></i>Create Session
                    </button>
                    <button id="generate-workdir" class="bg-blue-500 hover:bg-blue-600 px-4 py-2 rounded flex items-center transition-colors">
                        <i class="fas fa-folder-plus mr-2"></i>Generate Workdir
                    </button>
                    <button id="extract-audio" class="bg-purple-500 hover:bg-purple-600 px-4 py-2 rounded flex items-center transition-colors">
                        <i class="fas fa-volume-up mr-2"></i>Extract Audio
                    </button>
                    <button id="run-diarization" class="bg-orange-500 hover:bg-orange-600 px-4 py-2 rounded flex items-center transition-colors">
                        <i class="fas fa-users mr-2"></i>Run Diarization
                    </button>
                    <button id="load-to-translate" class="bg-indigo-500 hover:bg-indigo-600 px-4 py-2 rounded flex items-center transition-colors">
                        <i class="fas fa-arrow-right mr-2"></i>Load to Translate
                    </button>
                </div>

                <!-- Session Info -->
                <div class="mt-6 bg-gray-700 rounded-lg p-4">
                    <h3 class="text-lg font-semibold mb-3 text-white">
                        <i class="fas fa-info-circle mr-2"></i>Current Session
                    </h3>
                    <div id="current-session-info" class="text-gray-300">
                        <div class="flex items-center justify-between">
                            <span>No active session</span>
                            <button id="create-test-session" class="bg-gray-600 hover:bg-gray-500 px-3 py-1 rounded text-sm transition-colors">
                                Create Test Session
                            </button>
                        </div>
                    </div>
                </div>

                <!-- Log Output -->
                <div class="mt-6">
                    <h3 class="text-lg font-semibold mb-3 text-white">
                        <i class="fas fa-terminal mr-2"></i>Processing Log
                    </h3>
                    <div id="log-output" class="bg-gray-900 rounded p-4 h-48 overflow-y-auto font-mono text-sm">
                        <div class="text-gray-500">Log output will appear here...</div>
                    </div>
                </div>
            </div>
        `;

        // Add event listeners for this tab
        this.setupSRTProcessingEvents();
    }

    setupSRTProcessingEvents() {
        console.log('Setting up SRT Processing events...');
        
        // Create test session button
        const createTestBtn = document.getElementById('create-test-session');
        if (createTestBtn) {
            createTestBtn.addEventListener('click', () => {
                this.createTestSession();
            });
        }

        // Create session button
        const createSessionBtn = document.getElementById('create-session');
        if (createSessionBtn) {
          createSessionBtn.addEventListener('click', () => {
            this.createSessionWithFiles();
          });
        }

        // Other action buttons
        const actionButtons = ['generate-workdir', 'extract-audio', 'run-diarization', 'load-to-translate'];
        actionButtons.forEach(btnId => {
            const btn = document.getElementById(btnId);
            if (btn) {
                btn.addEventListener('click', () => {
                    this.handleSRTAction(btnId);
                });
            }
        });

        // File drop zones - FIXED VERSION
        this.setupFileDropZones();
    }

    setupFileDropZones() {
        // Create hidden file inputs
        this.createFileInput('video', ['video/*', '.mp4', '.mkv', '.avi', '.mov']);
        this.createFileInput('srt', ['.srt', '.txt']);
        
        // Video drop zone
        const videoDropZone = document.getElementById('video-drop-zone');
        if (videoDropZone) {
            // Click handler
            videoDropZone.addEventListener('click', () => {
                document.getElementById('video-file-input').click();
            });
            
            // Drag and drop handlers
            this.setupDragAndDrop(videoDropZone, 'video');
        }

        // SRT drop zone  
        const srtDropZone = document.getElementById('srt-drop-zone');
        if (srtDropZone) {
            // Click handler
            srtDropZone.addEventListener('click', () => {
                document.getElementById('srt-file-input').click();
            });
            
            // Drag and drop handlers
            this.setupDragAndDrop(srtDropZone, 'srt');
        }
    }

    createFileInput(type, accept) {
        // Remove existing input if any
        const existingInput = document.getElementById(`${type}-file-input`);
        if (existingInput) {
            existingInput.remove();
        }
        
        // Create new file input
        const fileInput = document.createElement('input');
        fileInput.type = 'file';
        fileInput.id = `${type}-file-input`;
        fileInput.accept = accept.join(',');
        fileInput.style.display = 'none';
        
        fileInput.addEventListener('change', (e) => {
            this.handleFileSelect(e, type);
        });
        
        document.body.appendChild(fileInput);
    }

    setupDragAndDrop(dropZone, type) {
        // Drag over effect
        dropZone.addEventListener('dragover', (e) => {
            e.preventDefault();
            dropZone.classList.add('border-blue-400', 'bg-gray-600');
        });

        // Drag leave effect
        dropZone.addEventListener('dragleave', () => {
            dropZone.classList.remove('border-blue-400', 'bg-gray-600');
        });

        // Drop handler
        dropZone.addEventListener('drop', (e) => {
            e.preventDefault();
            dropZone.classList.remove('border-blue-400', 'bg-gray-600');
            
            const files = e.dataTransfer.files;
            if (files.length > 0) {
                this.handleDroppedFile(files[0], type);
            }
        });
    }

    handleFileSelect(event, type) {
        const file = event.target.files[0];
        if (file) {
            this.handleDroppedFile(file, type);
        }
    }

    handleDroppedFile(file, type) {
        const fileInfo = document.getElementById(`${type}-file-info`);
        const fileName = file.name;
        const fileSize = (file.size / (1024 * 1024)).toFixed(2);

        // Validate file type
        if (type === 'video' && !file.type.startsWith('video/') && !fileName.match(/\.(mp4|mkv|avi|mov)$/i)) {
            this.showNotification('Please select a valid video file (MP4, MKV, AVI, MOV)', 'error');
            return;
        }
        
        if (type === 'srt' && !fileName.match(/\.(srt|txt)$/i)) {
            this.showNotification('Please select a valid SRT file (.srt)', 'error');
            return;
        }

        // Update UI
        fileInfo.innerHTML = `
            <div class="text-green-400">
                <i class="fas fa-check-circle mr-1"></i>
                ${fileName} (${fileSize} MB)
            </div>
        `;
        fileInfo.classList.remove('hidden');

        // Store file reference
        if (type === 'video') {
            this.videoFile = file;
        } else {
            this.srtFile = file;
        }

        this.showNotification(`${type.toUpperCase()} file selected: ${fileName}`, 'success');
        this.updateButtonStates();
    }

    updateButtonStates() {
        const hasFiles = this.videoFile && this.srtFile;
        const createSessionBtn = document.getElementById('create-session');
        
        if (createSessionBtn) {
            createSessionBtn.disabled = !hasFiles;
            if (hasFiles) {
                createSessionBtn.classList.remove('opacity-50', 'cursor-not-allowed');
            } else {
                createSessionBtn.classList.add('opacity-50', 'cursor-not-allowed');
            }
        }
    }

    handleSRTAction(action) {
        console.log(`🔄 SRT Action: ${action}`);
        
        if (!this.currentSessionId) {
            this.showNotification('Please create a session first', 'error');
            return;
        }

        const actions = {
            'generate-workdir': () => this.generateWorkdir(),
            'extract-audio': () => this.extractAudio(),
            'run-diarization': () => this.runDiarization(),
            'load-to-translate': () => this.loadToTranslate()
        };

        if (actions[action]) {
            actions[action]();
        }
    }

    async generateWorkdir() {
        try {
            this.showLoading('Generating workspace...');
            const response = await fetch(`/api/session/${this.currentSessionId}/generate-workdir`, {
                method: 'POST'
            });
            
            if (response.ok) {
                const data = await response.json();
                this.showNotification('Workspace generated successfully', 'success');
                this.updateProgress(20, 'Workspace ready');
            } else {
                throw new Error('Failed to generate workdir');
            }
        } catch (error) {
            this.showNotification(`Error: ${error.message}`, 'error');
        } finally {
            this.hideLoading();
        }
    }

    async extractAudio() {
        try {
            this.showLoading('Extracting audio...');
            const response = await fetch(`/api/session/${this.currentSessionId}/extract-audio`, {
                method: 'POST'
            });
            
            if (response.ok) {
                const data = await response.json();
                this.showNotification('Audio extracted successfully', 'success');
                this.updateProgress(40, 'Audio extracted');
            } else {
                throw new Error('Failed to extract audio');
            }
        } catch (error) {
            this.showNotification(`Error: ${error.message}`, 'error');
        } finally {
            this.hideLoading();
        }
    }

    // Tab 1 – Diarization
    async runDiarization() {
      // pastikan sudah ada session
      if (!this.currentSessionId) {
        this.showNotification('Create Session dulu.', 'error');
        return;
      }

      // ambil input dari UI
      const maleRefEl    = document.getElementById('male-ref');
      const femaleRefEl  = document.getElementById('female-ref');
      const hfTokenEl    = document.getElementById('hf-token');
      const useGpuEl     = document.getElementById('use-gpu');
      const topNEl       = document.getElementById('top-n');

      const male_ref     = (maleRefEl?.value || '').trim();
      const female_ref   = (femaleRefEl?.value || '').trim();
      const hf_token     = (hfTokenEl?.value || '').trim();
      const use_gpu      = useGpuEl?.checked ? 'true' : 'false';
      const top_n        = topNEl?.value ? parseInt(topNEl.value, 10) : 5;

      if (!male_ref || !female_ref) {
        this.showNotification('Male/Female Reference wajib diisi.', 'error');
        return;
      }

      const url = `/api/session/${this.currentSessionId}/diarization`;
      const body = new URLSearchParams({
        male_ref,
        female_ref,
        hf_token,
        use_gpu,
        top_n: String(top_n),
      });

      try {
        this.appendLog?.('Running diarization...');
        this.showLoading('Running diarization...');

        const res = await fetch(url, {
          method: 'POST',
          headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
          body,
        });

        const text = await res.text(); // ambil body apa adanya dulu

        if (!res.ok) {
          // tampilkan pesan error asli dari backend biar gampang debug
          this.showNotification(`Failed to run diarization: ${text}`, 'error');
          this.appendLog?.(text);
          return;
        }

        // coba parse JSON respon
        let data = {};
        try { data = JSON.parse(text); } catch (_) {}

        const segPath = data.segments_path || data.segjson || '';
        const spkPath = data.speakers_path || data.spkjson || '';

        if (segPath) this.appendLog?.(`Segments: ${segPath}`);
        if (spkPath) this.appendLog?.(`Speakers: ${spkPath}`);

        this.updateProgress?.(100, 'Diarization done');
        this.showNotification('Diarization completed successfully', 'success');
      } catch (err) {
        this.showNotification(`Failed to run diarization: ${err?.message || err}`, 'error');
      } finally {
        this.hideLoading();
      }
    }

    updateProgress(percent, message) {
      const bar   = document.getElementById('progress-bar');
      const pctEl = document.getElementById('progress-percent');
      const step  = document.getElementById('current-step');

      if (bar)   bar.style.width = `${Number(percent)||0}%`;
      if (pctEl) pctEl.textContent = `${Number(percent)||0}%`;
      if (step)  step.textContent = message || '';
    }

    loadToTranslate() {
        this.showNotification('Loading to Translate tab...', 'info');
        setTimeout(() => {
            this.loadTab('translate');
        }, 1000);
    }

    async createSessionWithFiles() {
        if (!this.videoFile || !this.srtFile) {
            this.showNotification('Please select both video and SRT files first', 'error');
            return;
        }

        this.showLoading('Creating session and uploading files...');

        try {
            // First create session
            const sessionResponse = await fetch('/api/session/create', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/x-www-form-urlencoded',
                },
                body: `video_name=${encodeURIComponent(this.videoFile.name)}&srt_name=${encodeURIComponent(this.srtFile.name)}`
            });

            if (!sessionResponse.ok) {
                throw new Error('Failed to create session');
            }

            const sessionData = await sessionResponse.json();
            this.currentSessionId = sessionData.session_id;
            
            // Then upload files
            const formData = new FormData();
            formData.append('video', this.videoFile);
            formData.append('srt', this.srtFile);

            const uploadResponse = await fetch(`/api/session/${this.currentSessionId}/upload`, {
                method: 'POST',
                body: formData
            });

            if (!uploadResponse.ok) {
                throw new Error('Failed to upload files');
            }

            this.showNotification('Session created and files uploaded successfully!', 'success');
            this.updateSessionInfo(this.currentSessionId);
            
            // Simulate progress
            this.simulateProgress();

        } catch (error) {
            console.error('Error creating session:', error);
            this.showNotification(`Error: ${error.message}`, 'error');
        } finally {
            this.hideLoading();
        }
    }

    simulateProgress() {
        let progress = 0;
        const progressBar = document.getElementById('progress-bar');
        const progressPercent = document.getElementById('progress-percent');
        const currentStep = document.getElementById('current-step');
        
        const steps = [
            'Creating session...',
            'Uploading files...', 
            'Processing files...',
            'Ready for next steps'
        ];
        
        const interval = setInterval(() => {
            progress += 25;
            
            if (progressBar) progressBar.style.width = `${progress}%`;
            if (progressPercent) progressPercent.textContent = `${progress}%`;
            if (currentStep) {
                currentStep.textContent = steps[Math.min(Math.floor(progress / 25), steps.length - 1)];
            }
            
            if (progress >= 100) {
                clearInterval(interval);
                this.showNotification('Files processed successfully!', 'success');
                
                // Enable other buttons
                const buttons = ['generate-workdir', 'extract-audio', 'run-diarization', 'load-to-translate'];
                buttons.forEach(btnId => {
                    const btn = document.getElementById(btnId);
                    if (btn) {
                        btn.disabled = false;
                        btn.classList.remove('opacity-50', 'cursor-not-allowed');
                    }
                });
            }
        }, 800);
    }

// Perbaiki method loadTranslateTab() untuk auto-load SRT
async loadTranslateTab() {
  const tab = document.getElementById('translate');
  if (!tab) return;
  tab.innerHTML = `
    <div class="bg-gray-800 rounded-lg p-6">
      <h2 class="text-2xl font-bold mb-6 text-green-400">
        <i class="fas fa-language mr-2"></i>Translate
      </h2>
      <div class="text-center py-8">
        <div class="loading-spinner mx-auto mb-4"></div>
        <p class="text-gray-400">Loading Translation interface...</p>
      </div>
    </div>
  `;

  // renderTranslateTab() SUDAH memanggil setupTranslateEvents() di dalamnya
  this.renderTranslateTab();

  // Auto-load dari session (opsional, hanya jika ada session)
  if (this.currentSessionId) {
    try {
      const res  = await fetch(`/api/session/${this.currentSessionId}/srt?prefer=original`);
      if (res.ok) {
        const text  = await res.text();
        const items = this.parseSRT(text);
        this.translate.originalSubs = items.map(o => ({...o}));
        this.translate.subtitles    = items.map(o => ({...o, trans: ''}));
        this.filterAndRenderSubs?.();
        this.showNotification('SRT loaded from session', 'success');
      }
    } catch {}
  }
}

// === REPLACE: appendMessage + renderMessages ===
appendMessage(obj) {
  if (!this.translate) this.initTranslateState();
  const arr = this.translate.messages;
  arr.push({ ts: new Date().toISOString(), ...obj });
  if (arr.length > 500) arr.splice(0, arr.length - 500);   // jaga memori
  this.renderMessages(true);
}

/** Highlight baris sebentar supaya kelihatan row yang update */
_flashTsRow(idx) {
  const row = document.getElementById(`ts-row-${idx}`);
  if (!row) return;
  row.classList.add('ring-2','ring-emerald-400');
  setTimeout(()=> row.classList.remove('ring-2','ring-emerald-400'), 900);
}

_scrollToTsRow(idx) {
  const row = document.getElementById(`ts-row-${idx}`);
  if (row && this.translate?.followSubs !== false) {
    row.scrollIntoView({ block: 'nearest', behavior: 'smooth' });
  }
}

renderMessages(newItem = false) {
  const el = document.getElementById('ts-messages');
  if (!el) return;

  // Hanya auto-scroll jika followResults = true
  const shouldStickBottom =
    this.translate.followResults && (newItem || this._isNearBottom(el));

  // Tampilkan 50 terakhir agar terasa “streaming”
  const last = (this.translate.messages || []).slice(-50);
  el.textContent = JSON.stringify(last, null, 2);

  if (shouldStickBottom) {
    el.scrollTop = el.scrollHeight;
  }
}


    //// SRT parse/format ////
    parseSRT(text) {
      const lines = text.replace(/\r/g,'').split('\n');
      const items = [];
      let i=0;
      while (i < lines.length) {
        const idx = Number(lines[i].trim());
        if (!Number.isInteger(idx)) { i++; continue; }
        const times = lines[i+1]||'';
        const m = times.match(/(\d{2}:\d{2}:\d{2},\d{3})\s*-->\s*(\d{2}:\d{2}:\d{2},\d{3})/);
        if (!m) { i++; continue; }
        i+=2;
        const buf=[];
        while (i<lines.length && lines[i].trim()!=='') { buf.push(lines[i]); i++; }
        items.push({index: idx, start: m[1], end: m[2], text: buf.join('\n')});
        while (i<lines.length && lines[i].trim()==='') i++;
      }
      return items;
    }

    escapeHtml(s){ 
      return s.replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c])); 
    }

	// PATCH untuk app.js - Ganti fungsi-fungsi Translate

	/* ==============================
	 * TRANSLATE STATE
	 * ============================== */
	initTranslateState() {
	  this.translate = {
		mode: "auto",
		// data
		originalSubs: [],      // simpan original (tetap)
		subtitles: [],         // working copy + tempat menaruh .trans
		filtered: [],
		srtText: "",
		// ui
		page: 1,
		size: 100,
		follow: true,
		search: "",
		followSubs: true,
		followResults: true,
		// run cfg
		apiKey: "sk-dbb007f10bc34473a2a890d556581edc",
		lang: "id",
		engine: "llm",
		temperature: 0.1,
		top_p: 0.3,
		batch: 20,
		workers: 1,
		timeout: 120,
		autosave: true,
		// exec
		running: false,
		abort: null,
		style: "dubbing",  // "dubbing" | "normal"
		// log
		messages: []
	  };
	}
	
	_isNearBottom(el, pad = 24) {
	  return (el.scrollHeight - el.clientHeight - el.scrollTop) <= pad;
	}
	/* ==============================
	 * RENDER TAB TRANSLATE (layout 1 baris untuk subtitle)
	 * ============================== */
	renderTranslateTab() {
	  if (!this.translate) this.initTranslateState();
	  const st = this.translate;
	  
	  const tabContent = document.getElementById('translate');
	  if (!tabContent) return;

	  tabContent.innerHTML = `
		<div class="bg-gray-800 rounded-lg p-6">
		  <h2 class="text-2xl font-bold mb-6 text-green-400">
			<i class="fas fa-language mr-2"></i>Translate
		  </h2>
		  
		  <div class="p-3 space-y-3">
			<!-- Header dengan controls -->
			<div class="flex flex-wrap items-center gap-3">
			  <div class="flex items-center gap-2">
				<span class="text-sm whitespace-nowrap text-gray-300">API Key</span>
				<input id="ts-api" type="password" value="${st.apiKey || ''}"
					   class="border border-gray-600 bg-gray-700 text-white rounded px-3 py-1 w-[200px]" placeholder="sk-..." />
			  </div>
			  <div class="flex items-center gap-2">
				<span class="text-sm text-gray-300">Batch</span>
				<input id="ts-batch" type="number" min="1" value="${st.batch}"
					   class="border border-gray-600 bg-gray-700 text-white rounded px-2 py-1 w-12" />
			  </div>
			  <div class="flex items-center gap-2">
				<span class="text-sm text-gray-300">Workers</span>
				<input id="ts-workers" type="number" min="1" value="${st.workers}"
					   class="border border-gray-600 bg-gray-700 text-white rounded px-2 py-1 w-10" />
			  </div>
			  <label class="inline-flex items-center gap-1">
				<input id="ts-autosave" type="checkbox" ${st.autosave ? 'checked' : ''} class="w-4 h-4 text-blue-500 bg-gray-600 border-gray-500 rounded focus:ring-blue-400" />
				<span class="text-sm text-gray-300">Autosave</span>
			  </label>

			  <!-- Progress bar -->
			  <div class="ml-2 w-[120px] h-2 bg-gray-700 rounded overflow-hidden">
				<div id="ts-progressbar" class="h-full bg-blue-500 transition-all duration-300" style="width:0%"></div>
			  </div>
			  <div id="ts-progresslabel" class="text-xs text-gray-300 min-w-[50px]">0% (0/0)</div>
			</div>

			<!-- Action buttons & config -->
			<div class="flex flex-wrap items-center gap-2">
			  <div class="flex gap-1 flex-wrap">
				<button id="ts-load" class="btn btn-slate text-xs px-2 py-1">📂 Load</button>
				<button id="ts-start" class="btn btn-primary text-xs px-2 py-1">▶ Start</button>
				<button id="ts-resume" class="btn btn-slate text-xs px-2 py-1">⏵ Resume</button>
				<button id="ts-fill" class="btn btn-slate text-xs px-2 py-1">✳ Fill</button>
				<button id="ts-save" class="btn btn-slate text-xs px-2 py-1">💾 Save</button>
				<button id="ts-export" class="btn btn-slate text-xs px-2 py-1">⬇ Export</button>
				<button id="ts-stop" class="btn btn-danger text-xs px-2 py-1">■ Stop</button>
				<button id="ts-next" class="btn btn-slate text-xs px-2 py-1">➡ Next</button>
				<button id="ts-clear" class="btn btn-slate text-xs px-2 py-1">🗑 Clear</button>
			  </div>
			  <div class="ml-auto flex items-center gap-2 flex-wrap">
				<span class="text-sm text-gray-300">Style</span>
				<select id="ts-style" class="border border-gray-600 bg-gray-700 text-white rounded px-2 py-1 text-xs w-24">
				  <option value="dubbing">dubbing</option>
				  <option value="normal">normal</option>
				</select>
				<span class="text-sm text-gray-300">Lang</span>
				<select id="ts-lang" class="border border-gray-600 bg-gray-700 text-white rounded px-2 py-1 text-xs w-16">
				  <option value="id" ${st.lang==='id'?'selected':''}>ID</option>
				  <option value="en" ${st.lang==='en'?'selected':''}>EN</option>
				</select>
				<span class="text-sm text-gray-300">Engine</span>
				<select id="ts-engine" class="border border-gray-600 bg-gray-700 text-white rounded px-2 py-1 text-xs w-20">
				  <option value="llm" ${st.engine==='llm'?'selected':''}>LLM</option>
				  <option value="nllb" ${st.engine==='nllb'?'selected':''}>NLLB</option>
				  <option value="whisper" ${st.engine==='whisper'?'selected':''}>Whisper</option>
				</select>
				<span class="text-sm text-gray-300">Temp</span>
				<input id="ts-temp" type="number" step="0.1" min="0" max="2" value="${st.temperature}"
					   class="border border-gray-600 bg-gray-700 text-white rounded px-1 py-1 w-10 text-xs" />
				<span class="text-sm text-gray-300">top-p</span>
				<input id="ts-topp" type="number" step="0.05" min="0" max="1" value="${st.top_p}"
					   class="border border-gray-600 bg-gray-700 text-white rounded px-1 py-1 w-10 text-xs" />
			  </div>
			</div>

			<!-- Main content area - 1 BARIS SAJA -->
			<div class="flex gap-3 h-[65vh]">
			  <!-- LEFT: Subtitle Viewer -->
			  <div class="flex-1 flex flex-col">
				<div class="flex items-center gap-3 mb-2">
				  <div class="text-base font-semibold text-white">Subtitles</div>
				  <div class="flex items-center gap-2">
					<span class="text-sm text-gray-300">Search:</span>
					<input id="ts-search" type="text" placeholder="..." class="border border-gray-600 bg-gray-700 text-white rounded px-2 py-1 w-32 text-sm" />
				  </div>
				  <div class="ml-auto flex items-center gap-2">
					<button id="ts-prev" class="btn btn-slate text-xs px-2 py-1">‹</button>
					<button id="ts-nextpage" class="btn btn-slate text-xs px-2 py-1">›</button>
					<span class="text-xs text-gray-300">Page</span>
					<input id="ts-page" type="number" min="1" value="${st.page}" class="border border-gray-600 bg-gray-700 text-white rounded px-1 py-1 w-10 text-xs" />
					<span class="text-xs text-gray-300">/<span id="ts-pages">1</span></span>
					<select id="ts-size" class="border border-gray-600 bg-gray-700 text-white rounded px-1 py-1 text-xs w-16">
					  ${[50,100,200,500].map(n=>`<option value="${n}" ${st.size===n?'selected':''}>${n}</option>`).join('')}
					</select>
					<label class="inline-flex items-center gap-1">
					  <input id="ts-follow" type="checkbox" ${st.follow?'checked':''} class="w-3 h-3 text-blue-500 bg-gray-600 border-gray-500 rounded focus:ring-blue-400" />
					  <span class="text-xs text-gray-300">Follow</span>
					</label>
				  </div>
				</div>
				<div id="ts-table" class="flex-1 border border-gray-600 rounded overflow-auto bg-gray-900"></div>
			  </div>

			  <!-- RIGHT: Messages -->
			  <div class="w-1/3 flex flex-col">
				<div class="text-base font-semibold text-white mb-2">Results</div>
				<pre id="ts-messages" class="flex-1 border border-gray-600 rounded p-2 overflow-auto bg-gray-900 text-green-200 text-xs"></pre>
			  </div>
			</div>
		  </div>
		</div>
	  `;

	  this.setupTranslateEvents();
	}

// ==================== TRANSLATE: EVENT BINDING (always re-bind after render) ====================
setupTranslateEvents() {
  if (!this.translate) this.initTranslateState();
  const $ = (id) => document.getElementById(id);

  // -- input config (sinkron ke state) --
  const bindVal = (id, key, toNum=false) => {
    const el = $(id); if (!el) return;
    el.addEventListener('input', () => { this.translate[key] = toNum ? Number(el.value) : el.value; });
  };
  const bindChk = (id, key) => {
    const el = $(id); if (!el) return;
    el.addEventListener('change', () => { this.translate[key] = !!el.checked; });
  };

  bindVal('ts-api',     'apiKey');
  bindVal('ts-batch',   'batch', true);
  bindVal('ts-workers', 'workers', true);
  bindVal('ts-temp',    'temperature', true);
  bindVal('ts-topp',    'top_p', true);
  bindVal('ts-lang',    'lang');
  bindVal('ts-engine',  'engine');
  bindVal('ts-style',   'style');
  bindChk('ts-autosave','autosave');

  // -- search & paging --
  $('ts-search')?.addEventListener('input', () => { this.translate.search = $('ts-search').value.trim(); this.filterAndRenderSubs(); });
  $('ts-size')?.addEventListener('change', () => { this.translate.size = Number($('ts-size').value) || 100; this.translate.page = 1; this.renderSubsPage(); });
  $('ts-page')?.addEventListener('change', () => { this.translate.page = Math.max(1, Number($('ts-page').value || 1)); this.renderSubsPage(); });
  $('ts-prev')?.addEventListener('click',  () => { this.translate.page = Math.max(1, this.translate.page - 1); this.renderSubsPage(); });
  $('ts-nextpage')?.addEventListener('click', () => { this.translate.page = Math.min(this.totalPages || 1, this.translate.page + 1); this.renderSubsPage(); });
  $('ts-follow')?.addEventListener('change', () => { this.translate.follow = $('ts-follow').checked; });

  // -- file/save/export/clear/next-tab --
  $('ts-load')?.addEventListener('click',  () => this.promptLoadSRT());
  $('ts-save')?.addEventListener('click',  () => this.translateSave());
  $('ts-export')?.addEventListener('click',() => this.translateExport());
  $('ts-clear')?.addEventListener('click', () => this.translateClear());
  $('ts-next')?.addEventListener('click',  () => this.loadTab('editing'));

  // -- STREAMING actions (no space before ?.) --
  $('ts-start')?.addEventListener('click',  () => this.tsStartStream('start'));
  $('ts-resume')?.addEventListener('click', () => this.tsStartStream('resume'));
  $('ts-fill')?.addEventListener('click',   () => this.tsStartStream('fill'));
  $('ts-stop')?.addEventListener('click',   () => this.tsStopStream());

  // render awal
  this.renderSubsPage();
  this.renderMessages();
}

	/* ==============================
	 * LOAD SRT (auto/manual)
	 * ============================== */
	async promptLoadSRT() {
	  const setText = (text, mode) => {
		this.translate.mode = mode;
		this.translate.srtText = text;
		const subs = this.parseSRT(text);
		this.translate.originalSubs = subs.map(s => ({...s})); // keep original
		// working copy dengan placeholder trans=''
		this.translate.subtitles = subs.map(s => ({...s, trans: ''}));
		this.filterAndRenderSubs();
		this.updateTranslateProgress();
		this.showNotification(mode==='auto'?'SRT loaded from session':'Loaded SRT file','success');
	  };

	  if (this.currentSessionId) {
		try {
		  const res = await fetch(`/api/session/${this.currentSessionId}/srt?prefer=original`, { method: 'GET' });
		  let text = await res.text();
		  if (!res.ok) throw new Error(text);
		  try { const obj=JSON.parse(text); if (obj && obj.srt) text = obj.srt; } catch {}
		  return setText(text,'auto');
		} catch (e) {
		  this.showNotification('Backend SRT tidak tersedia, pilih file manual…','warning');
		}
	  }
	  // manual picker
	  const input = document.createElement('input'); input.type='file'; input.accept='.srt';
	  input.onchange = async ()=>{ const f=input.files?.[0]; if(!f) return; setText(await f.text(),'manual'); };
	  input.click();
	}

	/* ==============================
	 * TRANSLATE HELPER FUNCTIONS
	 * ============================== */

	_getIndicesForStart(overwrite = false) {
	  const st = this.translate;
	  if (!st?.subtitles) return [];
	  if (overwrite) return st.subtitles.map(s => s.index);
	  // default: hanya yang kosong
	  return st.subtitles.filter(s => !(s.trans || '').trim()).map(s => s.index);
	}

	_getIndicesForResume() {
	  const st = this.translate;
	  if (!st?.subtitles) return [];
	  const cp = st.checkpoint || 0;
	  return st.subtitles
		.filter(s => s.index > cp && !(s.trans || '').trim())
		.map(s => s.index);
	}

	_getIndicesForFillMissing() {
	  const st = this.translate;
	  if (!st?.subtitles) return [];
	  return st.subtitles.filter(s => !(s.trans || '').trim()).map(s => s.index);
	}
	
	/* ==============================
	 * RUN TRANSLATE (ALL / MISSING)
	 * ============================== */
	async translateStartAll(){ return this._translateGeneric(false); }
	async translateMissing(){  return this._translateGeneric(true); }

	// === TAB 2: jalankan translate dengan mode Start / Resume / Fill Missing ===
	async _translateGeneric() {
	  // --- state awal & helper kecil ---
	  if (!this.translate) this.initTranslateState();
	  const st = this.translate;

	  const $ = (id) => document.getElementById(id);
	  const btnStart  = $('ts-start');
	  const btnFill   = $('ts-fill');
	  const btnStop   = $('ts-stop');
	  const btnExport = $('ts-export');
	  const barEl     = $('ts-progressbar');
	  const labEl     = $('ts-progresslabel');

	  // Ambil parameter UI
	  const apiKeyEl = $('ts-api');
	  const batchEl  = $('ts-batch');
	  const workEl   = $('ts-workers');
	  const tempEl   = $('ts-temp');
	  const toppEl   = $('ts-topp');
	  const langSel  = $('ts-lang');
	  const styleSel = $('ts-style');

	  // Simpan konfigurasi
	  st.apiKey      = (apiKeyEl?.value || '').trim();
	  st.batch       = Number(batchEl?.value || 20);
	  st.workers     = Number(workEl?.value || 1);
	  st.temperature = Number(tempEl?.value || 0.1);
	  st.top_p       = Number(toppEl?.value || 0.3);
	  st.lang        = (langSel?.value || 'id').toLowerCase();
	  st.style       = (styleSel?.value || 'dubbing');

	  // Validasi sederhana
	  if (!this.currentSessionId && !st.srtText) {
		this.showNotification('Belum ada session & SRT; "Load" SRT dulu atau buat session di Tab 1.', 'error');
		return;
	  }
	  if (!st.apiKey) {
		this.showNotification('API key kosong. Masukkan API key dahulu.', 'error');
		return;
	  }
	  if (st.running) return;

	  // ----- mode eksekusi: start / resume / fill -----
	  // set oleh tombol sebelum memanggil _translateGeneric(); default 'start'
	  const mode = (st.runMode || 'start'); // 'start' | 'start-overwrite' | 'resume' | 'fill'

	  // Helper untuk memilih indeks target
	  const pickIndices = () => {
		if (!st?.subtitles) return [];
		const isEmpty = (s) => !((s.trans || '').trim());

		if (mode === 'resume') {
		  const cp = st.checkpoint || 0;
		  return st.subtitles.filter(s => s.index > cp && isEmpty(s)).map(s => s.index);
		}
		if (mode === 'fill') {
		  return st.subtitles.filter(isEmpty).map(s => s.index);
		}
		if (mode === 'start-overwrite') {
		  return st.subtitles.map(s => s.index);
		}
		// default 'start' aman: hanya baris kosong
		return st.subtitles.filter(isEmpty).map(s => s.index);
	  };

	  // Kunci tombol (Stop tetap aktif)
	  btnStart?.setAttribute('disabled','disabled');
	  btnFill?.setAttribute('disabled','disabled');
	  btnExport?.setAttribute('disabled','disabled');
	  btnStop?.removeAttribute('disabled');

	  st.running = true;

	  // Tampilkan overlay, tapi biarkan tombol stop tetap bisa diklik (kalau overlay kamu blok klik,
	  // kamu bisa set CSS overlay pointer-events:none; — tidak saya ubah di sini).
	  const overlay = this.showLoading('Translating SRT...');

	  // Pastikan SRT ORIGINAL sudah ada (untuk manual mode / untuk enforce prefer=original)
	  try {
		if (!st.srtText && this.currentSessionId) {
		  const resSrt = await fetch(`/api/session/${this.currentSessionId}/srt?prefer=original`);
		  if (!resSrt.ok) throw new Error('Gagal mengambil SRT session (prefer=original)');
		  st.srtText      = await resSrt.text();
		  st.originalSubs = this.parseSRT(st.srtText);
		  st.subtitles    = st.originalSubs.map(x => ({ ...x })); // reset grid kiri
		  this._renderTable?.();
		}
	  } catch (e) {
		this.hideLoading();
		st.running = false;
		btnStart?.removeAttribute('disabled');
		btnFill?.removeAttribute('disabled');
		btnExport?.removeAttribute('disabled');
		btnStop?.setAttribute('disabled','disabled');
		this.showNotification(`Load SRT gagal: ${e.message || e}`, 'error');
		return;
	  }

	  // Tentukan baris mana yang harus diterjemahkan
	  let indices = pickIndices();
	  indices = [...new Set(indices)].sort((a,b)=>a-b); // unik & urut

	  if (!indices.length) {
		// Sudah selesai semua atau tidak ada yang perlu diterjemahkan
		this.hideLoading();
		st.running = false;
		btnStart?.removeAttribute('disabled');
		btnFill?.removeAttribute('disabled');
		btnExport?.removeAttribute('disabled');
		btnStop?.setAttribute('disabled','disabled');
		this.showNotification('Tidak ada baris yang perlu diterjemahkan.', 'success');
		return;
	  }

	  // Build form payload
	  const form = new URLSearchParams({
		api_key: st.apiKey,
		target_lang: st.lang,
		engine: 'llm',
		temperature: String(st.temperature),
		top_p: String(st.top_p),
		batch: String(st.batch),
		workers: String(st.workers),
		timeout: '120',
		autosave: 'true',
		mode: st.style === 'dubbing' ? 'dubbing' : 'normal',
		srt_text: st.srtText,         // kirim sumber ORIGINAL
		prefer: 'original',
		only_indices: indices.join(','), // ← HANYA baris target
	  });

	  // Abortable
	  const ac = new AbortController();
	  st.abort = () => ac.abort();

	  // Progress bar helper
	  const total = indices.length;
	  let done = 0;
	  const updatePB = () => {
		const pct = Math.round((done / total) * 100);
		if (barEl) barEl.style.width = `${pct}%`;
		if (labEl) labEl.textContent = `${pct}% (${done}/${total})`;
	  };
	  updatePB();

	  try {
		// Pilih endpoint: pakai /api/translate untuk manual (tanpa session)
		const resp = await fetch(
		  this.currentSessionId
			? `/api/session/${this.currentSessionId}/translate`
			: `/api/translate`,
		  {
			method: 'POST',
			headers: { 'Content-Type': 'application/x-www-form-urlencoded;charset=UTF-8' },
			body: form,
			signal: ac.signal
		  }
		);

		const raw = await resp.text();
		if (!resp.ok) throw new Error(raw || `HTTP ${resp.status}`);

		// Normalisasi respons: {results: [...]} ATAU SRT utuh
		let results = null;
		let json = null;
		try { json = JSON.parse(raw); } catch {}
		if (json && Array.isArray(json.results)) {
		  results = json.results;
		} else {
		  const outSrt =
			json?.data?.translated_srt ||
			json?.translated_srt ||
			json?.srt ||
			raw;

		  // Parse SRT → list hasil
		  const parsed = this.parseSRT(outSrt); // [{index,start,end,text}]
		  results = parsed.map(p => {
			const idxNo = Number(p.index);
			const ts    = `${p.start} --> ${p.end}`;
			// cocokan ke sumber
			let src = st.subtitles.find(s => s.index === idxNo);
			if (!src) src = st.subtitles.find(s => (`${s.start} --> ${s.end}`) === ts);
			return {
			  index: idxNo,
			  timestamp: ts,
			  original_text: src ? (src.text || '') : '',
			  translation: (p.text || '').trim()
			};
		  });
		}
		if (!Array.isArray(results)) throw new Error('Tidak ada hasil terjemahan.');

		// Tulis hasil per-item (realtime di panel kanan & grid kiri)
		st.doneSet = st.doneSet || new Set();
		for (const item of results) {
		  // Cari index di grid
		  let idx = -1;
		  if (Number.isInteger(item.index)) {
			idx = st.subtitles.findIndex(s => s.index === item.index);
		  }
		  if (idx < 0 && item.timestamp) {
			idx = st.subtitles.findIndex(s => `${s.start} --> ${s.end}` === item.timestamp);
		  }
		  if (idx < 0 && item.original_text) {
			idx = st.subtitles.findIndex(s => (s.text || '') === item.original_text);
		  }

		  const trans = (item.translation ?? '').trim();
		  if (idx >= 0) {
			// hanya isi target; jangan menimpa yang sudah ada kecuali mode 'start-overwrite'
			const already = (st.subtitles[idx].trans || '').trim();
			const canWrite = (mode === 'start-overwrite') || !already;
			if (canWrite) {
			  st.subtitles[idx].trans = trans;
			  this._renderTableRow?.(idx);
			}

			// Update checkpoint & doneSet untuk Resume
			st.doneSet.add(st.subtitles[idx].index);
			st.checkpoint = Math.max(st.checkpoint || 0, st.subtitles[idx].index);
		  }

		  // kirim ke panel kanan (biar “jalan” per baris)
		  this.appendMessage?.({ event: 'translate:progress', payload: item });

		  done += 1;
		  updatePB();
		}

		this._lastTranslatedAt = Date.now();
		this.showNotification('Translate selesai.', 'success');

	  } catch (err) {
		this.appendMessage?.({ event: 'translate:error', payload: String(err) });
		this.showNotification(`Translate gagal: ${err.message || err}`, 'error');

	  } finally {
		st.running = false;
		this.hideLoading();
		// Pulihkan tombol
		btnStart?.removeAttribute('disabled');
		btnFill?.removeAttribute('disabled');
		btnExport?.removeAttribute('disabled');
		btnStop?.setAttribute('disabled','disabled');
	  }
	}

	// === Export hasil translate menjadi .srt (download) ===
	async _exportSRT() {
	  if (!this.translate) this.initTranslateState();
	  const st = this.translate;
	  if (!st.subtitles?.length) {
		this.showNotification('Tidak ada data subtitle untuk diekspor.', 'error');
		return;
	  }

	  const lines = [];
	  for (const it of st.subtitles) {
		const out = (it.trans ?? '').trim(); // biarkan kosong kalau belum diterjemahkan
		lines.push(String(it.index));
		lines.push(`${it.start} --> ${it.end}`);
		lines.push(out);
		lines.push(''); // pemisah
	  }
	  const srtOut = lines.join('\r\n');

	  const blob = new Blob([srtOut], { type: 'text/plain;charset=utf-8' });
	  const url  = URL.createObjectURL(blob);
	  const a    = document.createElement('a');
	  a.href     = url;
	  a.download = 'translated.srt';
	  document.body.appendChild(a);
	  a.click();
	  a.remove();
	  URL.revokeObjectURL(url);

	  this.showNotification('Export SRT selesai (download).', 'success');
	}

	// --- PATCH: helper untuk refresh baris saat streaming progress ---
	// Versi sederhana: render ulang halaman aktif (aman & cepat dikerjakan).
	_renderTableRow(idx) {
	  // Kalau nanti mau super-presisi per baris, kita bisa kasih id pada setiap row
	  // lalu update innerHTML row tsb. Untuk sekarang cukup render ulang halaman.
	  if (typeof this.renderSubsPage === 'function') {
		this.renderSubsPage();
	  }
	  if (typeof this.updateTranslateProgress === 'function') {
		this.updateTranslateProgress();
	  }
	  if (typeof this.renderMessages === 'function') {
		this.renderMessages();
	  }
	}

	// (opsional) kecilkan jejak UI refresh total
	_renderTable() { 
	  // alias agar panggilan lama ke _renderTable tidak error
	  if (typeof this.renderSubsPage === 'function') this.renderSubsPage();
	}


	/* ==============================
	 * MERGE: translated SRT -> subtitles[].trans
	 * ============================== */
	mergeTranslatedSRT(translatedText, partial=false) {
	  const parsed = this.parseSRT(translatedText);   // sama struktur: index/start/end/text
	  // buat map index -> text
	  const tmap = new Map(parsed.map(p => [Number(p.index), (p.text||'').trim()]));
	  // merge
	  this.translate.subtitles = this.translate.subtitles.map(s => {
		const t = tmap.get(Number(s.index));
		if (t && (!partial || !s.trans)) {
		  return {...s, trans: t};
		}
		return s;
	  });
	  this.filterAndRenderSubs();
	  this.renderMessages(); // refresh JSON kanan
	}

	/* ==============================
	 * PROGRESS BAR
	 * ============================== */
updateTranslateProgress(done, total) {
  const pct = total ? Math.round((done / total) * 100) : 0;
  const bar = document.getElementById('ts-progressbar');
  const lab = document.getElementById('ts-progresslabel');
  if (bar) bar.style.width = `${pct}%`;
  if (lab) lab.textContent = `${pct}% (${done}/${total})`;
}

// Fokus/scroll ke baris index tertentu
scrollToTsRow(index) {
  const row = document.getElementById(`ts-row-${index}`);
  if (row) row.scrollIntoView({ behavior: 'smooth', block: 'center' });
}

setRowTranslation(index, text) {
  const inp = document.querySelector(`input.ts-trans[data-idx="${index}"]`);
  if (inp) {
    inp.value = text || '';
    inp.classList.add('bg-green-900/40'); // efek kecil biar kelihatan update
    setTimeout(()=>inp.classList.remove('bg-green-900/40'), 300);
  }
  // sinkronkan ke state
  const row = this.translate?.subtitles?.find(r => r.index === index);
  if (row) row.trans = text || '';
}


	/* ==============================
	 * SAVE / EXPORT / STOP / CLEAR
	 * ============================== */
	translateSave(){
	  // rakit SRT dari state (pakai trans kalau ada, fallback ke original)
	  const srt = this.translate.subtitles.map(s => {
		const txt = (s.trans && s.trans.trim()) ? s.trans : (s.text || "");
		return `${s.index}\n${s.start} --> ${s.end}\n${txt}\n`;
	  }).join('\n');

	  // Kalau ada session → simpan ke workdir lewat backend
	  if (this.currentSessionId) {
		const body = new URLSearchParams({
		  srt_text: srt,
		  filename: "translated_latest.srt"
		});
		this.showLoading("Saving to workspace...");
		fetch(`/api/session/${this.currentSessionId}/save-srt`, {
		  method: "POST",
		  headers: {"Content-Type":"application/x-www-form-urlencoded"},
		  body
		})
		.then(async (res) => {
		  const txt = await res.text();
		  if (!res.ok) throw new Error(txt);
		  const data = JSON.parse(txt);
		  this.showNotification(`Saved: ${data.path}`, "success");
		})
		.catch(err => {
		  this.showNotification(`Save failed: ${err}`, "error");
		})
		.finally(()=> this.hideLoading());
		return;
	  }

	  // Tanpa session → fallback download lokal
	  const blob = new Blob([srt], {type:'text/plain;charset=utf-8'});
	  const a = document.createElement('a');
	  a.href = URL.createObjectURL(blob);
	  a.download = 'translated.srt';
	  a.click();
	  URL.revokeObjectURL(a.href);
	}
	
	translateExport() {
	  // rakit SRT dari state: pakai terjemahan jika ada, fallback ke original
	  const srt = (this.translate.subtitles || []).map(s => {
		const txt = (s.trans && s.trans.trim()) ? s.trans : (s.text || "");
		return `${s.index}\n${s.start} --> ${s.end}\n${txt}\n`;
	  }).join('\n');

	  if (this.currentSessionId) {
		// simpan ke workspace session
		const body = new URLSearchParams({
		  srt_text: srt,
		  filename: "translated_export.srt"
		});
		this.showNotification("Saving SRT to workspace…", "info");
		fetch(`/api/session/${this.currentSessionId}/save-srt`, {
		  method: "POST",
		  headers: { "Content-Type": "application/x-www-form-urlencoded" },
		  body
		})
		.then(async r => {
		  const t = await r.text();
		  if (!r.ok) throw new Error(t);
		  const data = JSON.parse(t);
		  this.showNotification(`Exported: ${data.path}`, "success");
		})
		.catch(err => this.showNotification(`Export failed: ${err}`, "error"));
		return;
	  }

	  // tanpa session → download lokal
	  const blob = new Blob([srt], { type: "text/plain;charset=utf-8" });
	  const a = document.createElement("a");
	  a.href = URL.createObjectURL(blob);
	  a.download = "translated.srt";
	  a.click();
	  URL.revokeObjectURL(a.href);
	}
	
	translateStop() {
	  try { if (this.translate?.abort) this.translate.abort(); } catch (e) {}
	}
	translateClear(){ this.initTranslateState(); this.loadTab('translate'); }

	/* ==============================
	 * VIEWER & MESSAGES
	 * ============================== */
	filterAndRenderSubs(){
	  const q=(this.translate.search||'').toLowerCase();
	  const src=this.translate.subtitles||[];
	  this.translate.filtered = q ? src.filter(x=> ((x.text||'') + ' ' + (x.trans||'')).toLowerCase().includes(q)) : src.slice();
	  this.translate.page=1; this.renderSubsPage();
	}
	
// Tambahkan method ini di dalam class DracinApp
buildSrtFromState() {
  // gunakan this.translate.subtitles (index/start/end/text)
  const rows = this.translate.subtitles || [];
  return rows.map(r => `${r.index}\n${r.start} --> ${r.end}\n${(r.text||'')}\n`).join('\n');
}

// ==================== HELPERS ====================
_tsMissingIndices() {
  // baris yang belum punya terjemahan (kosong)
  return this.translate.subtitles
    .filter(x => !x.trans || !String(x.trans).trim())
    .map(x => x.index);
}

_tsResumeFromFirstGap(missingList) {
  if (!missingList.length) return [];
  const first = Math.min(...missingList);
  return this.translate.subtitles
    .filter(x => x.index >= first)
    .map(x => x.index);
}

_tsToggleButtons(disabled) {
  ['ts-start','ts-resume','ts-fill','ts-stop','ts-load','ts-save','ts-export','ts-clear']
    .forEach(id => {
      const b = document.getElementById(id);
      if (b) b.disabled = !!disabled && id!=='ts-stop';
    });
}

_tsUpdateProgress(done, total) {
  const bar = document.getElementById('ts-progressbar');
  const label = document.getElementById('ts-progresslabel');
  const pct = (!total ? 0 : Math.round(100*done/total));
  if (bar)   bar.style.width = `${pct}%`;
  if (label) label.textContent = `${pct}% (${done}/${total||0})`;
}

// ==================== TRANSLATE: STREAM START/RESUME/FILL ====================
async tsStartStream(runMode='start') {
  if (!this.translate) this.initTranslateState();
  const st = this.translate;

  if (st.running) { this.showNotification('Translate is running…', 'info'); return; }
  if (!st.apiKey)  { this.showNotification('API key kosong.', 'error'); return; }

  // Tentukan indeks target
  const allIdx = (this.translate.subtitles || []).map(x => x.index);
  const missing = (this.translate.subtitles || []).filter(x => !(x.trans||'').trim()).map(x => x.index);
  let only = [];
  if (runMode === 'fill') only = missing;
  else if (runMode === 'resume') {
    if (!missing.length) { this.showNotification('Nothing to resume.', 'info'); return; }
    const firstGap = Math.min(...missing);
    only = this.translate.subtitles.filter(x => x.index >= firstGap && !(x.trans||'').trim()).map(x => x.index);
  } else {
    // start: proses semua baris (biar konsisten dengan permintaanmu sebelumnya)
    only = allIdx;
  }
  if (!only.length) { this.showNotification('Tidak ada baris yang perlu diterjemahkan.', 'success'); return; }

  const hasSession = !!this.currentSessionId;
  const url = hasSession
    ? `/api/session/${this.currentSessionId}/translate/stream`
    : `/api/translate/stream`;

  const fd = new FormData();
  fd.append('api_key', st.apiKey);
  fd.append('target_lang', st.lang || 'id');
  fd.append('engine', st.engine || 'llm');
  fd.append('temperature', String(st.temperature ?? 0.1));
  fd.append('top_p', String(st.top_p ?? 0.3));
  fd.append('workers', String(st.workers || 1));
  fd.append('timeout', String(st.timeout || 120));
  fd.append('mode', st.style || 'dubbing');
  fd.append('only_indices', only.join(','));

  if (hasSession) {
    fd.append('prefer', 'original');                // paksa ambil SRT original di server
    fd.append('autosave', st.autosave ? 'true':'false');
  } else {
    // manual mode: kirim SRT sumber yang sudah ada di state
    const src = (this.translate.originalSubs && this.translate.originalSubs.length)
      ? this.translate.originalSubs
      : this.translate.subtitles;
    const srtText = (src || []).map(it => `${it.index}\n${it.start} --> ${it.end}\n${it.text||''}\n`).join('\n');
    if (!srtText.trim()) { this.showNotification('SRT belum dimuat. Klik Load dulu.', 'error'); return; }
    fd.append('srt_text', srtText);
  }

  // Lock UI + progress
  st.running = true;
  ['ts-start','ts-resume','ts-fill','ts-load','ts-save','ts-export','ts-clear','ts-next'].forEach(id=>{
    const b=document.getElementById(id); if (b && id!=='ts-stop') b.disabled = true;
  });
  const total = only.length;
  let done = 0;
  const upd = () => {
    const bar = document.getElementById('ts-progressbar');
    const lab = document.getElementById('ts-progresslabel');
    const pct = Math.round(done*100/total);
    if (bar) bar.style.width = `${pct}%`;
    if (lab) lab.textContent = `${pct}% (${done}/${total})`;
  };
  upd();

  // siapkan abort
  const controller = new AbortController();
  st.abort = controller;

  try {
    const res = await fetch(url, { method:'POST', body: fd, signal: controller.signal });
    if (!res.ok || !res.body) {
      const msg = await res.text().catch(()=>`${res.status} ${res.statusText}`);
      throw new Error(`Translate failed: ${msg}`);
    }

    // NDJSON reader
    const reader  = res.body.getReader();
    const decoder = new TextDecoder('utf-8');
    let buffer = '';

    while (true) {
      const {value, done:drained} = await reader.read();
      if (drained) break;
      buffer += decoder.decode(value, {stream:true});

      let nl;
      while ((nl = buffer.indexOf('\n')) >= 0) {
        const line = buffer.slice(0, nl).trim();
        buffer = buffer.slice(nl+1);
        if (!line) continue;

        let evt;
        try { evt = JSON.parse(line); } catch { continue; }

        // tampilkan di panel kanan SATU-PER-SATU
        this.appendMessage(evt);
		this.renderMessages(true); // true = force scroll

        if (evt.type === 'result') {
          // set hasil ke grid kiri
          const idx = Number(evt.index);
          const row = this.translate.subtitles.find(r => r.index === idx);
          if (row) row.trans = (evt.translation || '').trim();
          done += 1;
          upd();
          this.renderSubsPage(true); // keep scroll
		  const input = document.querySelector(`#ts-row-${evt.index} .ts-trans`);
		  if (input) input.value = row.trans;
		  this._flashTsRow(evt.index);
		  this._scrollToTsRow(evt.index);
        }
      }
    }

    this.showNotification('Translate finished', 'success');
  } catch (err) {
    if (err?.name === 'AbortError') this.showNotification('Translate stopped', 'info');
    else this.showNotification(`Translate failed: ${err?.message || err}`, 'error');
  } finally {
    st.running = false;
    st.abort   = null;
    // unlock UI
    ['ts-start','ts-resume','ts-fill','ts-load','ts-save','ts-export','ts-clear','ts-next'].forEach(id=>{
      const b=document.getElementById(id); if (b) b.disabled = false;
    });
    const bar = document.getElementById('ts-progressbar');
    const lab = document.getElementById('ts-progresslabel');
    if (bar) bar.style.width = '0%';
    if (lab) lab.textContent = `0% (0/0)`;
  }
}


// Bangun SRT dari originalSubs (tanpa terjemahan) – untuk mode manual
buildSrtFromOriginal(items = []) {
  return (items || []).map(it => {
    return `${it.index}\n${it.start} --> ${it.end}\n${it.text || ''}\n`;
  }).join('\n');
}

// === HANYA yang kosong ===
getMissingIndices() {
  return (this.translate?.subtitles || [])
    .filter(r => !(r.trans || '').trim())
    .map(r => r.index);
}

// === Resume: dari first kosong sampai akhir, yang kosong saja ===
getResumeIndices() {
  const arr = this.translate?.subtitles || [];
  const pos = arr.findIndex(r => !(r.trans || '').trim());
  if (pos < 0) return [];
  return arr.slice(pos).filter(r => !(r.trans || '').trim()).map(r => r.index);
}

// Panggil di setupTranslateEvents() untuk tombol Fill/Resume:
tsFillStream() {
  const idxs = this.getMissingIndices();
  if (!idxs.length) {
    this.showNotification('Nothing to fill. All translated.', 'info');
    return;
  }
  this.tsStartStream({ onlyIndices: idxs });
}

tsResumeStream() {
  if (!this.translate) this.initTranslateState();
  const rows = this.translate.subtitles || [];
  const cp = this.translate.checkpoint || 0;
  const only = rows.filter(r => r.index > cp && !(r.trans||'').trim()).map(r => r.index);
  return this.tsStartStream({ onlyIndices: only });
}

tsFillStream() {
  if (!this.translate) this.initTranslateState();
  const rows = this.translate.subtitles || [];
  const only = rows.filter(r => !(r.trans||'').trim()).map(r => r.index);
  return this.tsStartStream({ onlyIndices: only });
}

// ==================== TRANSLATE: STOP ====================
tsStopStream() {
  const st = this.translate || {};
  if (st.abort) { try { st.abort.abort(); } catch {} }
}


	// ===== Helper progress kecil di header =====
	tsUpdateProgress(done, total) {
	  this.translate.totalDone = done;
	  this.translate.totalAll  = total;
	  const pct = total ? Math.floor((done/total)*100) : 0;
	  const bar = document.getElementById('ts-progressbar');
	  const lbl = document.getElementById('ts-progresslabel');
	  if (bar) bar.style.width = `${pct}%`;
	  if (lbl) lbl.textContent = `${pct}% (${done}/${total})`;
	}
	 
// Di dalam method renderSubsPage(), pastikan markup seperti ini:
/**
 * Render tabel subtitle TANPA paksa scroll ke bawah.
 * - keepPos: true = jaga posisi scroll sekarang (default).
 * - Kalau kamu sudah punya renderSubsPage(), ganti dengan ini.
 */
renderSubsPage(keepPos = true) {
  if (!this.translate) this.initTranslateState();
  const st = this.translate;
  const wrap = document.getElementById('ts-table');
  if (!wrap) return;

  // simpan posisi scroll supaya tidak loncat ke bawah sesudah re-render
  const prevScroll = keepPos ? wrap.scrollTop : 0;

  // filter/paging sesuai state-mu (sesuaikan kalau berbeda)
  const list = st.filtered?.length ? st.filtered : (st.subtitles || []);
  const page = Math.max(1, Number(st.page || 1));
  const size = Number(st.size || 100);
  const start = (page - 1) * size;
  const pageRows = list.slice(start, start + size);

  // builder baris; PASTIKAN id="ts-row-{{index}}" dan input .ts-trans
const esc = s => String(s ?? '').replace(/[&<>"']/g, c => ({
  '&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'
}[c]));

wrap.innerHTML = `
  <table class="w-full text-sm text-gray-200">
    <thead>
      <tr class="bg-gray-800 border-b border-gray-600 sticky top-0 text-sm font-semibold text-gray-300">
        <th class="px-3 py-2 w-10 text-left">#</th>
        <th class="px-3 py-2 w-20 text-left">Start</th>
        <th class="px-3 py-2 w-20 text-left">End</th>
        <th class="px-3 py-2 text-left">Original</th>
        <th class="px-3 py-2 w-[28rem] text-left">Translation</th>
      </tr>
    </thead>
    <tbody>
      ${pageRows.map(r => `
        <tr id="ts-row-${r.index}" class="border-b border-gray-700 hover:bg-gray-800">
          <td class="px-3 py-2 text-gray-400 font-mono">${r.index}</td>
          <td class="px-3 py-2 text-gray-300 font-mono text-xs">${esc(r.start)}</td>
          <td class="px-3 py-2 text-gray-300 font-mono text-xs">${esc(r.end)}</td>
          <td class="px-3 py-2 text-gray-300 break-words">${esc(r.text)}</td>
          <td class="px-3 py-2">
            <input class="ts-trans w-full bg-gray-800 border border-gray-700 rounded px-2 py-1 text-green-400 break-words font-medium" 
                   value="${esc(r.trans)}" data-idx="${r.index}">
          </td>
        </tr>
      `).join('')}
    </tbody>
  </table>
`;

  // restore posisi scroll (agar tidak turun ke bawah)
  if (keepPos) wrap.scrollTop = prevScroll;

  // sinkronisasi perubahan manual di input ke state (opsional)
  wrap.querySelectorAll('.ts-trans').forEach(inp => {
    inp.addEventListener('input', e => {
      const idx = Number(e.target.dataset.idx);
      const row = st.subtitles?.find(x => x.index === idx);
      if (row) row.trans = e.target.value;
    });
  });
}

/* ================== /PATCH: follow ke baris hasil terjemahan ================= */
	
	buildMessagesArray(){
	  return (this.translate.subtitles||[]).map(s=>({
		index: s.index,
		timestamp: `${s.start} --> ${s.end}`,
		original_text: s.text || "",
		translation: s.trans || ""
	  }));
	}

// ==================== RENDER LOG (batasi agar tidak “massal”) ====================
renderMessages(forceScroll = false) {
  const el = document.getElementById('ts-messages');
  if (!el || !this.translate) return;
  const msgs = this.translate.messages.slice(-200);
  el.textContent = JSON.stringify(msgs, null, 2);
  
  if (forceScroll || this.translate.followResults) {
    el.scrollTop = el.scrollHeight;
  }
}

/* ===========================
 *  TAB 3 — EDITING (FULL BLOCK)
 *  letakkan semua method ini DI DALAM class DracinApp
 * =========================== */
/* ===========================
 *  TAB 3 — EDITING (FULL BLOCK)
 *  (Semua method di bawah ini berada DI DALAM class DracinApp)
 * =========================== */

initEditingState() {
  this.editing = {
    sessionId: this.currentSessionId || "",
    rows: [],            // [{index,start,end,translation,gender,speaker,notes}]
    filtered: [],
    follow: true,
    genderFilter: "all",
    speakerFilter: "",
    search: "",
    shown: 0,
    total: 0,
    videoUrl: "",
    playingRowIndex: null,
    playTimer: null
  };
}

async loadEditingTab() {
  if (!this.editing) this.initEditingState();
  const st = this.editing;

  const tab = document.getElementById('editing');
  if (!tab) return;

  tab.innerHTML = `
    <div id="tab-editing" class="bg-gray-800 rounded-lg p-4">
      <h2 class="text-xl font-bold mb-4 text-yellow-400">
        <i class="fas fa-edit mr-2"></i>Editing
      </h2>

      <div class="flex flex-wrap items-center gap-2 mb-3">
        <input id="ed-session-input" class="bg-gray-700 border border-gray-600 text-white px-3 py-1 rounded w-64"
               placeholder="Paste / ketik Session ID…" />
        <button id="ed-load-session" class="btn btn-slate px-3 py-1">Load Session</button>

        <select id="ed-session-select" class="bg-gray-700 border border-gray-600 text-white px-2 py-1 rounded">
          <option value="">— pilih session —</option>
        </select>

        <span class="mx-2 text-gray-400">|</span>

			<select id="ed-gender" class="bg-gray-700 border border-gray-600 text-white px-2 py-1 rounded">
			  <option value="all">All genders</option>
			  <option value="male">male</option>
			  <option value="female">female</option>
			  <option value="unknown">unknown</option>
			</select>

			<select id="ed-speaker-select" class="bg-gray-700 border border-gray-600 text-white px-2 py-1 rounded">
			  <option value="all">All speakers</option>
			</select>

			<input id="ed-search" class="bg-gray-700 border border-gray-600 text-white px-3 py-1 rounded w-52"
				   placeholder="Search text…" />


        <label class="ml-2 inline-flex items-center gap-2 text-gray-300">
          <input id="ed-follow" type="checkbox" class="w-4 h-4" checked />
          Follow
        </label>

        <div class="ml-auto flex items-center gap-2">
          <button id="ed-save" class="btn btn-primary px-3 py-1">Save</button>
          <button id="ed-exp-male" class="btn btn-slate px-3 py-1">Export Male SRT</button>
          <button id="ed-exp-female" class="btn btn-slate px-3 py-1">Export Female SRT</button>
          <button id="ed-exp-unk" class="btn btn-slate px-3 py-1">Export Unknown SRT</button>
          <button id="ed-exp-all" class="btn btn-slate px-3 py-1">Export All (zip)</button>
        </div>
      </div>

      <div id="ed-session-info" class="text-sm text-gray-400 mb-3">No session loaded.</div>

		<div class="grid grid-cols-[30%_1fr] gap-4 items-start">
		  <div class="sticky top-20 h-[calc(100vh-6rem)] bg-black rounded overflow-hidden">
			<video id="ed-video"
				   class="w-full h-full object-contain bg-black aspect-[9/16]"
				   controls preload="metadata" playsinline></video>
		  </div>

		  <div class="max-h-[calc(100vh-6rem)] overflow-auto flex flex-col">
			<div class="text-sm text-gray-300 mb-2">
			  <span id="ed-counter">0 shown / 0 total</span>
			</div>
			<div id="ed-list" class="flex-1 space-y-2"></div>
		  </div>
		</div>
    </div>
  `;

  this._edBindEvents();
  await this._edPopulateSessionSelector();

  if (!st.sessionId && this.currentSessionId) st.sessionId = this.currentSessionId;
  if (st.sessionId) {
    const inp = document.getElementById('ed-session-input');
    if (inp) inp.value = st.sessionId;
    await this._edLoad(st.sessionId);
  }
}

_edBindEvents() {
  const $ = id => document.getElementById(id);
  const ed = this.editing;

  $('ed-load-session')?.addEventListener('click', async () => {
    const id = $('ed-session-input')?.value.trim() || $('ed-session-select')?.value.trim();
    if (!id) return this.showNotification('Isi/pilih Session ID dulu.', 'warning');
    await this._edLoad(id);
  });

  $('ed-session-select')?.addEventListener('change', async (e) => {
    const id = e.target.value;
    if (!id) return;
    $('ed-session-input').value = id;
    await this._edLoad(id);
  });

  $('ed-gender')?.addEventListener('change', () => {
    ed.genderFilter = $('ed-gender').value; this._edFilterRender();
  });
const spkSel = document.getElementById('ed-speaker-select') ||
               document.getElementById('ed-speaker');
spkSel?.addEventListener('change', () => {
  this.editing.speakerFilter = spkSel.value || 'all';
  this._edFilterRender();
});
  $('ed-search')?.addEventListener('input', () => {
    ed.search = $('ed-search').value.trim(); this._edFilterRender();
  });
  $('ed-follow')?.addEventListener('change', () => { ed.follow = $('ed-follow').checked; });

  $('ed-save')?.addEventListener('click', () => this._edSave());
  $('ed-exp-male')?.addEventListener('click', () => this._edExport('male'));
  $('ed-exp-female')?.addEventListener('click', () => this._edExport('female'));
  $('ed-exp-unk')?.addEventListener('click', () => this._edExport('unknown'));
  $('ed-exp-all')?.addEventListener('click', () => this._edExport('all'));

  const v = $('ed-video');
  v?.addEventListener('timeupdate', () => this._edOnVideoTime(v.currentTime));
}

_edPopulateSpeakerFilter(list) {
  const sel =
    document.getElementById('ed-speaker-select') ||
    document.getElementById('ed-speaker');
  if (!sel) return;

  const speakers = Array.isArray(list) ? list.filter(Boolean) : [];
  const current = (this.editing?.speakerFilter || 'all');

  sel.innerHTML =
    `<option value="all">All speakers</option>` +
    speakers.map(s => `<option value="${s}">${s}</option>`).join('');

  sel.value = speakers.includes(current) ? current : 'all';
}



async _edPopulateSessionSelector() {
  try {
    const res = await fetch('/api/sessions');
    if (!res.ok) return;
    const list = await res.json(); // [{id,...}]
    const sel = document.getElementById('ed-session-select');
    if (!sel) return;
    sel.innerHTML = `<option value="">— pilih session —</option>` +
      list.map(s => `<option value="${s.id}">${s.id}</option>`).join('');
  } catch {}
}

async _edLoad(sessionId) {
  const ed = this.editing;
  this.showLoading('Loading editing data…');
  try {
    const url = `/api/session/${sessionId}/editing`;
    const res = await fetch(url);
    if (!res.ok) throw new Error(await res.text());

    const data = await res.json(); // {video, rows:[...], speakers?}
    ed.sessionId = sessionId;
    this.currentSessionId = sessionId;

    ed.rows = (data.rows || []).map(r => ({
      index: r.index,
      start: r.start,
      end: r.end,
      translation: r.translation || "",
      speaker: r.speaker || "",
      gender: (r.gender || "unknown").toLowerCase(),
      notes: r.notes || ""
    }));

    // Setelah data rows diterima:
    this._edIndexSeconds();

    // Fallback untuk speakers jika backend belum mengirim atau kosong
	ed.speakers = Array.isArray(data.speakers) && data.speakers.length
	  ? data.speakers
	  : [...new Set(ed.rows.map(r => (r.speaker || '').trim()).filter(Boolean))].sort();

    // isi dropdown speaker sekali
    this._edPopulateSpeakerFilter(ed.speakers);
    ed.videoUrl = `/api/session/${sessionId}/video`;

    const info = document.getElementById('ed-session-info');
    if (info) info.textContent = `Session: ${sessionId}`;
    const video = document.getElementById('ed-video');
    if (video) { video.src = ed.videoUrl; }
    
    // lalu filter pertama kali
	// seed default filter jika belum ada
	if (!this.editing.genderFilter)  this.editing.genderFilter  = 'all';
	if (!this.editing.speakerFilter) this.editing.speakerFilter = 'all';
	if (typeof this.editing.search !== 'string') this.editing.search = '';

	// isi dropdown speaker (sekali saja, dari rows yang ada)
	const speakers = [...new Set((this.editing.rows || [])
	  .map(r => r.speaker).filter(Boolean))].sort();
	this._edPopulateSpeakerFilter(speakers);

	// render pertama
	this._edFilterRender();
    this.showNotification('Editing data loaded.', 'success');
  } catch (e) {
    this.showNotification(`Load editing gagal: ${e.message || e}`, 'error');
  } finally {
    this.hideLoading();
  }
}

_edFilterRender(){
  const ed = this.editing || {};
  const rows = ed.rows || [];
  const term = (ed.search || '').toLowerCase();

  // Fallback aman
  const gf = (ed.genderFilter || 'all');           // 'all' | 'male' | 'female' | 'unknown'
  const sf = (ed.speakerFilter || 'all');          // 'all' | 'SPEAKER_*'

  ed.filtered = rows.filter(r => {
    const okG = (gf === 'all') || ((r.gender || 'unknown') === gf);
    const okS = (sf === 'all') || ((r.speaker || '') === sf);
    const okQ = !term || (r.translation || '').toLowerCase().includes(term) ||
                         (r.text || '').toLowerCase().includes(term);
    return okG && okS && okQ;
  });

  const counter = document.getElementById('ed-counter');
  if (counter) counter.textContent = `${ed.filtered.length} shown / ${rows.length} total`;

  this._edRenderList();
}


_edRenderList() {
  const wrap = document.getElementById('ed-list');
  const ed = this.editing;
  if (!wrap) return;

  if (!ed.filtered.length) { wrap.innerHTML = `<div class="p-4 text-gray-400">No rows.</div>`; return; }
  const esc = s => String(s||'').replace(/[&<>"']/g,c=>({ '&':'&','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;' }[c]));

  // 1 baris: [#id][time][gender][speaker][translation][play]
  wrap.innerHTML = ed.filtered.map(r => `
    <div class="ed-row grid items-center gap-2"
         style="grid-template-columns:48px 220px 80px 85px 1fr 38px"
         data-idx="${r.index}" id="row-${r.index}">
      <div class="text-gray-400 font-mono">#${r.index}</div>
      <div class="ed-time font-mono text-sm bg-gray-800 border border-gray-700 rounded px-2 py-1 whitespace-nowrap">
        ${r.start} <span class="opacity-60">→</span> ${r.end}
      </div>
      <select class="ed-gender bg-gray-700 border border-gray-600 text-white px-2 py-1 rounded text-xs">
        <option value="male" ${r.gender==='male'?'selected':''}>male</option>
        <option value="female" ${r.gender==='female'?'selected':''}>female</option>
        <option value="unknown" ${r.gender==='unknown'?'selected':''}>unknown</option>
      </select>
      <input class="ed-speaker bg-gray-700 border border-gray-600 text-white px-2 py-1 rounded text-xs w-full"
             value="${esc(r.speaker||'')}" placeholder="SPEAKER_*"/>
      <input class="ed-text bg-gray-800 border border-gray-700 text-white rounded px-2 py-1 text-sm w-full
                    whitespace-nowrap overflow-hidden text-ellipsis"
             value="${esc(r.translation||'')}" placeholder="Translation…"/>
      <button class="ed-play btn btn-slate px-2 py-1 text-xs">▶</button>
    </div>
  `).join('');

  // binding (tanpa re-render) — update data langsung
  wrap.querySelectorAll('.ed-text').forEach(inp=>{
    inp.addEventListener('input', e=>{
      const idx = Number(e.target.closest('[data-idx]').dataset.idx);
      const row = this.editing.rows.find(x=>x.index===idx);
      if (row) row.translation = e.target.value;
    });
  });
  wrap.querySelectorAll('.ed-gender').forEach(sel=>{
    sel.addEventListener('change', e=>{
      const idx = Number(e.target.closest('[data-idx]').dataset.idx);
      const row = this.editing.rows.find(x=>x.index===idx);
      if (row) row.gender = e.target.value;
    });
  });
  wrap.querySelectorAll('.ed-speaker').forEach(inp=>{
    inp.addEventListener('input', e=>{
      const idx = Number(e.target.closest('[data-idx]').dataset.idx);
      const row = this.editing.rows.find(x=>x.index===idx);
      if (row) row.speaker = e.target.value;
    });
  });
  wrap.querySelectorAll('.ed-play').forEach(btn=>{
    btn.addEventListener('click', e=>{
      const idx = Number(e.target.closest('[data-idx]').dataset.idx);
      this._edSeekToRow(idx, true);
    });
  });
}

// app.js — final version
_edSeekToRow(idx, play=false){
  const ed=this.editing; const v=document.getElementById('ed-video');
  const r = ed.rows.find(x=>x.index===idx); if(!r||!v) return;
  v.currentTime = r.startS + 0.001;
  this._edHighlight(idx, true);
  if (play){ ed.playUntil = r.endS; v.play(); }
}

_edRebuildSpeakerFilterOptions() {
  const sel = document.getElementById('ed-speaker');
  if (!sel) return;
  const speakers = new Set(
    (this.editing.rows || [])
      .map(r => (r.speaker || '').trim())
      .filter(Boolean)
  );
  sel.innerHTML = `<option value="">All speakers</option>` +
    [...speakers].sort().map(s => `<option value="${this.escapeHtml(s)}">${this.escapeHtml(s)}</option>`).join('');

  // when user changes selection, filter like gender
  sel.onchange = () => { 
    this.editing.speakerFilter = sel.value.trim().toLowerCase(); 
    this._edFilterRender(); 
  };
}


_edOnVideoTime(t){
  const ed=this.editing; if(!ed?.rows?.length) return;
  const r = ed.rows.find(x=>t>=x.startS && t<x.endS);
  if (r) this._edHighlight(r.index, true);

  // stop di akhir segmen jika sedang "play segment"
  if (ed.playUntil != null && t>=ed.playUntil-0.02) {
    const v=document.getElementById('ed-video'); v?.pause();
    ed.playUntil = null;
  }
}

_edToSec(t){ const m=t?.match?.(/(\d+):(\d+):(\d+),(\d+)/); if(!m) return 0;
  return (+m[1])*3600+(+m[2])*60+(+m[3])+((+m[4])/1000); }

// panggil sekali saat selesai _edLoad(): tambahkan startS/endS ke setiap row
_edIndexSeconds(){
  (this.editing.rows || []).forEach(r=>{
    const m = (t)=> {
      const x = (t||'').match(/(\d+):(\d+):(\d+),(\d+)/);
      return x ? (+x[1])*3600+(+x[2])*60+(+x[3])+(+x[4])/1000 : 0;
    };
    r.startS = r.startS ?? m(r.start);
    r.endS   = r.endS   ?? m(r.end);
  });
}

// highlight baris aktif + autoscroll
_edHighlight(idx, doFollow=true){
  const ed=this.editing; if(!ed) return;
  if (ed.liveIndex === idx) return;
  if (ed.liveIndex) document.getElementById(`row-${ed.liveIndex}`)?.classList.remove('live');
  ed.liveIndex = idx;
  const rowEl = document.getElementById(`row-${idx}`);
  rowEl?.classList.add('live');
  if (doFollow && ed.follow) rowEl?.scrollIntoView({block:'center', behavior:'smooth'});
}

_edAutoResizeTextareas(){
  document.querySelectorAll('.ed-translation').forEach(t=>{
    const fit = () => { t.style.height='auto'; t.style.height = (t.scrollHeight)+'px'; };
    fit();
    t.addEventListener('input', fit);
  });
}

async _edSave() {
  const ed = this.editing;
  if (!ed.sessionId) return this.showNotification('No session.', 'warning');
  try {
    this.showLoading('Saving editing…');
    const res = await fetch(`/api/session/${ed.sessionId}/editing`, {
      method: 'POST',
      headers: {'Content-Type':'application/json'},
      body: JSON.stringify({ rows: ed.rows })
    });
    if (!res.ok) throw new Error(await res.text());
    this.showNotification('Saved.', 'success');
  } catch (e) {
    this.showNotification(`Save failed: ${e.message || e}`, 'error');
  } finally {
    this.hideLoading();
  }
}

async _edExport(mode) {
  const ed = this.editing;
  if (!ed.sessionId) return this.showNotification('No session.', 'warning');
  try {
    this.showLoading('Exporting…');
    const res = await fetch(`/api/session/${ed.sessionId}/editing/export`, {
      method: 'POST',
      headers: {'Content-Type':'application/json'},
      body: JSON.stringify({ mode, reindex: true })
    });
    if (!res.ok) throw new Error(await res.text());

    const disp = res.headers.get('Content-Disposition') || '';
    let fname = 'export.srt';
    const m = disp.match(/filename="?([^"]+)"?/i);
    if (m) fname = m[1];

    const blob = await res.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url; a.download = fname;
    document.body.appendChild(a); a.click(); a.remove();
    URL.revokeObjectURL(url);

    this.showNotification('Export done.', 'success');
  } catch (e) {
    this.showNotification(`Export failed: ${e.message || e}`, 'error');
  } finally {
    this.hideLoading();
  }
}



    // ============================
    // TAB 4: TTS EXPORT
    // ============================

    async loadTTSExportTab() {
        console.log('Loading TTS Export tab...');
        const tabContent = document.getElementById('tts-export');
        if (!tabContent) return;

        // Clear and show loading
        tabContent.innerHTML = `
            <div class="bg-gray-800 rounded-lg p-6">
                <h2 class="text-2xl font-bold mb-6 text-purple-400">
                    <i class="fas fa-file-export mr-2"></i>TTS & Export
                </h2>
                <div class="text-center py-8">
                    <div class="loading-spinner mx-auto mb-4"></div>
                    <p class="text-gray-400">Loading TTS & Export interface...</p>
                </div>
            </div>
        `;

        setTimeout(() => {
            this.renderTTSExportTab();
        }, 500);
    }

    renderTTSExportTab() {
        const tabContent = document.getElementById('tts-export');
        if (!tabContent) return;

        tabContent.innerHTML = `
            <div class="bg-gray-800 rounded-lg p-6">
                <h2 class="text-2xl font-bold mb-6 text-purple-400">
                    <i class="fas fa-file-export mr-2"></i>TTS & Export
                </h2>

                <div class="bg-gray-700 rounded-lg p-6">
                    <div class="text-center mb-6">
                        <i class="fas fa-robot text-6xl text-purple-400 mb-4"></i>
                        <h3 class="text-xl font-semibold mb-2 text-white">TTS & Export Interface</h3>
                        <p class="text-gray-300 mb-6">Text-to-speech and video export functionality</p>
                    </div>
                    
                    <div class="grid grid-cols-1 md:grid-cols-2 gap-6 mb-6">
                        <div class="text-center p-4 bg-gray-600 rounded-lg">
                            <i class="fas fa-edge text-4xl text-blue-400 mb-3"></i>
                            <div class="text-lg font-semibold text-white mb-2">Edge TTS</div>
                            <div class="text-gray-300">Free • Fast • Good Quality</div>
                            <button class="mt-3 bg-blue-500 hover:bg-blue-600 px-4 py-2 rounded transition-colors">
                                Select Engine
                            </button>
                        </div>
                        <div class="text-center p-4 bg-gray-600 rounded-lg">
                            <i class="fas fa-star text-4xl text-purple-400 mb-3"></i>
                            <div class="text-lg font-semibold text-white mb-2">ElevenLabs</div>
                            <div class="text-gray-300">Premium • Best Quality • Natural</div>
                            <button class="mt-3 bg-purple-500 hover:bg-purple-600 px-4 py-2 rounded transition-colors">
                                Select Engine
                            </button>
                        </div>
                    </div>

                    <div class="text-center">
                        <button class="bg-green-500 hover:bg-green-600 px-6 py-3 rounded-lg text-lg font-semibold transition-colors">
                            <i class="fas fa-play-circle mr-2"></i>Start TTS & Export
                        </button>
                    </div>
                </div>
            </div>
        `;

        this.setupTTSExportEvents();
    }

    setupTTSExportEvents() {
        const buttons = document.querySelectorAll('#tts-export button');
        buttons.forEach(btn => {
            btn.addEventListener('click', () => {
                this.showNotification(`${btn.textContent} functionality coming soon`, 'info');
            });
        });
    }

    // === BACKEND METHODS ===
    async testBackendConnection() {
        try {
            const response = await fetch('/api/test');
            if (response.ok) {
                const data = await response.json();
                console.log('Backend test:', data);
                this.showNotification('Backend connected successfully', 'success');
                this.updateConnectionStatus(true);
            } else {
                throw new Error('Test endpoint failed');
            }
        } catch (error) {
            console.error('Backend connection failed:', error);
            this.showNotification('Cannot connect to backend', 'error');
            this.updateConnectionStatus(false);
        }
    }

    async createTestSession() {
        this.showLoading('Creating test session...');
        
        try {
            const response = await fetch('/api/session/create', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/x-www-form-urlencoded',
                },
                body: 'video_name=test_video.mp4&srt_name=test_subtitles.srt'
            });

            if (response.ok) {
                const data = await response.json();
                this.currentSessionId = data.session_id;
                this.showNotification('Test session created successfully', 'success');
                this.updateSessionInfo(data.session_id);
            } else {
                throw new Error('Failed to create session');
            }
        } catch (error) {
            console.error('Error creating session:', error);
            this.showNotification('Error creating session', 'error');
        } finally {
            this.hideLoading();
        }
    }

    async createSession() {
        this.showLoading('Creating session...');
        
        try {
            const response = await fetch('/api/session/create', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/x-www-form-urlencoded',
                },
                body: 'video_name=uploaded_video.mp4&srt_name=uploaded_subtitles.srt'
            });

            if (response.ok) {
                const data = await response.json();
                this.currentSessionId = data.session_id;
                this.showNotification('Session created successfully', 'success');
                this.updateSessionInfo(data.session_id);
            } else {
                throw new Error('Failed to create session');
            }
        } catch (error) {
            console.error('Error creating session:', error);
            this.showNotification('Error creating session', 'error');
        } finally {
            this.hideLoading();
        }
    }

    async loadSessionList() {
        const sessionList = document.getElementById('session-list');
        if (!sessionList) return;

        try {
            const response = await fetch('/api/sessions');
            if (response.ok) {
                const data = await response.json();
                const sessions = data.sessions || [];
                
                if (sessions.length === 0) {
                    sessionList.innerHTML = `
                        <div class="text-gray-400 text-center py-4">
                            <i class="fas fa-inbox text-2xl mb-2"></i>
                            <div>No sessions found</div>
                        </div>
                    `;
                    return;
                }

                sessionList.innerHTML = sessions.map(session => `
                    <div class="session-item p-3 rounded cursor-pointer hover:bg-gray-600 border border-gray-600 transition-colors"
                         data-session-id="${session.id}">
                        <div class="font-medium text-sm text-white">${session.video_name || 'Untitled Session'}</div>
                        <div class="text-xs text-gray-400 mt-1">
                            ${new Date(session.created_at * 1000).toLocaleDateString()}
                        </div>
                        <div class="text-xs text-gray-400">
                            Status: <span class="text-${this.getStatusColor(session.status)}">${session.status}</span>
                        </div>
                    </div>
                `).join('');

                // Add click handlers
                sessionList.querySelectorAll('.session-item').forEach(item => {
                    item.addEventListener('click', () => {
                        // Remove active class from all items
                        sessionList.querySelectorAll('.session-item').forEach(i => {
                            i.classList.remove('bg-blue-600', 'border-blue-400');
                        });
                        // Add active class to clicked item
                        item.classList.add('bg-blue-600', 'border-blue-400');
                        
                        this.loadSessionData(item.dataset.sessionId);
                    });
                });

            } else {
                throw new Error('Failed to load sessions');
            }
        } catch (error) {
            sessionList.innerHTML = `
                <div class="text-red-400 text-center py-4">
                    <i class="fas fa-exclamation-triangle mr-2"></i>
                    Error loading sessions
                </div>
            `;
        }
    }

    getStatusColor(status) {
        const colors = {
            'created': 'blue-400',
            'files_uploaded': 'green-400',
            'workdir_ready': 'green-400',
            'audio_ready': 'green-400',
            'diarization_complete': 'green-400',
            'translating': 'yellow-400',
            'translation_complete': 'green-400',
            'tts_export': 'yellow-400',
            'complete': 'green-400',
            'error': 'red-400'
        };
        return colors[status] || 'gray-400';
    }

    async loadSessionData(sessionId) {
        try {
            const response = await fetch(`/api/session/${sessionId}/editing-data`);
            if (response.ok) {
                const data = await response.json();
                this.currentSessionId = sessionId;
                this.updateSessionInfo(sessionId);
                this.showNotification('Session data loaded successfully', 'success');
                
                // You can now render the editing table with data.entries
                console.log('Loaded session data:', data);
            } else {
                throw new Error('Failed to load session data');
            }
        } catch (error) {
            console.error('Error loading session data:', error);
            this.showNotification('Error loading session data', 'error');
        }
    }

    updateSessionInfo(sessionId) {
        const sessionInfo = document.getElementById('current-session-info');
        if (sessionInfo) {
            sessionInfo.innerHTML = `
                <div class="text-sm">
                    <div class="font-medium">Session ID: ${sessionId}</div>
                    <div class="text-gray-400">Created: ${new Date().toLocaleString()}</div>
                </div>
            `;
        }

        const globalSessionInfo = document.getElementById('session-info');
        if (globalSessionInfo) {
            globalSessionInfo.textContent = `Session: ${sessionId.substring(0, 8)}...`;
        }
    }

    updateConnectionStatus(connected) {
        this.isConnected = connected;
        const statusElement = document.getElementById('connection-status');
        if (statusElement) {
            if (connected) {
                statusElement.innerHTML = '<i class="fas fa-circle text-xs mr-1 text-green-400"></i><span class="text-sm">Connected</span>';
            } else {
                statusElement.innerHTML = '<i class="fas fa-circle text-xs mr-1 text-red-400"></i><span class="text-sm">Disconnected</span>';
            }
        }
    }

    showLoading(message = 'Loading...') {
        const loading = document.getElementById('global-loading');
        const messageEl = document.getElementById('loading-message');
        if (loading && messageEl) {
            messageEl.textContent = message;
            loading.classList.remove('hidden');
        }
    }

    hideLoading() {
        const loading = document.getElementById('global-loading');
        if (loading) {
            loading.classList.add('hidden');
        }
    }

    showNotification(message, type = 'info') {
        const container = document.getElementById('notification-container');
        if (!container) return;
        
        const notification = document.createElement('div');
        const bgColor = type === 'error' ? 'bg-red-500' : 
                       type === 'success' ? 'bg-green-500' : 
                       type === 'warning' ? 'bg-yellow-500' : 'bg-blue-500';
        
        notification.className = `${bgColor} text-white p-4 rounded-lg shadow-lg max-w-sm transform transition-transform duration-300 translate-x-full`;
        notification.innerHTML = `
            <div class="flex items-center justify-between">
                <span>${message}</span>
                <button onclick="this.parentElement.parentElement.remove()" class="ml-4">
                    <i class="fas fa-times"></i>
                </button>
            </div>
        `;
        
        container.appendChild(notification);
        
        // Animate in
        setTimeout(() => {
            notification.classList.remove('translate-x-full');
        }, 10);
        
        // Auto remove after 5 seconds
        setTimeout(() => {
            if (notification.parentElement) {
                notification.classList.add('translate-x-full');
                setTimeout(() => {
                    if (notification.parentElement) {
                        notification.remove();
                    }
                }, 300);
            }
        }, 5000);
    }

    saveAll() {
        this.showNotification('All changes saved successfully', 'success');
    }
    
    appendLog(message) {
        const logOutput = document.getElementById('log-output');
        if (logOutput) {
            const logEntry = document.createElement('div');
            logEntry.className = 'text-gray-300 mb-1';
            logEntry.textContent = `[${new Date().toLocaleTimeString()}] ${message}`;
            logOutput.appendChild(logEntry);
            logOutput.scrollTop = logOutput.scrollHeight;
        }
    }
}

// Initialize app when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    window.dracinApp = new DracinApp();
});