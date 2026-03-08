document.getElementById('uploadForm').addEventListener('submit', async function(e) {
    e.preventDefault();
    
    const itpFile = document.getElementById('itpFile').files[0];
    const wirSampleFile = document.getElementById('wirSampleFile').files[0];
    
    if (!itpFile || !wirSampleFile) {
        alert("Please select both files.");
        return;
    }

    const formData = new FormData();
    formData.append("itp_file", itpFile);
    formData.append("wir_sample", wirSampleFile);

    // Show loading state
    const submitBtn = this.querySelector('button[type="submit"]');
    const loadingDiv = document.getElementById('loading');
    const resultsSection = document.getElementById('resultsSection');
    
    submitBtn.disabled = true;
    loadingDiv.style.display = 'block';
    resultsSection.style.display = 'none';

    try {
        const response = await fetch('http://localhost:8000/session/initialize', {
            method: 'POST',
            body: formData
        });

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        const data = await response.json();
        
        // Render results
        document.getElementById('sessionIdBadge').textContent = `Session: ${data.session_id.substring(0, 8)}...`;
        renderChecklist(data.checklist);
        
        // Show results
        resultsSection.style.display = 'block';
    } catch (error) {
        console.error("Error processing documents:", error);
        alert("An error occurred while processing the documents. Ensure the backend is running and CORS is configured.");
    } finally {
        // Reset loading state
        submitBtn.disabled = false;
        loadingDiv.style.display = 'none';
    }
});

function renderChecklist(checklist) {
    const container = document.getElementById('checklistContainer');
    container.innerHTML = ''; // Clear previous results

    if (!checklist || checklist.length === 0) {
        container.innerHTML = '<div class="alert alert-warning">No checklist items were extracted. Check the documents and try again.</div>';
        return;
    }

    checklist.forEach((item, index) => {
        // Handle varying keys returned by Gemini based on the prompt
        const itemNum = item.item_number || (index + 1);
        const activity = item.activity || "N/A";
        const criteria = item.acceptance_criteria || item.criteria || "N/A";
        const reference = item.reference || "N/A";

        const itemDiv = document.createElement('div');
        itemDiv.className = 'checklist-item';
        
        itemDiv.innerHTML = `
            <div class="row">
                <div class="col-md-1">
                    <span class="badge bg-secondary fs-6">${itemNum}</span>
                </div>
                <div class="col-md-11">
                    <h5 class="text-dark">${activity}</h5>
                    <div class="mt-2">
                        <strong>Acceptance Criteria:</strong>
                        <p class="mb-1 text-muted">${criteria}</p>
                    </div>
                    ${reference !== "N/A" ? `<div class="mt-2 text-primary small"><strong>Reference:</strong> ${reference}</div>` : ''}
                </div>
            </div>
        `;
        container.appendChild(itemDiv);
    });
}
