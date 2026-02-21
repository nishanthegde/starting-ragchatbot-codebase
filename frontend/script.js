// API base URL - use relative path to work from any host
const API_URL = '/api';
const REQUEST_TIMEOUT_MS = 45000;
const THEME_STORAGE_KEY = 'course-assistant-theme';
const REDUCED_MOTION_QUERY = '(prefers-reduced-motion: reduce)';
const WELCOME_MESSAGE =
    'Welcome to the Course Materials Assistant! I can help you with questions about courses, lessons and specific content. What would you like to know?';

// Global state
let currentSessionId = null;
let activeAbortController = null;
let activeTimeoutId = null;
let activeLoadingMessage = null;
let requestEpoch = 0;
let isResettingSession = false;

// DOM elements
let chatMessages, chatInput, sendButton, newChatButton, totalCourses, courseTitles, themeToggleButton;

// Initialize
document.addEventListener('DOMContentLoaded', async () => {
    // Get DOM elements after page loads
    chatMessages = document.getElementById('chatMessages');
    chatInput = document.getElementById('chatInput');
    sendButton = document.getElementById('sendButton');
    newChatButton = document.getElementById('newChatButton');
    totalCourses = document.getElementById('totalCourses');
    courseTitles = document.getElementById('courseTitles');
    themeToggleButton = document.getElementById('themeToggle');

    initializeTheme();
    setupEventListeners();
    await createNewSession();
    loadCourseStats();
});

// Event Listeners
function setupEventListeners() {
    // Chat functionality
    sendButton.addEventListener('click', sendMessage);
    chatInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') sendMessage();
    });

    if (newChatButton) {
        newChatButton.addEventListener('click', createNewSession);
    }

    if (themeToggleButton) {
        themeToggleButton.addEventListener('click', toggleTheme);
    }

    // Suggested questions
    document.querySelectorAll('.suggested-item').forEach(button => {
        button.addEventListener('click', (e) => {
            const question = e.target.getAttribute('data-question');
            chatInput.value = question;
            sendMessage();
        });
    });
}

function initializeTheme() {
    const storedTheme = getStoredTheme();
    const prefersLight =
        typeof window.matchMedia === 'function' &&
        window.matchMedia('(prefers-color-scheme: light)').matches;
    const initialTheme = storedTheme || (prefersLight ? 'light' : 'dark');
    applyTheme(initialTheme);
}

function toggleTheme() {
    const currentTheme = document.body.getAttribute('data-theme') === 'light' ? 'light' : 'dark';
    const nextTheme = currentTheme === 'light' ? 'dark' : 'light';
    applyThemeWithTransition(nextTheme);
}

function applyThemeWithTransition(theme) {
    const supportsViewTransitions = typeof document.startViewTransition === 'function';
    const prefersReducedMotion =
        typeof window.matchMedia === 'function' &&
        window.matchMedia(REDUCED_MOTION_QUERY).matches;

    if (!supportsViewTransitions || prefersReducedMotion) {
        applyTheme(theme);
        return;
    }

    try {
        document.startViewTransition(() => applyTheme(theme));
    } catch (error) {
        console.warn('Unable to run view transition, falling back:', error);
        applyTheme(theme);
    }
}

function applyTheme(theme) {
    const isLightTheme = theme === 'light';
    const label = isLightTheme ? 'Switch to dark theme' : 'Switch to light theme';

    document.body.setAttribute('data-theme', isLightTheme ? 'light' : 'dark');

    if (themeToggleButton) {
        themeToggleButton.setAttribute('aria-pressed', String(isLightTheme));
        themeToggleButton.setAttribute('aria-label', label);
        themeToggleButton.setAttribute('title', label);
    }

    try {
        localStorage.setItem(THEME_STORAGE_KEY, isLightTheme ? 'light' : 'dark');
    } catch (error) {
        console.warn('Unable to persist theme preference:', error);
    }
}

function getStoredTheme() {
    try {
        const theme = localStorage.getItem(THEME_STORAGE_KEY);
        return theme === 'light' || theme === 'dark' ? theme : null;
    } catch (error) {
        console.warn('Unable to access stored theme preference:', error);
        return null;
    }
}


// Chat Functions
async function sendMessage() {
    const query = chatInput.value.trim();
    if (!query || chatInput.disabled || isResettingSession) return;

    const localRequestEpoch = ++requestEpoch;

    // Disable input
    chatInput.value = '';
    setInputDisabled(true);

    // Add user message
    addMessage(query, 'user');

    // Add loading message
    activeLoadingMessage = createLoadingMessage();
    chatMessages.appendChild(activeLoadingMessage);
    chatMessages.scrollTop = chatMessages.scrollHeight;

    const controller = new AbortController();
    activeAbortController = controller;
    let timedOut = false;
    activeTimeoutId = setTimeout(() => {
        timedOut = true;
        controller.abort();
    }, REQUEST_TIMEOUT_MS);

    try {
        const response = await fetch(`${API_URL}/query`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            signal: controller.signal,
            body: JSON.stringify({
                query: query,
                session_id: currentSessionId
            })
        });

        if (localRequestEpoch !== requestEpoch) {
            return;
        }

        const data = await response.json().catch(() => ({}));
        if (!response.ok) {
            const message = data?.detail || `Query failed (${response.status})`;
            throw new Error(message);
        }
        
        // Update session ID if new
        if (!currentSessionId) {
            currentSessionId = data.session_id;
        }

        removeActiveLoadingMessage();
        addMessage(data.answer, 'assistant', data.sources);

    } catch (error) {
        if (localRequestEpoch !== requestEpoch) {
            return;
        }

        const isTimeout = error?.name === 'AbortError';
        if (isTimeout && !timedOut) {
            return;
        }

        const errorMessage = isTimeout
            ? `Request timed out after ${REQUEST_TIMEOUT_MS / 1000} seconds. Please try again.`
            : error.message;

        removeActiveLoadingMessage();
        addMessage(`Error: ${errorMessage}`, 'assistant');
    } finally {
        clearActiveTimeout();

        if (activeAbortController === controller) {
            activeAbortController = null;
        }

        if (localRequestEpoch !== requestEpoch) {
            return;
        }

        removeActiveLoadingMessage();
        setInputDisabled(false);
        chatInput.focus();
    }
}

function createLoadingMessage() {
    const messageDiv = document.createElement('div');
    messageDiv.className = 'message assistant';
    messageDiv.innerHTML = `
        <div class="message-content">
            <div class="loading">
                <span></span>
                <span></span>
                <span></span>
            </div>
        </div>
    `;
    return messageDiv;
}

function addMessage(content, type, sources = null, isWelcome = false) {
    const messageId = Date.now();
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${type}${isWelcome ? ' welcome-message' : ''}`;
    messageDiv.id = `message-${messageId}`;
    
    // Convert markdown to HTML for assistant messages
    const displayContent = type === 'assistant' ? marked.parse(content) : escapeHtml(content);
    
    let html = `<div class="message-content">${displayContent}</div>`;
    
    if (sources && sources.length > 0) {
        const sourceItems = sources
            .map(source => `<span class="source-item">${source}</span>`)
            .join('');

        html += `
            <details class="sources-collapsible">
                <summary class="sources-header">Sources</summary>
                <div class="sources-content">${sourceItems}</div>
            </details>
        `;
    }
    
    messageDiv.innerHTML = html;
    chatMessages.appendChild(messageDiv);
    chatMessages.scrollTop = chatMessages.scrollHeight;
    
    return messageId;
}

// Helper function to escape HTML for user messages
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

async function createNewSession() {
    if (isResettingSession) {
        return;
    }

    isResettingSession = true;
    if (newChatButton) {
        newChatButton.disabled = true;
    }

    const previousSessionId = currentSessionId;
    cancelInFlightRequest();
    currentSessionId = null;

    try {
        const newSessionData = await requestNewSession(previousSessionId);
        currentSessionId = newSessionData.session_id;
    } catch (error) {
        console.error('Error creating new session:', error);
    } finally {
        setInputDisabled(false);
        if (newChatButton) {
            newChatButton.disabled = false;
        }
        isResettingSession = false;
    }

    chatMessages.innerHTML = '';
    addMessage(WELCOME_MESSAGE, 'assistant', null, true);
    chatInput.focus();
}

async function requestNewSession(previousSessionId) {
    const body = {};
    if (previousSessionId) {
        body.previous_session_id = previousSessionId;
    }

    const response = await fetch(`${API_URL}/session/new`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify(body),
    });

    const data = await response.json().catch(() => ({}));
    if (!response.ok) {
        const message = data?.detail || `Session reset failed (${response.status})`;
        throw new Error(message);
    }

    if (!data?.session_id) {
        throw new Error('Session reset failed: missing session ID');
    }

    return data;
}

function cancelInFlightRequest() {
    requestEpoch += 1;

    if (activeAbortController) {
        activeAbortController.abort();
        activeAbortController = null;
    }

    clearActiveTimeout();
    removeActiveLoadingMessage();
    setInputDisabled(false);
}

function clearActiveTimeout() {
    if (activeTimeoutId !== null) {
        clearTimeout(activeTimeoutId);
        activeTimeoutId = null;
    }
}

function removeActiveLoadingMessage() {
    if (activeLoadingMessage) {
        activeLoadingMessage.remove();
        activeLoadingMessage = null;
    }
}

function setInputDisabled(disabled) {
    chatInput.disabled = disabled;
    sendButton.disabled = disabled;
}

// Load course statistics
async function loadCourseStats() {
    try {
        console.log('Loading course stats...');
        const response = await fetch(`${API_URL}/courses`);
        if (!response.ok) throw new Error('Failed to load course stats');
        
        const data = await response.json();
        console.log('Course data received:', data);
        
        // Update stats in UI
        if (totalCourses) {
            totalCourses.textContent = data.total_courses;
        }
        
        // Update course titles
        if (courseTitles) {
            if (data.course_titles && data.course_titles.length > 0) {
                courseTitles.innerHTML = data.course_titles
                    .map(title => `<div class="course-title-item">${title}</div>`)
                    .join('');
            } else {
                courseTitles.innerHTML = '<span class="no-courses">No courses available</span>';
            }
        }
        
    } catch (error) {
        console.error('Error loading course stats:', error);
        // Set default values on error
        if (totalCourses) {
            totalCourses.textContent = '0';
        }
        if (courseTitles) {
            courseTitles.innerHTML = '<span class="error">Failed to load courses</span>';
        }
    }
}
