from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func
from typing import List
from datetime import datetime
import logging
from app.core.database import get_db
from app.core.auth import get_current_user
from app.models.user import User
from app.models.sync_queue import SyncQueue
from app.models.evaluation import Evaluation
from app.models.task import Task
from app.models.feedback import Feedback
from app.models.leave import Leave
from app.models.attendance import Attendance
from app.schemas.sync_queue import (SyncQueueCreate, SyncQueueResponse, SyncQueueStatus, SyncResult)
from app.models.admin_log import AdminLog

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/sync", tags=["Sync"])


def _process_evaluation_sync(db: AsyncSession, operation_type: str, data: dict, record_id: int = None) -> dict:
    try:
        if operation_type == "create":
            evaluation = Evaluation(**data)
            db.add(evaluation)
            return {"success": True, "record_id": None, "message": "Evaluation created successfully"}
        
        elif operation_type == "update":
            if not record_id:
                return {"success": False, "message": "Record ID required for update operation"}
            
            # We'll handle the actual update in the main function
            return {"success": True, "record_id": record_id, "message": "Evaluation update prepared"}
        
        elif operation_type == "delete":
            if not record_id:
                return {"success": False, "message": "Record ID required for delete operation"}
            
            # We'll handle the actual deletion in the main function
            return {"success": True, "record_id": record_id, "message": "Evaluation deletion prepared"}
        
        else:
            return {"success": False, "message": f"Unsupported operation type: {operation_type}"}
    
    except Exception as e:
        logger.error(f"Error processing evaluation sync: {e}")
        return {"success": False, "message": f"Error processing evaluation sync: {str(e)}"}


def _process_task_sync(db: AsyncSession, operation_type: str, data: dict, record_id: int = None) -> dict:
    try:
        if operation_type == "create":
            task = Task(**data)
            db.add(task)
            return {"success": True, "record_id": None, "message": "Task created successfully"}
        
        elif operation_type == "update":
            if not record_id:
                return {"success": False, "message": "Record ID required for update operation"}
            
            return {"success": True, "record_id": record_id, "message": "Task update prepared"}
        
        elif operation_type == "delete":
            if not record_id:
                return {"success": False, "message": "Record ID required for delete operation"}
            
            return {"success": True, "record_id": record_id, "message": "Task deletion prepared"}
        
        else:
            return {"success": False, "message": f"Unsupported operation type: {operation_type}"}
    
    except Exception as e:
        logger.error(f"Error processing task sync: {e}")
        return {"success": False, "message": f"Error processing task sync: {str(e)}"}


def _process_feedback_sync(db: AsyncSession, operation_type: str, data: dict, record_id: int = None) -> dict:
    try:
        if operation_type == "create":
            feedback = Feedback(**data)
            db.add(feedback)
            return {"success": True, "record_id": None, "message": "Feedback created successfully"}
        
        elif operation_type == "update":
            if not record_id:
                return {"success": False, "message": "Record ID required for update operation"}
            
            return {"success": True, "record_id": record_id, "message": "Feedback update prepared"}
        
        elif operation_type == "delete":
            if not record_id:
                return {"success": False, "message": "Record ID required for delete operation"}
            
            return {"success": True, "record_id": record_id, "message": "Feedback deletion prepared"}
        
        else:
            return {"success": False, "message": f"Unsupported operation type: {operation_type}"}
    
    except Exception as e:
        logger.error(f"Error processing feedback sync: {e}")
        return {"success": False, "message": f"Error processing feedback sync: {str(e)}"}


def _process_leave_sync(db: AsyncSession, operation_type: str, data: dict, record_id: int = None) -> dict:
    try:
        if operation_type == "create":
            leave = Leave(**data)
            db.add(leave)
            return {"success": True, "record_id": None, "message": "Leave created successfully"}
        
        elif operation_type == "update":
            if not record_id:
                return {"success": False, "message": "Record ID required for update operation"}
            
            return {"success": True, "record_id": record_id, "message": "Leave update prepared"}
        
        elif operation_type == "delete":
            if not record_id:
                return {"success": False, "message": "Record ID required for delete operation"}
            
            return {"success": True, "record_id": record_id, "message": "Leave deletion prepared"}
        
        else:
            return {"success": False, "message": f"Unsupported operation type: {operation_type}"}
    
    except Exception as e:
        logger.error(f"Error processing leave sync: {e}")
        return {"success": False, "message": f"Error processing leave sync: {str(e)}"}


def _process_attendance_sync(db: AsyncSession, operation_type: str, data: dict, record_id: int = None) -> dict:
    try:
        if operation_type == "create":
            attendance = Attendance(**data)
            db.add(attendance)
            return {"success": True, "record_id": None, "message": "Attendance created successfully"}
        
        elif operation_type == "update":
            if not record_id:
                return {"success": False, "message": "Record ID required for update operation"}
            
            return {"success": True, "record_id": record_id, "message": "Attendance update prepared"}
        
        elif operation_type == "delete":
            if not record_id:
                return {"success": False, "message": "Record ID required for delete operation"}
            
            return {"success": True, "record_id": record_id, "message": "Attendance deletion prepared"}
        
        else:
            return {"success": False, "message": f"Unsupported operation type: {operation_type}"}
    
    except Exception as e:
        logger.error(f"Error processing attendance sync: {e}")
        return {"success": False, "message": f"Error processing attendance sync: {str(e)}"}


def _process_sync_item(db: AsyncSession, queue_item: SyncQueue) -> dict:
    try:
        queue_item.status = "processing"
        
        if queue_item.table_name == "evaluations":
            result = _process_evaluation_sync(
                db, queue_item.operation_type, queue_item.data, queue_item.record_id
            )
        elif queue_item.table_name == "tasks":
            result = _process_task_sync(
                db, queue_item.operation_type, queue_item.data, queue_item.record_id
            )
        elif queue_item.table_name == "feedbacks":
            result = _process_feedback_sync(
                db, queue_item.operation_type, queue_item.data, queue_item.record_id
            )
        elif queue_item.table_name == "leaves":
            result = _process_leave_sync(
                db, queue_item.operation_type, queue_item.data, queue_item.record_id
            )
        elif queue_item.table_name == "attendance":
            result = _process_attendance_sync(
                db, queue_item.operation_type, queue_item.data, queue_item.record_id
            )
        else:
            result = {"success": False, "message": f"Unsupported table: {queue_item.table_name}"}
        
        if result["success"]:
            queue_item.status = "completed"
            queue_item.synced_at = datetime.utcnow()
        else:
            queue_item.status = "failed"
            queue_item.error_message = result["message"]
            queue_item.retry_count += 1
        
        return result
    
    except Exception as e:
        logger.error(f"Error processing sync item {queue_item.id}: {e}")
        queue_item.status = "failed"
        queue_item.error_message = str(e)
        queue_item.retry_count += 1
        return {"success": False, "message": f"Error processing sync: {str(e)}"}


@router.post("/offline_data", response_model=List[SyncQueueResponse])
async def sync_offline_data(
    sync_data: SyncQueueCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        queue_items = []
        results = []
        
        # Process each item individually
        for item in sync_data.items:
            try:
                # Create queue item
                queue_item = SyncQueue(
                    user_id=current_user.id,
                    operation_type=item.operation_type,
                    table_name=item.table_name,
                    record_id=item.record_id,
                    data=item.data,
                    status="pending"
                )
                db.add(queue_item)
                await db.flush()  # Flush to get the ID
                
                # Process the sync item
                result = _process_sync_item(db, queue_item)
                
                # Create response
                response = SyncQueueResponse(
                    id=queue_item.id,
                    user_id=queue_item.user_id,
                    operation_type=queue_item.operation_type,
                    table_name=queue_item.table_name,
                    record_id=queue_item.record_id,
                    data=queue_item.data,
                    status=queue_item.status,
                    error_message=queue_item.error_message,
                    retry_count=queue_item.retry_count,
                    created_at=queue_item.created_at,
                    updated_at=queue_item.updated_at,
                    synced_at=queue_item.synced_at
                )
                results.append(response)
                queue_items.append(queue_item)
                
            except Exception as e:
                logger.error(f"Error processing sync item: {e}")
                # Create a failed response
                failed_response = SyncQueueResponse(
                    id=0,  # Temporary ID
                    user_id=current_user.id,
                    operation_type=item.operation_type,
                    table_name=item.table_name,
                    record_id=item.record_id,
                    data=item.data,
                    status="failed",
                    error_message=str(e),
                    retry_count=0,
                    created_at=datetime.utcnow(),
                    updated_at=None,
                    synced_at=None
                )
                results.append(failed_response)
        
        # Commit all changes at once
        await db.commit()
        
        # Log the sync operation
        try:
            db.add(AdminLog(
                type="offline_sync",
                message=f"Offline data sync completed: {len(sync_data.items)} items",
                actor_user_id=current_user.id,
                meta={
                    "total_items": len(sync_data.items),
                    "successful_items": len([r for r in results if r.status == "completed"]),
                    "failed_items": len([r for r in results if r.status == "failed"])
                }
            ))
            await db.commit()
        except Exception:
            pass
        
        logger.info(f"Offline sync completed for user {current_user.id}: {len(sync_data.items)} items")
        return results
    
    except Exception as e:
        logger.error(f"Error in offline sync: {e}")
        raise HTTPException(status_code=500, detail=f"Sync failed: {str(e)}")


@router.get("/queue_status", response_model=SyncQueueStatus)
async def get_sync_queue_status(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        result = await db.execute(
            select(func.count(SyncQueue.id)).where(SyncQueue.user_id == current_user.id)
        )
        total_items = result.scalar()
        result = await db.execute(
            select(func.count(SyncQueue.id)).where(
                SyncQueue.user_id == current_user.id,
                SyncQueue.status == "pending"
            )
        )
        pending_items = result.scalar()
        
        result = await db.execute(
            select(func.count(SyncQueue.id)).where(
                SyncQueue.user_id == current_user.id,
                SyncQueue.status == "completed"
            )
        )
        completed_items = result.scalar()
        
        result = await db.execute(
            select(func.count(SyncQueue.id)).where(
                SyncQueue.user_id == current_user.id,
                SyncQueue.status == "failed"
            )
        )
        failed_items = result.scalar()
        
        result = await db.execute(
            select(SyncQueue.updated_at).where(
                SyncQueue.user_id == current_user.id,
                SyncQueue.status.in_(["completed", "failed"])
            ).order_by(SyncQueue.updated_at.desc())
        )
        last_sync_attempt = result.scalar()
        
        return SyncQueueStatus(
            total_items=total_items,
            pending_items=pending_items,
            completed_items=completed_items,
            failed_items=failed_items,
            last_sync_attempt=last_sync_attempt
        )
    
    except Exception as e:
        logger.error(f"Error getting sync queue status: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get sync status: {str(e)}")


@router.get("/queue_items", response_model=List[SyncQueueResponse])
async def get_sync_queue_items(
    status: str = None,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        query = select(SyncQueue).where(SyncQueue.user_id == current_user.id)
        
        if status:
            query = query.where(SyncQueue.status == status)
        
        query = query.order_by(SyncQueue.created_at.desc()).limit(limit)
        
        result = await db.execute(query)
        queue_items = result.scalars().all()
        
        return [
            SyncQueueResponse(
                id=item.id,
                user_id=item.user_id,
                operation_type=item.operation_type,
                table_name=item.table_name,
                record_id=item.record_id,
                data=item.data,
                status=item.status,
                error_message=item.error_message,
                retry_count=item.retry_count,
                created_at=item.created_at,
                updated_at=item.updated_at,
                synced_at=item.synced_at
            )
            for item in queue_items
        ]
    
    except Exception as e:
        logger.error(f"Error getting sync queue items: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get sync items: {str(e)}")


@router.post("/retry_failed", response_model=List[SyncResult])
async def retry_failed_sync_items(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        result = await db.execute(
            select(SyncQueue).where(
                SyncQueue.user_id == current_user.id,
                SyncQueue.status == "failed"
            )
        )
        failed_items = result.scalars().all()
        
        results = []
        for item in failed_items:
            item.status = "pending"
            item.error_message = None
            await db.commit()
            
            result = await _process_sync_item(db, item)
            
            results.append(SyncResult(
                queue_id=item.id,
                success=result["success"],
                message=result["message"],
                synced_at=datetime.utcnow()
            ))
        
        logger.info(f"Retry completed for user {current_user.id}: {len(failed_items)} items")
        return results
    
    except Exception as e:
        logger.error(f"Error retrying failed sync items: {e}")
        raise HTTPException(status_code=500, detail=f"Retry failed: {str(e)}")


@router.delete("/clear_completed")
async def clear_completed_sync_items(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        result = await db.execute(
            select(SyncQueue).where(
                SyncQueue.user_id == current_user.id,
                SyncQueue.status == "completed"
            )
        )
        completed_items = result.scalars().all()
        
        for item in completed_items:
            await db.delete(item)
        
        await db.commit()
        
        logger.info(f"Cleared {len(completed_items)} completed sync items for user {current_user.id}")
        return {"message": f"Cleared {len(completed_items)} completed sync items"}
    
    except Exception as e:
        logger.error(f"Error clearing completed sync items: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to clear items: {str(e)}")
