import json
import unittest
from types import SimpleNamespace

from backend.routers.learn import _recent_diagnostic_weak_points


class DashboardDiagnosticsTest(unittest.TestCase):
    def test_recent_diagnostic_weak_points_are_deduped_in_order(self):
        sessions = [
            SimpleNamespace(diagnostic_json=json.dumps({"weak_spots": ["思路启动", "计算细节"]})),
            SimpleNamespace(diagnostic_json=json.dumps({"weak_spots": ["思路启动", "列方程"]})),
            SimpleNamespace(diagnostic_json=None),
        ]

        self.assertEqual(
            _recent_diagnostic_weak_points(sessions, limit=3),
            ["思路启动", "计算细节", "列方程"],
        )

    def test_generic_weak_point_uses_question_graph_node_name(self):
        sessions = [
            SimpleNamespace(
                question_id="q1",
                diagnostic_json=json.dumps({"weak_spots": ["本题关键步骤"]}),
            )
        ]
        questions = {
            "q1": SimpleNamespace(knowmap_nodes=json.dumps(["bx1_c3_s1"]), knowledge_points=json.dumps(["一次函数"]))
        }

        result = _recent_diagnostic_weak_points(
            sessions,
            q_map=questions,
            node_lookup=lambda node_id: {"name": "3.1 函数的概念及其表示"} if node_id == "bx1_c3_s1" else None,
            limit=3,
        )

        self.assertEqual(result, ["3.1 函数的概念及其表示"])


if __name__ == "__main__":
    unittest.main()
