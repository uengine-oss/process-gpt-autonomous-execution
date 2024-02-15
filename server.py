import asyncio
import websockets
from main import create_chain
from langchain.callbacks import StdOutCallbackHandler
from typing import Dict, Any, Union, Optional
from main import get_config_context_var



# 세션별 체인 실행 상태를 관리하기 위한 딕셔너리
session_chains = {}

async def server(websocket, path):
    # 세션 식별을 위해 websocket 객체를 키로 사용
    session_id = id(websocket)
    print(f"New session: {session_id}")

    async for message in websocket:
        # 세션별 체인 실행 로직
        callback_handler = WebSocketCallbackHandler(websocket)
        chain = create_chain()
        
        config = {
            "callbacks": [callback_handler]
        }

        # 컨텍스트 변수 생성
        var = get_config_context_var()
        var.set(config)


        await chain.ainvoke({"topic": message}, config=config)
        # 체인 실행 결과를 클라이언트에게 전송
        # await websocket.send(f"Chain started for session {session_id} with topic: {message}")

start_server = websockets.serve(server, "localhost", 6789)

asyncio.get_event_loop().run_until_complete(start_server)


class WebSocketCallbackHandler(StdOutCallbackHandler):
    def __init__(self, websocket):
        self.websocket = websocket  # 웹소켓 클라이언트 객체를 직접 저장

    async def send_log(self, message):
        # 저장된 웹소켓 클라이언트 객체를 사용하여 로그 메시지를 전송
        await self.websocket.send(message)

    async def on_chain_start(self, serialized: Dict[str, Any], inputs: Dict[str, Any], **kwargs: Any) -> Any:
        await self.send_log(f"Chain started with inputs: {inputs}")

    async def on_chain_end(self, outputs: Dict[str, Any], **kwargs: Any) -> Any:
        try:
            await self.send_log(f"Chain ended with outputs: {outputs['kwargs']['messages'][0]['kwargs']['content']}")
        except:
            await self.send_log(f"Chain ended with outputs: {outputs}")

    async def on_text(
        self,
        text: str,
        color: Optional[str] = None,
        end: str = "",
        **kwargs: Any,
    ) -> None:
        await self.send_log(f"{text}")

    async def on_chain_error(self, error: Union[Exception, KeyboardInterrupt], **kwargs: Any) -> Any:
        await self.send_log(f"Chain encountered an error: {error}")



asyncio.get_event_loop().run_forever()