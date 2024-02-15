from typing import Any, Dict, Optional
from uuid import UUID
from langchain.chat_models import ChatOpenAI
from langchain.prompts import ChatPromptTemplate
from langchain.schema.output_parser import StrOutputParser
from langchain.output_parsers.json import SimpleJsonOutputParser  # JsonOutputParser 임포트
from langchain.schema.runnable import RunnablePassthrough

# Importing necessary modules for integration with CrewAI.
from crewai import Crew, Agent, Task
import json

from langchain_core.agents import AgentAction, AgentFinish


from calculator_tools import CalculatorTools
from search_tools import SearchTools

from contextvars import ContextVar

var = ContextVar('config')
def get_config_context_var():
    return var

# Creating a dictionary to map string names to actual functions.
tools_by_name = {
    "SearchTools.search_internet": SearchTools.search_internet,
    "SearchTools.search_internal_documents": SearchTools.search_internal_documents,
    "CalculatorTools.calculate": CalculatorTools.calculate,
}


from crewai.agents.tools_handler import ToolsHandler
from crewai.agents.cache.cache_handler import CacheHandler

class CustomToolsHandler(ToolsHandler):
    handler: Any = None
    agent: Agent = None

    def __init__(self, handler: Any, cache_handler: CacheHandler, agent: Agent, **kwargs: Any):
        super().__init__(cache=cache_handler, **kwargs)        
        self.handler = handler
        self.agent = agent

    async def on_agent_finish(self, finish: AgentFinish, *, run_id: UUID, parent_run_id: UUID | None = None, **kwargs: Any) -> Any:
        return super().on_agent_finish(finish, run_id=run_id, parent_run_id=parent_run_id, **kwargs)
    
    async def on_agent_action(self, action: AgentAction, *, run_id: UUID, parent_run_id: UUID | None = None, **kwargs: Any) -> Any:
        await self.handler['callbacks'][0].send_log(f"Agent: {self.agent.role}\nTool: {action.messages}")
        return super().on_agent_action(action, run_id=run_id, parent_run_id=parent_run_id, **kwargs)
    
    async def on_tool_start(self, serialized: Dict[str, Any], input_str: str, **kwargs: Any) -> Any:
        super().on_tool_start(serialized, input_str, **kwargs)

        tool_name = serialized.get("name")
    
        await self.handler['callbacks'][0].send_log(f"Agent: {self.agent.role}\nTool: {tool_name}\nInput: {input_str}")

    async def on_tool_end(self, output: str, **kwargs: Any) -> Any:
        super().on_tool_end(output, **kwargs)
        await self.handler['callbacks'][0].send_log(f"Tool Output: {output}")

class CustomAgent(Agent):

    handler: Any = None

    def __init__(self, handler: Any, **kwargs):
        super().__init__(**kwargs)
        self.handler = handler

    def set_cache_handler(self, cache_handler) -> None:
        super().set_cache_handler(cache_handler)
   
        self.tools_handler = CustomToolsHandler(handler=self.handler, cache_handler=cache_handler, agent=self)

def create_crew_from_json(json_data):
    # Converting JSON string to a Python dictionary
    data = json.loads(json_data)

    # Creating agent and task instances
    agents = []
    tasks = []
    agent_by_name = {}  # Dictionary with agent names as keys and agent objects as values

    for agent_data in data['agents']:

        tools = [tools_by_name[tool_name] for tool_name in agent_data['tools']]

        custom_handler = None
        if var:
            try:
                custom_handler = var.get()
                
                #custom_handler = CustomToolsHandler(handler=websocketHandler, agent=agent)

            except Exception as e:
                print(f"Failed to get websocketHandler: {str(e)}")
                custom_handler = None

        #llm = ChatOpenAI(model="gpt-3.5-turbo-16k", callbacks=[custom_handler])

        agent = CustomAgent(
            
            handler=custom_handler,
            allow_delegation=True,
            role=agent_data['role'],
            goal=agent_data['goal'],
            backstory=agent_data['backstory'],
            verbose=True,
            tools=tools,  # In actual implementation, tools may need to be converted to appropriate objects.
            
            #llm=llm   # causes token limits occasionally 
        )

        #agent.custom_handler=custom_handler



        agents.append(agent)
        agent_by_name[agent_data['name']] = agent  # Mapping agent name to agent object

    for task_data in data['tasks']:
        # Finding the agent assigned to the task. In this example, matching by name.
        assigned_agent = agent_by_name.get(task_data['agent'], None)

        task = Task(
            description=task_data['description']+ ". The result MUST be written in Korean language.",
            agent=assigned_agent
        )
        tasks.append(task)

    # Creating Crew object
    crew = Crew(agents=agents, tasks=tasks)
    return crew

# Preparing the prompt
prompt_template = """
    You are a tool for creating configurations for an Agent framework called CrewAI.

    To achieve a certain Goal, multiple Agents will collaborate to solve problems. Therefore, divide the necessary expertise areas to solve the problem with at least two or more Agent if possible.
    It mainly consists of the configuration of Agents and the Tasks each Agent performs. And divide the Tasks so that each Agent can deal with problems in their expertise area by passing work among themselves.
    The definition of tools that each Agent can use is as follows: SearchTools.search_internet, SearchTools.search_internal_documents, CalculatorTools.calculate
    Since the Tasks will be executed sequentially, they must be defined in order.
    the result MUST be written in Korean language.


    The resulting json will be as follows (Please use VALID JSON with double-quoted for key and value):
    ```
    {{
        "agents":[{{
            "name": "name of the agent (e.g. Financial Analyst)",
            "role": "role of the agent (e.g., The Best Financial Analyst)",
            "goal": "goal of the agent (e.g., Impress all customers with your financial data and market trends analysis)",
            "backstory": "backstory of the agent (e.g., The most seasoned financial analyst with lots of expertise in stock market analysis and investment strategies that is working for a super important customer.)",
            "tools": [
                "list of tools the agent uses (e.g., SearchTools.search_internet, CalculatorTools.calculate)"
            ]
        }}],
        "tasks":[
            {{
            "description": "Task description (e.g., Collect and summarize recent news articles, press releases, and market analyses related to the stock and its industry. Pay special attention to any significant events, market sentiments, and analysts' opinions. Also include upcoming events like earnings and others. Your final answer MUST be a report that includes a comprehensive summary of the latest news, any notable shifts in market sentiment, and potential impacts on the stock. Also make sure to return the stock ticker. Make sure to use the most recent data as possible. Selected company by the customer: {{company}})",
            "agent": "agent assigned to the task (e.g., agent)"
            }}
        ]
    }}
    ```

    Please configure a crew for the following mission: {topic}
    """
prompt = ChatPromptTemplate.from_template(prompt_template)

# Setting up the OpenAI model
model = ChatOpenAI(model="gpt-3.5-turbo", callbacks=[])


# Replace the StrOutputParser instance with JSONOutputParser
#output_parser = SimpleJsonOutputParser()
# Setting up the output parser
output_parser = StrOutputParser()

# Defining a function to execute CrewAI kickoff
def execute_crew_kickoff(crew_config):
    crew = create_crew_from_json(crew_config)
    #crew.language = "ko"
    print("Executing CrewAI kickoff with the following configuration:\n", json.dumps(crew_config, indent=4))


    
    if var:
        try:
            crew.config = var.get()
        except:
            crew.config = None

    result = crew.kickoff()
    return result

from langchain.schema.runnable import RunnableLambda


def create_chain():
# Configuring the chain
    return (
        RunnablePassthrough()
        | prompt
        | model
        | output_parser
        | execute_crew_kickoff
    )

# Executing the chain
# The chain is executed based on the description of the crew configuration provided by the user.

#chain.invoke({"topic": "Write a proposal for a sales management system for insurance companies. The proposal needs to be written in Korean, requiring a Korean language expert. It would be beneficial to include the results of the predicted ROI calculations."})


if __name__ == "__main__":
    chain = create_chain()
    chain.invoke({"topic": "클라우드 네이티브 앱을 정부에 적용할 제안서"})
#    chain.invoke({"topic": "오픈 AI 에 대한 투자 의견서. 내부 문서도 참고하고 ."})



