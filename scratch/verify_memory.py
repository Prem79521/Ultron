"""
Verification script for ULTRON Memory Engine (UME).
Tests: CRUD, Persistence across restarts, Working Memory promotion, and Core Context/Reflection integration.
"""

import os
import asyncio
from ultron.memory import MemoryManager
from ultron.perception import CognitiveRequest, Modality
from ultron.context import ContextHydrator
from ultron.reflection import ReflectionEngine
from ultron.planner import ExecutionPlan
from ultron.execution import ExecutionResult

# Configuration
TEST_DB = "test_memory.db"

async def test_crud_and_persistence():
    print("--- 1. Testing CRUD & Persistence ---")
    if os.path.exists(TEST_DB):
        os.remove(TEST_DB)

    # Initialize manager
    mgr = MemoryManager(db_path=TEST_DB)

    # Create Preferences
    pref_id = mgr.create_record(
        memory_type="preference",
        title="display_name",
        content="Prem",
        tags=["profile", "settings"],
        importance_score=10
    )
    print(f"Created Preference record. ID: {pref_id}")

    # Read Preference
    pref = mgr.read_record("preference", pref_id)
    assert pref is not None, "Failed to read preference"
    assert pref["content"] == "Prem", "Content mismatch"
    assert pref["access_count"] == 1, "Access count was not incremented"
    print("Read Preference verified successfully.")

    # Update Preference
    success = mgr.update_record("preference", pref_id, {"content": "Prem Stark"})
    assert success, "Failed to update record"
    pref = mgr.read_record("preference", pref_id)
    assert pref["content"] == "Prem Stark", "Updated content mismatch"
    print("Update Preference verified successfully.")

    # Simulate restart by re-instantiating manager
    del mgr
    mgr = MemoryManager(db_path=TEST_DB)
    pref = mgr.read_record("preference", pref_id)
    assert pref is not None, "Record did not survive restart persistence!"
    assert pref["content"] == "Prem Stark", "Persistence mismatch"
    print("Persistence across restart verified successfully.")

    # Cleanup DB at the end
    del mgr
    if os.path.exists(TEST_DB):
        os.remove(TEST_DB)
    print("CRUD & Persistence passed.")

async def test_working_memory_and_promotion():
    print("\n--- 2. Testing Working Memory & Promotion ---")
    mgr = MemoryManager(db_path=TEST_DB)

    # Create Working entry
    work_id = mgr.create_record(
        memory_type="working",
        title="temp_compile_status",
        content="building project module successfully",
        tags=["compilation", "task_state"],
        importance_score=7,
        related_project="ultron-platform"
    )
    print(f"Created Working Memory entry. ID: {work_id}")

    # Verify exists
    rec = mgr.read_record("working", work_id)
    assert rec is not None, "Failed to read working memory record"
    assert rec["content"] == "building project module successfully"

    # Promote to Project Memory
    promoted_id = mgr.promote_working_entry(work_id, "project", title="compile_history_success")
    print(f"Promoted Working Memory entry to Project Store. New ID: {promoted_id}")

    # Verify Working Memory entry is deleted
    assert mgr.read_record("working", work_id) is None, "Working entry was not deleted after promotion"
    print("Verified Working entry deleted after promotion.")

    # Verify Project Memory entry exists
    promoted = mgr.read_record("project", promoted_id)
    assert promoted is not None, "Promoted entry not found in Project Memory"
    assert promoted["title"] == "compile_history_success"
    assert promoted["content"] == "building project module successfully"
    print("Verified Project entry created after promotion.")

    # Test working memory clear
    dummy_id = mgr.create_record("working", "dummy", "test contents")
    assert mgr.read_record("working", dummy_id) is not None
    mgr._stores["working"].clear()
    assert mgr.read_record("working", dummy_id) is None, "Working memory clear failed"
    print("Working Memory clear verified successfully.")

    del mgr
    if os.path.exists(TEST_DB):
        os.remove(TEST_DB)
    print("Working Memory & Promotion passed.")

async def test_core_integration():
    print("\n--- 3. Testing Cognitive Core Integration ---")
    mgr = MemoryManager(db_path=TEST_DB)

    # Hydrate preferences
    mgr.create_record("preference", "display_name", "Prem Kumar")
    mgr.create_record("preference", "theme", "dark")

    # Hydrate project
    proj_id = mgr.create_record(
        memory_type="project",
        title="active_project",
        content="building ultron memory subsystem",
        tags=["python", "database"],
        importance_score=8
    )

    # 1. Test Context Hydrator
    hydrator = ContextHydrator(core_system=None, memory_manager=mgr)
    req = CognitiveRequest(
        session_id="session_123",
        modality=Modality.TEXT,
        payload=b"Verify memory retrieval strategy",
        metadata={"related_project": proj_id}
    )

    context = await hydrator.hydrate(req)
    assert context.user_name == "Prem Kumar", "Context did not resolve preference name"
    assert context.preferences["theme"] == "dark", "Context did not load configurations"
    assert context.project_metadata["title"] == "active_project", "Context failed to load project state"
    print("Context Hydration Integration verified successfully.")

    # 2. Test Reflection Engine
    reflector = ReflectionEngine(core_system=None, memory_manager=mgr)
    plan = ExecutionPlan("Verify memory retrieval strategy")
    result = ExecutionResult(task_id="task_001", success=True, output="Memory CRUD passes verification checks.")

    # Mock working memory content to be cleared
    mgr.create_record("working", "temp_task", "working value")
    assert len(mgr.list_records("working")) > 0

    response = await reflector.evaluate_results("session_123", plan, [result])
    assert response.text_content == "Memory CRUD passes verification checks."

    # Verify conversation history was created (Selective Persistence Policy is met)
    conv_records = mgr.list_records("conversation")
    assert len(conv_records) == 1, "Failed to persist conversation interaction"
    assert "Memory CRUD passes" in conv_records[0]["content"]
    print("Reflection Persistence verified successfully.")

    # Verify Working Memory was cleared
    assert len(mgr.list_records("working")) == 0, "Working Memory was not flushed after Reflection execution"
    print("Reflection Working Memory reset verified successfully.")

    del mgr
    if os.path.exists(TEST_DB):
        os.remove(TEST_DB)
    print("Cognitive Core Integration passed.")

async def main():
    try:
        await test_crud_and_persistence()
        await test_working_memory_and_promotion()
        await test_core_integration()
        print("\n=== ALL UME MEMORY VERIFICATIONS PASSED ===")
    except AssertionError as e:
        print(f"\nVerification FAILED: {e}")
        import sys
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
