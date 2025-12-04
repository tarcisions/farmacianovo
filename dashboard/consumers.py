import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth.models import User
from core.models import PontuacaoFuncionario
from decimal import Decimal

class DashboardConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.user = self.scope["user"]
        if self.user.is_authenticated:
            self.group_name = f'dashboard_{self.user.id}'
            
            await self.channel_layer.group_add(
                self.group_name,
                self.channel_name
            )
            
            await self.accept()
        else:
            await self.close()
    
    async def disconnect(self, close_code):
        if self.user.is_authenticated:
            await self.channel_layer.group_discard(
                self.group_name,
                self.channel_name
            )
    
    async def receive(self, text_data):
        pass
    
    async def dashboard_update(self, event):
        await self.send(text_data=json.dumps({
            'type': 'dashboard_update',
            'data': event['data']
        }))


class PontuacaoConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.user = self.scope["user"]
        if self.user.is_authenticated:
            self.group_name = f'pontuacao_{self.user.id}'
            
            await self.channel_layer.group_add(
                self.group_name,
                self.channel_name
            )
            
            await self.accept()
            
            pontos = await self.get_pontos_atuais()
            await self.send(text_data=json.dumps({
                'type': 'pontuacao_atual',
                'pontos': str(pontos)
            }))
        else:
            await self.close()
    
    async def disconnect(self, close_code):
        if self.user.is_authenticated:
            await self.channel_layer.group_discard(
                self.group_name,
                self.channel_name
            )
    
    async def receive(self, text_data):
        pass
    
    @database_sync_to_async
    def get_pontos_atuais(self):
        return PontuacaoFuncionario.pontos_mes_atual(self.user)
    
    async def pontuacao_update(self, event):
        await self.send(text_data=json.dumps({
            'type': 'pontuacao_update',
            'pontos': event['pontos'],
            'origem': event.get('origem', ''),
            'delta': event.get('delta', '0')
        }))
