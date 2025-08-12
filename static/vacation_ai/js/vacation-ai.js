/**
 * Vacation AI Frontend JavaScript Library
 * Enhanced interactivity and real-time features for the vacation AI system
 */

class VacationAI {
    constructor() {
        this.init();
        this.bindEvents();
        this.setupWebSocket();
    }

    init() {
        console.log('🌍 Vacation AI System Initialized');
        this.loadingOverlay = this.createLoadingOverlay();
        this.notificationContainer = this.createNotificationContainer();
        this.setupProgressTracking();
    }

    // ======================
    // Real-time AI Suggestions
    // ======================
    
    setupAISuggestions() {
        const suggestionElements = document.querySelectorAll('[data-ai-suggest]');
        
        suggestionElements.forEach(element => {
            const triggerEvent = element.dataset.triggerEvent || 'input';
            const suggestionType = element.dataset.aiSuggest;
            const delay = parseInt(element.dataset.delay) || 1000;
            
            let timeoutId;
            
            element.addEventListener(triggerEvent, () => {
                clearTimeout(timeoutId);
                timeoutId = setTimeout(() => {
                    this.generateAISuggestion(element, suggestionType);
                }, delay);
            });
        });
    }

    async generateAISuggestion(element, type) {
        try {
            const formData = this.gatherFormContext(element);
            const response = await this.apiCall('/vacation-ai/api/suggest/', {
                type: type,
                context: formData
            });

            if (response.success) {
                this.displaySuggestion(element, response.suggestion);
            }
        } catch (error) {
            console.error('AI Suggestion error:', error);
        }
    }

    displaySuggestion(element, suggestion) {
        let suggestionBox = element.parentNode.querySelector('.ai-suggestion-box');
        
        if (!suggestionBox) {
            suggestionBox = document.createElement('div');
            suggestionBox.className = 'ai-suggestion-box';
            suggestionBox.innerHTML = `
                <div class="suggestion-header">
                    <i class="fas fa-robot"></i>
                    <span>AI Suggestion</span>
                    <button class="suggestion-close">&times;</button>
                </div>
                <div class="suggestion-content"></div>
                <div class="suggestion-actions">
                    <button class="btn-apply">Apply</button>
                    <button class="btn-dismiss">Dismiss</button>
                </div>
            `;
            element.parentNode.appendChild(suggestionBox);
            
            // Bind suggestion actions
            this.bindSuggestionActions(suggestionBox, element, suggestion);
        }
        
        suggestionBox.querySelector('.suggestion-content').textContent = suggestion.text;
        suggestionBox.style.display = 'block';
        
        // Animate in
        setTimeout(() => suggestionBox.classList.add('show'), 10);
    }

    bindSuggestionActions(suggestionBox, targetElement, suggestion) {
        const applyBtn = suggestionBox.querySelector('.btn-apply');
        const dismissBtn = suggestionBox.querySelector('.btn-dismiss');
        const closeBtn = suggestionBox.querySelector('.suggestion-close');

        applyBtn.addEventListener('click', () => {
            if (suggestion.action === 'set_value') {
                targetElement.value = suggestion.value;
                targetElement.dispatchEvent(new Event('change'));
            } else if (suggestion.action === 'add_tags') {
                this.addTagsToElement(targetElement, suggestion.tags);
            }
            this.hideSuggestion(suggestionBox);
        });

        dismissBtn.addEventListener('click', () => {
            this.hideSuggestion(suggestionBox);
        });

        closeBtn.addEventListener('click', () => {
            this.hideSuggestion(suggestionBox);
        });
    }

    hideSuggestion(suggestionBox) {
        suggestionBox.classList.remove('show');
        setTimeout(() => {
            suggestionBox.style.display = 'none';
        }, 300);
    }

    // ======================
    // Real-time Progress Tracking
    // ======================
    
    setupProgressTracking() {
        this.progressTrackers = new Map();
    }

    trackAnalysisProgress(analysisId) {
        if (this.progressTrackers.has(analysisId)) {
            return; // Already tracking
        }

        const tracker = {
            id: analysisId,
            interval: setInterval(() => {
                this.checkAnalysisStatus(analysisId);
            }, 5000),
            startTime: Date.now()
        };

        this.progressTrackers.set(analysisId, tracker);
        console.log(`📊 Started tracking analysis ${analysisId}`);
    }

    async checkAnalysisStatus(analysisId) {
        try {
            const response = await this.apiCall(`/vacation-ai/api/analysis-status/${analysisId}/`);
            
            if (response.status === 'completed') {
                this.handleAnalysisComplete(analysisId, response);
            } else if (response.status === 'failed') {
                this.handleAnalysisError(analysisId, response);
            } else {
                this.updateProgressUI(analysisId, response);
            }
        } catch (error) {
            console.error('Progress tracking error:', error);
        }
    }

    handleAnalysisComplete(analysisId, response) {
        const tracker = this.progressTrackers.get(analysisId);
        if (tracker) {
            clearInterval(tracker.interval);
            this.progressTrackers.delete(analysisId);
        }

        this.showNotification('success', '✅ Analysis Complete!', 'Your vacation report is ready.');
        
        // Auto-redirect or show completion UI
        setTimeout(() => {
            window.location.href = response.redirect_url || `/vacation-ai/payment/${analysisId}/`;
        }, 2000);
    }

    handleAnalysisError(analysisId, response) {
        const tracker = this.progressTrackers.get(analysisId);
        if (tracker) {
            clearInterval(tracker.interval);
            this.progressTrackers.delete(analysisId);
        }

        this.showNotification('error', '❌ Analysis Failed', response.error || 'Please try again.');
    }

    updateProgressUI(analysisId, status) {
        // Update progress bars, step indicators, etc.
        const progressElements = document.querySelectorAll(`[data-analysis-id="${analysisId}"]`);
        
        progressElements.forEach(element => {
            if (element.classList.contains('progress-step')) {
                this.updateProgressStep(element, status);
            } else if (element.classList.contains('progress-bar')) {
                this.updateProgressBar(element, status);
            }
        });

        // Update ETA
        this.updateETA(analysisId, status);
    }

    updateProgressStep(element, status) {
        const step = parseInt(element.dataset.step);
        const currentStep = status.current_step || 1;
        
        element.classList.remove('pending', 'active', 'completed');
        
        if (step < currentStep) {
            element.classList.add('completed');
        } else if (step === currentStep) {
            element.classList.add('active');
        } else {
            element.classList.add('pending');
        }
    }

    updateProgressBar(element, status) {
        const progress = status.progress_percentage || 0;
        const progressBar = element.querySelector('.progress-fill') || element;
        progressBar.style.width = `${progress}%`;
        
        const progressText = element.querySelector('.progress-text');
        if (progressText) {
            progressText.textContent = `${Math.round(progress)}%`;
        }
    }

    updateETA(analysisId, status) {
        const etaElements = document.querySelectorAll(`[data-eta-for="${analysisId}"]`);
        
        etaElements.forEach(element => {
            if (status.estimated_completion) {
                const eta = new Date(status.estimated_completion);
                const now = new Date();
                const remaining = Math.max(0, eta - now);
                
                element.textContent = this.formatTimeRemaining(remaining);
            }
        });
    }

    formatTimeRemaining(milliseconds) {
        if (milliseconds < 60000) {
            return 'Less than a minute';
        }
        
        const minutes = Math.floor(milliseconds / 60000);
        const seconds = Math.floor((milliseconds % 60000) / 1000);
        
        if (minutes > 0) {
            return `${minutes}:${seconds.toString().padStart(2, '0')}`;
        }
        
        return `${seconds} seconds`;
    }

    // ======================
    // Enhanced Form Interactions
    // ======================
    
    enhanceForms() {
        this.setupSmartValidation();
        this.setupAutoSave();
        this.setupDynamicFields();
        this.setupBudgetCalculator();
    }

    setupSmartValidation() {
        const forms = document.querySelectorAll('form[data-smart-validation]');
        
        forms.forEach(form => {
            const inputs = form.querySelectorAll('input, select, textarea');
            
            inputs.forEach(input => {
                input.addEventListener('blur', () => {
                    this.validateField(input);
                });
                
                input.addEventListener('input', () => {
                    this.clearValidationErrors(input);
                });
            });
        });
    }

    async validateField(input) {
        const validationType = input.dataset.validate;
        if (!validationType) return;

        try {
            const response = await this.apiCall('/vacation-ai/api/validate-field/', {
                field: input.name,
                value: input.value,
                type: validationType
            });

            if (!response.valid) {
                this.showFieldError(input, response.message);
            } else {
                this.showFieldSuccess(input);
            }
        } catch (error) {
            console.error('Validation error:', error);
        }
    }

    showFieldError(input, message) {
        this.clearValidationErrors(input);
        
        input.classList.add('is-invalid');
        
        const errorDiv = document.createElement('div');
        errorDiv.className = 'field-error';
        errorDiv.textContent = message;
        
        input.parentNode.appendChild(errorDiv);
    }

    showFieldSuccess(input) {
        this.clearValidationErrors(input);
        input.classList.add('is-valid');
    }

    clearValidationErrors(input) {
        input.classList.remove('is-invalid', 'is-valid');
        
        const existingError = input.parentNode.querySelector('.field-error');
        if (existingError) {
            existingError.remove();
        }
    }

    setupAutoSave() {
        const forms = document.querySelectorAll('form[data-auto-save]');
        
        forms.forEach(form => {
            const saveKey = form.dataset.autoSave;
            const interval = parseInt(form.dataset.saveInterval) || 30000;
            
            // Load saved data
            this.loadAutoSavedData(form, saveKey);
            
            // Setup auto-save
            let saveTimeout;
            
            form.addEventListener('input', () => {
                clearTimeout(saveTimeout);
                saveTimeout = setTimeout(() => {
                    this.autoSaveForm(form, saveKey);
                }, interval);
            });
        });
    }

    autoSaveForm(form, saveKey) {
        const formData = new FormData(form);
        const data = Object.fromEntries(formData.entries());
        
        localStorage.setItem(`autosave_${saveKey}`, JSON.stringify({
            data: data,
            timestamp: Date.now()
        }));
        
        this.showNotification('info', '💾 Draft Saved', '', 2000);
    }

    loadAutoSavedData(form, saveKey) {
        const saved = localStorage.getItem(`autosave_${saveKey}`);
        if (!saved) return;
        
        try {
            const { data, timestamp } = JSON.parse(saved);
            
            // Don't load data older than 24 hours
            if (Date.now() - timestamp > 24 * 60 * 60 * 1000) {
                localStorage.removeItem(`autosave_${saveKey}`);
                return;
            }
            
            // Populate form fields
            Object.keys(data).forEach(name => {
                const field = form.querySelector(`[name="${name}"]`);
                if (field && data[name]) {
                    field.value = data[name];
                }
            });
            
            this.showNotification('info', '📋 Draft Loaded', 'Previous data restored', 3000);
        } catch (error) {
            console.error('Error loading auto-saved data:', error);
        }
    }

    setupBudgetCalculator() {
        const budgetInputs = document.querySelectorAll('[data-budget-calculator]');
        
        budgetInputs.forEach(input => {
            input.addEventListener('input', () => {
                this.updateBudgetDisplay(input);
                this.calculateRecommendations(input);
            });
        });
    }

    updateBudgetDisplay(input) {
        const min = document.querySelector('[name="budget_min"]')?.value || 0;
        const max = document.querySelector('[name="budget_max"]')?.value || 0;
        
        const display = document.querySelector('.budget-display');
        if (display) {
            display.textContent = `$${parseInt(min).toLocaleString()} - $${parseInt(max).toLocaleString()}`;
        }
        
        // Update budget quality indicator
        this.updateBudgetQuality(min, max);
    }

    updateBudgetQuality(min, max) {
        const qualityIndicator = document.querySelector('.budget-quality');
        if (!qualityIndicator) return;
        
        const avgBudget = (parseInt(min) + parseInt(max)) / 2;
        let quality, message;
        
        if (avgBudget < 100) {
            quality = 'budget';
            message = 'Budget Travel - Great for backpackers and budget-conscious travelers';
        } else if (avgBudget < 300) {
            quality = 'comfort';
            message = 'Comfort Travel - Good balance of comfort and value';
        } else if (avgBudget < 500) {
            quality = 'luxury';
            message = 'Luxury Travel - Premium experiences and accommodations';
        } else {
            quality = 'ultra-luxury';
            message = 'Ultra-Luxury - The finest experiences money can buy';
        }
        
        qualityIndicator.className = `budget-quality ${quality}`;
        qualityIndicator.textContent = message;
    }

    // ======================
    // Destination Exploration
    // ======================
    
    setupDestinationExplorer() {
        this.setupDestinationFilters();
        this.setupDestinationComparison();
        this.setupDestinationFavorites();
    }

    setupDestinationFilters() {
        const filterForm = document.querySelector('#destinationFilters');
        if (!filterForm) return;
        
        const inputs = filterForm.querySelectorAll('input, select');
        
        inputs.forEach(input => {
            input.addEventListener('change', () => {
                this.applyDestinationFilters();
            });
        });
        
        // Filter tags
        const filterTags = document.querySelectorAll('.filter-tag');
        filterTags.forEach(tag => {
            tag.addEventListener('click', () => {
                tag.classList.toggle('active');
                this.applyDestinationFilters();
            });
        });
    }

    async applyDestinationFilters() {
        const filters = this.gatherFilterData();
        
        try {
            this.showLoading('Searching destinations...');
            
            const response = await this.apiCall('/vacation-ai/api/destinations/search/', filters);
            
            this.hideLoading();
            this.updateDestinationResults(response.destinations);
            
        } catch (error) {
            this.hideLoading();
            this.showNotification('error', 'Search failed', 'Please try again');
        }
    }

    gatherFilterData() {
        const form = document.querySelector('#destinationFilters');
        if (!form) return {};
        
        const formData = new FormData(form);
        const filters = Object.fromEntries(formData.entries());
        
        // Add active filter tags
        const activeTags = Array.from(document.querySelectorAll('.filter-tag.active'))
            .map(tag => tag.dataset.filter);
        
        if (activeTags.length > 0) {
            filters.tags = activeTags;
        }
        
        return filters;
    }

    updateDestinationResults(destinations) {
        const container = document.querySelector('#destinationResults');
        if (!container) return;
        
        if (destinations.length === 0) {
            container.innerHTML = this.getNoResultsHTML();
            return;
        }
        
        container.innerHTML = destinations.map(dest => this.getDestinationCardHTML(dest)).join('');
        
        // Bind new card events
        this.bindDestinationCardEvents();
    }

    getDestinationCardHTML(destination) {
        return `
            <div class="destination-card" data-destination-id="${destination.id}">
                <div class="destination-image">
                    <img src="${destination.image_url}" alt="${destination.name}" />
                    <div class="destination-badge">${destination.badge}</div>
                    <button class="favorite-btn" data-destination-id="${destination.id}">
                        <i class="far fa-heart"></i>
                    </button>
                </div>
                <div class="destination-content">
                    <h4 class="destination-title">
                        <span>${destination.flag}</span>
                        ${destination.name}
                    </h4>
                    <p class="destination-description">${destination.description}</p>
                    <div class="destination-features">
                        ${destination.features.map(f => `<span class="feature-tag">${f}</span>`).join('')}
                    </div>
                    <div class="destination-stats">
                        <div class="stat-item">
                            <span class="stat-value">${destination.match_score}%</span>
                            <span class="stat-label">Match</span>
                        </div>
                        <div class="stat-item">
                            <span class="stat-value">$${destination.avg_cost}</span>
                            <span class="stat-label">Avg/Day</span>
                        </div>
                        <div class="stat-item">
                            <span class="stat-value">${destination.rating}★</span>
                            <span class="stat-label">Rating</span>
                        </div>
                        <button class="explore-btn" data-destination-id="${destination.id}">
                            <i class="fas fa-compass"></i> Explore
                        </button>
                    </div>
                </div>
            </div>
        `;
    }

    bindDestinationCardEvents() {
        // Favorite buttons
        document.querySelectorAll('.favorite-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                e.stopPropagation();
                this.toggleDestinationFavorite(btn.dataset.destinationId);
            });
        });
        
        // Explore buttons
        document.querySelectorAll('.explore-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                this.exploreDestination(btn.dataset.destinationId);
            });
        });
        
        // Card hover effects
        document.querySelectorAll('.destination-card').forEach(card => {
            card.addEventListener('mouseenter', () => {
                this.showDestinationPreview(card.dataset.destinationId);
            });
        });
    }

    // ======================
    // Utility Functions
    // ======================
    
    createLoadingOverlay() {
        const overlay = document.createElement('div');
        overlay.className = 'vacation-ai-loading-overlay';
        overlay.innerHTML = `
            <div class="loading-content">
                <div class="loading-spinner"></div>
                <div class="loading-text">Processing...</div>
            </div>
        `;
        document.body.appendChild(overlay);
        return overlay;
    }

    createNotificationContainer() {
        const container = document.createElement('div');
        container.className = 'vacation-ai-notifications';
        document.body.appendChild(container);
        return container;
    }

    showLoading(message = 'Loading...') {
        this.loadingOverlay.querySelector('.loading-text').textContent = message;
        this.loadingOverlay.style.display = 'flex';
    }

    hideLoading() {
        this.loadingOverlay.style.display = 'none';
    }

    showNotification(type, title, message = '', duration = 5000) {
        const notification = document.createElement('div');
        notification.className = `vacation-ai-notification ${type}`;
        notification.innerHTML = `
            <div class="notification-icon">
                ${this.getNotificationIcon(type)}
            </div>
            <div class="notification-content">
                <div class="notification-title">${title}</div>
                ${message ? `<div class="notification-message">${message}</div>` : ''}
            </div>
            <button class="notification-close">&times;</button>
        `;
        
        this.notificationContainer.appendChild(notification);
        
        // Auto-remove
        setTimeout(() => {
            notification.classList.add('fade-out');
            setTimeout(() => notification.remove(), 300);
        }, duration);
        
        // Manual close
        notification.querySelector('.notification-close').addEventListener('click', () => {
            notification.remove();
        });
    }

    getNotificationIcon(type) {
        const icons = {
            success: '✅',
            error: '❌',
            warning: '⚠️',
            info: 'ℹ️'
        };
        return icons[type] || 'ℹ️';
    }

    async apiCall(url, data = null, method = 'GET') {
        const options = {
            method: method,
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': this.getCSRFToken()
            }
        };
        
        if (data && method !== 'GET') {
            options.body = JSON.stringify(data);
        }
        
        const response = await fetch(url, options);
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        return await response.json();
    }

    getCSRFToken() {
        return document.querySelector('[name=csrfmiddlewaretoken]')?.value || '';
    }

    gatherFormContext(element) {
        const form = element.closest('form');
        if (!form) return {};
        
        const formData = new FormData(form);
        return Object.fromEntries(formData.entries());
    }

    bindEvents() {
        // Initialize all interactive features
        document.addEventListener('DOMContentLoaded', () => {
            this.setupAISuggestions();
            this.enhanceForms();
            this.setupDestinationExplorer();
        });
    }

    setupWebSocket() {
        // WebSocket for real-time updates (if available)
        if (typeof WebSocket !== 'undefined' && window.location.protocol === 'https:') {
            try {
                const wsUrl = `wss://${window.location.host}/ws/vacation-ai/`;
                this.websocket = new WebSocket(wsUrl);
                
                this.websocket.onmessage = (event) => {
                    const data = JSON.parse(event.data);
                    this.handleWebSocketMessage(data);
                };
                
                this.websocket.onerror = (error) => {
                    console.log('WebSocket error:', error);
                };
            } catch (error) {
                console.log('WebSocket not available:', error);
            }
        }
    }

    handleWebSocketMessage(data) {
        switch (data.type) {
            case 'analysis_update':
                this.updateProgressUI(data.analysis_id, data.status);
                break;
            case 'notification':
                this.showNotification(data.level, data.title, data.message);
                break;
            default:
                console.log('Unknown WebSocket message:', data);
        }
    }
}

// Initialize the Vacation AI system
window.VacationAI = new VacationAI();

// Export for module systems
if (typeof module !== 'undefined' && module.exports) {
    module.exports = VacationAI;
}
