"""
Telemedicine WebRTC Signaling Server
Handles WebRTC offer/answer exchange and ICE candidates for video consultations
"""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query, HTTPException, Depends
from typing import Dict, Optional
import json
import logging
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models import User, Appointment
from app.core.auth import get_current_user
from database import get_async_session

router = APIRouter(prefix="/telemedicine", tags=["Telemedicine"])

logger = logging.getLogger(__name__)

# Store active WebRTC connections: {appointment_id: {doctor_ws: WebSocket, patient_ws: WebSocket}}
active_webrtc_connections: Dict[int, Dict[str, WebSocket]] = {}


class WebRTCSignalingManager:
    """Manages WebRTC signaling connections for telemedicine"""
    
    def __init__(self):
        self.connections: Dict[int, Dict[str, WebSocket]] = {}
    
    async def connect(self, appointment_id: int, role: str, websocket: WebSocket):
        """Connect a peer to the signaling server"""
        await websocket.accept()
        
        if appointment_id not in self.connections:
            self.connections[appointment_id] = {}
        
        self.connections[appointment_id][role] = websocket
        logger.info(f"WebRTC connection established: appointment_id={appointment_id}, role={role}")
    
    def disconnect(self, appointment_id: int, role: str):
        """Disconnect a peer from the signaling server"""
        if appointment_id in self.connections:
            self.connections[appointment_id].pop(role, None)
            if not self.connections[appointment_id]:
                del self.connections[appointment_id]
        logger.info(f"WebRTC connection closed: appointment_id={appointment_id}, role={role}")
    
    async def send_to_peer(self, appointment_id: int, from_role: str, message: dict):
        """Send signaling message to the other peer"""
        if appointment_id not in self.connections:
            return False
        
        other_role = "patient" if from_role == "doctor" else "doctor"
        
        if other_role not in self.connections[appointment_id]:
            logger.warning(f"Peer not connected: appointment_id={appointment_id}, role={other_role}")
            return False
        
        try:
            await self.connections[appointment_id][other_role].send_json(message)
            return True
        except Exception as e:
            logger.error(f"Error sending message to peer: {e}")
            return False


signaling_manager = WebRTCSignalingManager()


@router.websocket("/signaling/{appointment_id}")
async def webrtc_signaling(
    websocket: WebSocket,
    appointment_id: int,
    user_id: int = Query(...),
    role: str = Query(...),  # "doctor" or "patient"
    db: AsyncSession = Depends(get_async_session)
):
    """
    WebRTC signaling endpoint for offer/answer/ICE candidate exchange
    
    Message types:
    - offer: WebRTC offer from initiator
    - answer: WebRTC answer from receiver
    - ice-candidate: ICE candidate for NAT traversal
    - call-ended: Notification that call has ended
    """
    # Verify appointment exists and user has access
    appointment_query = select(Appointment).where(Appointment.id == appointment_id)
    appointment_result = await db.execute(appointment_query)
    appointment = appointment_result.scalar_one_or_none()
    
    if not appointment:
        await websocket.close(code=1008, reason="Appointment not found")
        return
    
    # Verify user role matches appointment
    if role == "doctor" and appointment.doctor_id != user_id:
        await websocket.close(code=1008, reason="Unauthorized: Not the appointment doctor")
        return
    elif role == "patient" and appointment.patient_id != user_id:
        await websocket.close(code=1008, reason="Unauthorized: Not the appointment patient")
        return
    
    # Connect to signaling server
    await signaling_manager.connect(appointment_id, role, websocket)
    
    try:
        # Send connection confirmation
        await websocket.send_json({
            "type": "connected",
            "appointment_id": appointment_id,
            "role": role,
            "message": "Connected to signaling server"
        })
        
        # Notify other peer if already connected
        other_role = "patient" if role == "doctor" else "doctor"
        if other_role in signaling_manager.connections.get(appointment_id, {}):
            await signaling_manager.send_to_peer(appointment_id, role, {
                "type": "peer-connected",
                "role": role
            })
        
        # Handle signaling messages
        while True:
            try:
                data = await websocket.receive_json()
                message_type = data.get("type")
                
                logger.debug(f"Received signaling message: type={message_type}, appointment_id={appointment_id}, from={role}")
                
                # Forward signaling messages to the other peer
                if message_type in ["offer", "answer", "ice-candidate"]:
                    success = await signaling_manager.send_to_peer(appointment_id, role, data)
                    if not success:
                        await websocket.send_json({
                            "type": "error",
                            "message": "Peer not connected yet"
                        })
                
                elif message_type == "call-ended":
                    # Notify other peer and close connections
                    await signaling_manager.send_to_peer(appointment_id, role, data)
                    break
                
            except json.JSONDecodeError:
                await websocket.send_json({
                    "type": "error",
                    "message": "Invalid JSON format"
                })
            except Exception as e:
                logger.error(f"Error handling signaling message: {e}")
                await websocket.send_json({
                    "type": "error",
                    "message": str(e)
                })
                
    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected: appointment_id={appointment_id}, role={role}")
    except Exception as e:
        logger.error(f"WebRTC signaling error: {e}")
    finally:
        signaling_manager.disconnect(appointment_id, role)
        # Notify other peer of disconnection
        other_role = "patient" if role == "doctor" else "doctor"
        await signaling_manager.send_to_peer(appointment_id, role, {
            "type": "peer-disconnected",
            "role": role
        })


@router.get("/connection-status/{appointment_id}")
async def get_connection_status(
    appointment_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session)
):
    """Get WebRTC connection status for an appointment"""
    # Verify appointment access
    appointment_query = select(Appointment).where(
        Appointment.id == appointment_id,
        (Appointment.doctor_id == current_user.id) | (Appointment.patient_id == current_user.id)
    )
    appointment_result = await db.execute(appointment_query)
    appointment = appointment_result.scalar_one_or_none()
    
    if not appointment:
        raise HTTPException(status_code=404, detail="Appointment not found")
    
    connections = signaling_manager.connections.get(appointment_id, {})
    
    return {
        "appointment_id": appointment_id,
        "doctor_connected": "doctor" in connections,
        "patient_connected": "patient" in connections,
        "both_connected": "doctor" in connections and "patient" in connections
    }
