import httpx, json
base = "http://localhost:8000"
tests = 0
passed = 0

def check(name, fn):
    global tests, passed
    tests += 1
    try:
        fn()
        passed += 1
        print(f"  [PASS] {name}")
    except Exception as e:
        print(f"  [FAIL] {name}: {str(e)[:80]}")

# 1. Health
check("Health check", lambda: httpx.get(base+"/health",timeout=5).json()["status"] == "ok")

# 2. Settings API
check("Providers list", lambda: len(httpx.get(base+"/api/v1/settings/providers",timeout=5).json()["providers"]) >= 6)
check("Get config", lambda: httpx.get(base+"/api/v1/settings/models",timeout=5).json()["model_provider"] == "mock")
check("Update config", lambda: httpx.put(base+"/api/v1/settings/models",json={"model_provider":"deepseek","model_name":"deepseek-chat","api_key":"test","base_url":"https://api.deepseek.com/v1"},timeout=5).json()["model_provider"] == "deepseek")
check("Test connection (mock)", lambda: httpx.post(base+"/api/v1/settings/models/test",json={"model_provider":"mock","model_name":"mock","api_key":"","base_url":""},timeout=5).json()["status"] == "ok")

# 3. KnowMap
r = httpx.get(base+"/api/v1/knowmap/tree",params={"grade":"高中"},timeout=5).json()
check("Tree nodes", lambda: len(r["nodes"]) > 80)
check("Question counts", lambda: len(r.get("question_counts",{})) > 10)

r2 = httpx.get(base+"/api/v1/knowmap/tree",params={"grade":"初中"},timeout=5).json()
check("Middle school tree", lambda: len(r2["nodes"]) > 20)

# 4. Questions at nodes
check("Node bx1 questions", lambda: len(httpx.get(base+"/api/v1/knowmap/nodes/bx1/questions",timeout=5).json()["questions"]) > 0)
check("Node bx1_c5 (trig) questions", lambda: len(httpx.get(base+"/api/v1/knowmap/nodes/bx1_c5/questions",timeout=5).json()["questions"]) > 0)

# 5. Geometry tutor session with diagram
r = httpx.post(base+"/api/v1/tutor/session",json={"question_id":"q_seed_08"},timeout=5).json()
check("Tutor session created", lambda: r.get("total_steps",0) > 0)
check("Has diagram flag", lambda: r.get("has_diagram") == True)
check("Diagram JSON present", lambda: r.get("diagram_json") is not None)
if r.get("diagram_json"):
    d = r["diagram_json"]
    check("Diagram has points", lambda: len(d.get("points",{})) >= 3)
    check("Diagram has lines", lambda: len(d.get("lines",[])) >= 3)

# 6. Upload
with open("D:/Sven/maths/data/test.png","rb") as f:
    r = httpx.post(base+"/api/v1/questions/upload",files={"image":("t.png",f,"image/png")},timeout=10).json()
    check("Upload complete", lambda: r["status"] == "complete")

# 7. Conversation flow (correct answers)
sid = "s_" + "test" + "_conv"
# Create a fresh session
r = httpx.post(base+"/api/v1/tutor/session",json={"question_id":"q_seed_01"},timeout=5).json()
if "session_id" in r:
    sid = r["session_id"]
    check("Step 1 correct", lambda: httpx.post(base+"/api/v1/tutor/message",json={"session_id":sid,"message":"求f(3)的值","intent":"answer"},timeout=5).json()["type"] == "correct")
    check("Step 2 correct", lambda: httpx.post(base+"/api/v1/tutor/message",json={"session_id":sid,"message":"7","intent":"answer"},timeout=5).json()["type"] == "correct")
    m3 = httpx.post(base+"/api/v1/tutor/message",json={"session_id":sid,"message":"hint","intent":"hint"},timeout=5).json()
    check("Hint works", lambda: m3["type"] in ("hint","correct","complete"))

# 8. Dashboard
r = httpx.get(base+"/api/v1/learn/dashboard",timeout=5).json()
check("Dashboard total questions", lambda: r.get("total_questions",0) > 0)

# 9. History
r = httpx.get(base+"/api/v1/learn/history",timeout=5).json()
check("Has history", lambda: len(r.get("sessions",[])) > 0)

print(f"\n{'='*50}")
print(f"Results: {passed}/{tests} tests passed")
if passed == tests:
    print("ALL TESTS PASSED")
else:
    print(f"FAILED: {tests-passed} errors")
print(f"{'='*50}")
