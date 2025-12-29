"""
LangGraph workflow for the agent reasoning loop.

Implements the core loop from the spec:
1. Query Decomposition
2. Observation Gathering
3. Pattern Detection
4. Hypothesis Testing
5. Meta-Reasoning
6. Synthesis
"""

import json
from datetime import datetime
from typing import Dict, List, Any
from loguru import logger
from openai import OpenAI

from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

from src.agent.state import AgentState, SubQuestion, Hypothesis
from src.agent.prompts import (
    DECOMPOSE_QUERY_PROMPT,
    GATHER_OBSERVATIONS_PROMPT,
    PATTERN_DETECTION_PROMPT,
    HYPOTHESIS_TESTING_PROMPT,
    META_REASONING_PROMPT,
    SYNTHESIS_PROMPT,
)
from src.tools import RetrievalTools
from src.config import config


class ECUAgent:
    """Emergent Corpus Understanding Agent."""
    
    def __init__(self, engine):
        self.engine = engine
        self.tools = RetrievalTools(engine)
        self.client = OpenAI(api_key=config.OPENAI_API_KEY)
        self.model = config.OPENAI_MODEL
        
        # Build LangGraph workflow
        self.workflow = self._build_workflow()
        
        # Set up checkpointer for persistence
        memory = MemorySaver()
        self.app = self.workflow.compile(
            checkpointer=memory,
            interrupt_before=[],  # Can add human-in-the-loop points
        )
    
    def _build_workflow(self) -> StateGraph:
        """Build the LangGraph workflow."""
        workflow = StateGraph(AgentState)
        
        # Add nodes
        workflow.add_node("decompose", self.decompose_query)
        workflow.add_node("gather", self.gather_observations)
        workflow.add_node("detect_patterns", self.detect_patterns)
        workflow.add_node("test_hypotheses", self.test_hypotheses)
        workflow.add_node("meta_reason", self.meta_reasoning)
        workflow.add_node("synthesize", self.synthesize_answer)
        
        # Set entry point
        workflow.set_entry_point("decompose")
        
        # Add edges
        workflow.add_edge("decompose", "gather")
        workflow.add_edge("gather", "detect_patterns")
        workflow.add_edge("detect_patterns", "test_hypotheses")
        workflow.add_edge("test_hypotheses", "meta_reason")
        
        # Conditional edge: continue or stop?
        workflow.add_conditional_edges(
            "meta_reason",
            self.should_continue,
            {
                "continue": "gather",
                "synthesize": "synthesize",
                "stop": END,
            }
        )
        
        workflow.add_edge("synthesize", END)
        
        return workflow
    
    def _call_llm(self, prompt: str, temperature: float = 0.7) -> Dict:
        """Call LLM and parse JSON response."""
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are an expert reasoning system. Always respond with valid JSON."},
                    {"role": "user", "content": prompt}
                ],
                temperature=temperature,
                response_format={"type": "json_object"}
            )
            
            content = response.choices[0].message.content
            return json.loads(content)
            
        except Exception as e:
            logger.error(f"LLM call error: {e}")
            return {}
    
    # Node implementations
    
    def decompose_query(self, state: AgentState) -> AgentState:
        """Decompose query into sub-questions."""
        logger.info(f"Decomposing query: {state['query']}")
        
        prompt = DECOMPOSE_QUERY_PROMPT.format(query=state['query'])
        result = self._call_llm(prompt)
        
        sub_questions = []
        for i, sq in enumerate(result.get('sub_questions', [])):
            sub_questions.append(SubQuestion(
                id=i,
                text=sq['text'],
                priority=sq['priority'],
                confidence=0.0,
                status='pending'
            ))
        
        state['sub_questions'] = sub_questions
        state['evidence_trail'].append(f"Decomposed query into {len(sub_questions)} sub-questions")
        
        logger.info(f"Created {len(sub_questions)} sub-questions")
        return state
    
    def gather_observations(self, state: AgentState) -> AgentState:
        """Gather observations using tools."""
        logger.info(f"Gathering observations (iteration {state['iterations']})")
        
        prompt = GATHER_OBSERVATIONS_PROMPT.format(
            query=state['query'],
            sub_questions=json.dumps([sq for sq in state['sub_questions']], indent=2),
            hypotheses=json.dumps([h for h in state.get('hypotheses', [])], indent=2),
            num_observations=len(state.get('observations', []))
        )
        
        result = self._call_llm(prompt)
        
        new_observations = []
        
        # Execute tool calls
        for tool_call in result.get('tool_calls', []):
            tool_name = tool_call['tool']
            params = tool_call['parameters']
            reasoning = tool_call.get('reasoning', '')
            
            logger.info(f"Executing tool: {tool_name} with params {params}")
            
            try:
                if tool_name == 'semantic_search':
                    obs = self.tools.semantic_search(**params)
                elif tool_name == 'find_cooccurrences':
                    obs = self.tools.find_cooccurrences(**params)
                elif tool_name == 'temporal_query':
                    obs = self.tools.temporal_query(**params)
                elif tool_name == 'traverse_graph':
                    obs = self.tools.traverse_graph(**params)
                elif tool_name == 'find_contradictions':
                    obs = self.tools.find_contradictions(**params)
                else:
                    obs = []
                
                new_observations.extend(obs)
                state['evidence_trail'].append(f"Tool {tool_name}: {reasoning} -> {len(obs)} observations")
                
            except Exception as e:
                logger.error(f"Tool execution error: {e}")
        
        # Add new observations to state (using annotated add)
        if 'observations' not in state:
            state['observations'] = []
        state['observations'].extend(new_observations)
        
        # Memory pruning: prevent unbounded observation growth
        MAX_OBS = config.MAX_OBSERVATIONS_IN_MEMORY
        if len(state['observations']) > MAX_OBS:
            pruned_count = len(state['observations']) - MAX_OBS
            state['observations'] = state['observations'][-MAX_OBS:]
            state['evidence_trail'].append(f"Pruned {pruned_count} old observations, kept last {MAX_OBS}")
            logger.info(f"Pruned observations: kept {MAX_OBS}, removed {pruned_count}")
        
        logger.info(f"Gathered {len(new_observations)} new observations (total: {len(state['observations'])})")
        return state
    
    def detect_patterns(self, state: AgentState) -> AgentState:
        """Detect patterns in observations."""
        logger.info("Detecting patterns")
        
        # Get recent observations with truncated context to reduce memory/token usage
        all_obs = state.get('observations', [])[-20:]  # Reduced from 50 to 20
        recent_obs = [
            {
                'id': o.get('id', i),
                'doc_id': o.get('doc_id', ''),
                'context': o.get('context', '')[:config.OBSERVATION_CONTEXT_LIMIT],  # Truncate long contexts
                'similarity': o.get('similarity', 0.0)
            }
            for i, o in enumerate(all_obs)
        ]
        
        prompt = PATTERN_DETECTION_PROMPT.format(
            observations=json.dumps(recent_obs, indent=2),
            sub_questions=json.dumps([sq for sq in state['sub_questions']], indent=2)
        )
        
        result = self._call_llm(prompt)
        
        # Create new hypotheses
        hypotheses = state.get('hypotheses', [])
        hypothesis_id = len(hypotheses)
        
        for pattern in result.get('patterns', []):
            hypothesis = Hypothesis(
                id=hypothesis_id,
                claim=pattern['claim'],
                confidence=pattern['confidence'],
                evidence_ids=pattern['evidence_ids'],
                contradicting_ids=[],
                relevant_to_subquestion=pattern['relevant_to_subquestion'],
                impact_on_answer=pattern.get('reasoning', ''),
                tested_at_iteration=state['iterations'],
                num_tests=1
            )
            hypotheses.append(hypothesis)
            hypothesis_id += 1
            
            state['evidence_trail'].append(f"Formed hypothesis: {pattern['claim'][:100]}... (confidence: {pattern['confidence']})")
        
        state['hypotheses'] = hypotheses
        
        # Prune hypotheses if too many
        MAX_HYPOTHESES = config.MAX_HYPOTHESES
        if len(state['hypotheses']) > MAX_HYPOTHESES:
            # Keep highest confidence hypotheses
            state['hypotheses'] = sorted(
                state['hypotheses'], 
                key=lambda h: h.get('confidence', 0), 
                reverse=True
            )[:MAX_HYPOTHESES]
            state['evidence_trail'].append(f"Pruned to top {MAX_HYPOTHESES} hypotheses by confidence")
        
        logger.info(f"Detected {len(result.get('patterns', []))} patterns")
        return state
    
    def test_hypotheses(self, state: AgentState) -> AgentState:
        """Test existing hypotheses against new evidence."""
        logger.info("Testing hypotheses")
        
        hypotheses = state.get('hypotheses', [])
        if not hypotheses:
            return state
        
        # Get observations added in this iteration
        all_obs = state.get('observations', [])
        recent_obs = all_obs[-50:]
        
        prompt = HYPOTHESIS_TESTING_PROMPT.format(
            hypotheses=json.dumps([h for h in hypotheses], indent=2),
            new_observations=json.dumps(recent_obs, indent=2)
        )
        
        result = self._call_llm(prompt)
        
        # Update hypothesis confidences
        for evaluation in result.get('evaluations', []):
            hyp_id = evaluation['hypothesis_id']
            if hyp_id < len(hypotheses):
                hypotheses[hyp_id]['confidence'] = evaluation['new_confidence']
                hypotheses[hyp_id]['num_tests'] += 1
                hypotheses[hyp_id]['tested_at_iteration'] = state['iterations']
                
                state['evidence_trail'].append(
                    f"Updated hypothesis {hyp_id}: {evaluation['verdict']} -> confidence {evaluation['new_confidence']}"
                )
        
        state['hypotheses'] = hypotheses
        
        logger.info(f"Tested {len(result.get('evaluations', []))} hypotheses")
        return state
    
    def meta_reasoning(self, state: AgentState) -> AgentState:
        """Meta-reasoning: can we answer? Should we continue?"""
        logger.info("Meta-reasoning")
        
        state['iterations'] += 1
        
        prompt = META_REASONING_PROMPT.format(
            query=state['query'],
            sub_questions=json.dumps([sq for sq in state['sub_questions']], indent=2),
            hypotheses=json.dumps([h for h in state.get('hypotheses', [])], indent=2),
            iterations=state['iterations'],
            max_iterations=config.MAX_ITERATIONS
        )
        
        result = self._call_llm(prompt, temperature=0.3)
        
        state['confidence_score'] = result.get('confidence_score', 0.0)
        state['_decision'] = result.get('decision', 'CONTINUE')
        state['_next_action'] = result.get('next_action', '')
        
        state['evidence_trail'].append(
            f"Meta-reasoning: confidence={state['confidence_score']}, decision={state['_decision']}"
        )
        
        # Prune evidence trail if too long
        MAX_TRAIL = config.MAX_EVIDENCE_TRAIL_ITEMS
        if len(state['evidence_trail']) > MAX_TRAIL:
            # Keep first 10 (context) and last (MAX_TRAIL - 10) entries
            state['evidence_trail'] = state['evidence_trail'][:10] + state['evidence_trail'][-(MAX_TRAIL - 10):]
        
        logger.info(f"Meta-reasoning: {state['_decision']} (confidence: {state['confidence_score']})")
        return state
    
    def should_continue(self, state: AgentState) -> str:
        """Decide whether to continue exploring or stop."""
        decision = state.get('_decision', 'CONTINUE')
        iterations = state.get('iterations', 0)
        confidence = state.get('confidence_score', 0.0)
        
        # Hard limits
        if iterations >= config.MAX_ITERATIONS:
            logger.info("Stopping: max iterations reached")
            return "stop"
        
        # Decision-based routing
        if decision == 'SYNTHESIZE' or confidence >= 8.0:
            return "synthesize"
        elif decision == 'STOP' or (confidence < 5.0 and iterations >= 5):
            return "stop"
        else:
            return "continue"
    
    def synthesize_answer(self, state: AgentState) -> AgentState:
        """Synthesize final answer from evidence."""
        logger.info("Synthesizing answer")
        
        # Filter high-confidence hypotheses
        high_conf_hypotheses = [
            h for h in state.get('hypotheses', [])
            if h['confidence'] >= 0.7
        ]
        
        prompt = SYNTHESIS_PROMPT.format(
            query=state['query'],
            sub_questions=json.dumps([sq for sq in state['sub_questions']], indent=2),
            hypotheses=json.dumps(high_conf_hypotheses, indent=2),
            observations=json.dumps(state.get('observations', [])[-100:], indent=2),
            evidence_trail=json.dumps(state.get('evidence_trail', []), indent=2)
        )
        
        result = self._call_llm(prompt, temperature=0.5)
        
        state['answer'] = result.get('answer', 'Unable to determine answer from available evidence.')
        state['uncertainties'] = result.get('uncertainties', [])
        state['confidence_score'] = result.get('confidence', state.get('confidence_score', 0.0))
        
        state['evidence_trail'].append("Synthesized final answer")
        
        logger.info("Answer synthesized")
        return state
    
    def query(self, query: str, session_id: str = None) -> Dict[str, Any]:
        """
        Execute a query against the corpus.
        
        Args:
            query: User's question
            session_id: Optional session ID for resuming
            
        Returns:
            Dictionary with answer, evidence, confidence, etc.
        """
        if session_id is None:
            session_id = f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        # Initial state
        initial_state = AgentState(
            query=query,
            session_id=session_id,
            sub_questions=[],
            observations=[],
            hypotheses=[],
            evidence_trail=[],
            iterations=0,
            confidence_score=0.0,
            stop_reason=None,
            answer=None,
            uncertainties=[],
            started_at=datetime.now().isoformat(),
            tokens_used=0,
        )
        
        # Run the workflow
        config_dict = {"configurable": {"thread_id": session_id}}
        
        try:
            final_state = self.app.invoke(initial_state, config_dict)
            
            return {
                'answer': final_state.get('answer'),
                'confidence': final_state.get('confidence_score'),
                'evidence_trail': final_state.get('evidence_trail'),
                'hypotheses': final_state.get('hypotheses'),
                'observations_count': len(final_state.get('observations', [])),
                'iterations': final_state.get('iterations'),
                'uncertainties': final_state.get('uncertainties'),
                'session_id': session_id,
            }
            
        except Exception as e:
            logger.error(f"Query execution error: {e}")
            return {
                'answer': f"Error executing query: {e}",
                'confidence': 0.0,
                'error': str(e),
            }

