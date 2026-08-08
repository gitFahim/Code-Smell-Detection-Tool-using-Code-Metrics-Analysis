// ===== State Management =====
const state = {
    mode: 'github',
    uploadedFiles: {}, // Raw files uploaded by user { [filename]: { name, content, type, rawFile } }
    files: {},          // Extracted/parsed files returned from server
    classes: [],
    smells: [],
    activeFile: null,
    activeSmell: null,
    smellFilter: 'all'
};

// ===== DOM Elements =====
const elements = {
    tabBtns: document.querySelectorAll('.tab-btn'),
    inputSections: document.querySelectorAll('.input-section'),
    analyzeBtn: document.getElementById('analyzeBtn'),
    newSessionBtn: document.getElementById('newSessionBtn'),
    inputPanel: document.getElementById('inputPanel'),
    mainContent: document.getElementById('mainContent'),
    loadingOverlay: document.getElementById('loadingOverlay'),
    loadingDetail: document.getElementById('loadingDetail'),
    githubUrl: document.getElementById('githubUrl'),
    dropZone: document.getElementById('dropZone'),
    fileInput: document.getElementById('fileInput'),
    fileList: document.getElementById('fileList'),
    codeInput: document.getElementById('codeInput'),
    fileTree: document.getElementById('fileTree'),
    fileCount: document.getElementById('fileCount'),
    editorTabs: document.getElementById('editorTabs'),
    lineNumbers: document.getElementById('lineNumbers'),
    codeEditor: document.getElementById('codeEditor'),
    smellsList: document.getElementById('smellsList'),
    smellCount: document.getElementById('smellCount'),
    metricsDashboard: document.getElementById('metricsDashboard'),
    panelTabs: document.querySelectorAll('.panel-tab'),
    panelContents: document.querySelectorAll('.panel-content'),
    filterBtns: document.querySelectorAll('.filter-btn')
};

// Helper to escape HTML characters in file names
function escapeHtml(str) {
    if (!str) return '';
    return str
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#039;');
}

// ===== Event Listeners =====
function init() {
    // Tab switching
    elements.tabBtns.forEach(btn => {
        btn.addEventListener('click', () => switchMode(btn.dataset.mode));
    });

    // Analyze button
    elements.analyzeBtn.addEventListener('click', handleAnalyze);

    // New Session button
    if (elements.newSessionBtn) {
        elements.newSessionBtn.addEventListener('click', startNewSession);
    }

    // Drop zone
    elements.dropZone.addEventListener('click', () => elements.fileInput.click());
    elements.dropZone.addEventListener('dragover', handleDragOver);
    elements.dropZone.addEventListener('dragleave', handleDragLeave);
    elements.dropZone.addEventListener('drop', handleDrop);
    elements.fileInput.addEventListener('change', handleFileSelect);

    // Panel tabs
    elements.panelTabs.forEach(tab => {
        tab.addEventListener('click', () => switchPanel(tab.dataset.panel));
    });

    // Filter buttons
    elements.filterBtns.forEach(btn => {
        btn.addEventListener('click', () => filterSmells(btn.dataset.filter));
    });
}

// ===== Mode Switching =====
function switchMode(mode) {
    state.mode = mode;
    elements.tabBtns.forEach(btn => btn.classList.toggle('active', btn.dataset.mode === mode));
    elements.inputSections.forEach(sec => sec.classList.toggle('active', sec.id === mode + 'Section'));
}

function switchPanel(panel) {
    elements.panelTabs.forEach(tab => tab.classList.toggle('active', tab.dataset.panel === panel));
    elements.panelContents.forEach(content => content.classList.toggle('active', content.id === panel + 'Panel'));
}

// ===== File Handling =====
function handleDragOver(e) {
    e.preventDefault();
    elements.dropZone.classList.add('dragover');
}

function handleDragLeave(e) {
    e.preventDefault();
    elements.dropZone.classList.remove('dragover');
}

function handleDrop(e) {
    e.preventDefault();
    elements.dropZone.classList.remove('dragover');
    const files = Array.from(e.dataTransfer.files);
    processFiles(files);
}

function handleFileSelect(e) {
    const files = Array.from(e.target.files);
    processFiles(files);
}

// Dictionary of metric abbreviations to full human-readable names
const METRIC_FULL_NAMES = {
    // Class-level metrics
    LOC: 'Lines of Code (LOC)',
    NOM: 'Number of Methods (NOM)',
    NOPM: 'Number of Public Methods (NOPM)',
    WMC: 'Weighted Method Count (WMC)',
    TCC: 'Tight Class Cohesion (TCC)',
    WOC: 'Weight of Class (WOC)',
    NAS: 'Number of Added Services (NAS)',
    PNAS: 'Percentage of Newly Added Services (PNAS)',
    NProtM: 'Number of Protected Members (NProtM)',
    BUR: 'Base Class Usage Ratio (BUR)',
    BOvR: 'Base Class Overriding Ratio (BOvR)',
    AMW: 'Average Method Weight (AMW)',
    NOPA: 'Number of Public Attributes (NOPA)',
    NOAM: 'Number of Accessor Methods (NOAM)',
    
    // Method-level metrics
    CYCLO: 'Cyclomatic Complexity (CYCLO)',
    MAXNESTING: 'Maximum Nesting Level (MAXNESTING)',
    NOAV: 'Number of Accessed Variables (NOAV)',
    CINT: 'Coupling Intensity (CINT)',
    CDISP: 'Coupling Dispersion (CDISP)',
    CM: 'Changing Methods (CM)',
    CC: 'Changing Classes (CC)',
    ATFD: 'Access To Foreign Data (ATFD)',
    FDP: 'Foreign Data Providers (FDP)',
    LAA: 'Locality of Attribute Access (LAA)',
    BrainMethods: 'Brain Methods Count'
};

function processFiles(files) {
    files.forEach(file => {
        const lowerName = file.name.toLowerCase();
        if (lowerName.endsWith('.java') || lowerName.endsWith('.zip')) {
            const reader = new FileReader();
            reader.onload = (e) => {
                state.uploadedFiles[file.name] = {
                    name: file.name,
                    content: e.target.result,
                    type: file.type,
                    rawFile: file
                };
                updateFileList();
            };
            if (lowerName.endsWith('.zip')) {
                reader.readAsArrayBuffer(file);
            } else {
                reader.readAsText(file);
            }
        }
    });
}

function updateFileList() {
    const filesList = Object.values(state.uploadedFiles);
    if (filesList.length === 0) {
        elements.fileList.innerHTML = '';
        return;
    }

    elements.fileList.innerHTML = filesList.map(file => {
        const isZip = file.name.toLowerCase().endsWith('.zip');
        const safeName = escapeHtml(file.name);
        return `
            <div class="file-item">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    ${isZip 
                        ? '<path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z"/>'
                        : '<path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/>'
                    }
                </svg>
                <span>${safeName}</span>
                <button class="remove-btn" data-name="${safeName}" title="Remove file">&times;</button>
            </div>
        `;
    }).join('');

    elements.fileList.querySelectorAll('.remove-btn').forEach(btn => {
        btn.onclick = (e) => {
            e.stopPropagation();
            const fileName = btn.getAttribute('data-name');
            removeFile(fileName);
        };
    });
}

function removeFile(name) {
    for (const key of Object.keys(state.uploadedFiles)) {
        if (key === name || escapeHtml(key) === name) {
            delete state.uploadedFiles[key];
            break;
        }
    }
    if (elements.fileInput) {
        elements.fileInput.value = '';
    }
    updateFileList();
}

function startNewSession() {
    state.uploadedFiles = {};
    state.files = {};
    state.classes = [];
    state.smells = [];
    state.activeFile = null;
    state.activeSmell = null;
    state.smellFilter = 'all';

    if (elements.fileInput) {
        elements.fileInput.value = '';
    }
    elements.githubUrl.value = 'https://github.com/apache/commons-lang';
    elements.codeInput.value = '';
    updateFileList();

    elements.fileTree.innerHTML = '';
    elements.editorTabs.innerHTML = '';
    elements.lineNumbers.innerHTML = '';
    elements.codeEditor.innerHTML = '<code></code>';
    elements.smellsList.innerHTML = '';
    elements.metricsDashboard.innerHTML = '';

    elements.filterBtns.forEach(btn => btn.classList.toggle('active', btn.dataset.filter === 'all'));

    switchMode('github');
    switchPanel('smells');

    elements.inputPanel.classList.remove('hidden');
    elements.mainContent.classList.add('hidden');
    elements.analyzeBtn.disabled = false;
}

// ===== Analysis =====
async function handleAnalyze() {
    elements.analyzeBtn.disabled = true;
    elements.loadingOverlay.classList.remove('hidden');

    try {
        let response;

        if (state.mode === 'github') {
            elements.loadingDetail.textContent = 'Fetching repository from GitHub...';
            const url = elements.githubUrl.value.trim();
            if (!url) throw new Error('Please enter a GitHub URL');

            response = await fetch('/api/analyze/github', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ url })
            });
        } else if (state.mode === 'upload') {
            elements.loadingDetail.textContent = 'Processing uploaded files...';
            const fileEntries = Object.entries(state.uploadedFiles);
            if (fileEntries.length === 0) throw new Error('Please upload Java or ZIP files first');

            const fd = new FormData();
            fileEntries.forEach(([name, item]) => {
                if (item.rawFile) {
                    fd.append('files', item.rawFile, name);
                } else if (name.toLowerCase().endsWith('.zip')) {
                    fd.append('files', new Blob([item.content]), name);
                } else {
                    fd.append('files', new Blob([item.content], { type: 'text/plain' }), name);
                }
            });

            response = await fetch('/api/analyze/upload', {
                method: 'POST',
                body: fd
            });
        } else {
            elements.loadingDetail.textContent = 'Analyzing pasted code...';
            const content = elements.codeInput.value.trim();
            if (!content) throw new Error('Please paste some Java code');

            response = await fetch('/api/analyze/text', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ content })
            });
        }

        elements.loadingDetail.textContent = 'Calculating metrics...';

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.error || 'Analysis failed');
        }

        const data = await response.json();
        state.classes = data.classes;
        state.files = data.files;

        // Flatten smells
        state.smells = [];
        data.classes.forEach(cls => {
            cls.smells.forEach(smell => {
                state.smells.push({ ...smell, className: cls.name });
            });
        });

        elements.loadingDetail.textContent = 'Rendering results...';

        showResults(data);
    } catch (error) {
        alert('Error: ' + error.message);
        console.error(error);
    } finally {
        elements.loadingOverlay.classList.add('hidden');
        elements.analyzeBtn.disabled = false;
    }
}

// ===== Results Display =====
function showResults(data) {
    elements.inputPanel.classList.add('hidden');
    elements.mainContent.classList.remove('hidden');

    renderFileTree();
    renderSmells();
    renderMetrics();

    // Open first file with smells, or first file
    const filesWithSmells = Object.keys(data.files).filter(path => 
        data.classes.some(c => c.smells.length > 0 && path.includes(c.name))
    );

    const firstFile = filesWithSmells[0] || Object.keys(data.files)[0];
    if (firstFile) openFile(firstFile);
}

function renderFileTree() {
    const paths = Object.keys(state.files);
    elements.fileCount.textContent = `${paths.length} file${paths.length !== 1 ? 's' : ''}`;

    // Group by directory
    const tree = {};
    paths.forEach(path => {
        const parts = path.split('/');
        let current = tree;
        parts.forEach((part, i) => {
            if (i === parts.length - 1) {
                current[part] = { type: 'file', path };
            } else {
                current[part] = current[part] || { type: 'dir', children: {} };
                current = current[part].children;
            }
        });
    });

    function renderTree(node, prefix = '') {
        let html = '';
        Object.entries(node).forEach(([name, item]) => {
            if (item.type === 'file') {
                const smellCount = state.smells.filter(s => 
                    item.path.includes(s.className)
                ).length;
                html += `
                    <div class="tree-item" data-path="${item.path}" onclick="openFile('${item.path}')">
                        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                            <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
                            <polyline points="14 2 14 8 20 8"/>
                        </svg>
                        ${name}
                        ${smellCount > 0 ? `<span class="smell-badge">${smellCount}</span>` : ''}
                    </div>
                `;
            } else {
                html += `
                    <div class="tree-item" style="padding-left: ${prefix ? 24 : 16}px; color: var(--text-muted);">
                        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                            <path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"/>
                        </svg>
                        ${name}
                    </div>
                `;
                html += renderTree(item.children, prefix + '  ');
            }
        });
        return html;
    }

    elements.fileTree.innerHTML = renderTree(tree);
}

function openFile(path) {
    state.activeFile = path;

    // Update tree selection
    document.querySelectorAll('.tree-item').forEach(item => {
        item.classList.toggle('active', item.dataset.path === path);
    });

    // Update tabs
    const tabExists = document.querySelector(`.editor-tab[data-path="${path}"]`);
    if (!tabExists) {
        const tab = document.createElement('button');
        tab.className = 'editor-tab active';
        tab.dataset.path = path;
        tab.innerHTML = `
            <span>${path.split('/').pop()}</span>
            <button class="close-tab" onclick="closeTab(event, '${path}')">&times;</button>
        `;
        tab.onclick = () => openFile(path);
        elements.editorTabs.appendChild(tab);
    }

    document.querySelectorAll('.editor-tab').forEach(t => t.classList.toggle('active', t.dataset.path === path));

    // Render code
    const content = state.files[path] || '';
    const lines = content.split('\n');

    elements.lineNumbers.innerHTML = lines.map((_, i) => {
        const lineNum = i + 1;
        const hasSmell = state.smells.some(s => 
            s.line === lineNum && path.includes(s.className)
        );
        return `<span class="line-num ${hasSmell ? 'highlight' : ''}">${lineNum}</span>`;
    }).join('');

    elements.codeEditor.innerHTML = `<code>${syntaxHighlight(content)}</code>`;
}

function closeTab(e, path) {
    e.stopPropagation();
    const tab = document.querySelector(`.editor-tab[data-path="${path}"]`);
    if (tab) tab.remove();

    if (state.activeFile === path) {
        const remaining = document.querySelector('.editor-tab');
        if (remaining) openFile(remaining.dataset.path);
    }
}

function syntaxHighlight(code) {
    // Simple syntax highlighting
    const keywords = ['public', 'private', 'protected', 'static', 'final', 'abstract', 'class', 'interface', 'extends', 'implements', 'return', 'if', 'else', 'for', 'while', 'do', 'switch', 'case', 'break', 'continue', 'new', 'this', 'super', 'try', 'catch', 'throw', 'throws', 'import', 'package', 'void', 'int', 'long', 'float', 'double', 'boolean', 'char', 'byte', 'short', 'String'];

    return code.split('\n').map((line, i) => {
        let highlighted = line
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;');

        // Comments
        highlighted = highlighted.replace(/(\/\/.*$)/, '<span class="comment">$1</span>');

        // Strings
        highlighted = highlighted.replace(/(".*?")/g, '<span class="string">$1</span>');

        // Keywords
        keywords.forEach(kw => {
            const regex = new RegExp(`\\b${kw}\\b`, 'g');
            highlighted = highlighted.replace(regex, `<span class="keyword">${kw}</span>`);
        });

        // Types (capitalized words)
        highlighted = highlighted.replace(/ ([A-Z][a-zA-Z0-9_]*) /g, '<span class="type">$1</span>');

        // Numbers
        highlighted = highlighted.replace(/ (\d+) /g, '<span class="number">$1</span>');

        // Check if this line has a smell
        const lineNum = i + 1;
        const hasSmell = state.smells.some(s => 
            s.line === lineNum && state.activeFile && state.activeFile.includes(s.className)
        );

        return `<span class="line ${hasSmell ? 'smell-line' : ''}">${highlighted || ' '}</span>`;
    }).join('');
}

function renderSmells() {
    const filtered = state.smellFilter === 'all' 
        ? state.smells 
        : state.smells.filter(s => s.severity === state.smellFilter);

    elements.smellCount.textContent = `${filtered.length} smell${filtered.length !== 1 ? 's' : ''} detected`;

    elements.smellsList.innerHTML = filtered.map((smell, index) => `
        <div class="smell-card ${state.activeSmell === index ? 'active' : ''}" 
             data-index="${index}" 
             onclick="selectSmell(${index})">
            <div class="smell-header">
                <span class="smell-type">${smell.type}</span>
                <span class="severity ${smell.severity}">${smell.severity}</span>
            </div>
            <div class="smell-location">${smell.className}:${smell.line}</div>
            <div class="smell-description">${smell.description}</div>
            <div class="smell-metrics">
                ${Object.entries(smell.metrics || {}).map(([k, v]) => 
                    `<span class="metric-tag" title="${METRIC_FULL_NAMES[k] || k}">${METRIC_FULL_NAMES[k] || k}: ${v}</span>`
                ).join('')}
            </div>
        </div>
    `).join('');
}

function selectSmell(index) {
    state.activeSmell = index;
    const smell = state.smells[index];

    // Find and open the file containing this smell
    const filePath = Object.keys(state.files).find(path => path.includes(smell.className));
    if (filePath) {
        openFile(filePath);

        // Scroll to line
        setTimeout(() => {
            const lineHeight = 20.8;
            const scrollPos = (smell.line - 1) * lineHeight - 100;
            document.querySelector('.editor-container').scrollTop = Math.max(0, scrollPos);
        }, 50);
    }

    renderSmells();
}

function filterSmells(filter) {
    state.smellFilter = filter;
    elements.filterBtns.forEach(btn => btn.classList.toggle('active', btn.dataset.filter === filter));
    renderSmells();
}

function renderMetrics() {
    if (state.classes.length === 0) return;

    // Aggregate metrics
    const totalLOC = state.classes.reduce((sum, c) => sum + (c.metrics.LOC || 0), 0);
    const totalMethods = state.classes.reduce((sum, c) => sum + (c.metrics.NOM || 0), 0);
    const avgWMC = state.classes.reduce((sum, c) => sum + (c.metrics.WMC || 0), 0) / state.classes.length;
    const avgTCC = state.classes.reduce((sum, c) => sum + (c.metrics.TCC || 0), 0) / state.classes.length;
    const avgAMW = state.classes.reduce((sum, c) => sum + (c.metrics.AMW || 0), 0) / state.classes.length;

    const smellCounts = {};
    state.smells.forEach(s => {
        smellCounts[s.type] = (smellCounts[s.type] || 0) + 1;
    });

    elements.metricsDashboard.innerHTML = `
        <div class="metric-card">
            <h4>Project Overview</h4>
            <div class="metric-row">
                <span class="metric-name">Total Classes</span>
                <span class="metric-value">${state.classes.length}</span>
            </div>
            <div class="metric-row">
                <span class="metric-name">Total Methods</span>
                <span class="metric-value">${totalMethods}</span>
            </div>
            <div class="metric-row">
                <span class="metric-name">Lines of Code (LOC)</span>
                <span class="metric-value">${totalLOC}</span>
            </div>
            <div class="metric-row">
                <span class="metric-name">Total Smells Detected</span>
                <span class="metric-value ${state.smells.length > 10 ? 'high' : state.smells.length > 0 ? 'medium' : 'good'}">${state.smells.length}</span>
            </div>
        </div>

        <div class="metric-card">
            <h4>Average Project Metrics</h4>
            <div class="metric-row">
                <span class="metric-name">Avg Weighted Method Count (WMC)</span>
                <span class="metric-value ${avgWMC > 47 ? 'high' : avgWMC > 20 ? 'medium' : 'good'}">${avgWMC.toFixed(2)}</span>
            </div>
            <div class="metric-row">
                <span class="metric-name">Avg Tight Class Cohesion (TCC)</span>
                <span class="metric-value ${avgTCC < 0.33 ? 'high' : avgTCC < 0.5 ? 'medium' : 'good'}">${avgTCC.toFixed(2)}</span>
            </div>
            <div class="metric-row">
                <span class="metric-name">Avg Average Method Weight (AMW)</span>
                <span class="metric-value">${avgAMW.toFixed(2)}</span>
            </div>
        </div>

        <div class="metric-card">
            <h4>Smell Distribution</h4>
            ${Object.keys(smellCounts).length === 0 
                ? '<div class="metric-row"><span class="metric-name">No Code Smells Found</span><span class="metric-value good">0</span></div>'
                : Object.entries(smellCounts).map(([type, count]) => `
                    <div class="metric-row">
                        <span class="metric-name">${type}</span>
                        <span class="metric-value ${count > 5 ? 'high' : count > 2 ? 'medium' : 'good'}">${count}</span>
                    </div>
                `).join('')}
        </div>

        ${state.classes.map(cls => `
            <div class="metric-card">
                <h4>Class: ${cls.name}</h4>
                ${Object.entries(cls.metrics).map(([key, val]) => `
                    <div class="metric-row">
                        <span class="metric-name">${METRIC_FULL_NAMES[key] || key}</span>
                        <span class="metric-value ${
                            key === 'WMC' && val >= 47 ? 'high' :
                            key === 'TCC' && val < 0.33 ? 'high' :
                            key === 'WOC' && val < 0.33 ? 'high' : 'good'
                        }">${val}</span>
                    </div>
                `).join('')}

                ${cls.methods && cls.methods.length > 0 ? `
                    <div style="margin-top: 12px; padding-top: 8px; border-top: 1px dashed var(--border-color);">
                        <h5 style="font-size: 11px; text-transform: uppercase; color: var(--text-muted); margin-bottom: 8px;">Method Metrics (${cls.methods.length} methods)</h5>
                        ${cls.methods.map(m => `
                            <div style="background: var(--bg-secondary); padding: 8px; border-radius: 4px; margin-bottom: 6px;">
                                <div style="font-weight: 600; font-size: 11px; color: var(--accent-blue); margin-bottom: 4px;">${m.name}()</div>
                                ${Object.entries(m.metrics).map(([mk, mv]) => `
                                    <div class="metric-row" style="font-size: 11px; padding: 2px 0;">
                                        <span class="metric-name">${METRIC_FULL_NAMES[mk] || mk}</span>
                                        <span class="metric-value">${mv}</span>
                                    </div>
                                `).join('')}
                            </div>
                        `).join('')}
                    </div>
                ` : ''}
            </div>
        `).join('')}
    `;
}

// ===== Initialize =====
document.addEventListener('DOMContentLoaded', init);

