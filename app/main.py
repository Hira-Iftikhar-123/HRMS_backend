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

app = FastAPI()

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

@app.get("/")
def read_root():
    return {"message": "HRMS Backend is running successfully at localhost:8001"}
