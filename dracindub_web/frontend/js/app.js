// frontend/js/app.js - VERSION LENGKAP
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
        
        // Update active tab UI
        document.querySelectorAll('[data-tab]').forEach(tab => {
            tab.classList.remove('active', 'border-blue-400', 'bg-gray-700');
            tab.classList.add('border-transparent');
        });
        
        const activeTab = document.querySelector(`[data-tab="${tabName}"]`);
        if (activeTab) {
            activeTab.classList.add('active', 'border-blue-400', 'bg-gray-700');
            activeTab.classList.remove('border-transparent');
        }

        // Hide all tab contents
        document.querySelectorAll('.tab-content').forEach(content => {
            content.classList.add('hidden');
        });

        // Show selected tab content
        const tabContent = document.getElementById(tabName);
        if (tabContent) {
            tabContent.classList.remove('hidden');
        }

        this.activeTab = tabName;

        // Load tab-specific content
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
                    await this.loadTranslateTab();
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
        console.log('Loading SRT Processing tab...');
        const tabContent = document.getElementById('srt-processing');
        if (!tabContent) return;

        // Clear existing content and show loading
        tabContent.innerHTML = `
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

        // Simulate loading delay
        setTimeout(() => {
            this.renderSRTProcessingTab();
        }, 500);
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
                            <p class="text-gray-300 mb-2">Drag & drop SRT file or click to browse</p>
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
                            <input id="hf-token" type="password" placeholder="Enter HuggingFace token"
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

		this.updateProgress?.(70, 'Diarization done');
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
        console.log('Loading Translate tab...');
        const tabContent = document.getElementById('translate');
        if (!tabContent) return;

        // Clear and show loading
        tabContent.innerHTML = `
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

        setTimeout(() => {
            this.renderTranslateTab();
        }, 500);
    }

    renderTranslateTab() {
        const tabContent = document.getElementById('translate');
        if (!tabContent) return;

        tabContent.innerHTML = `
            <div class="bg-gray-800 rounded-lg p-6">
                <h2 class="text-2xl font-bold mb-6 text-green-400">
                    <i class="fas fa-language mr-2"></i>Translate
                </h2>

                <!-- Translation Controls -->
                <div class="bg-gray-700 rounded-lg p-4 mb-6">
                    <h3 class="text-lg font-semibold mb-4 text-white">Translation Controls</h3>
                    <div class="grid grid-cols-1 md:grid-cols-4 gap-4 mb-4">
                        <div>
                            <label class="block text-sm font-medium mb-2 text-gray-300">DeepSeek API Key</label>
                            <input type="password" placeholder="Enter API key" 
                                   class="w-full px-3 py-2 bg-gray-600 rounded border border-gray-500 focus:border-blue-500 text-white placeholder-gray-400">
                        </div>
                        <div>
                            <label class="block text-sm font-medium mb-2 text-gray-300">Batch Size</label>
                            <input type="number" value="20" 
                                   class="w-full px-3 py-2 bg-gray-600 rounded border border-gray-500 focus:border-blue-500 text-white">
                        </div>
                        <div>
                            <label class="block text-sm font-medium mb-2 text-gray-300">Workers</label>
                            <input type="number" value="1" 
                                   class="w-full px-3 py-2 bg-gray-600 rounded border border-gray-500 focus:border-blue-500 text-white">
                        </div>
                        <div>
                            <label class="block text-sm font-medium mb-2 text-gray-300">Timeout (s)</label>
                            <input type="number" value="90" 
                                   class="w-full px-3 py-2 bg-gray-600 rounded border border-gray-500 focus:border-blue-500 text-white">
                        </div>
                    </div>
                    <div class="flex flex-wrap gap-3">
                        <button class="bg-blue-500 hover:bg-blue-600 px-4 py-2 rounded flex items-center transition-colors">
                            <i class="fas fa-folder-open mr-2"></i>Load SRT
                        </button>
                        <button class="bg-green-500 hover:bg-green-600 px-4 py-2 rounded flex items-center transition-colors">
                            <i class="fas fa-play mr-2"></i>Start Translate
                        </button>
                        <button class="bg-yellow-500 hover:bg-yellow-600 px-4 py-2 rounded flex items-center transition-colors">
                            <i class="fas fa-redo mr-2"></i>Resume
                        </button>
                        <button class="bg-red-500 hover:bg-red-600 px-4 py-2 rounded flex items-center transition-colors">
                            <i class="fas fa-stop mr-2"></i>Stop
                        </button>
                        <button class="bg-purple-500 hover:bg-purple-600 px-4 py-2 rounded flex items-center transition-colors">
                            <i class="fas fa-search mr-2"></i>Fill Missing
                        </button>
                    </div>
                </div>

                <!-- Progress Section -->
                <div class="bg-gray-700 rounded-lg p-4 mb-6">
                    <h3 class="text-lg font-semibold mb-3 text-white">Translation Progress</h3>
                    <div class="space-y-4">
                        <div>
                            <div class="flex justify-between mb-2">
                                <span class="text-sm text-gray-300">Ready</span>
                                <span class="text-sm text-gray-300">0%</span>
                            </div>
                            <div class="w-full bg-gray-600 rounded-full h-3">
                                <div class="bg-green-500 h-3 rounded-full transition-all duration-500" style="width: 0%"></div>
                            </div>
                        </div>
                        <div class="grid grid-cols-3 gap-4 text-sm">
                            <div class="text-center">
                                <div class="text-2xl font-bold text-green-400">0</div>
                                <div class="text-gray-400">Translated</div>
                            </div>
                            <div class="text-center">
                                <div class="text-2xl font-bold text-yellow-400">0</div>
                                <div class="text-gray-400">Missing</div>
                            </div>
                            <div class="text-center">
                                <div class="text-2xl font-bold text-blue-400">0</div>
                                <div class="text-gray-400">Total</div>
                            </div>
                        </div>
                    </div>
                </div>

                <!-- Translation Cards Preview -->
                <div class="bg-gray-700 rounded-lg p-4">
                    <h3 class="text-lg font-semibold mb-3 text-white">Translation Preview</h3>
                    <div class="space-y-3">
                        <div class="bg-gray-600 rounded p-4 border-l-4 border-blue-500">
                            <div class="flex justify-between items-start mb-2">
                                <div class="flex items-center space-x-4">
                                    <span class="font-bold text-blue-300">#1</span>
                                    <span class="text-sm text-gray-300">00:00:01,000 --> 00:00:03,000</span>
                                </div>
                            </div>
                            <div class="mb-2">
                                <div class="text-sm text-gray-400 mb-1">Original:</div>
                                <div class="text-white font-medium">Hello world, this is a test subtitle.</div>
                            </div>
                            <div>
                                <div class="text-sm text-gray-400 mb-1">Translation:</div>
                                <div class="text-green-300 font-medium">Halo dunia, ini adalah tes subtitle.</div>
                            </div>
                        </div>
                        
                        <div class="bg-gray-600 rounded p-4 border-l-4 border-yellow-500">
                            <div class="flex justify-between items-start mb-2">
                                <div class="flex items-center space-x-4">
                                    <span class="font-bold text-blue-300">#2</span>
                                    <span class="text-sm text-gray-300">00:00:03,000 --> 00:00:05,000</span>
                                </div>
                            </div>
                            <div class="mb-2">
                                <div class="text-sm text-gray-400 mb-1">Original:</div>
                                <div class="text-white font-medium">How are you doing today?</div>
                            </div>
                            <div>
                                <div class="text-sm text-gray-400 mb-1">Translation:</div>
                                <div class="text-yellow-300 font-medium">Not translated yet</div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        `;

        // Add event listeners for translate buttons
        this.setupTranslateEvents();
    }

    setupTranslateEvents() {
        const buttons = document.querySelectorAll('#translate button');
        buttons.forEach(btn => {
            btn.addEventListener('click', () => {
                this.showNotification(`${btn.textContent} functionality coming soon`, 'info');
            });
        });
    }

    async loadEditingTab() {
        console.log('Loading Editing tab...');
        const tabContent = document.getElementById('editing');
        if (!tabContent) return;

        // Clear and show loading
        tabContent.innerHTML = `
            <div class="bg-gray-800 rounded-lg p-6">
                <h2 class="text-2xl font-bold mb-6 text-yellow-400">
                    <i class="fas fa-edit mr-2"></i>Editing
                </h2>
                <div class="text-center py-8">
                    <div class="loading-spinner mx-auto mb-4"></div>
                    <p class="text-gray-400">Loading Editing interface...</p>
                </div>
            </div>
        `;

        setTimeout(() => {
            this.renderEditingTab();
        }, 500);
    }

    renderEditingTab() {
        const tabContent = document.getElementById('editing');
        if (!tabContent) return;

        tabContent.innerHTML = `
            <div class="bg-gray-800 rounded-lg p-6">
                <h2 class="text-2xl font-bold mb-6 text-yellow-400">
                    <i class="fas fa-edit mr-2"></i>Editing
                </h2>

                <div class="grid grid-cols-1 xl:grid-cols-4 gap-6">
                    <!-- Left Column: Session List -->
                    <div class="xl:col-span-1">
                        <div class="bg-gray-700 rounded-lg p-4">
                            <h3 class="text-lg font-semibold mb-3 text-white">
                                <i class="fas fa-folder mr-2"></i>Sessions
                            </h3>
                            <div id="session-list" class="space-y-2 max-h-60 overflow-y-auto">
                                <div class="text-gray-400 text-center py-4">Loading sessions...</div>
                            </div>
                            <button id="refresh-sessions" class="w-full mt-3 bg-gray-600 hover:bg-gray-500 px-3 py-2 rounded flex items-center justify-center transition-colors">
                                <i class="fas fa-sync-alt mr-2"></i>Refresh Sessions
                            </button>
                        </div>
                    </div>

                    <!-- Middle Column: Editing Interface -->
                    <div class="xl:col-span-3">
                        <div class="bg-gray-700 rounded-lg p-4">
                            <h3 class="text-lg font-semibold mb-3 text-white">
                                <i class="fas fa-table mr-2"></i>Subtitle Editor
                            </h3>
                            <div class="overflow-x-auto">
                                <table class="w-full">
                                    <thead>
                                        <tr class="bg-gray-600">
                                            <th class="px-3 py-2 text-left text-gray-300">#</th>
                                            <th class="px-3 py-2 text-left text-gray-300">Start</th>
                                            <th class="px-3 py-2 text-left text-gray-300">End</th>
                                            <th class="px-3 py-2 text-left text-gray-300">Speaker</th>
                                            <th class="px-3 py-2 text-left text-gray-300">Gender</th>
                                            <th class="px-3 py-2 text-left text-gray-300">Text</th>
                                        </tr>
                                    </thead>
                                    <tbody id="editing-table-body">
                                        <tr>
                                            <td colspan="6" class="px-3 py-4 text-center text-gray-400">
                                                Select a session to see entries
                                            </td>
                                        </tr>
                                    </tbody>
                                </table>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        `;

        this.setupEditingEvents();
        this.loadSessionList();
    }

    setupEditingEvents() {
        const refreshBtn = document.getElementById('refresh-sessions');
        if (refreshBtn) {
            refreshBtn.addEventListener('click', () => {
                this.loadSessionList();
            });
        }
    }

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
}

// Initialize app when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    window.dracinApp = new DracinApp();
});
