"""
Système d'agents IA autonomes avec capacité d'utiliser des outils.
Utilise le pattern ReAct (Reasoning + Acting) de LangChain.
"""

from typing import Dict, List, Any, Optional
from langchain.agents import AgentExecutor, create_react_agent
from langchain_openai import ChatOpenAI
from langchain.tools import Tool
from langchain.prompts import PromptTemplate
import structlog
import time

from app.core.tools import (
    CalculatorTool, 
    WebSearchTool, 
    DateTimeTool, 
    DocumentQueryTool,
    TextAnalysisTool
)

logger = structlog.get_logger(__name__)

# Template de prompt pour l'agent ReAct
REACT_PROMPT_TEMPLATE = """Tu es un assistant IA intelligent qui peut utiliser des outils pour répondre aux questions.

Tu as accès aux outils suivants :

{tools}

Utilise le format suivant pour répondre :

Question: la question d'entrée que tu dois répondre
Thought: tu dois toujours réfléchir à ce que tu dois faire
Action: l'action à entreprendre, doit être l'un de [{tool_names}]
Action Input: l'entrée de l'action
Observation: le résultat de l'action
... (ce Thought/Action/Action Input/Observation peut se répéter N fois)
Thought: Je connais maintenant la réponse finale
Final Answer: la réponse finale à la question originale

IMPORTANT:
- Utilise les outils à ta disposition quand c'est nécessaire
- Pour les calculs mathématiques, utilise toujours l'outil calculator
- Pour les informations récentes ou actuelles, utilise web_search
- Pour interroger les documents uploadés, utilise document_query
- Pour la date/heure actuelle, utilise current_datetime
- Raisonne étape par étape avant de répondre
- Réponds toujours en français

Commence !

Question: {input}
Thought: {agent_scratchpad}
"""


class RAGAgent:
    """Agent IA intelligent avec accès à des outils."""
    
    def __init__(self, rag_pipeline=None, model_name: str = "gpt-3.5-turbo", temperature: float = 0):
        """
        Initialise l'agent avec les outils disponibles.
        
        Args:
            rag_pipeline: Pipeline RAG pour l'outil document_query
            model_name: Nom du modèle LLM à utiliser
            temperature: Température pour la génération
        """
        self.rag_pipeline = rag_pipeline
        self.model_name = model_name
        self.llm = ChatOpenAI(model_name=model_name, temperature=temperature)
        
        # Initialiser les outils
        self.tools = self._setup_tools()
        
        # Créer le prompt
        self.prompt = PromptTemplate(
            input_variables=["input", "agent_scratchpad", "tools", "tool_names"],
            template=REACT_PROMPT_TEMPLATE
        )
        
        # Créer l'agent et l'executor
        self.agent = create_react_agent(
            llm=self.llm,
            tools=self.tools,
            prompt=self.prompt
        )
        
        self.agent_executor = AgentExecutor(
            agent=self.agent,
            tools=self.tools,
            verbose=True,
            max_iterations=5,
            handle_parsing_errors=True,
            return_intermediate_steps=True
        )
        
        logger.info("RAG Agent initialized", 
                   model=model_name, 
                   tools_count=len(self.tools))
    
    def _setup_tools(self) -> List[Tool]:
        """Configure tous les outils disponibles pour l'agent."""
        tools = []
        
        # Outil Calculator
        calc_tool = CalculatorTool()
        tools.append(Tool(
            name=calc_tool.name,
            func=calc_tool.run,
            description=calc_tool.description
        ))
        
        # Outil DateTime
        datetime_tool = DateTimeTool()
        tools.append(Tool(
            name=datetime_tool.name,
            func=datetime_tool.run,
            description=datetime_tool.description
        ))
        
        # Outil Text Analysis
        text_tool = TextAnalysisTool()
        tools.append(Tool(
            name=text_tool.name,
            func=text_tool.run,
            description=text_tool.description
        ))
        
        # Outil Web Search (avec gestion d'erreur améliorée)
        try:
            search_tool = WebSearchTool()
            tools.append(Tool(
                name=search_tool.name,
                func=search_tool.run,
                description=search_tool.description
            ))
        except Exception as e:
            logger.warning("Web search tool not available", error=str(e))
        
        # Outil Document Query (si RAG pipeline disponible)
        if self.rag_pipeline:
            try:
                doc_tool = DocumentQueryTool(self.rag_pipeline)
                tools.append(Tool(
                    name=doc_tool.name,
                    func=doc_tool.run,
                    description=doc_tool.description
                ))
            except Exception as e:
                logger.warning("Document query tool not available", error=str(e))
        
        return tools
    
    def run(self, question: str, session_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Exécute l'agent sur une question.
        
        Args:
            question: La question à traiter
            session_id: ID de session (optionnel)
            
        Returns:
            Dictionnaire avec la réponse et les étapes intermédiaires
        """
        start_time = time.time()
        
        logger.info("Agent execution started", 
                   question=question[:100],
                   session_id=session_id)
        
        try:
            # Exécuter l'agent
            result = self.agent_executor.invoke({"input": question})
            
            response_time = time.time() - start_time
            
            # Extraire les étapes de raisonnement
            intermediate_steps = []
            if result.get("intermediate_steps"):
                for step in result["intermediate_steps"]:
                    action, observation = step
                    intermediate_steps.append({
                        "tool": action.tool,
                        "tool_input": action.tool_input,
                        "observation": str(observation)[:500]  # Limiter la taille
                    })
            
            # Structurer la réponse
            response = {
                "answer": result.get("output", ""),
                "reasoning_steps": intermediate_steps,
                "tools_used": [step["tool"] for step in intermediate_steps],
                "response_time": response_time,
                "session_id": session_id,
                "model_used": self.model_name,
                "agent_type": "ReAct"
            }
            
            logger.info("Agent execution completed",
                       response_time=response_time,
                       tools_used=len(intermediate_steps),
                       session_id=session_id)
            
            return response
            
        except Exception as e:
            logger.error("Agent execution failed",
                        question=question[:100],
                        error=str(e),
                        session_id=session_id)
            
            return {
                "answer": f"Erreur lors de l'exécution de l'agent : {str(e)}",
                "reasoning_steps": [],
                "tools_used": [],
                "response_time": time.time() - start_time,
                "session_id": session_id,
                "error": str(e)
            }
    
    def get_available_tools(self) -> List[Dict[str, str]]:
        """Retourne la liste des outils disponibles."""
        return [
            {
                "name": tool.name,
                "description": tool.description
            }
            for tool in self.tools
        ]


class SimpleAgent:
    """Agent simple sans outils, pour comparaison."""
    
    def __init__(self, model_name: str = "gpt-3.5-turbo"):
        self.llm = ChatOpenAI(model_name=model_name, temperature=0)
        self.model_name = model_name
    
    def run(self, question: str, session_id: Optional[str] = None) -> Dict[str, Any]:
        """Exécute l'agent simple."""
        start_time = time.time()
        
        try:
            response = self.llm.invoke(question)
            
            return {
                "answer": response.content,
                "reasoning_steps": [],
                "tools_used": [],
                "response_time": time.time() - start_time,
                "session_id": session_id,
                "model_used": self.model_name,
                "agent_type": "Simple"
            }
            
        except Exception as e:
            return {
                "answer": f"Erreur : {str(e)}",
                "reasoning_steps": [],
                "tools_used": [],
                "response_time": time.time() - start_time,
                "session_id": session_id,
                "error": str(e)
            }


# Factory pour créer des agents
def create_agent(agent_type: str = "react", rag_pipeline=None, **kwargs) -> Any:
    """
    Factory pour créer différents types d'agents.
    
    Args:
        agent_type: Type d'agent ("react" ou "simple")
        rag_pipeline: Pipeline RAG optionnel
        **kwargs: Arguments supplémentaires
        
    Returns:
        Instance de l'agent
    """
    if agent_type == "react":
        return RAGAgent(rag_pipeline=rag_pipeline, **kwargs)
    elif agent_type == "simple":
        return SimpleAgent(**kwargs)
    else:
        raise ValueError(f"Type d'agent inconnu : {agent_type}")

