# Inspectra AI

## Project Description
Inspectra AI is a 4-step iterative Work Inspection Request (WIR) generator designed for MBL. The primary goal is to streamline the process of moving from raw Inspection and Test Plans (ITPs) and engineering drawings to a finalized Work Inspection Request. Human verification is required at every step before proceeding.

## Tech Stack
*   **Backend:** FastAPI (Python)
*   **Database:** PostgreSQL (SQLAlchemy ORM)
*   **Frontend:** Bootstrap 5
*   **Infrastructure:** Docker & Docker Compose
*   **AI Integration:** Gemini 1.5 Pro (Long-Context Mode)

## Key Features
*   **Iterative WIR Generation:** A structured 4-step process for generating WIRs.
*   **Human Verification:** Each step requires explicit human approval before advancing.
*   **High-Fidelity PDF Extraction:** Utilizes PyMuPDF for accurate extraction of data from ITPs and drawings.
*   **State Management:** Maintains the progress of WIR generation through a state machine implemented in PostgreSQL using a JSONB field.

## Setup and Installation

### Prerequisites
*   Docker
*   Docker Compose

### Running the Application
1.  **Clone the repository:**
    ```bash
    git clone <repository_url>
    cd wir_inspector
    ```
    (Note: Replace `<repository_url>` with the actual repository URL once known.)
2.  **Start the services:**
    ```bash
    docker-compose up -d --build
    ```
3.  **Apply database migrations:**
    Access the backend service shell and run Alembic migrations. (Specific commands will be added here once the alembic setup is clearer, e.g., `docker-compose exec backend alembic upgrade head`)

## Guidelines
*   **Formatting and Terminology:** Strictly adhere to the formatting and terminology found in the 'Final WIR Sample'.
*   **PDF Extraction:** PyMuPDF is used for high-fidelity PDF data extraction.
