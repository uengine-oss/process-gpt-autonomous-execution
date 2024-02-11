from langchain.chat_models import ChatOpenAI
from langchain.prompts import ChatPromptTemplate
from langchain.schema.output_parser import StrOutputParser
from langchain.schema.runnable import RunnablePassthrough

# Importing necessary modules for integration with CrewAI.
from crewai import Crew, Agent, Task
import json


from calculator_tools import CalculatorTools
from search_tools import SearchTools

# Creating a dictionary to map string names to actual functions.
tools_by_name = {
    "SearchTools.search_internet": SearchTools.search_internet,
    "CalculatorTools.calculate": CalculatorTools.calculate,
}

def create_crew_from_json(json_data):
    # Converting JSON string to a Python dictionary
    data = json.loads(json_data)

    # Creating agent and task instances
    agents = []
    tasks = []
    agent_by_name = {}  # Dictionary with agent names as keys and agent objects as values

    for agent_data in data['agents']:

        tools = [tools_by_name[tool_name] for tool_name in agent_data['tools']]

        agent = Agent(
            allow_delegation=True,
            role=agent_data['role'],
            goal=agent_data['goal'],
            backstory=agent_data['backstory'],
            verbose=True,
            tools=tools  # In actual implementation, tools may need to be converted to appropriate objects.
        )
        agents.append(agent)
        agent_by_name[agent_data['name']] = agent  # Mapping agent name to agent object

    for task_data in data['tasks']:
        # Finding the agent assigned to the task. In this example, matching by name.
        assigned_agent = agent_by_name.get(task_data['agent'], None)

        task = Task(
            description=task_data['description'],
            agent=assigned_agent
        )
        tasks.append(task)

    # Creating Crew object
    crew = Crew(agents=agents, tasks=tasks)
    return crew

# Preparing the prompt
prompt_template = """
    You are a tool for creating configurations for an Agent framework called CrewAI.

    To achieve a certain Goal, multiple Agents will collaborate to solve problems. Therefore, divide the necessary expertise areas to solve the problem with at least one Agent if possible.
    It mainly consists of the configuration of Agents and the Tasks each Agent performs. And divide the Tasks so that each Agent can deal with problems in their expertise area by passing work among themselves.
    The definition of tools that each Agent can use is as follows: SearchTools.search_internet, CalculatorTools.calculate
    Since the Tasks will be executed sequentially, they must be defined in order.

    The resulting json will be as follows:
    {{
        "agents":[{{
            "name": "name of the agent (e.g. Financial Analyst)",
            "role": "role of the agent (e.g., The Best Financial Analyst)",
            "goal": "goal of the agent (e.g., Impress all customers with your financial data and market trends analysis)",
            "backstory": "backstory of the agent (e.g., The most seasoned financial analyst with lots of expertise in stock market analysis and investment strategies that is working for a super important customer.)",
            "verbose": "verbosity status (e.g., true)",
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

    Please configure a crew for the following mission: {topic}
    """
prompt = ChatPromptTemplate.from_template(prompt_template)

# Setting up the OpenAI model
model = ChatOpenAI(model="gpt-3.5-turbo")

# Setting up the output parser
output_parser = StrOutputParser()

# Defining a function to execute CrewAI kickoff
def execute_crew_kickoff(crew_config):
    crew = create_crew_from_json(crew_config)
    print("Executing CrewAI kickoff with the following configuration:", crew_config)
    result = crew.kickoff()
    return result

from langchain.schema.runnable import RunnableLambda

# Configuring the chain
chain = (
    RunnablePassthrough()
    | prompt
    | model
    | output_parser
    | execute_crew_kickoff
)

# Executing the chain
# The chain is executed based on the description of the crew configuration provided by the user.

chain.invoke({"topic": "Write a proposal for a sales management system for insurance companies. The proposal needs to be written in Korean, requiring a Korean language expert. It would be beneficial to include the results of the predicted ROI calculations."})


