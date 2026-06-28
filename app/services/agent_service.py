import os
import uuid
import json
import asyncio
from datetime import datetime, timezone
from typing import Optional
from dotenv import load_dotenv
from google import genai
from google.genai import types
from app.models.session import ConfirmationEvent, SessionResponse

load_dotenv()

_client: Optional[genai.Client] = None


def get_genai_client() -> genai.Client:
    """Gemini 클라이언트 싱글턴을 반환한다."""
    global _client
    if _client is None:
        _client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
    return _client


# 세션 상태를 메모리에 저장한다 (세션ID → SessionResponse)
_sessions: dict[str, SessionResponse] = {}
# 세션별 확인 요청 이벤트 큐
_event_queues: dict[str, asyncio.Queue] = {}
# 세션별 운영자 응답 Future
_confirm_futures: dict[str, asyncio.Future] = {}


def _build_tool_declarations(allowed_tools: list[str]) -> list[types.Tool]:
    """허용 툴 + request_confirmation 툴을 Gemini Tool 형식으로 반환한다."""
    tool_descriptions = {
        "read_file": "파일 내용을 읽는다.",
        "write_file": "파일을 생성하거나 수정한다.",
        "list_files": "디렉토리의 파일 목록을 나열한다.",
        "delete_file": "파일을 삭제한다.",
        "web_search": "웹에서 정보를 검색한다.",
        "fetch_url": "URL의 내용을 가져온다.",
        "execute_code": "코드를 실행하고 결과를 반환한다.",
        "query_database": "데이터베이스에 쿼리를 실행한다.",
        "update_database": "데이터베이스 레코드를 수정한다.",
        "call_api": "외부 API를 호출한다.",
    }

    declarations = []
    for tool_id in allowed_tools:
        if tool_id in tool_descriptions:
            declarations.append(
                types.FunctionDeclaration(
                    name=tool_id,
                    description=tool_descriptions[tool_id],
                    parameters=types.Schema(
                        type=types.Type.OBJECT,
                        properties={
                            "input": types.Schema(type=types.Type.STRING, description="툴 입력값")
                        },
                    ),
                )
            )

    # 경계 초과 시 운영자 확인 요청 툴
    declarations.append(
        types.FunctionDeclaration(
            name="request_confirmation",
            description="허용되지 않은 작업을 수행하기 전에 운영자에게 확인을 요청한다.",
            parameters=types.Schema(
                type=types.Type.OBJECT,
                properties={
                    "tool_name": types.Schema(type=types.Type.STRING, description="실행하려는 툴 이름"),
                    "tool_args": types.Schema(type=types.Type.STRING, description="툴에 전달하려는 인자 (JSON 문자열)"),
                    "reason": types.Schema(type=types.Type.STRING, description="확인이 필요한 이유"),
                },
                required=["tool_name", "tool_args", "reason"],
            ),
        )
    )

    return [types.Tool(function_declarations=declarations)]


def _execute_tool(tool_name: str, tool_input: str) -> str:
    """허용된 툴을 시뮬레이션 실행하고 결과를 반환한다."""
    simulated = {
        "read_file": f"[시뮬레이션] '{tool_input}' 파일 내용을 읽었다.",
        "write_file": f"[시뮬레이션] '{tool_input}' 파일에 내용을 저장했다.",
        "list_files": "[시뮬레이션] 파일 목록: file1.txt, file2.txt, file3.txt",
        "delete_file": f"[시뮬레이션] '{tool_input}' 파일을 삭제했다.",
        "web_search": f"[시뮬레이션] '{tool_input}' 검색 결과: 관련 정보를 찾았다.",
        "fetch_url": f"[시뮬레이션] '{tool_input}' URL의 내용을 가져왔다.",
        "execute_code": f"[시뮬레이션] 코드를 실행했다. 출력: Hello from {tool_input}",
        "query_database": f"[시뮬레이션] '{tool_input}' 쿼리 결과: 3개의 레코드를 찾았다.",
        "update_database": f"[시뮬레이션] '{tool_input}' 쿼리로 레코드를 수정했다.",
        "call_api": f"[시뮬레이션] '{tool_input}' API 호출 완료. 응답: 200 OK",
    }
    return simulated.get(tool_name, f"[시뮬레이션] {tool_name} 실행 완료.")


def init_session(session_id: str, contract_id: str) -> SessionResponse:
    """세션과 이벤트 큐를 사전 초기화하고 SessionResponse를 반환한다."""
    session = SessionResponse(
        session_id=session_id,
        contract_id=contract_id,
        status="running",
        created_at=datetime.now(timezone.utc),
    )
    _sessions[session_id] = session
    _event_queues[session_id] = asyncio.Queue()
    return session


async def run_agent(
    session_id: str,
    contract_id: str,
    user_message: str,
    allowed_tools: list[str],
) -> None:
    """Gemini 에이전트를 실행하고 세션 상태를 업데이트한다."""
    loop = asyncio.get_event_loop()
    queue = _event_queues[session_id]

    try:
        client = get_genai_client()
        tools = _build_tool_declarations(allowed_tools)

        system_prompt = (
            f"당신은 위임 계약에 따라 동작하는 AI 에이전트다. "
            f"허용된 툴: {', '.join(allowed_tools)}. "
            f"허용되지 않은 작업이 필요하면 반드시 request_confirmation을 호출해야 한다."
        )

        contents: list = [user_message]

        while True:
            response = await client.aio.models.generate_content(
                model="gemini-2.5-flash",
                contents=contents,
                config=types.GenerateContentConfig(
                    system_instruction=system_prompt,
                    tools=tools,
                ),
            )

            candidate = response.candidates[0]
            contents.append(candidate.content)

            tool_responses = []
            terminal = True

            for part in candidate.content.parts:
                if not part.function_call:
                    continue

                terminal = False
                fn = part.function_call

                if fn.name == "request_confirmation":
                    raw_tool_args = fn.args.get("tool_args", {})
                    if isinstance(raw_tool_args, str):
                        raw_tool_args = json.loads(raw_tool_args) if raw_tool_args else {}
                    if not isinstance(raw_tool_args, dict):
                        raw_tool_args = {}

                    event = ConfirmationEvent(
                        session_id=session_id,
                        tool_name=fn.args.get("tool_name", "unknown"),
                        tool_args=raw_tool_args,
                        reason=fn.args.get("reason", ""),
                    )
                    _sessions[session_id].status = "waiting_confirmation"
                    await queue.put(event)

                    future: asyncio.Future = loop.create_future()
                    _confirm_futures[session_id] = future
                    try:
                        approved = await future
                    finally:
                        _confirm_futures.pop(session_id, None)

                    if not approved:
                        _sessions[session_id].status = "rejected"
                        _sessions[session_id].result = "운영자가 거절했다. 작업을 중단한다."
                        await queue.put(None)
                        return

                    tool_responses.append(
                        types.Part.from_function_response(
                            name=fn.name,
                            response={"result": "운영자가 승인했다. 작업을 진행한다."},
                        )
                    )
                else:
                    tool_input = fn.args.get("input", "")
                    result = _execute_tool(fn.name, tool_input)
                    tool_responses.append(
                        types.Part.from_function_response(
                            name=fn.name,
                            response={"result": result},
                        )
                    )

            if terminal:
                text_parts = [p.text for p in candidate.content.parts if hasattr(p, "text") and p.text]
                _sessions[session_id].status = "completed"
                _sessions[session_id].result = "\n".join(text_parts) if text_parts else "완료됐다."
                await queue.put(None)
                return

            contents.append(types.Content(role="user", parts=tool_responses))

    except Exception as e:
        _sessions[session_id].status = "failed"
        _sessions[session_id].result = f"오류가 발생했다: {str(e)}"
        await queue.put(None)


def create_session_id() -> str:
    """새 세션 ID를 생성한다."""
    return str(uuid.uuid4())


def get_session(session_id: str) -> Optional[SessionResponse]:
    """세션 상태를 반환한다."""
    return _sessions.get(session_id)


def get_event_queue(session_id: str) -> Optional[asyncio.Queue]:
    """세션의 이벤트 큐를 반환한다."""
    return _event_queues.get(session_id)


def resolve_confirmation(session_id: str, approved: bool) -> bool:
    """운영자 확인 응답을 처리한다. 세션이 없으면 False를 반환한다."""
    future = _confirm_futures.get(session_id)
    if future and not future.done():
        future.get_loop().call_soon_threadsafe(future.set_result, approved)
        return True
    return False
