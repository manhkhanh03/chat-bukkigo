import asyncio
from types import SimpleNamespace

from chat_bukkigo.config import load_settings
from chat_bukkigo.main import encode_sse
from chat_bukkigo.schemas import ChatRequest
from chat_bukkigo.service import ChatService


class FakeStream:
    def __init__(self) -> None:
        response = SimpleNamespace(id="resp_test")
        self.events = [
            SimpleNamespace(type="response.created", response=response),
            SimpleNamespace(type="response.output_text.delta", delta="Xin "),
            SimpleNamespace(type="response.output_text.delta", delta="chào"),
            SimpleNamespace(type="response.completed", response=response),
        ]
        self.closed = False

    def __aiter__(self):
        return self._iterate()

    async def _iterate(self):
        for event in self.events:
            yield event

    async def close(self) -> None:
        self.closed = True


class FakeResponses:
    def __init__(self, stream: FakeStream) -> None:
        self.stream = stream
        self.kwargs = None

    async def create(self, **kwargs):
        self.kwargs = kwargs
        return self.stream


class FakeClient:
    def __init__(self, stream: FakeStream) -> None:
        self.responses = FakeResponses(stream)


def test_encode_sse_preserves_vietnamese_and_event_boundary() -> None:
    encoded = encode_sse("delta", {"text": "thanh lịch"})

    assert encoded == 'event: delta\ndata: {"text":"thanh lịch"}\n\n'


def test_service_streams_deltas_and_latency_metadata() -> None:
    async def collect_events():
        stream = FakeStream()
        client = FakeClient(stream)
        service = ChatService(load_settings())
        service.client = client
        events = [
            event async for event in service.stream_chat(ChatRequest(message="Nail Tết"))
        ]
        return stream, client, events

    stream, client, events = asyncio.run(collect_events())

    assert [event.event for event in events] == ["status", "meta", "delta", "delta", "done"]
    assert "".join(event.data["text"] for event in events if event.event == "delta") == "Xin chào"
    assert events[-1].data["response_id"] == "resp_test"
    assert len(events[1].data["trace_id"]) == 12
    assert events[-1].data["trace_id"] == events[1].data["trace_id"]
    assert isinstance(events[-1].data["total_ms"], int)
    assert isinstance(events[-1].data["time_to_first_token_ms"], int)
    assert client.responses.kwargs["stream"] is True
    assert stream.closed is True
