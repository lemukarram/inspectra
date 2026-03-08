document.addEventListener('DOMContentLoaded', function() {
    console.log("Inspectra AI App Initialized");

    // State management
    let currentSessionId = null;
    let currentSessionName = null;
    let currentChecklist = [];
    let currentStep = 1;
    let sessionStatus = null;
    
    const editModalEl = document.getElementById('editModal');
    let editModal = null;
    if (editModalEl && typeof bootstrap !== 'undefined') {
        editModal = new bootstrap.Modal(editModalEl);
    }

    const BASE_URL = 'http://localhost:8000';

    // Helper to switch sections
    function showSection(sectionId) {
        const sections = ['newSessionSection', 'explorerSection', 'resultsSection', 'step2UploadSection'];
        sections.forEach(id => {
            const el = document.getElementById(id);
            if (el) el.style.display = (id === sectionId) ? 'block' : 'none';
        });
        
        // Show/hide step header
        const stepHeader = document.getElementById('stepHeader');
        if (sectionId === 'resultsSection' || sectionId === 'step2UploadSection') {
            stepHeader.style.display = 'flex';
        } else {
            stepHeader.style.display = 'none';
        }
    }

    function setActiveNav(navId) {
        document.querySelectorAll('.nav-link').forEach(link => link.classList.remove('active'));
        const activeLink = document.getElementById(navId);
        if (activeLink) activeLink.classList.add('active');
    }

    // Navigation Logic
    document.getElementById('navNewSession')?.addEventListener('click', (e) => {
        e.preventDefault();
        showSection('newSessionSection');
        setActiveNav('navNewSession');
    });

    document.getElementById('navSessionExplorer')?.addEventListener('click', (e) => {
        e.preventDefault();
        loadSessions();
        showSection('explorerSection');
        setActiveNav('navSessionExplorer');
    });

    document.getElementById('btnStep1')?.addEventListener('click', () => {
        if (currentSessionId) loadStep(1);
    });

    document.getElementById('btnStep2')?.addEventListener('click', () => {
        if (currentSessionId && currentStep >= 2) loadStep(2);
    });

    // Session Explorer
    async function loadSessions() {
        const tableBody = document.getElementById('sessionTableBody');
        if (!tableBody) return;

        tableBody.innerHTML = '<tr><td colspan="5" class="text-center py-4"><div class="spinner-border spinner-border-sm text-primary"></div> Loading...</td></tr>';

        try {
            const response = await fetch(`${BASE_URL}/sessions`);
            if (!response.ok) throw new Error(`HTTP error!`);
            
            const sessions = await response.json();
            tableBody.innerHTML = '';
            
            if (sessions.length === 0) {
                tableBody.innerHTML = '<tr><td colspan="5" class="text-center py-4">No sessions found. Start a new WIR.</td></tr>';
                return;
            }

            sessions.forEach(session => {
                const date = session.created_at ? new Date(session.created_at).toLocaleString() : 'N/A';
                const name = session.session_name || `Session ${session.session_id.substring(0, 8)}`;
                const row = document.createElement('tr');
                row.innerHTML = `
                    <td>${date}</td>
                    <td><strong>${name}</strong><br><small class="text-muted">${session.session_id.substring(0, 8)}...</small></td>
                    <td><span class="badge bg-info text-dark">${session.status}</span></td>
                    <td>Step ${session.current_step}</td>
                    <td>
                        <button class="btn btn-sm btn-primary continue-btn" data-id="${session.session_id}" data-name="${session.session_name || ''}" data-step="${session.current_step}">Continue</button>
                    </td>
                `;
                tableBody.appendChild(row);
            });

            document.querySelectorAll('.continue-btn').forEach(btn => {
                btn.addEventListener('click', (e) => {
                    const sid = e.target.getAttribute('data-id');
                    const sname = e.target.getAttribute('data-name');
                    const step = parseInt(e.target.getAttribute('data-step'));
                    resumeSession(sid, sname, step);
                });
            });
        } catch (error) {
            tableBody.innerHTML = '<tr><td colspan="5" class="text-center text-danger py-4">Failed to load sessions. Ensure backend is running.</td></tr>';
        }
    }

    async function resumeSession(sessionId, sessionName, step) {
        currentSessionId = sessionId;
        currentSessionName = sessionName;
        document.getElementById('sessionIdBadge').textContent = `ID: ${sessionId.substring(0, 8)}...`;
        document.getElementById('sessionNameBadge').textContent = sessionName || '';
        
        try {
            const sessionRes = await fetch(`${BASE_URL}/sessions/${sessionId}`);
            const sessionData = await sessionRes.json();
            sessionStatus = sessionData.status;
            
            const checklistRes = await fetch(`${BASE_URL}/sessions/${sessionId}/checklist`);
            currentChecklist = await checklistRes.json();
            
            loadStep(step || sessionData.current_step);
        } catch (error) {
            alert("Error resuming session.");
        }
    }

    async function loadStep(stepNumber) {
        currentStep = stepNumber;
        document.getElementById('btnStep2').disabled = (stepNumber < 2 && currentStep < 2 && sessionStatus !== 'STEP_1_VERIFIED');
        
        if (stepNumber === 1) {
            document.getElementById('stepTitle').textContent = "Step 1: ITP Checklist";
            document.getElementById('btnStep1').classList.replace('btn-outline-primary', 'btn-primary');
            document.getElementById('btnStep2').classList.replace('btn-primary', 'btn-outline-primary');
            
            // Hide Step 2 columns
            document.querySelectorAll('.step2-col').forEach(col => col.style.display = 'none');
            document.getElementById('step2EditFields').style.display = 'none';
            document.getElementById('regenerateBtn').style.display = 'none';
            
            renderChecklist(currentChecklist);
            showSection('resultsSection');
        } 
        else if (stepNumber === 2 || stepNumber == null) {
            document.getElementById('stepTitle').textContent = "Step 2: Enriched Checklist (MES)";
            document.getElementById('btnStep2').classList.replace('btn-outline-primary', 'btn-primary');
            document.getElementById('btnStep1').classList.replace('btn-primary', 'btn-outline-primary');
            document.getElementById('btnStep2').disabled = false;
            
            // Show Step 2 columns
            document.querySelectorAll('.step2-col').forEach(col => col.style.display = 'table-cell');
            document.getElementById('step2EditFields').style.display = 'block';
            
            // Check if MES is already extracted
            if (sessionStatus === 'MES_EXTRACTED' || currentChecklist.some(item => item.procedure_text && item.procedure_text !== 'N/A')) {
                document.getElementById('regenerateBtn').style.display = 'inline-block';
                renderChecklist(currentChecklist);
                showSection('resultsSection');
            } else {
                showSection('step2UploadSection');
            }
        }
    }

    // New Session Upload (Step 1)
    document.getElementById('uploadForm')?.addEventListener('submit', async function(e) {
        e.preventDefault();
        
        const sessionNameEl = document.getElementById('sessionName');
        const itpFileEl = document.getElementById('itpFile');
        const wirSampleFileEl = document.getElementById('wirSampleFile');
        
        const formData = new FormData();
        formData.append("session_name", sessionNameEl.value);
        formData.append("itp_file", itpFileEl.files[0]);
        formData.append("wir_sample", wirSampleFileEl.files[0]);

        const submitBtn = this.querySelector('button[type="submit"]');
        const loadingDiv = document.getElementById('loading');
        
        submitBtn.disabled = true;
        loadingDiv.style.display = 'block';

        try {
            const response = await fetch(`${BASE_URL}/session/initialize`, { method: 'POST', body: formData });
            if (!response.ok) throw new Error("Initialization failed");

            const data = await response.json();
            currentSessionId = data.session_id;
            currentSessionName = data.session_name;
            currentChecklist = data.checklist;
            sessionStatus = "ITP_EXTRACTED";
            
            document.getElementById('sessionIdBadge').textContent = `ID: ${currentSessionId.substring(0, 8)}...`;
            document.getElementById('sessionNameBadge').textContent = currentSessionName || '';
            
            loadStep(1);
        } catch (error) {
            alert("An error occurred while processing documents.");
        } finally {
            submitBtn.disabled = false;
            loadingDiv.style.display = 'none';
        }
    });

    // Step 2 Upload
    document.getElementById('uploadMesForm')?.addEventListener('submit', async function(e) {
        e.preventDefault();
        
        const mesFileEl = document.getElementById('mesFile');
        const formData = new FormData();
        formData.append("mes_file", mesFileEl.files[0]);

        const submitBtn = this.querySelector('button[type="submit"]');
        const loadingDiv = document.getElementById('loadingMes');
        
        submitBtn.disabled = true;
        loadingDiv.style.display = 'block';

        try {
            const response = await fetch(`${BASE_URL}/wir/session/${currentSessionId}/step2`, { method: 'POST', body: formData });
            if (!response.ok) throw new Error("MES processing failed");

            const data = await response.json();
            currentChecklist = data.checklist;
            sessionStatus = "MES_EXTRACTED";
            
            loadStep(2);
        } catch (error) {
            alert("An error occurred while processing the Method Statement.");
        } finally {
            submitBtn.disabled = false;
            loadingDiv.style.display = 'none';
        }
    });

    // Regenerate Step 2
    document.getElementById('regenerateBtn')?.addEventListener('click', () => {
        showSection('step2UploadSection');
    });

    function renderChecklist(checklist) {
        const tableBody = document.getElementById('checklistTableBody');
        if (!tableBody) return;
        tableBody.innerHTML = '';

        if (!checklist || checklist.length === 0) {
            tableBody.innerHTML = `<tr><td colspan="${currentStep === 2 ? 7 : 5}" class="text-center py-4">No items.</td></tr>`;
            return;
        }

        checklist.forEach((item, index) => {
            const row = document.createElement('tr');
            let html = `
                <td>${item.item_number || (index + 1)}</td>
                <td>${item.item_text}</td>
                <td>${item.acceptance_criteria}</td>
                <td>${item.control_point || 'N/A'}</td>
            `;
            if (currentStep === 2) {
                html += `
                    <td class="step2-col">${item.procedure_text || 'N/A'}</td>
                    <td class="step2-col">${item.safety_text || 'N/A'}</td>
                `;
            }
            html += `
                <td>
                    <button class="btn btn-sm btn-outline-primary edit-btn" data-index="${index}">Edit</button>
                    <button class="btn btn-sm btn-outline-danger delete-btn" data-index="${index}">Delete</button>
                </td>
            `;
            row.innerHTML = html;
            tableBody.appendChild(row);
        });

        document.querySelectorAll('.edit-btn').forEach(btn => btn.addEventListener('click', (e) => openEditModal(e.target.getAttribute('data-index'))));
        document.querySelectorAll('.delete-btn').forEach(btn => btn.addEventListener('click', (e) => deleteItem(e.target.getAttribute('data-index'))));
    }

    function openEditModal(index) {
        const item = currentChecklist[index];
        document.getElementById('editItemIndex').value = index;
        document.getElementById('editItemId').value = item.id || '';
        document.getElementById('editItemNum').value = item.item_number || '';
        document.getElementById('editActivity').value = item.item_text || '';
        document.getElementById('editCriteria').value = item.acceptance_criteria || '';
        document.getElementById('editControlPoint').value = item.control_point || '';
        
        if (currentStep === 2) {
            document.getElementById('editProcedure').value = item.procedure_text || '';
            document.getElementById('editSafety').value = item.safety_text || '';
        }
        
        if (editModal) editModal.show();
    }

    document.getElementById('saveEditBtn')?.addEventListener('click', async () => {
        const index = document.getElementById('editItemIndex').value;
        const itemId = document.getElementById('editItemId').value;
        
        const updatedData = {
            item_number: document.getElementById('editItemNum').value,
            item_text: document.getElementById('editActivity').value,
            acceptance_criteria: document.getElementById('editCriteria').value,
            control_point: document.getElementById('editControlPoint').value,
            procedure_text: currentStep === 2 ? document.getElementById('editProcedure').value : currentChecklist[index].procedure_text,
            safety_text: currentStep === 2 ? document.getElementById('editSafety').value : currentChecklist[index].safety_text
        };

        try {
            if (itemId) {
                await fetch(`${BASE_URL}/checklist/${itemId}`, {
                    method: 'PUT',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(updatedData)
                });
            }
            currentChecklist[index] = { ...currentChecklist[index], ...updatedData };
            renderChecklist(currentChecklist);
            if (editModal) editModal.hide();
        } catch (error) {
            alert("Failed to update item.");
        }
    });

    async function deleteItem(index) {
        if (!confirm("Delete this item?")) return;
        const item = currentChecklist[index];
        try {
            if (item.id) await fetch(`${BASE_URL}/checklist/${item.id}`, { method: 'DELETE' });
            currentChecklist.splice(index, 1);
            renderChecklist(currentChecklist);
        } catch (error) {
            alert("Failed to delete item.");
        }
    }

    document.getElementById('saveChangesBtn')?.addEventListener('click', async () => {
        if (!currentSessionId) return;
        const saveBtn = document.getElementById('saveChangesBtn');
        saveBtn.disabled = true;
        
        try {
            await fetch(`${BASE_URL}/wir/session/${currentSessionId}/verify`, { method: 'PUT' });
            
            if (currentStep === 1) {
                // Move to Step 2
                await fetch(`${BASE_URL}/wir/session/${currentSessionId}/step/2`, { method: 'PUT' });
                alert("Step 1 Verified! Moving to Step 2: Method Statement Processing.");
                sessionStatus = 'STEP_1_VERIFIED';
                loadStep(2);
            } else if (currentStep === 2) {
                alert("Step 2 Verified! Workflow completed for now.");
                loadSessions();
                showSection('explorerSection');
            }
        } catch (error) {
            alert("Failed to save changes.");
        } finally {
            saveBtn.disabled = false;
        }
    });
});
