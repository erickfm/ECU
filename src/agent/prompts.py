"""
Prompts for the agent reasoning loop.

Following spec: decomposition, pattern detection, hypothesis formation, 
meta-reasoning, synthesis.
"""

DECOMPOSE_QUERY_PROMPT = """You are an expert at breaking down complex questions into tractable sub-questions.

Given the user's query, decompose it into 2-5 sub-questions that, when answered together, would fully address the main query.

For each sub-question, specify:
1. The question text
2. Priority: ESSENTIAL (must answer), CONDITIONAL (depends on other answers), or OPTIONAL (nice to have)
3. Why this sub-question is needed

User Query: {query}

Provide your decomposition in this JSON format:
{{
    "sub_questions": [
        {{
            "text": "Sub-question here?",
            "priority": "ESSENTIAL",
            "reasoning": "Why this is needed"
        }},
        ...
    ]
}}
"""

PATTERN_DETECTION_PROMPT = """You are an expert at detecting patterns, relationships, and potential entity resolutions in text.

Given these observations retrieved from the corpus, identify:
1. Potential coreferences (e.g., "John" might be "J. Smith")
2. Temporal patterns (changes over time)
3. Relationships between entities
4. Contradictions or inconsistencies

Observations:
{observations}

Current sub-questions:
{sub_questions}

For each pattern you detect, explain:
- What pattern/relationship you see
- Which sub-question it helps answer
- Your confidence (0.0-1.0)
- Supporting evidence (observation IDs)

Provide your analysis in JSON format:
{{
    "patterns": [
        {{
            "claim": "Pattern or relationship description",
            "relevant_to_subquestion": 0,
            "confidence": 0.7,
            "evidence_ids": [1, 2, 3],
            "reasoning": "Why you believe this"
        }},
        ...
    ]
}}
"""

HYPOTHESIS_TESTING_PROMPT = """You are testing hypotheses about patterns in the corpus.

Current hypotheses:
{hypotheses}

New observations retrieved:
{new_observations}

For each hypothesis:
1. Does the new evidence support it, contradict it, or neither?
2. Should the confidence increase, decrease, or stay the same?
3. Is it now strong enough to accept (>0.85) or weak enough to reject (<0.15)?

Provide your evaluation in JSON format:
{{
    "evaluations": [
        {{
            "hypothesis_id": 0,
            "verdict": "support" | "contradict" | "neutral",
            "new_confidence": 0.8,
            "reasoning": "Why this verdict"
        }},
        ...
    ]
}}
"""

META_REASONING_PROMPT = """You are evaluating whether you can confidently answer the user's query.

Original query: {query}

Sub-questions and their current status:
{sub_questions}

Current hypotheses:
{hypotheses}

Iterations completed: {iterations}
Max iterations: {max_iterations}

Answer these questions:
1. Can you answer the query now? (yes/no)
2. If yes, what's your confidence (0-10)?
3. If no, what specific information are you missing?
4. Should you continue exploring, or stop?

Decision criteria:
- If confidence >= 8: STOP and synthesize answer
- If confidence < 5 and iterations >= 5: STOP (probably can't answer)
- If last 2 iterations added <5 new observations: STOP (diminishing returns)
- If essential sub-questions remain at 0% confidence after 5 iterations: STOP
- Otherwise: CONTINUE

Provide your evaluation in JSON format:
{{
    "can_answer": true | false,
    "confidence_score": 7.5,
    "missing_information": "What you still need to know",
    "decision": "CONTINUE" | "STOP" | "SYNTHESIZE",
    "reasoning": "Why this decision",
    "next_action": "What to do next if continuing"
}}
"""

SYNTHESIS_PROMPT = """You are synthesizing a final answer based on accumulated evidence.

Original query: {query}

Sub-questions answered:
{sub_questions}

Hypotheses (high confidence):
{hypotheses}

All observations retrieved:
{observations}

Evidence trail:
{evidence_trail}

Create a comprehensive answer that includes:
1. Direct answer to the query (bottom-line up front)
2. Supporting evidence with observation IDs
3. Reasoning chain showing how you arrived at this conclusion
4. Known uncertainties or contradictions
5. Confidence level (0-10)

If there are contradictions, present both sides and explain possible reasons.

Provide your answer in JSON format:
{{
    "answer": "Direct answer to the query",
    "summary": "1-2 sentence summary",
    "evidence": [
        {{
            "claim": "Supporting claim",
            "observation_ids": [1, 2, 3],
            "reasoning": "How this supports the answer"
        }},
        ...
    ],
    "reasoning_chain": ["Step 1", "Step 2", ...],
    "uncertainties": ["Known gaps or contradictions"],
    "confidence": 8.0
}}
"""

GATHER_OBSERVATIONS_PROMPT = """You are deciding what evidence to gather next.

Query: {query}

Sub-questions:
{sub_questions}

Current hypotheses (if any):
{hypotheses}

Observations gathered so far: {num_observations}

Tools available:
1. semantic_search(query, k=20) - Find semantically similar observations
2. find_cooccurrences(surface_form) - Find related observations
3. temporal_query(keyword, start_date, end_date) - Find observations in time range
4. traverse_graph(observation_id, max_hops=2) - Follow co-occurrence graph
5. cluster_observations(obs_ids) - Group similar observations
6. find_contradictions(query) - Find conflicting observations

What tool(s) should you use next and with what parameters?

Focus on:
- Which sub-questions still need evidence
- Which hypotheses need testing
- Gaps in your current understanding

Provide your tool calls in JSON format:
{{
    "tool_calls": [
        {{
            "tool": "semantic_search",
            "parameters": {{"query": "...", "k": 20}},
            "reasoning": "Why this tool will help"
        }},
        ...
    ]
}}

Important: Choose 1-3 tool calls that will give you the most valuable information.
"""

