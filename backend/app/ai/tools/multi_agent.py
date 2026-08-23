import uuid
import json
import logging
from typing import List, Dict, Any
from concurrent.futures import ThreadPoolExecutor, as_completed
from app.ai.tools import tool
from app.ai.llm_client import execute_with_fallback

logger = logging.getLogger(__name__)

# In-memory stateless storage for teams
# In production, you might use Redis or a Database, but since teams are ephemeral per chat session, dict is fine.
# We keep track of teams by team_id
_TEAMS: Dict[str, List[Dict[str, str]]] = {}

@tool(
    name="TeamCreate",
    description="Create a dynamic team of specialized AI agents to analyze a problem from multiple perspectives.",
    parameters={
        "type": "object",
        "properties": {
            "agents": {
                "type": "array",
                "description": "List of agents to create. Max 5 agents.",
                "items": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string", "description": "Name of the agent (e.g. 'Macro Economist')"},
                        "persona": {"type": "string", "description": "Detailed instructions on how this agent should think and analyze."}
                    },
                    "required": ["name", "persona"]
                }
            }
        },
        "required": ["agents"]
    }
)
def create_team(agents: List[Dict[str, str]]) -> Dict[str, Any]:
    """Creates a team of agents and returns a team_id for future task assignment."""
    if not isinstance(agents, list):
        return {"error": "agents must be a list"}
    
    if len(agents) > 5:
        return {"error": "Security Limit Reached: Maximum 5 agents allowed per team to prevent excessive token usage."}
    
    team_id = f"team_{uuid.uuid4().hex[:8]}"
    _TEAMS[team_id] = agents
    
    agent_names = [a.get("name", "Unknown") for a in agents]
    return {
        "status": "success",
        "team_id": team_id,
        "message": f"Team created successfully with {len(agents)} agents: {', '.join(agent_names)}",
        "next_step": "Use TaskCreate to assign a task to this team_id."
    }

def _run_single_agent(agent: Dict[str, str], task: str) -> Dict[str, str]:
    """Helper function to run a single agent via LLM API."""
    name = agent.get("name", "Analyst")
    persona = agent.get("persona", "You are an expert analyst.")
    
    system_prompt = f"You are {name}.\nYour persona/instructions: {persona}\nRespond to the user's task clearly and concisely."
    
    try:
        response = execute_with_fallback(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": task}
            ],
            stream=False
        )
        # response is the parsed string or raw string
        if isinstance(response, str):
            result = response
        else:
            # If execute_with_fallback returned a complex object
            result = str(response)
            
        return {"agent": name, "status": "success", "output": result}
    except Exception as e:
        logger.error(f"Agent {name} failed: {e}")
        return {"agent": name, "status": "error", "output": str(e)}

@tool(
    name="TaskCreate",
    description="Assign a task to a previously created team. The agents will run concurrently and return their combined analysis.",
    parameters={
        "type": "object",
        "properties": {
            "team_id": {
                "type": "string",
                "description": "The ID of the team created via TeamCreate."
            },
            "task": {
                "type": "string",
                "description": "The specific task, context, or data for the team to analyze."
            }
        },
        "required": ["team_id", "task"]
    }
)
def create_task(team_id: str, task: str) -> Dict[str, Any]:
    """Executes a task across all agents in the team concurrently."""
    if team_id not in _TEAMS:
        return {"error": f"Team ID {team_id} not found. Please run TeamCreate first."}
    
    agents = _TEAMS[team_id]
    results = []
    
    # Run agents concurrently to save time
    with ThreadPoolExecutor(max_workers=5) as executor:
        future_to_agent = {executor.submit(_run_single_agent, agent, task): agent for agent in agents}
        
        for future in as_completed(future_to_agent):
            agent = future_to_agent[future]
            name = agent.get("name", "Unknown")
            try:
                res = future.result()
                results.append(res)
            except Exception as e:
                logger.error(f"Agent {name} raised an exception: {e}")
                results.append({"agent": name, "status": "error", "output": str(e)})
                
    return {
        "status": "success",
        "team_id": team_id,
        "task": task,
        "results": results
    }
