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

    // New Step 3 elements
    const step3UploadSection = document.getElementById('step3UploadSection');
    const uploadDrawingForm = document.getElementById('uploadDrawingForm');
    const loadingDrawing = document.getElementById('loadingDrawing');
    const displayGridLines = document.getElementById('displayGridLines');
    const displayLevels = document.getElementById('displayLevels');
    const displayZone = document.getElementById('displayZone');
    const editGridLines = document.getElementById('editGridLines');
    const editLevels = document.getElementById('editLevels');
    const editZone = document.getElementById('editZone');
    const updateLocationDataBtn = document.getElementById('updateLocationDataBtn');
    
    // Global elements for notifications
    const errorMessage = document.getElementById('errorMessage');
    const successMessage = document.getElementById('successMessage');
    const masterDisciplineBadge = document.getElementById('masterDisciplineBadge');
    const masterWorkTypeBadge = document.getElementById('masterWorkTypeBadge');

    // Helper functions for messages
    function showMessage(element, message, type) {
        if (element) {
            element.textContent = message;
            element.className = `alert alert-${type}`;
            element.style.display = 'block';
        }
    }

    function showError(message) {
        showMessage(errorMessage, message, 'danger');
    }

    function showSuccess(message) {
        showMessage(successMessage, message, 'success');
    }

    function clearMessages() {
        if (errorMessage) errorMessage.style.display = 'none';
        if (successMessage) successMessage.style.display = 'none';
    }

    // Helper to switch sections
    function showSection(sectionId) {
        const sections = ['newSessionSection', 'explorerSection', 'resultsSection', 'step2UploadSection', 'step3UploadSection']; // Added step3UploadSection
        sections.forEach(id => {
            const el = document.getElementById(id);
            if (el) el.style.display = (id === sectionId) ? 'block' : 'none';
        });
        
        // Show/hide step header
        const stepHeader = document.getElementById('stepHeader');
        if (sectionId === 'resultsSection' || sectionId === 'step2UploadSection' || sectionId === 'step3UploadSection') { // Added step3UploadSection
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

    // New Step 3 navigation button handler
    // This button will be dynamically added/updated by updateStepNavigation
    // No need for a global btnStep3 reference here, updateStepNavigation handles creation
    
    function updateStepNavigation(sessionCurrentStep) {
        const btnStep1 = document.getElementById('btnStep1');
        const btnStep2 = document.getElementById('btnStep2');
        let btnStep3 = document.getElementById('btnStep3'); // Re-get in case it was just created

        // Create Step 3 button if it doesn't exist
        if (!btnStep3) {
            btnStep3 = document.createElement('button');
            btnStep3.id = 'btnStep3';
            btnStep3.classList.add('btn', 'btn-outline-primary', 'btn-sm', 'me-2');
            btnStep3.textContent = 'Step 3 (Drawing)';
            document.getElementById('stepNavigation').appendChild(btnStep3);
            btnStep3.addEventListener('click', () => {
                if (currentSessionId && currentStep >= 3) loadStep(3);
            });
        }

        // Reset button styles
        btnStep1.classList.remove('btn-primary', 'btn-outline-primary', 'active');
        btnStep2.classList.remove('btn-primary', 'btn-outline-primary', 'active');
        btnStep3.classList.remove('btn-primary', 'btn-outline-primary', 'active');

        // Set default states
        btnStep1.classList.add('btn-outline-primary');
        btnStep2.classList.add('btn-outline-primary');
        btnStep3.classList.add('btn-outline-primary');

        // Enable/Disable and Highlight based on session state
        btnStep1.disabled = false;
        if (sessionCurrentStep >= 1) {
            btnStep1.classList.remove('btn-outline-primary');
            btnStep1.classList.add('btn-primary');
        }
        if (sessionCurrentStep === 1) btnStep1.classList.add('active');


        btnStep2.disabled = sessionCurrentStep < 2;
        if (sessionCurrentStep >= 2) {
            btnStep2.classList.remove('btn-outline-primary');
            btnStep2.classList.add('btn-primary');
        }
        if (sessionCurrentStep === 2) btnStep2.classList.add('active');

        btnStep3.disabled = sessionCurrentStep < 3;
        if (sessionCurrentStep >= 3) {
            btnStep3.classList.remove('btn-outline-primary');
            btnStep3.classList.add('btn-primary');
        }
        if (sessionCurrentStep === 3) btnStep3.classList.add('active');
    }

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
        // Badges are now updated in loadStep after fetching session details
        
        try {
            // Fetch session details and checklist within loadStep for consistency
            loadStep(step || currentStep); // Pass initial step
        } catch (error) {
            showError("Error resuming session: " + error.message);
        }
    }

    async function fetchSessionDetails(sessionId) {
        try {
            const response = await fetch(`${BASE_URL}/sessions/${sessionId}`);
            if (!response.ok) throw new Error("Failed to fetch session details.");
            return await response.json();
        } catch (error) {
            showError(error.message);
            return null;
        }
    }

    async function fetchChecklist(sessionId) {
        try {
            const response = await fetch(`${BASE_URL}/sessions/${sessionId}/checklist`);
            if (!response.ok) throw new Error("Failed to fetch checklist.");
            return await response.json();
        } catch (error) {
            showError(error.message);
            return [];
        }
    }

    async function loadStep(stepNumber) {
        currentStep = stepNumber;
        clearMessages(); // Clear any previous messages
        
        // Fetch latest session details to ensure UI is up-to-date
        const session = await fetchSessionDetails(currentSessionId);
        if (!session) {
            showError("Failed to load session details.");
            return;
        }
        sessionStatus = session.status;
        currentChecklist = await fetchChecklist(currentSessionId); // Fetch latest checklist

        // Update step header badges
        document.getElementById('sessionIdBadge').textContent = `ID: ${session.session_id.substring(0, 8)}...`;
        document.getElementById('sessionNameBadge').textContent = session.session_name || '';

        if (session.master_discipline) {
            masterDisciplineBadge.textContent = `Discipline: ${session.master_discipline}`;
            masterDisciplineBadge.style.display = 'inline-block';
        } else {
            masterDisciplineBadge.style.display = 'none';
        }
        if (session.master_work_type) {
            masterWorkTypeBadge.textContent = `Work Type: ${session.master_work_type}`;
            masterWorkTypeBadge.style.display = 'inline-block';
        } else {
            masterWorkTypeBadge.style.display = 'none';
        }

        // Update step navigation buttons based on session state
        updateStepNavigation(session.current_step);

        // Logic based on stepNumber
        if (stepNumber === 1) {
            document.getElementById('stepTitle').textContent = "Step 1: ITP Checklist";
            // No need to set button classes here, updateStepNavigation handles it
            
            // Hide Step 2 & 3 specific columns/fields
            document.querySelectorAll('.step2-col').forEach(col => col.style.display = 'none');
            document.getElementById('step2EditFields').style.display = 'none';
            document.getElementById('regenerateBtn').style.display = 'none';
            
            renderChecklist(currentChecklist);
            showSection('resultsSection');
        } 
        else if (stepNumber === 2) { 
            document.getElementById('stepTitle').textContent = "Step 2: Enriched Checklist (MES)";
            // No need to set button classes here, updateStepNavigation handles it
            
            // Show Step 2 columns
            document.querySelectorAll('.step2-col').forEach(col => col.style.display = 'table-cell');
            document.getElementById('step2EditFields').style.display = 'block';
            
            // Check if MES is already extracted or verified
            if (sessionStatus === 'MES_EXTRACTED' || sessionStatus === 'STEP_2_VERIFIED' || currentChecklist.some(item => item.procedure_text && item.procedure_text !== 'N/A')) {
                document.getElementById('regenerateBtn').style.display = 'inline-block';
                renderChecklist(currentChecklist);
                showSection('resultsSection');
            } else {
                showSection('step2UploadSection');
            }
        }
        else if (stepNumber === 3) {
            document.getElementById('stepTitle').textContent = "Step 3: Drawing & Location Processor";
            // No need to set button classes here, updateStepNavigation handles it
            
            // Hide Step 2 columns
            document.querySelectorAll('.step2-col').forEach(col => col.style.display = 'none');
            document.getElementById('step2EditFields').style.display = 'none';
            document.getElementById('regenerateBtn').style.display = 'none'; // No regenerate for step 3 yet

            // Display extracted data
            displayGridLines.textContent = session.grid_lines ? session.grid_lines.join(', ') : 'N/A';
            displayLevels.textContent = session.levels ? session.levels.join(', ') : 'N/A';
            displayZone.textContent = session.zone || 'N/A';

            // Populate manual correction fields
            editGridLines.value = session.grid_lines ? session.grid_lines.join(', ') : '';
            editLevels.value = session.levels ? session.levels.join(', ') : '';
            editZone.value = session.zone || '';
            
            showSection('step3UploadSection');
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
            
            // All session details (including master discipline/work type) will be
            // fetched and displayed by loadStep(1)
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

    // Step 3 Upload (Drawing)
    uploadDrawingForm?.addEventListener('submit', async function(e) {
        e.preventDefault();
        clearMessages();
        
        const drawingFile = document.getElementById('drawingFile').files[0];
        
        if (!drawingFile) {
            showError('Please select a drawing file.');
            return;
        }

        const formData = new FormData();
        formData.append('drawing_file', drawingFile);

        const submitBtn = this.querySelector('button[type="submit"]');
        
        submitBtn.disabled = true;
        loadingDrawing.style.display = 'block';

        try {
            const response = await fetch(`${BASE_URL}/wir/session/${currentSessionId}/step3`, {
                method: 'POST',
                body: formData
            });
            const data = await response.json();
            if (!response.ok) {
                throw new Error(data.detail || 'Failed to process drawing.');
            }
            showSuccess('Drawing processed successfully. Review extracted data below.');
            // Update session details and UI
            loadStep(3); // Reload step 3 to show updated data
        } catch (error) {
            showError(error.message);
        } finally {
            submitBtn.disabled = false;
            loadingDrawing.style.display = 'none';
        }
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

    // Event listener for manual location data update
    updateLocationDataBtn?.addEventListener('click', async () => {
        clearMessages();
        
        const updatedGridLines = editGridLines.value.split(',').map(s => s.trim()).filter(s => s);
        const updatedLevels = editLevels.value.split(',').map(s => s.trim()).filter(s => s);
        const updatedZone = editZone.value.trim();

        // Display the updated values
        displayGridLines.textContent = updatedGridLines.join(', ');
        displayLevels.textContent = updatedLevels.join(', ');
        displayZone.textContent = updatedZone;
        showSuccess('Location data updated locally. (Backend update not yet implemented, refresh to revert)');

        // Ideally, you'd make an API call here to persist changes:
        // For example, a PATCH endpoint: /wir/session/{currentSessionId}/location
        // try {
        //     const response = await fetch(`${BASE_URL}/wir/session/${currentSessionId}/location`, {
        //         method: 'PATCH',
        //         headers: { 'Content-Type': 'application/json' },
        //         body: JSON.stringify({ grid_lines: updatedGridLines, levels: updatedLevels, zone: updatedZone })
        //     });
        //     const data = await response.json();
        //     if (!response.ok) {
        //         throw new Error(data.detail || 'Failed to update location data.');
        //     }
        //     await fetchAndDisplaySession(currentSessionId); // Or just loadStep(3)
        //     showSuccess('Location data updated successfully!');
        // } catch (error) {
        //     showError(error.message);
        // }
    });

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
                showSuccess("Step 2 Verified! Moving to Step 3: Drawing & Location Processor.");
                await fetch(`${BASE_URL}/wir/session/${currentSessionId}/step/3`, { method: 'PUT' });
                sessionStatus = 'STEP_2_VERIFIED'; // Or 'MES_EXTRACTED', depending on backend's state after verification
                loadStep(3); // Load step 3
            } else if (currentStep === 3) {
                showSuccess("Step 3 Verified! Workflow completed for now.");
                loadSessions();
                showSection('explorerSection');
            }
        } catch (error) {
            showError("Failed to save changes: " + error.message);
        } finally {
            saveBtn.disabled = false;
        }
    });
});
