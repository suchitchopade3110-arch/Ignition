import os
import sys
import uuid
import asyncio

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.main import app
from app.services.stream_manager import stream_manager
from fastapi.testclient import TestClient

def test_sse():
    review_id = str(uuid.uuid4())
    
    # Pre-populate the queue with a test event exactly as run_review_stream_task does
    async def publish_events():
        await stream_manager.publish(
            review_id,
            {
                "type": "review.started",
                "reviewId": review_id,
                "status": "running",
            }
        )
        await asyncio.sleep(0.1)
        await stream_manager.publish(
            review_id,
            {
                "type": "review.completed",
                "reviewId": review_id,
                "status": "completed",
            }
        )
    
    # Run publish_events in the event loop that TestClient uses
    # TestClient runs synchronously but wraps async code. We can just use it.
    client = TestClient(app)
    
    # Start a background task to publish events? Actually TestClient blocks, so we need threading or just call publish before, but stream_manager queue is created dynamically.
    # We can manually register the queue, publish, and then call the endpoint.
    queue = stream_manager.register(review_id)
    queue.put_nowait({
        "type": "review.started",
        "reviewId": review_id,
        "status": "running",
    })
    queue.put_nowait({
        "type": "review.completed",
        "reviewId": review_id,
        "status": "completed",
    })

    with client.stream("GET", f"/api/reviews/{review_id}/stream") as response:
        lines = []
        for line in response.iter_lines():
            if line:
                lines.append(line)
                print(line)
        
    out_path = os.path.join(os.path.dirname(__file__), "sse_test_results.txt")
    with open(out_path, "w") as f:
        f.write("\n".join(lines))
    print(f"Saved to {out_path}")

if __name__ == "__main__":
    test_sse()
