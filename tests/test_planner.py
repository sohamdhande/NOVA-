import asyncio
import sys
sys.path.insert(
    0, '/Users/sohamdhande/Docs_Local/NOVA'
)

from core.task_planner import task_planner

async def test_planner():
    print("\n=== N.O.V.A Task Planner Test ===\n")
    
    # Test 1: Simple plan generation
    print("Test 1: Planning simple task...")
    task = await task_planner.plan(
        "open chrome and go to google.com"
    )
    print(f"  ✅ Task ID: {task.id}")
    print(f"  ✅ Title: {task.title}")
    print(f"  ✅ Steps planned: {len(task.steps)}")
    for i, step in enumerate(task.steps):
        print(f"     {i+1}. [{step.action_type}] "
              f"{step.description}")
    
    # Test 2: Complex plan
    print("\nTest 2: Planning complex task...")
    task2 = await task_planner.plan(
        "check system health and save a report "
        "to my desktop"
    )
    print(f"  ✅ Steps: {len(task2.steps)}")
    for i, step in enumerate(task2.steps):
        print(f"     {i+1}. [{step.action_type}] "
              f"{step.description}")
    
    # Test 3: Execute safe task (screenshot only)
    print("\nTest 3: Executing safe task...")
    task3 = await task_planner.plan(
        "take a screenshot and save it"
    )
    result = await task_planner.execute(task3)
    print(f"  ✅ Status: {result.status.value}")
    print(f"  ✅ Result: {result.result_summary}")
    
    print("\n=== Planner Test Complete ===\n")

if __name__ == "__main__":
    asyncio.run(test_planner())
