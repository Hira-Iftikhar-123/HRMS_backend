from fastapi import FastAPI
from app.routers.user import router as user_router
from app.routers.role import router as role_router
from app.routers.project import router as project_router
from app.routers.attendance import router as attendance_router
from app.routers.task import router as task_router
from app.routers.auth import router as auth_router
from app.routers.leave import router as leave_router
from app.routers.dashboard import router as dashboard_router
from app.routers.department import router as department_router
from app.routers.export import router as export_router
from app.routers.evaluation import router as evaluation_router
from app.routers.feedback import router as feedback_router
from app.routers.notification import router as notification_router
from app.routers.report import router as report_router
from app.routers.admin import router as admin_router
from app.routers.sync import router as sync_router
from app.core.security import setup_security_middleware
import os

ENVIRONMENT = os.getenv("ENVIRONMENT", "development")

if ENVIRONMENT == "production":
    app = FastAPI(
        title="HRMS Backend",
        description="Secure HR Management System Backend",
        version="1.0.0",
        docs_url=None,  
        redoc_url=None,  
        openapi_url=None  
    )
else:
    app = FastAPI(
        title="HRMS Backend",
        description="Secure HR Management System Backend",
        version="1.0.0"
    )

setup_security_middleware(app)

app.include_router(user_router)
app.include_router(role_router)
app.include_router(project_router)
app.include_router(attendance_router)
app.include_router(task_router)
app.include_router(auth_router)
app.include_router(leave_router)
app.include_router(dashboard_router)
app.include_router(department_router)
app.include_router(export_router)
app.include_router(evaluation_router)
app.include_router(feedback_router)
app.include_router(notification_router)
app.include_router(report_router)
app.include_router(admin_router)
app.include_router(sync_router)

@app.get("/")
def read_root():
    return {"message": "HRMS Backend is running successfully", "environment": ENVIRONMENT}

@app.get("/health")
def health_check():
    return {"status": "healthy", "environment": ENVIRONMENT} 