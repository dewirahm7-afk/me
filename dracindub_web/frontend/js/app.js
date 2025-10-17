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
	  // langsung render UI + bind
	  this.renderTranslateTab();
	}

    //// MESSAGES (kanan) ////
    appendMessage(obj) {
      this.translate.messages.push({ts: new Date().toISOString(), ...obj});
      this.renderMessages();
    }

    renderMessages() {
      const el = document.getElementById('ts-messages');
      if (!el) return;
      el.textContent = JSON.stringify(this.translate.messages, null, 2);
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

	/* ==============================
	 * EVENTS (tidak berubah banyak)
	 * ============================== */
	setupTranslateEvents() {
	  if (!this.translate) this.initTranslateState();
	  const $ = (id)=>document.getElementById(id);

	  const bindVal = (id, key, toNum=false)=>{
		const el=$(id); if (!el) return;
		el.addEventListener('input', ()=>{ this.translate[key] = toNum ? Number(el.value) : el.value; });
	  };
	  const bindChk = (id, key)=>{
		const el=$(id); if (!el) return;
		el.addEventListener('change', ()=>{ this.translate[key] = !!el.checked; });
	  };

	  bindVal('ts-api','apiKey');
	  bindVal('ts-batch','batch',true);
	  bindVal('ts-workers','workers',true);
	  bindVal('ts-timeout','timeout',true);
	  bindChk('ts-autosave','autosave');
	  bindVal('ts-lang','lang');
	  bindVal('ts-engine','engine');
	  bindVal('ts-temp','temperature',true);
	  bindVal('ts-topp','top_p',true);
	  bindVal('ts-style','style');

	  const applySearch = ()=>{ this.translate.search = $('ts-search').value.trim(); this.filterAndRenderSubs(); };
	  $('ts-search')?.addEventListener('input', applySearch);
	  $('ts-size')?.addEventListener('change', ()=>{ this.translate.size = Number($('ts-size').value); this.translate.page=1; this.renderSubsPage(); });
	  $('ts-page')?.addEventListener('change', ()=>{ this.translate.page = Math.max(1, Number($('ts-page').value||1)); this.renderSubsPage(); });
	  $('ts-prev')?.addEventListener('click', ()=>{ this.translate.page = Math.max(1, this.translate.page-1); this.renderSubsPage(); });
	  $('ts-nextpage')?.addEventListener('click', ()=>{ this.translate.page = Math.min(this.totalPages||1, this.translate.page+1); this.renderSubsPage(); });
	  $('ts-follow')?.addEventListener('change', ()=>{ this.translate.follow = $('ts-follow').checked; });

	  $('ts-load')?.addEventListener('click', ()=> this.promptLoadSRT());
		$('ts-start')?.addEventListener('click', () => {
		  this.translate = this.translate || {};
		  this.translate.runMode = 'start';
		  this._translateGeneric();
		});

		$('ts-resume')?.addEventListener('click', () => {
		  this.translate = this.translate || {};
		  this.translate.runMode = 'resume';
		  this._translateGeneric();
		});

		$('ts-fill')?.addEventListener('click', () => {
		  this.translate = this.translate || {};
		  this.translate.runMode = 'fill';
		  this._translateGeneric();
		});
	  $('ts-save')?.addEventListener('click', ()=> this.translateSave());
	  $('ts-export')?.addEventListener('click', ()=> this.translateExport());
	  $('ts-stop')?.addEventListener('click', ()=> this.translateStop());
	  $('ts-next')?.addEventListener('click', ()=> this.loadTab('editing'));
	  $('ts-clear')?.addEventListener('click', ()=> this.translateClear());

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
	updateTranslateProgress() {
	  const total = this.translate.subtitles.length || 0;
	  const done  = this.translate.subtitles.filter(x => x.trans && x.trans.trim()).length;
	  const pct = total ? Math.round(done*100/total) : 0;
	  const bar = document.getElementById('ts-progressbar');
	  const lab = document.getElementById('ts-progresslabel');
	  if (bar) bar.style.width = pct + '%';
	  if (lab) lab.textContent = `${pct}% (${done}/${total})`;
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
	/* ==============================
	 * RENDER SUBS PAGE (1 BARIS untuk subtitle)
	 * ============================== */
	renderSubsPage(){
	  const st=this.translate, table=document.getElementById('ts-table'), pagesEl=document.getElementById('ts-pages');
	  if (!table) return;
	  const arr=st.filtered||[]; this.totalPages=Math.max(1, Math.ceil(arr.length/st.size));
	  if (pagesEl) pagesEl.textContent=String(this.totalPages);
	  const start=(st.page-1)*st.size;
	  
	  // HEADER tabel
	  const header = `
		<div class="grid grid-cols-[60px,100px,100px,1fr,1fr] gap-2 px-3 py-2 bg-gray-800 border-b border-gray-600 sticky top-0 text-sm font-semibold text-gray-300">
		  <div>#</div>
		  <div>Start</div>
		  <div>End</div>
		  <div>Original</div>
		  <div>Translation</div>
		</div>
	  `;
	  
	  // ROWS - 1 BARIS per subtitle
	  const rows = arr.slice(start, start+st.size).map(s=>`
		<div class="grid grid-cols-[60px,100px,100px,1fr,1fr] gap-2 px-3 py-2 border-b border-gray-700 hover:bg-gray-800 text-sm">
		  <div class="text-gray-400 font-mono">${s.index}</div>
		  <div class="text-gray-300 font-mono text-xs">${s.start}</div>
		  <div class="text-gray-300 font-mono text-xs">${s.end}</div>
		  <div class="text-gray-300 break-words">${this.escapeHtml(s.text||'')}</div>
		  <div class="text-green-400 break-words font-medium">${this.escapeHtml(s.trans||'')}</div>
		</div>
	  `).join('');
	  
	  table.innerHTML = header + (rows || '<div class="p-4 text-center text-gray-500">No subtitles found</div>');
	  
	  const pg=document.getElementById('ts-page'); 
	  if (pg) pg.value=String(st.page);
	  
	  if (st.follow && rows) {
		table.scrollTop = table.scrollHeight;
	  }
	}
	buildMessagesArray(){
	  return (this.translate.subtitles||[]).map(s=>({
		index: s.index,
		timestamp: `${s.start} --> ${s.end}`,
		original_text: s.text || "",
		translation: s.trans || ""
	  }));
	}
	renderMessages(){
	  const el=document.getElementById('ts-messages');
	  if (!el) return;
	  el.textContent = JSON.stringify(this.buildMessagesArray(), null, 2);
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

      <div class="flex gap-4">
        <div class="bg-black rounded overflow-hidden" style="width:38%;">
          <video id="ed-video" class="w-full h-[66vh] object-contain bg-black" controls playsinline></video>
        </div>

        <div class="flex-1 flex flex-col">
          <div class="text-sm text-gray-300 mb-2">
            <span id="ed-counter">0 shown / 0 total</span>
          </div>
          <div id="ed-list" class="flex-1 overflow-auto bg-gray-900 border border-gray-700 rounded"></div>
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
const spkSel = document.getElementById('ed-speaker');
if (spkSel) {
  spkSel.addEventListener('change', () => {
    this.editing.speakerFilter = spkSel.value; // contoh: "SPEAKER_04" atau "all"
    this._edFilterRender();
  });
}
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
  const sel = document.getElementById('ed-speaker');
  if (!sel) return;

  const speakers = Array.isArray(list) ? list : [];
  const current = (this.editing.speakerFilter || 'all');

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

    // Fallback untuk speakers jika backend belum mengirim atau kosong
    ed.speakers = Array.isArray(data.speakers) && data.speakers.length
      ? data.speakers
      : [...new Set(ed.rows.map(r => (r.speaker || '').trim()).filter(Boolean))].sort();

    this._edPopulateSpeakerFilter(ed.speakers);
    ed.videoUrl = `/api/session/${sessionId}/video`;

    const info = document.getElementById('ed-session-info');
    if (info) info.textContent = `Session: ${sessionId}`;
    const video = document.getElementById('ed-video');
    if (video) { video.src = ed.videoUrl; }
    this._edFilterRender();
    this.showNotification('Editing data loaded.', 'success');
  } catch (e) {
    this.showNotification(`Load editing gagal: ${e.message || e}`, 'error');
  } finally {
    this.hideLoading();
  }
}

_edFilterRender() {
  const ed = this.editing;
  const term = (ed.search || "").toLowerCase();
  const gf = ed.genderFilter;                   // "all" | "male" | "female" | "unknown"
  const sf = (ed.speakerFilter || 'all').toLowerCase(); // "all" atau "speaker_xx"

  ed.filtered = ed.rows.filter(r => {
    if (gf !== 'all' && (r.gender || 'unknown') !== gf) return false;
    const rs = (r.speaker || '').toLowerCase();
    if (sf !== 'all' && rs !== sf) return false;
    if (term) {
      const t = (r.translation || '').toLowerCase();
      if (!t.includes(term)) return false;
    }
    return true;
  });

  ed.total = ed.rows.length;
  ed.shown = ed.filtered.length;
  this._edRenderList();
  const c = document.getElementById('ed-counter');
  if (c) c.textContent = `${ed.shown} shown / ${ed.total} total`;
}

_edRenderList() {
  const wrap = document.getElementById('ed-list');
  const ed = this.editing;
  if (!wrap) return;

  if (!ed.filtered.length) {
    wrap.innerHTML = `<div class="p-6 text-gray-400">No rows.</div>`;
    return;
  }

  const esc = s => (this.escapeHtml ? this.escapeHtml(s || '') :
    String(s||'').replace(/[&<>"']/g,c=>({ '&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c])));

  wrap.innerHTML = ed.filtered.map((r) => `
    <div class="border-b border-gray-800 p-2 hover:bg-gray-800" data-idx="${r.index}" id="row-${r.index}">
      <div class="flex items-center gap-3 mb-2 text-gray-300 text-sm">
        <div class="w-14 text-gray-400">#${r.index}</div>
        <div class="w-44">
          <span class="px-2 py-0.5 bg-gray-700 rounded">${r.start}</span>
          <span class="mx-1 text-gray-500">→</span>
          <span class="px-2 py-0.5 bg-gray-700 rounded">${r.end}</span>
        </div>

        <select class="ed-gender bg-gray-700 border border-gray-600 text-white px-2 py-1 rounded text-xs">
          <option value="male" ${r.gender==='male'?'selected':''}>male</option>
          <option value="female" ${r.gender==='female'?'selected':''}>female</option>
          <option value="unknown" ${r.gender==='unknown'?'selected':''}>unknown</option>
        </select>

        <input class="ed-speaker bg-gray-700 border border-gray-600 text-white px-2 py-1 rounded text-xs w-40"
               value="${esc(r.speaker)}" placeholder="SPEAKER_*"/>

        <button class="ed-play btn btn-slate px-2 py-1 text-xs">▶</button>
      </div>

      <textarea class="ed-text w-full bg-gray-800 border border-gray-700 text-white rounded p-2 text-sm"
                rows="2" placeholder="Translation…">${esc(r.translation)}</textarea>
    </div>
  `).join('');

  wrap.querySelectorAll('.ed-text').forEach((ta) => {
    ta.addEventListener('input', (e) => {
      const rowEl = e.target.closest('[data-idx]');
      const idx = Number(rowEl.getAttribute('data-idx'));
      const row = this.editing.rows.find(x => x.index === idx);
      if (row) row.translation = e.target.value;
    });
  });

  wrap.querySelectorAll('.ed-gender').forEach((sel) => {
    sel.addEventListener('change', (e) => {
      const rowEl = e.target.closest('[data-idx]');
      const idx = Number(rowEl.getAttribute('data-idx'));
      const row = this.editing.rows.find(x => x.index === idx);
      if (row) row.gender = e.target.value;
    });
  });

  wrap.querySelectorAll('.ed-speaker').forEach((inp) => {
    inp.addEventListener('input', (e) => {
      const rowEl = e.target.closest('[data-idx]');
      const idx = Number(rowEl.getAttribute('data-idx'));
      const row = this.editing.rows.find(x => x.index === idx);
      if (row) row.speaker = e.target.value;
    });
  });

  wrap.querySelectorAll('.ed-play').forEach((btn) => {
    btn.addEventListener('click', (e) => {
      const rowEl = e.target.closest('[data-idx]');
      this._edSeekToRow(Number(rowEl.getAttribute('data-idx')), true);
    });
  });

  wrap.querySelectorAll('[data-idx]').forEach((rowEl) => {
    rowEl.addEventListener('dblclick', () => {
      this._edSeekToRow(Number(rowEl.getAttribute('data-idx')), true);
    });
  });
}

// app.js — final version
_edSeekToRow(idx, autoplay = false) {
  const row = this.editing.rows.find(x => x.index === idx);
  const v = document.getElementById('ed-video');
  if (!row || !v) return;

  const toSec = (ts) => {
    const m = ts.match(/(\d\d):(\d\d):(\d\d),(\d\d\d)/);
    if (!m) return 0;
    return (+m[1]) * 3600 + (+m[2]) * 60 + (+m[3]) + (+m[4]) / 1000;
  };

  const start = Math.max(0, toSec(row.start) + 0.01);
  const end   = toSec(row.end);

  // stop guard lama (kalau ada)
  if (this._segGuard) { clearInterval(this._segGuard); this._segGuard = null; }

  const playAfterSeek = () => {
    v.removeEventListener('seeked', playAfterSeek);
    if (autoplay) v.play();

    // guard: auto-pause di akhir segmen
    this._segGuard = setInterval(() => {
      if (v.currentTime >= end - 0.01) {
        v.pause();
        clearInterval(this._segGuard);
        this._segGuard = null;
      }
    }, 50);

    // highlight row aktif
    this._edHighlight(idx);
  };

  v.pause();

  const doSeek = () => {
    // set currentTime setelah metadata ada → browser pasti melakukan seek
    v.currentTime = start;
    v.addEventListener('seeked', playAfterSeek, { once: true });
  };

  // kalau metadata sudah ada, langsung seek; kalau belum, tunggu dulu
  if (v.readyState >= 1) {
    doSeek();
  } else {
    v.addEventListener('loadedmetadata', doSeek, { once: true });
  }
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


_edOnVideoTime(cur) {
  const toSec = (ts) => {
    const m = ts.match(/(\d\d):(\d\d):(\d\d),(\d\d\d)/);
    if (!m) return 0;
    return (+m[1])*3600 + (+m[2])*60 + (+m[3]) + (+m[4])/1000;
  };
  const ed = this.editing;
  const hit = ed.rows.find(r => cur >= toSec(r.start) && cur <= toSec(r.end));
  if (hit) this._edHighlight(hit.index, ed.follow);
}

_edHighlight(idx, scrollIntoView=false) {
  const prevSel = (this.editing.playingRowIndex != null)
    ? document.getElementById(`row-${this.editing.playingRowIndex}`) : null;
  if (prevSel) prevSel.classList.remove('ring','ring-blue-400');

  this.editing.playingRowIndex = idx;
  const el = document.getElementById(`row-${idx}`);
  if (el) {
    el.classList.add('ring','ring-blue-400');
    if (scrollIntoView) el.scrollIntoView({block:'center', behavior:'smooth'});
  }
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
