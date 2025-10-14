"""
Quick test to verify that prompt composition works correctly.

Run with: python test_prompts.py
"""

from orchestrator.prompts import (
    BUG_TRIAGE_WORLD,
    DOCUMENTATION_SYNC_WORLD,
    ENGINEER_PERSONA,
    HELLO_TICKET_WORLD,
    PLANNER_PERSONA,
    SPRINT_PLANNING_WORLD,
    build_agent_prompt,
)


def test_prompt_composition():
    """Test that we can compose different scenarios with different personas."""
    
    print("=" * 80)
    print("TESTING PROMPT COMPOSITION")
    print("=" * 80)
    
    # Test 1: Hello Ticket scenario
    print("\n[TEST 1] Hello Ticket - Planner")
    print("-" * 80)
    planner_hello = build_agent_prompt(HELLO_TICKET_WORLD, PLANNER_PERSONA)
    assert "Hello Ticket" in planner_hello
    assert "Aanya" in planner_hello
    assert len(planner_hello) > 500
    print(f"✅ Length: {len(planner_hello)} chars")
    print(f"✅ Contains scenario context: {'Smartsheet' in planner_hello}")
    print(f"✅ Contains persona traits: {'warm and incisive' in planner_hello}")
    
    # Test 2: Bug Triage scenario
    print("\n[TEST 2] Bug Triage - Engineer")
    print("-" * 80)
    engineer_bug = build_agent_prompt(BUG_TRIAGE_WORLD, ENGINEER_PERSONA)
    assert "Bug Triage" in engineer_bug
    assert "Arjun" in engineer_bug
    assert len(engineer_bug) > 500
    print(f"✅ Length: {len(engineer_bug)} chars")
    print(f"✅ Contains scenario context: {'bug' in engineer_bug.lower()}")
    print(f"✅ Contains persona traits: {'pragmatic' in engineer_bug}")
    
    # Test 3: Sprint Planning scenario
    print("\n[TEST 3] Sprint Planning - Planner")
    print("-" * 80)
    planner_sprint = build_agent_prompt(SPRINT_PLANNING_WORLD, PLANNER_PERSONA)
    assert "Sprint Planning" in planner_sprint
    assert "Aanya" in planner_sprint
    assert len(planner_sprint) > 500
    print(f"✅ Length: {len(planner_sprint)} chars")
    print(f"✅ Contains scenario context: {'sprint' in planner_sprint.lower()}")
    print(f"✅ Contains persona traits: {'warm and incisive' in planner_sprint}")
    
    # Test 4: Documentation Sync scenario
    print("\n[TEST 4] Documentation Sync - Engineer")
    print("-" * 80)
    engineer_doc = build_agent_prompt(DOCUMENTATION_SYNC_WORLD, ENGINEER_PERSONA)
    assert "Documentation Sync" in engineer_doc
    assert "Arjun" in engineer_doc
    assert len(engineer_doc) > 500
    print(f"✅ Length: {len(engineer_doc)} chars")
    print(f"✅ Contains scenario context: {'documentation' in engineer_doc.lower()}")
    print(f"✅ Contains persona traits: {'pragmatic' in engineer_doc}")
    
    # Test 5: Verify persona reuse
    print("\n[TEST 5] Persona Reuse Verification")
    print("-" * 80)
    # Same persona, different scenarios should keep persona consistent
    planner_scenarios = [
        build_agent_prompt(HELLO_TICKET_WORLD, PLANNER_PERSONA),
        build_agent_prompt(BUG_TRIAGE_WORLD, PLANNER_PERSONA),
        build_agent_prompt(SPRINT_PLANNING_WORLD, PLANNER_PERSONA),
    ]
    
    # All should contain Aanya's personality traits
    for prompt in planner_scenarios:
        assert "Aanya" in prompt
        assert "warm and incisive" in prompt
        assert "planner" in prompt.lower()
    
    print("✅ Planner persona consistent across all scenarios")
    
    engineer_scenarios = [
        build_agent_prompt(HELLO_TICKET_WORLD, ENGINEER_PERSONA),
        build_agent_prompt(BUG_TRIAGE_WORLD, ENGINEER_PERSONA),
        build_agent_prompt(DOCUMENTATION_SYNC_WORLD, ENGINEER_PERSONA),
    ]
    
    # All should contain Arjun's personality traits
    for prompt in engineer_scenarios:
        assert "Arjun" in prompt
        assert "pragmatic" in prompt
        assert "engineer" in prompt.lower()
    
    print("✅ Engineer persona consistent across all scenarios")
    
    # Test 6: Verify scenarios are different
    print("\n[TEST 6] Scenario Differentiation")
    print("-" * 80)
    # Same persona with different scenarios should have different objectives
    assert "Hello Ticket" in planner_scenarios[0]
    assert "Bug Triage" in planner_scenarios[1]
    assert "Sprint Planning" in planner_scenarios[2]
    
    # Each should have unique success criteria
    assert planner_scenarios[0] != planner_scenarios[1]
    assert planner_scenarios[1] != planner_scenarios[2]
    assert planner_scenarios[0] != planner_scenarios[2]
    
    print("✅ Each scenario produces unique composed prompts")
    
    print("\n" + "=" * 80)
    print("ALL TESTS PASSED ✅")
    print("=" * 80)
    print("\nThe prompt composition system is working correctly!")
    print("Agent personas can be reused across different scenarios.")


def show_example_output():
    """Show an example of what a composed prompt looks like."""
    print("\n" + "=" * 80)
    print("EXAMPLE: Composed Prompt for Planner in Hello Ticket Scenario")
    print("=" * 80 + "\n")
    
    composed = build_agent_prompt(HELLO_TICKET_WORLD, PLANNER_PERSONA)
    
    # Show first 800 chars
    print(composed[:800])
    print("\n[... truncated for brevity ...]\n")
    print(f"Total length: {len(composed)} characters")
    print(f"Estimated tokens: ~{len(composed) // 4}")


if __name__ == "__main__":
    test_prompt_composition()
    show_example_output()

