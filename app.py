import uvicorn
import os
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, BackgroundTasks, logger
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from starlette.templating import Jinja2Templates
from utils import process_resumes, generate_report

app = FastAPI(
    title="AI Resume Ranker API",
    description="AI-powered resume ranking system",
    version="1.0.0",
    docs_url="/docs",
    redoc_url=None
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

UPLOAD_DIR = "upload"
REPORT_DIR = "reports"
os.makedirs(REPORT_DIR, exist_ok=True)
os.makedirs(UPLOAD_DIR, exist_ok=True)

def _delete_file(path: str):
    if os.path.exists(path):
        os.unlink(path)


@app.post("/api/rank")
async def rank_resumes(
    job_description: str = Form(...),
    resumes: list[UploadFile] = File(...)
):
    """Endpoint to rank resumes based on job description"""
    try:
        if not job_description.strip():
            raise HTTPException(400, "Job description cannot be empty")
            
        if not resumes or not any(resume.filename for resume in resumes):
            raise HTTPException(400, "No resumes uploaded")
        
        file_paths = []
        for file in resumes:
            if not file.filename.lower().endswith(('.pdf', '.docx')):
                continue
                
            file_path = os.path.join(UPLOAD_DIR, file.filename)
            with open(file_path, "wb") as f:
                content = await file.read()
                f.write(content)
                
            file_paths.append(file_path)
        
        if not file_paths:
            raise HTTPException(400, "No valid resumes uploaded (PDF/DOCX only)")
        
        results = process_resumes(job_description, file_paths)

        for path in file_paths:
            _delete_file(path)

        report_filename = generate_report(results, REPORT_DIR)
        
        response_data = {
            "job_description": job_description,
            "results": [
                {
                    "rank": res["rank"],
                    "filename": res["filename"],
                    "grand_score": res["grand_score"],
                    "tech_stack": res["tech_stack"]
                } for res in results
            ],
            "report_url": f"/api/download/{report_filename}"
        }
        
        return response_data
        
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(500, f"Processing error: {str(e)}")

@app.get("/api/download/{filename}")
async def download_report(filename: str, bgTask : BackgroundTasks):
    """Endpoint to download generated reports"""
    file_path = os.path.join(REPORT_DIR, filename)
    if not os.path.exists(file_path):
        raise HTTPException(404, "Report not found")
    try:

        bgTask.add_task(_delete_file, file_path)

        return FileResponse(
            file_path,
            media_type="text/csv",
            filename=f"resume_report_{filename.split('_')[-1]}"
        )
    except Exception as e:
        logger.error(f"Error downloading report: {e}")
        raise HTTPException(500, "Error downloading report")

@app.get("/", response_class=HTMLResponse)
async def serve_frontend():
    """Serve the main frontend HTML page."""
    return templates.TemplateResponse("index.html", {"request": {}})

@app.get("/api/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "active",
        "message": "AI Resume Ranker API is running",
        "version": "1.0.0"
    }

if __name__ == "__main__":
    uvicorn.run("app:app", host="0.0.0.0", port=8080, reload=True)
