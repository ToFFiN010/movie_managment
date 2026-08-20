import json
import logging
from channels.generic.websocket import AsyncWebsocketConsumer

logger = logging.getLogger(__name__)


class SeatBookingConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.show_id = self.scope['url_route']['kwargs']['show_id']
        self.room_group_name = f"show_{self.show_id}"

        # Join show seat group
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        await self.accept()
        logger.info(f"WebSocket client connected to show group {self.room_group_name}")

    async def disconnect(self, close_code):
        # Leave group
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )
        logger.info(f"WebSocket client disconnected from show group {self.room_group_name}")

    async def receive(self, text_data):
        try:
            data = json.loads(text_data)
            action = data.get('action')
            if action == 'ping':
                await self.send(text_data=json.dumps({'type': 'pong'}))
        except Exception as e:
            logger.error(f"Error handling WS message: {e}")

    async def seat_update(self, event):
        """
        Handler for seat_update group message broadcast.
        """
        await self.send(text_data=json.dumps({
            'type': 'seat_update',
            'seat_ids': event.get('seat_ids', []),
            'status': event.get('status'),
            'user_id': event.get('user_id'),
            'timestamp': event.get('timestamp')
        }))
