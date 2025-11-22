"""
WebSocket endpoint for real-time messaging between patients and doctors
Using FastAPI native WebSocket support
"""
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from typing import Dict, List, Set
import json
from datetime import datetime

router = APIRouter(prefix="/ws", tags=["WebSocket Messages"])


class MessageConnectionManager:
    """Manages WebSocket connections for messages"""
    
    def __init__(self):
        # Structure: {clinic_id: {user_id: [websocket1, websocket2]}}
        self.active_connections: Dict[int, Dict[int, List[WebSocket]]] = {}
        # Track threads users are viewing: {user_id: {thread_id}}
        self.user_threads: Dict[int, Set[int]] = {}
    
    async def connect(self, websocket: WebSocket, clinic_id: int, user_id: int):
        """Connect a user to the message WebSocket (connection must be accepted before calling this)"""
        if clinic_id not in self.active_connections:
            self.active_connections[clinic_id] = {}
        if user_id not in self.active_connections[clinic_id]:
            self.active_connections[clinic_id][user_id] = []
        self.active_connections[clinic_id][user_id].append(websocket)
        
        # Initialize user threads tracking
        if user_id not in self.user_threads:
            self.user_threads[user_id] = set()
    
    def disconnect(self, websocket: WebSocket, clinic_id: int, user_id: int):
        """Disconnect a user from the message WebSocket"""
        if clinic_id in self.active_connections and user_id in self.active_connections[clinic_id]:
            self.active_connections[clinic_id][user_id] = [
                conn for conn in self.active_connections[clinic_id][user_id] if conn != websocket
            ]
            if not self.active_connections[clinic_id][user_id]:
                del self.active_connections[clinic_id][user_id]
            if not self.active_connections[clinic_id]:
                del self.active_connections[clinic_id]
        
        # Clean up user threads if no connections
        if user_id in self.user_threads and not self._has_connections(user_id):
            del self.user_threads[user_id]
    
    def _has_connections(self, user_id: int) -> bool:
        """Check if user has any active connections"""
        for clinic_connections in self.active_connections.values():
            if user_id in clinic_connections and clinic_connections[user_id]:
                return True
        return False
    
    def subscribe_to_thread(self, user_id: int, thread_id: int):
        """Subscribe user to a specific thread"""
        if user_id not in self.user_threads:
            self.user_threads[user_id] = set()
        self.user_threads[user_id].add(thread_id)
    
    def unsubscribe_from_thread(self, user_id: int, thread_id: int):
        """Unsubscribe user from a specific thread"""
        if user_id in self.user_threads:
            self.user_threads[user_id].discard(thread_id)
    
    async def send_to_user(self, clinic_id: int, user_id: int, message: dict):
        """Send message to a specific user"""
        if clinic_id in self.active_connections and user_id in self.active_connections[clinic_id]:
            disconnected = []
            for connection in self.active_connections[clinic_id][user_id]:
                try:
                    await connection.send_json(message)
                except Exception as e:
                    print(f"Error sending to user {user_id}: {e}")
                    disconnected.append(connection)
            
            # Remove disconnected connections
            for conn in disconnected:
                self.disconnect(conn, clinic_id, user_id)
    
    async def broadcast_to_thread_participants(
        self, 
        clinic_id: int, 
        thread_id: int, 
        patient_user_id: int, 
        provider_user_id: int, 
        message: dict
    ):
        """Broadcast message to both patient and provider in a thread"""
        # Send to patient (using user_id, not patient_id)
        await self.send_to_user(clinic_id, patient_user_id, message)
        
        # Send to provider (using user_id)
        await self.send_to_user(clinic_id, provider_user_id, message)
    
    async def broadcast_thread_update(
        self,
        clinic_id: int,
        thread_id: int,
        patient_id: int,
        provider_id: int,
        update_data: dict
    ):
        """Broadcast thread update (new message, read status, etc.)"""
        message = {
            "type": "thread_update",
            "thread_id": thread_id,
            "data": update_data
        }
        await self.broadcast_to_thread_participants(
            clinic_id, thread_id, patient_id, provider_id, message
        )


message_manager = MessageConnectionManager()


@router.websocket("/messages")
async def messages_websocket(
    websocket: WebSocket,
    clinic_id: int = Query(...),
    user_id: int = Query(...),
    token: str = Query(None)
):
    """
    WebSocket endpoint for real-time messaging
    
    Query parameters:
    - clinic_id: Clinic ID
    - user_id: User ID
    - token: JWT token for authentication (recommended)
    """
    print(f"[WebSocket] Connection attempt - user_id={user_id}, clinic_id={clinic_id}, has_token={bool(token)}")
    
    # Initialize variables for exception handling
    verified_clinic_id = clinic_id
    verified_user_id = user_id
    connection_accepted = False
    
    try:
        # Accept connection first (required by FastAPI WebSocket)
        print(f"[WebSocket] Attempting to accept connection...")
        await websocket.accept()
        connection_accepted = True
        print(f"[WebSocket] ✓ Connection accepted for user {user_id}, clinic {clinic_id}")
        
        # Verify token if provided
        if token:
            try:
                from app.core.auth import verify_token
                payload = verify_token(token)
                verified_clinic_id = payload.get("clinic_id")
                verified_user_id = payload.get("user_id")
                
                # Verify that query params match token
                if verified_clinic_id != clinic_id or verified_user_id != user_id:
                    print(f"Token mismatch: query params (clinic={clinic_id}, user={user_id}) vs token (clinic={verified_clinic_id}, user={verified_user_id})")
                    await websocket.close(code=4403, reason="Token mismatch")
                    return
            except Exception as e:
                print(f"Token verification failed: {e}")
                import traceback
                traceback.print_exc()
                await websocket.close(code=4401, reason="Invalid token")
                return
        
        # Register connection with manager
        message_manager.connect(websocket, verified_clinic_id, verified_user_id)
        print(f"User {verified_user_id} connected to messages WebSocket")
        
        # Send connection confirmation
        await websocket.send_json({
            "type": "connected",
            "message": "Connected to messages WebSocket",
            "user_id": verified_user_id,
            "clinic_id": verified_clinic_id
        })
        
        # Handle incoming messages
        while True:
            data = await websocket.receive_text()
            try:
                message = json.loads(data)
                
                # Handle ping/pong for keepalive
                if message.get("type") == "ping":
                    await websocket.send_json({"type": "pong"})
                
                # Handle thread subscription
                elif message.get("type") == "subscribe_thread":
                    thread_id = message.get("thread_id")
                    if thread_id:
                        message_manager.subscribe_to_thread(verified_user_id, thread_id)
                        await websocket.send_json({
                            "type": "subscribed",
                            "thread_id": thread_id
                        })
                
                # Handle thread unsubscription
                elif message.get("type") == "unsubscribe_thread":
                    thread_id = message.get("thread_id")
                    if thread_id:
                        message_manager.unsubscribe_from_thread(verified_user_id, thread_id)
                        await websocket.send_json({
                            "type": "unsubscribed",
                            "thread_id": thread_id
                        })
                
            except json.JSONDecodeError:
                await websocket.send_json({
                    "type": "error",
                    "message": "Invalid JSON"
                })
                
    except WebSocketDisconnect:
        print(f"WebSocket disconnected normally for user {verified_user_id}")
        if connection_accepted:
            message_manager.disconnect(websocket, verified_clinic_id, verified_user_id)
    except Exception as e:
        print(f"WebSocket error for user {user_id}: {e}")
        import traceback
        traceback.print_exc()
        if connection_accepted:
            try:
                message_manager.disconnect(websocket, verified_clinic_id, verified_user_id)
            except:
                pass


async def broadcast_new_message(
    clinic_id: int,
    thread_id: int,
    patient_user_id: int,
    provider_user_id: int,
    message_data: dict
):
    """Broadcast a new message to thread participants"""
    await message_manager.broadcast_to_thread_participants(
        clinic_id,
        thread_id,
        patient_user_id,
        provider_user_id,
        {
            "type": "new_message",
            "thread_id": thread_id,
            "message": message_data
        }
    )


async def broadcast_message_read(
    clinic_id: int,
    thread_id: int,
    patient_user_id: int,
    provider_user_id: int,
    message_id: int
):
    """Broadcast message read status"""
    await message_manager.broadcast_to_thread_participants(
        clinic_id,
        thread_id,
        patient_user_id,
        provider_user_id,
        {
            "type": "message_read",
            "thread_id": thread_id,
            "message_id": message_id
        }
    )


async def broadcast_thread_updated(
    clinic_id: int,
    thread_id: int,
    patient_user_id: int,
    provider_user_id: int,
    thread_data: dict
):
    """Broadcast thread update (e.g., new thread, archived, etc.)"""
    await message_manager.broadcast_to_thread_participants(
        clinic_id,
        thread_id,
        patient_user_id,
        provider_user_id,
        {
            "type": "thread_updated",
            "thread_id": thread_id,
            "thread": thread_data
        }
    )

