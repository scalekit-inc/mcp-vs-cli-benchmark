import pytest


@pytest.mark.asyncio
async def test_cli_agent_executes_bash_command():
    from benchmark.agents.cli_agent import CliAgent
    agent = CliAgent(model="claude-sonnet-4-20250514")
    result = await agent.execute_tool("bash", {"command": "echo hello"})
    assert "hello" in result


@pytest.mark.asyncio
async def test_cli_agent_returns_stderr_on_failure():
    from benchmark.agents.cli_agent import CliAgent
    agent = CliAgent(model="claude-sonnet-4-20250514")
    result = await agent.execute_tool("bash", {"command": "ls /nonexistent_dir_xyz_12345"})
    assert len(result) > 0  # Should have error output


@pytest.mark.asyncio
async def test_cli_agent_rejects_non_bash_tool():
    from benchmark.agents.cli_agent import CliAgent
    agent = CliAgent(model="claude-sonnet-4-20250514")
    with pytest.raises(ValueError, match="CLI agent only supports 'bash'"):
        await agent.execute_tool("not_bash", {"command": "echo hi"})


def test_cli_agent_has_bash_tool():
    from benchmark.agents.cli_agent import CliAgent
    agent = CliAgent(model="claude-sonnet-4-20250514")
    assert len(agent.tools) == 1
    assert agent.tools[0]["name"] == "bash"
