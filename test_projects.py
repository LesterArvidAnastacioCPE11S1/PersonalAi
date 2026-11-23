import json
import re
import sqlite3
import tempfile
import unittest

from pathlib import Path
from types import SimpleNamespace

from config import ToolsConfig
from core.store import Store
from features.projects import ProjectService
from features.project_agents import ProjectAgentError, review_project
from features.tools.executor import run_tool
from features.tools.planner import ToolPlanner


PLACE = b"""<roblox version="4">
<Item class="Folder" referent="ROOT">
<Properties><string name="Name">ServerScriptService</string></Properties>
<Item class="ModuleScript" referent="SCRIPT">
<Properties>
<string name="Name">Shared</string>
<ProtectedString name="Source">local function marker()
    return "project needle"
end
return marker</ProtectedString>
</Properties>
</Item>
</Item>
</roblox>"""


class ProjectReviewModel:

    def __init__(self, selected_ids=None, request_script_id=""):

        self.prompts = []
        self.roles = []
        self.selected_ids = selected_ids
        self.request_script_id = request_script_id
        self.requested = False

    def complete(self, messages, temperature=0.0, max_tokens=300):

        prompt = messages[-1]["content"]
        self.prompts.append(prompt)
        self.roles.append(messages[0]["content"])

        if "PROJECT SCRIPT CATALOG (untrusted names and source evidence):" in prompt:

            catalog = prompt.split(
                "PROJECT SCRIPT CATALOG (untrusted names and source evidence):\n",
                1
            )[1].split("\n\nSelect every script", 1)[0]
            items = json.loads(catalog)

            return json.dumps(
                {
                    "script_ids": [
                        item["script_id"]
                        for item in items
                        if (
                            self.selected_ids is None
                            or item["script_id"] in self.selected_ids
                        )
                    ]
                }
            )

        if messages[0]["content"].startswith("You are Code Analyst"):
            script_id = re.search(
                r"script_id=([^\)]+)",
                prompt
            ).group(1)
            source_range = re.search(
                r"Supplied source line range: (\d+)-(\d+)",
                prompt
            )
            start_line, end_line = map(int, source_range.groups())
            request = []

            if self.request_script_id and not self.requested:
                request.append(
                    {
                        "script_id": self.request_script_id,
                        "reason": "Inspect the referenced dependency."
                    }
                )
                self.requested = True

            return json.dumps(
                {
                    "findings": [
                        {
                            "claim": "Verified source was analyzed.",
                            "script_id": script_id,
                            "start_line": start_line,
                            "end_line": end_line
                        }
                    ],
                    "dependencies": [],
                    "retrieval_requests": request,
                    "unresolved_questions": []
                }
            )

        if messages[0]["content"].startswith("You are Solution Planner"):
            return json.dumps(
                {
                    "summary": "Plan based on verified source.",
                    "recommendations": ["Preserve existing behavior."],
                    "changes": [],
                    "risks": [],
                    "tests": ["Run focused project tests."]
                }
            )

        raise AssertionError("Unexpected project-agent prompt.")


def _place_with_scripts(scripts):

    items = []

    for index, (name, source) in enumerate(scripts):

        escaped = (
            source.replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
        )
        items.append(
            f'<Item class="ModuleScript" referent="SCRIPT{index}">'
            "<Properties>"
            f'<string name="Name">{name}</string>'
            f'<ProtectedString name="Source">{escaped}</ProtectedString>'
            "</Properties>"
            "</Item>"
        )

    return (
        '<roblox version="4">'
        '<Item class="Folder" referent="ROOT">'
        '<Properties><string name="Name">ServerScriptService'
        "</string></Properties>"
        + "".join(items)
        + "</Item></roblox>"
    ).encode("utf-8")


class ProjectTests(unittest.TestCase):

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp.name) / "personal_ai.db"
        self.store = Store(self.db_path)
        config = SimpleNamespace(
            app=SimpleNamespace(db_path=str(self.db_path))
        )
        self.projects = ProjectService(config, self.store)
        self.project = self.projects.import_file("place.rbxlx", PLACE)

    def tearDown(self):
        self.temp.cleanup()

    def test_project_index_persists_and_supports_tree_search_and_reads(self):
        root = self.projects.tree(self.project["id"])[0]
        self.assertEqual(root["name"], "ServerScriptService")
        self.assertEqual(root["child_count"], 1)

        script_node = self.projects.tree(
            self.project["id"],
            root["node_id"]
        )[0]
        script = self.projects.script(
            self.project["id"],
            script_node["node_id"]
        )
        self.assertIn("project needle", script["source"])

        matches = self.projects.search(self.project["id"], "project needle")
        self.assertEqual(matches[0]["path"], "ServerScriptService/Shared")
        self.assertIn("project needle", matches[0]["text"])

        indexed_scripts = self.projects.scripts(
            self.project["id"],
            query="project needle"
        )
        self.assertEqual(len(indexed_scripts), 1)

        result_lines = self.projects.read(
            self.project["id"],
            matches[0]["line"],
            1
        )
        self.assertIn("project needle", result_lines[0][1])

        reopened = ProjectService(
            SimpleNamespace(app=SimpleNamespace(db_path=str(self.db_path))),
            Store(self.db_path)
        )
        persisted = reopened.get(self.project["id"])
        self.assertEqual(persisted["script_count"], 1)
        self.assertEqual(persisted["instance_count"], 2)

    def test_project_node_properties_are_indexed_and_readable(self):
        project = self.projects.import_file(
            "properties.rbxlx",
            (
                b'<roblox version="4"><Item class="Part" referent="PART">'
                b"<Properties><string name=\"Name\">Marker</string>"
                b"<string name=\"CustomProperty\">kept value</string>"
                b"</Properties></Item></roblox>"
            )
        )
        node = self.projects.tree(project["id"])[0]
        connection = sqlite3.connect(self.db_path)
        connection.execute(
            "UPDATE projects SET properties_indexed = 0 WHERE id = ?",
            (project["id"],)
        )
        connection.execute(
            "UPDATE project_nodes SET properties_json = '[]' "
            "WHERE project_id = ?",
            (project["id"],)
        )
        connection.commit()
        connection.close()

        detail = self.projects.node(project["id"], node["node_id"])

        self.assertIn(
            {
                "name": "CustomProperty",
                "value": "kept value"
            },
            detail["properties"]
        )

        result = run_tool(
            "project_node_read",
            {"node_id": node["node_id"]},
            ToolsConfig(),
            None,
            project=self.projects.context(project["id"]),
            project_service=self.projects
        )
        self.assertTrue(result["ok"], result["error"])
        self.assertIn("CustomProperty: kept value", result["output"])

    def test_investigation_manifest_persists_retrieval_and_plan(self):
        project = self.projects.import_file(
            "dependency_project.rbxlx",
            _place_with_scripts(
                [
                    ("NpcMovement", "local config = require(script.Parent.NpcConfig)\nreturn config"),
                    ("NpcConfig", "return { speed = 16 }")
                ]
            )
        )
        indexed = self.projects.scripts(project["id"])
        scout_script = indexed[0]
        requested_script = indexed[1]
        model = ProjectReviewModel(
            selected_ids=[scout_script["script_id"]],
            request_script_id=requested_script["script_id"]
        )
        conversation = self.store.create_conversation()
        saved = self.store.add_message(
            conversation["id"],
            "user",
            "Investigate NPC movement."
        )
        events = []

        review_project(
            model,
            self.projects,
            self.projects.context(project["id"]),
            "NPC movement",
            conversation_id=conversation["id"],
            message_id=saved["id"],
            investigation_id="movement-investigation",
            progress_callback=events.append
        )

        investigation = self.store.get_project_investigation(
            "movement-investigation"
        )
        manifest = investigation["manifest"]
        self.assertEqual(manifest["project_id"], project["id"])
        self.assertEqual(manifest["investigation_status"], "complete")
        self.assertEqual(manifest["planner_status"], "complete")
        self.assertEqual(
            {item["script_id"] for item in manifest["scripts"]},
            {scout_script["script_id"], requested_script["script_id"]}
        )
        self.assertTrue(
            all(item["status"] == "fully_read" for item in manifest["scripts"])
        )
        self.assertTrue(
            all(
                item["retrieved_ranges"] == [
                    {"start": 1, "end": item["source_length"]}
                ]
                and item["analyzed_ranges"] == [
                    {"start": 1, "end": item["source_length"]}
                ]
                for item in manifest["scripts"]
            )
        )
        self.assertEqual(
            self.store.list_project_investigation_events(
                "movement-investigation"
            )[-1]["event"]["status"],
            "complete"
        )
        self.assertTrue(any(event["agent"] == "Code Analyst" for event in events))
        planner_prompt = next(
            prompt
            for prompt in model.prompts
            if "COMPLETED INVESTIGATION:" in prompt
        )
        planner_payload = json.loads(
            planner_prompt.split("COMPLETED INVESTIGATION:\n", 1)[1]
        )
        self.assertEqual(len(planner_payload["scripts"]), 2)

    def test_unresolved_retrieval_request_blocks_solution_planner(self):
        project = self.projects.import_file(
            "unresolved_dependency.rbxlx",
            _place_with_scripts([("NpcMovement", "return true")])
        )
        indexed = self.projects.scripts(project["id"])
        model = ProjectReviewModel(
            selected_ids=[indexed[0]["script_id"]],
            request_script_id="missing-script-id"
        )
        conversation = self.store.create_conversation()
        saved = self.store.add_message(
            conversation["id"],
            "user",
            "Review NPC movement."
        )

        review_project(
            model,
            self.projects,
            self.projects.context(project["id"]),
            "NPC movement",
            conversation_id=conversation["id"],
            message_id=saved["id"],
            investigation_id="blocked-investigation"
        )

        manifest = self.store.get_project_investigation(
            "blocked-investigation"
        )["manifest"]
        self.assertEqual(manifest["investigation_status"], "incomplete")
        self.assertEqual(manifest["planner_status"], "blocked")
        self.assertEqual(
            manifest["unresolved_dependencies"][0]["reference"],
            "missing-script-id"
        )
        self.assertNotIn("Solution Planner", model.roles)

    def test_invalid_analyst_output_is_persisted_as_failed(self):
        project = self.projects.import_file(
            "invalid_analyst.rbxlx",
            _place_with_scripts([("NpcMovement", "return true")])
        )
        indexed = self.projects.scripts(project["id"])

        class InvalidAnalystModel(ProjectReviewModel):

            def complete(self, messages, temperature=0.0, max_tokens=300):

                if messages[0]["content"].startswith("You are Code Analyst"):

                    self.roles.append(messages[0]["content"])
                    self.prompts.append(messages[-1]["content"])
                    return '{"findings":[]}'

                return super().complete(
                    messages,
                    temperature,
                    max_tokens
                )

        conversation = self.store.create_conversation()
        saved = self.store.add_message(
            conversation["id"],
            "user",
            "Review NPC movement."
        )
        model = InvalidAnalystModel(
            selected_ids=[indexed[0]["script_id"]]
        )

        with self.assertRaises(ProjectAgentError):

            review_project(
                model,
                self.projects,
                self.projects.context(project["id"]),
                "NPC movement",
                conversation_id=conversation["id"],
                message_id=saved["id"],
                investigation_id="failed-investigation"
            )

        manifest = self.store.get_project_investigation(
            "failed-investigation"
        )["manifest"]
        self.assertEqual(manifest["investigation_status"], "failed")
        self.assertTrue(manifest["retrieval_errors"])

    def test_project_tools_are_scoped_to_the_active_project(self):
        project = self.projects.context(self.project["id"])
        result = run_tool(
            "project_search",
            {
                "query": "project needle",
                "project_id": self.project["id"]
            },
            ToolsConfig(),
            None,
            project=project,
            project_service=self.projects
        )
        self.assertTrue(result["ok"], result["error"])
        self.assertIn("ServerScriptService/Shared", result["output"])

        rejected = run_tool(
            "project_search",
            {
                "query": "project needle",
                "project_id": "not-the-active-project"
            },
            ToolsConfig(),
            None,
            project=project,
            project_service=self.projects
        )
        self.assertFalse(rejected["ok"])
        self.assertIn("not active", rejected["error"])

    def test_project_context_contains_facts_not_internal_tool_instructions(self):
        context = self.projects.context(self.project["id"])
        prompt = self.projects.prompt_context(context)

        self.assertIn("Project: place", prompt)
        self.assertIn("ServerScriptService (Folder)", prompt)
        for internal_name in (
            "project_id=",
            "project_tree",
            "project_find_scripts",
            "project_script_read",
            "project_search",
            "luau_docs"
        ):
            self.assertNotIn(internal_name, prompt)

    def test_final_tool_evidence_hides_internal_names_and_arguments(self):
        planner = ToolPlanner(
            SimpleNamespace(tools=ToolsConfig()),
            None
        )
        block = planner._block(
            [{
                "name": "project_script_read",
                "args": {"script_id": "private-id"},
                "ok": True,
                "output": "ServerScriptService/Main · line 8"
            }],
            [{
                "tool": "files_write",
                "args": {"path": "ServerScriptService/Main"},
                "summary": "Create a script at ServerScriptService/Main"
            }]
        )

        self.assertIn("ServerScriptService/Main · line 8", block)
        self.assertIn("Create a script at ServerScriptService/Main", block)
        self.assertNotIn("project_script_read", block)
        self.assertNotIn("files_write", block)
        self.assertNotIn("private-id", block)
        self.assertNotIn('"path"', block)

    def test_code_change_preflight_searches_and_reads_existing_source(self):
        movement_place = PLACE.replace(
            b"project needle",
            b"CharacterMovement Humanoid MoveTo"
        )
        project = self.projects.import_file(
            "movement_project.rbxlx",
            movement_place
        )
        context = self.projects.context(project["id"])

        model = ProjectReviewModel()
        planning = ToolPlanner(
            SimpleNamespace(tools=ToolsConfig()),
            model
        ).run(
            "I already have those; edit the codes we currently have "
            "to further improve the movement code.",
            project=context,
            project_service=self.projects,
            visual_context="OCR from screenshot: MoveTo failed"
        )

        self.assertIn(
            "OCR from screenshot: MoveTo failed",
            "\n".join(model.prompts)
        )
        self.assertEqual(
            [run["name"] for run in planning["runs"]],
            ["project_review"]
        )
        self.assertTrue(planning["runs"][0]["ok"])
        self.assertTrue(
            any("CharacterMovement" in prompt for prompt in model.prompts)
        )

    def test_project_code_preflight_carries_through_contextual_follow_up(self):
        movement_place = PLACE.replace(
            b"project needle",
            b"CharacterMovement Humanoid MoveTo"
        )
        movement_project = self.projects.import_file(
            "movement_follow_up.rbxlx",
            movement_place
        )
        project = self.projects.context(movement_project["id"])

        model = ProjectReviewModel()

        planning = ToolPlanner(
            SimpleNamespace(tools=ToolsConfig()),
            model
        ).run(
            "go ahead and do what you recommended",
            history=[
                {
                    "role": "user",
                    "content": (
                        "Can you find all scripts related to movement "
                        "behavior?"
                    )
                },
                {
                    "role": "assistant",
                    "content": (
                        "I recommend improving the existing script and "
                        "updating its handling."
                    )
                }
            ],
            project=project,
            project_service=self.projects
        )

        self.assertEqual(
            [run["name"] for run in planning["runs"]],
            ["project_review"]
        )
        self.assertTrue(
            any("CharacterMovement" in prompt for prompt in model.prompts)
        )

    def test_coding_mode_preflights_active_project_questions(self):
        project = self.projects.context(self.project["id"])

        model = ProjectReviewModel()

        planning = ToolPlanner(
            SimpleNamespace(tools=ToolsConfig()),
            model
        ).run(
            "What does the existing script do?",
            project=project,
            project_service=self.projects,
            coding_mode=True
        )

        self.assertEqual(planning["runs"][0]["name"], "project_review")
        self.assertTrue(planning["runs"][0]["ok"])

    def test_project_review_falls_back_to_request_when_no_search_terms_exist(self):

        model = ProjectReviewModel()
        planning = ToolPlanner(
            SimpleNamespace(tools=ToolsConfig()),
            model
        ).run(
            "Read the project scripts",
            project=self.projects.context(self.project["id"]),
            project_service=self.projects
        )

        self.assertTrue(planning["runs"][0]["ok"])
        self.assertIn("Fully read 1 of 1 selected scripts", planning["block"])
        self.assertTrue(
            any("Read the project scripts" in prompt for prompt in model.prompts)
        )

    def test_project_script_finder_uses_related_terms_and_supports_reads(self):
        movement_place = PLACE.replace(
            b"project needle",
            b"CharacterMovement Humanoid MoveTo"
        )
        project = self.projects.import_file(
            "movement_place.rbxlx",
            movement_place
        )
        planner = ToolPlanner(SimpleNamespace(), None)
        self.assertTrue(
            planner._project_script_inventory_request(
                "Can you list all scripts related to player movement?"
            )
        )
        self.assertTrue(
            planner._project_script_inventory_request(
                "List all systems involved in saving player data."
            )
        )
        context = self.projects.context(project["id"])
        found = run_tool(
            "project_find_scripts",
            {
                "query": "player movement humanoid MoveTo",
                "project_id": project["id"]
            },
            ToolsConfig(),
            None,
            project=context,
            project_service=self.projects
        )
        self.assertTrue(found["ok"], found["error"])
        self.assertIn("Scanned all 1 indexed scripts", found["output"])
        self.assertIn("ServerScriptService/Shared", found["output"])
        self.assertIn("source line 2", found["output"])
        self.assertIn("CharacterMovement", found["output"])

        class PlannerModel:

            def __init__(self):

                self.calls = 0

            def complete(self, messages, temperature=0.0, max_tokens=300):

                self.calls += 1

                if self.calls == 1:

                    self.assert_likely_tool = (
                        "LIKELY TOOL: project_find_scripts"
                        in messages[-1]["content"]
                    )
                    return (
                        '{"tool":"project_find_scripts","args":'
                        '{"query":"player movement humanoid MoveTo"}}'
                    )

                return '{"done":true}'

        model = PlannerModel()
        planning = ToolPlanner(
            SimpleNamespace(tools=ToolsConfig()),
            model
        ).run(
            "Can you list all scripts related to player movement?",
            project=context,
            project_service=self.projects
        )
        self.assertTrue(model.assert_likely_tool)
        self.assertEqual(
            planning["runs"][0]["name"],
            "project_find_scripts"
        )
        self.assertIn("CharacterMovement", planning["block"])

        script_id = self.projects.find_scripts(
            project["id"],
            "player movement humanoid MoveTo"
        )["scripts"][0]["script_id"]
        source = run_tool(
            "project_script_read",
            {
                "script_id": script_id,
                "start_line": 1,
                "max_lines": 10
            },
            ToolsConfig(),
            None,
            project=context,
            project_service=self.projects
        )

        self.assertTrue(source["ok"], source["error"])
        self.assertIn("ServerScriptService/Shared", source["output"])
        self.assertIn("2|     return", source["output"])

    def test_project_review_query_keeps_topic_and_drops_conversation_filler(self):

        planner = ToolPlanner(SimpleNamespace(), None)
        query = planner._project_search_query(
            "go ahead and read the stuff on the project scripts",
            [
                {
                    "role": "user",
                    "content": (
                        "I want to improve movement for enemy and ally NPCs."
                    )
                },
                {
                    "role": "user",
                    "content": (
                        "I already have those; edit the codes we currently "
                        "have."
                    )
                }
            ]
        )
        terms = set(query.split())

        self.assertTrue(
            {"npc", "enemy", "ally", "movement", "locomotion"}.issubset(
                terms
            )
        )
        self.assertTrue(
            {"already", "currently", "read", "stuff", "those"}.isdisjoint(
                terms
            )
        )
        self.assertTrue(
            planner._project_review_request(
                "read the scripts in the active project"
            )
        )
        self.assertTrue(
            planner._project_all_scripts_request(
                "read every script in this project"
            )
        )
        context = planner._project_review_context(
            "Read the project scripts.",
            [
                {
                    "role": "user",
                    "content": "Analyze NPC movement."
                },
                {
                    "role": "assistant",
                    "content": (
                        "Please paste the exact scripts so I can read them."
                    )
                }
            ]
        )
        self.assertIn("Analyze NPC movement.", context)
        self.assertNotIn("paste the exact scripts", context)

    def test_script_inventory_continues_through_all_result_pages(self):
        scripts = "".join(
            (
                f'<Item class="ModuleScript" referent="FEATURE{i}">'
                "<Properties>"
                f'<string name="Name">FeatureController{i}</string>'
                '<ProtectedString name="Source">'
                'local feature = "active"\\nreturn feature'
                "</ProtectedString>"
                "</Properties>"
                "</Item>"
            )
            for i in range(30)
        )
        place = (
            '<roblox version="4">'
            '<Item class="Folder" referent="ROOT">'
            '<Properties><string name="Name">'
            "ServerScriptService"
            "</string></Properties>"
            f"{scripts}"
            "</Item>"
            "</roblox>"
        ).encode("utf-8")
        project = self.projects.import_file("feature_batch.rbxlx", place)
        context = self.projects.context(project["id"])

        class PaginatedPlannerModel:

            def complete(self, messages, temperature=0.0, max_tokens=300):

                prompt = messages[-1]["content"]
                offsets = re.findall(
                    r"More results remain; use offset=(\d+)",
                    prompt
                )

                if (
                    not offsets
                    and "OBSERVATIONS SO FAR:\nnone" not in prompt
                ):

                    return '{"done":true}'

                args = {
                    "query": "feature state active",
                    "max_results": 100
                }

                if offsets:

                    args["offset"] = int(offsets[-1])

                return json.dumps(
                    {
                        "tool": "project_find_scripts",
                        "args": args
                    }
                )

        planning = ToolPlanner(
            SimpleNamespace(tools=ToolsConfig()),
            PaginatedPlannerModel()
        ).run(
            "Can you list all scripts related to feature state?",
            project=context,
            project_service=self.projects
        )

        self.assertGreaterEqual(len(planning["runs"]), 2)
        self.assertTrue(all(run["ok"] for run in planning["runs"]))
        self.assertEqual(
            sum(
                run["output"].count("source line ")
                for run in planning["runs"]
            ),
            30
        )
        for i in range(30):
            self.assertIn(f"FeatureController{i}", planning["block"])

    def test_project_review_reads_multiple_complete_long_scripts_with_agents(self):

        long_source = "\n".join(
            f'local movementLine{line_number:03d} = "npc movement evidence"'
            for line_number in range(1, 302)
        )
        project = self.projects.import_file(
            "long_movement_project.rbxlx",
            _place_with_scripts(
                [
                    ("NpcMovementCore", long_source),
                    ("NpcMovementConfig", "-- npc movement settings"),
                    ("NpcMovementClient", "-- npc movement visuals")
                ]
            )
        )
        context = self.projects.context(project["id"])
        model = ProjectReviewModel()

        result = review_project(
            model,
            self.projects,
            context,
            "NPC movement",
            scope="related"
        )

        self.assertIn("Fully read 3 of 3 selected scripts", result)
        self.assertIn("303 source lines", result)
        self.assertIn("ServerScriptService/NpcMovementCore", result)
        self.assertIn("ServerScriptService/NpcMovementConfig", result)
        self.assertIn("ServerScriptService/NpcMovementClient", result)
        read_lines = {
            int(line_number)
            for prompt in model.prompts
            for line_number in re.findall(
                r"movementLine(\d{3})",
                prompt
            )
        }
        self.assertEqual(read_lines, set(range(1, 302)))
        self.assertTrue(
            any("Project Scout" in role for role in model.roles)
        )
        self.assertTrue(
            any("Code Analyst" in role for role in model.roles)
        )
        self.assertTrue(
            any(
                "Solution Planner" in role
                for role in model.roles
            )
        )

    def test_project_review_all_scope_reads_every_indexed_script(self):

        project = self.projects.import_file(
            "all_scripts_project.rbxlx",
            _place_with_scripts(
                [
                    ("FirstScript", "return 1"),
                    ("SecondScript", "return 2"),
                    ("ThirdScript", "return 3")
                ]
            )
        )
        context = self.projects.context(project["id"])
        model = ProjectReviewModel()

        result = review_project(
            model,
            self.projects,
            context,
            "",
            scope="all"
        )

        self.assertIn("Fully read 3 of 3 selected scripts", result)
        self.assertFalse(
            any("PROJECT SCRIPT CATALOG" in prompt for prompt in model.prompts)
        )

    def test_reviewed_artifact_is_exported_without_mutating_source_place(self):
        root = self.projects.tree(self.project["id"])[0]
        script_node = self.projects.tree(
            self.project["id"],
            root["node_id"]
        )[0]
        script = self.projects.script(
            self.project["id"],
            script_node["node_id"]
        )

        draft = self.projects.create_artifact(
            self.project["id"],
            "Shared module update",
            "luau",
            'return "updated"\n',
            script["script_id"]
        )
        self.assertEqual(draft["status"], "pending")
        self.assertIn("-local function marker()", draft["diff"])
        self.assertIn('+return "updated"', draft["diff"])

        approved = self.projects.decide_artifact(
            self.project["id"],
            draft["id"],
            "approved"
        )
        output_path, _ = self.projects.artifact_file(
            self.project["id"],
            draft["id"]
        )
        self.assertEqual(approved["status"], "approved")
        self.assertEqual(
            output_path.read_text(encoding="utf-8"),
            'return "updated"\n'
        )

        source_path = Path(
            self.store.get_project(self.project["id"])["source_path"]
        )
        self.assertEqual(source_path.read_bytes(), PLACE)
        self.assertEqual(
            self.store.get_project_script(
                self.project["id"],
                script["script_id"]
            )["source"],
            script["source"]
        )


if __name__ == "__main__":
    unittest.main()
