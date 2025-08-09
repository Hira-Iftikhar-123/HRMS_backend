# Import all models to ensure they are registered with SQLAlchemy
from .user import User
from .role import Role
from .project import Project
from .task import Task
from .leave import Leave
from .attendance import Attendance
from .department import Department 
from .project_assignment import ProjectAssignment
from .evaluation import Evaluation
from .hr_department_map import HRDepartmentMap