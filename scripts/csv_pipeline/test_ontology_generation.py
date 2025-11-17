import sys
from pathlib import Path

# Ensure the project 'src' directory is on sys.path so 'knowledge_graph' resolves
_ROOT = Path(__file__).resolve().parents[2]
_SRC = _ROOT / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from knowledge_graph.agent.ontology import generate_ontology_from_analysis
from knowledge_graph.agent.agent import CsvAnalysisAgent
import logging
logger = logging.getLogger("knowledgeAgent.pipeline.csv.agent_analyze")

DATASET_1 = "/Users/mawuliagamah/gitprojects/pre_release/kg_extract/src/knowledge_graph/agent/testdata/Netflix_Data.csv"
DATASET_2 = "/Users/mawuliagamah/Datasets/NBA Shots Data/NBA_2024_Shots.csv"


def generate_analysis_text():
    agent = CsvAnalysisAgent()
    analysis_text = agent.analyze_with_llm(
        DATASET_1,
        sample_rows=10,
        delimiter=",",
    )
    return analysis_text

def test_ontology_extraction():
    analysis_text = generate_analysis_text()
    ontology = generate_ontology_from_analysis(analysis_text)
    print(ontology)


if __name__ == "__main__":
    test_ontology_extraction()