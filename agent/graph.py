from langgraph.graph import StateGraph, END
from agent.state import AnalysisState
from agent.nodes.planner import plan_node
from agent.nodes.analyzer import analyze_node
from agent.nodes.visualizer import visualize_node
from agent.nodes.reporter import report_node
# from agent.nodes.reflection import reflection_node

def build_graph():
    graph = StateGraph(AnalysisState)

    graph.add_node("plan", plan_node)
    graph.add_node("analyze", analyze_node)
    graph.add_node("visualize", visualize_node)
    graph.add_node("report", report_node)
    # graph.add_node("reflection", reflection_node)

    graph.set_entry_point("plan")
    graph.add_edge("plan", "analyze")
    graph.add_edge("analyze", "visualize")
    # graph.add_edge("reflection", "visualize")
    graph.add_edge("visualize", "report")
    graph.add_edge("report", END)

    return graph.compile()