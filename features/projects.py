import difflib
import json
import os
import re
import shutil
import uuid

from datetime import datetime, timezone
from pathlib import Path

from features.attachments import MAX_ROBLOX_BYTES
from features.roblox_files import RobloxFileError, extract_index


SUPPORTED_EXTENSIONS = {".rbxl", ".rbxlx", ".rbxm", ".rbxmx"}
MAX_ARTIFACT_CHARS = 2_000_000
LANGUAGE_EXTENSIONS = {
    "luau": ".luau",
    "lua": ".lua",
    "python": ".py",
    "javascript": ".js",
    "typescript": ".ts",
    "json": ".json",
    "text": ".txt"
}
SCRIPT_HEADER = re.compile(
    r"^--- (.+?) \((?:Script|LocalScript|ModuleScript)\) ---$"
)
SCRIPT_QUERY_STOP_WORDS = {
    "all",
    "already",
    "and",
    "any",
    "ahead",
    "are",
    "be",
    "can",
    "control",
    "controls",
    "code",
    "codes",
    "currently",
    "create",
    "do",
    "does",
    "edit",
    "edits",
    "every",
    "find",
    "for",
    "from",
    "further",
    "give",
    "go",
    "handle",
    "handles",
    "has",
    "have",
    "improve",
    "in",
    "list",
    "making",
    "me",
    "meant",
    "next",
    "of",
    "plan",
    "project",
    "read",
    "recommend",
    "related",
    "script",
    "scripts",
    "show",
    "should",
    "some",
    "stuff",
    "such",
    "tell",
    "that",
    "the",
    "these",
    "then",
    "to",
    "those",
    "using",
    "wanna",
    "well",
    "want",
    "wanted",
    "wants",
    "what",
    "will",
    "which",
    "with",
    "both",
    "you"
}
SCRIPT_QUERY_EXPANSIONS = {
    "ally": {"ally", "friendly", "support"},
    "enemy": {"enemy", "hostile", "opponent"},
    "movement": {
        "movement",
        "move",
        "locomotion",
        "navigation",
        "nav",
        "pathfinding",
        "path",
        "formation",
        "walk"
    },
    "movements": {
        "movement",
        "move",
        "locomotion",
        "navigation",
        "nav",
        "pathfinding",
        "path",
        "formation",
        "walk"
    },
    "npc": {"npc", "npcs", "enemy", "ally"},
    "npcs": {"npc", "npcs", "enemy", "ally"},
    "behavior": {
        "behavior",
        "behaviour",
        "decision",
        "tactic",
        "target",
        "sense",
        "combat"
    },
    "behaviour": {
        "behavior",
        "behaviour",
        "decision",
        "tactic",
        "target",
        "sense",
        "combat"
    }
}
class ProjectError(Exception):
    pass


class ProjectNotFound(ProjectError):
    pass


def _normalize_search_text(text):

    text = str(text or "")
    text = re.sub(r"\bNPCs\b", "NPC", text, flags=re.IGNORECASE)
    text = re.sub(
        r"(?<=[a-z0-9])(?=[A-Z])|(?<=[A-Z])(?=[A-Z][a-z])",
        " ",
        text
    )
    text = re.sub(r"[_./\\-]+", " ", text)

    return text.casefold()


def script_query_terms(query):

    terms = {
        term
        for term in re.findall(
            r"[a-z0-9]+",
            _normalize_search_text(query)
        )
        if (
            len(term) >= 3
            or term == "ai"
        )
        and term not in SCRIPT_QUERY_STOP_WORDS
    }
    expanded = set(terms)

    for term in terms:

        expanded.update(SCRIPT_QUERY_EXPANSIONS.get(term, set()))

    return expanded


def _now():

    return datetime.now(
        timezone.utc
    ).isoformat(timespec="seconds")


class ProjectService:

    def __init__(self, config, store):

        self.store = store
        self.root = (
            Path(getattr(config.app, "db_path", "data/personal_ai.db"))
            .resolve()
            .parent
            / "projects"
        )
        self._script_find_cache = {}
        self.root.mkdir(parents=True, exist_ok=True)

    def _project_dir(self, project_id):

        if not re.fullmatch(r"[a-f0-9]{32}", str(project_id or "")):

            raise ProjectNotFound("Roblox project not found.")

        project_dir = (self.root / project_id).resolve()

        if project_dir.parent != self.root.resolve():

            raise ProjectNotFound("Roblox project not found.")

        return project_dir

    def _get(self, project_id):

        project = self.store.get_project(project_id)

        if project is None:

            raise ProjectNotFound("Roblox project not found.")

        project["extracted_path"] = project["parsed_path"]
        project["class_counts"] = json.loads(
            project.pop("class_counts_json") or "{}"
        )
        return project

    def import_file(self, filename, data, name=""):

        safe_filename = Path(
            str(filename or "").replace("\\", "/")
        ).name
        extension = Path(safe_filename).suffix.lower()

        if extension not in SUPPORTED_EXTENSIONS:

            raise ProjectError(
                "Choose a Roblox place or model file "
                "(.rbxl, .rbxlx, .rbxm, or .rbxmx)."
            )

        if not data:

            raise ProjectError("The Roblox file is empty.")

        if len(data) > MAX_ROBLOX_BYTES:

            raise ProjectError("The Roblox file is larger than 500 MB.")

        project_id = uuid.uuid4().hex
        project_dir = self._project_dir(project_id)
        project_dir.mkdir(parents=True, exist_ok=False)
        source_path = project_dir / ("source" + extension)
        parsed_path = project_dir / "parsed.txt"

        try:

            source_path.write_bytes(data)
            index = extract_index(data, safe_filename)
            parsed_path.write_bytes(index["text"].encode("utf-8"))
            now = _now()
            project = {
                "id": project_id,
                "name": (
                    str(name or "").strip()[:120]
                    or Path(safe_filename).stem[:120]
                    or "Roblox project"
                ),
                "filename": safe_filename[:160],
                "source_path": str(source_path),
                "parsed_path": str(parsed_path),
                "instance_count": index["instance_count"],
                "script_count": index["script_count"],
                "root_count": index["root_count"],
                "class_counts_json": json.dumps(
                    index["class_counts"],
                    sort_keys=True
                ),
                "created_at": now,
                "updated_at": now
            }
            self.store.create_project(
                project,
                index["tree_rows"],
                index["script_rows"]
            )

        except Exception as error:

            shutil.rmtree(project_dir, ignore_errors=True)

            if isinstance(error, ProjectError):

                raise

            raise ProjectError(
                f"Could not import Roblox project: {error}"
            ) from error

        return self.public(self._get(project_id))

    def list(self):

        return [
            self.public(self._get(row["id"]))
            for row in self.store.list_projects()
        ]

    def public(self, project):

        roots = self.store.list_project_nodes(
            project["id"],
            limit=30
        )
        return {
            "id": project["id"],
            "name": project["name"],
            "filename": project["filename"],
            "instance_count": project["instance_count"],
            "script_count": project["script_count"],
            "root_count": project["root_count"],
            "class_counts": project.get("class_counts") or {},
            "roots": roots,
            "created_at": project["created_at"],
            "updated_at": project["updated_at"]
        }

    def get(self, project_id):

        return self.public(self._get(project_id))

    def context(self, project_id):

        return self._get(project_id)

    def prompt_context(self, project):

        roots = self.store.list_project_nodes(
            project["id"],
            limit=30
        )
        root_paths = "\n".join(
            f"- {node['name']} ({node['class_name']})"
            for node in roots
        )

        return (
            "\n\n[Active Roblox project]\n"
            f"Project: {project['name']}\n"
            f"Source file: {project['filename']}; "
            f"{project['instance_count']} instances, "
            f"{project['script_count']} scripts, "
            f"{project['root_count']} root instances.\n"
            f"Top-level hierarchy:\n{root_paths or '- (empty)'}\n"
            "The project is indexed for source-aware answers.\n"
        )

    def tree(self, project_id, parent_id=None, limit=200, offset=0):

        self._get(project_id)

        if parent_id:

            if self.store.get_project_node(project_id, parent_id) is None:

                raise ProjectNotFound("Hierarchy node not found.")

        safe_limit = min(500, max(1, int(limit or 200)))
        safe_offset = max(0, int(offset or 0))
        return self.store.list_project_nodes(
            project_id,
            parent_id=parent_id,
            limit=safe_limit,
            offset=safe_offset
        )

    def node(self, project_id, node_id):

        project = self._get(project_id)

        if not project.get("properties_indexed"):

            try:

                source = Path(project["source_path"]).read_bytes()
                index = extract_index(source, project["filename"])
                self.store.update_project_node_properties(
                    project_id,
                    index["tree_rows"]
                )

            except (OSError, RobloxFileError) as error:

                raise ProjectError(
                    f"Could not index instance properties: {error}"
                ) from error

        node = self.store.get_project_node(project_id, node_id)

        if node is None:

            raise ProjectNotFound("Hierarchy node not found.")

        node["properties"] = json.loads(
            node.pop("properties_json") or "[]"
        )
        return node

    def scripts(self, project_id, query="", limit=200, offset=0):

        self._get(project_id)
        safe_limit = min(500, max(1, int(limit or 200)))
        safe_offset = max(0, int(offset or 0))

        if query:

            return self.store.search_project_scripts(
                project_id,
                str(query)[:200],
                safe_limit
            )

        return self.store.list_project_scripts(
            project_id,
            safe_limit,
            safe_offset
        )

    def script(self, project_id, script_id):

        self._get(project_id)
        script = self.store.get_project_script(project_id, script_id)

        if script is None:

            raise ProjectNotFound("Project script not found.")

        return script

    def find_scripts(self, project_id, query, limit=100, offset=0):

        project = self._get(project_id)
        text = str(query or "").strip()

        if not text:

            raise ProjectError("Search query cannot be empty.")

        if len(text) > 500:

            raise ProjectError("Script search is limited to 500 characters.")

        terms = script_query_terms(text)

        if not terms:

            raise ProjectError(
                "Search query must include a script or behavior term."
            )

        pattern_terms = []

        for term in sorted(terms, key=len, reverse=True):

            pattern_terms.append(
                r"\bai\b"
                if term == "ai"
                else re.escape(term)
            )

        matcher = re.compile(
            "|".join(f"(?:{term})" for term in pattern_terms),
            re.IGNORECASE
        )
        cache_key = (project_id, tuple(sorted(terms)))
        matches = self._script_find_cache.get(cache_key)

        if matches is None:

            matches = []

            for script in self.store.iter_project_script_sources(project_id):

                path_matches = {
                    match.group(0).casefold()
                    for match in matcher.finditer(
                        _normalize_search_text(
                            f"{script['path']} {script['name']}"
                        )
                    )
                }
                evidence = []
                source_terms = set()

                for line_number, line in enumerate(
                    script["source"].splitlines(),
                    1
                ):

                    line_match_objects = list(
                        matcher.finditer(_normalize_search_text(line))
                    )
                    line_matches = {
                        match.group(0).casefold()
                        for match in line_match_objects
                    }

                    if not line_matches:

                        continue

                    source_terms.update(line_matches)
                    score = len(line_matches)
                    excerpt = line.strip()

                    if len(excerpt) > 160:

                        excerpt = excerpt[:157].rstrip() + "..."

                    evidence.append(
                        (
                            score,
                            line_number,
                            excerpt
                        )
                    )

                if not source_terms and not path_matches:

                    continue

                evidence.sort(
                    key=lambda item: (-item[0], item[1])
                )
                matches.append(
                    {
                        "script_id": script["script_id"],
                        "path": script["path"],
                        "name": script["name"],
                        "class_name": script["class_name"],
                        "matched_terms": sorted(source_terms | path_matches),
                        "source_match_count": len(evidence),
                        "evidence": [
                            {
                                "line": line_number,
                                "text": line
                            }
                            for _, line_number, line in evidence[:2]
                        ],
                        "score": (
                            len(source_terms) * 10
                            + min(len(evidence), 10)
                            + len(path_matches) * 2
                        )
                    }
                )

            matches.sort(
                key=lambda item: (
                    -item["score"],
                    item["path"].casefold()
                )
            )
            if len(self._script_find_cache) >= 12:

                self._script_find_cache.pop(
                    next(iter(self._script_find_cache))
                )

            self._script_find_cache[cache_key] = matches

        safe_offset = max(0, int(offset or 0))
        safe_limit = min(200, max(1, int(limit or 100)))

        return {
            "query": text,
            "expanded_terms": sorted(terms),
            "total": len(matches),
            "offset": safe_offset,
            "scripts": matches[safe_offset:safe_offset + safe_limit],
            "project_script_count": project["script_count"]
        }

    def read_script(
        self,
        project_id,
        script_id,
        start_line=1,
        max_lines=100
    ):

        script = self.script(project_id, script_id)
        lines = script["source"].splitlines()
        start = max(1, int(start_line or 1))
        count = min(200, max(1, int(max_lines or 100)))
        selected = [
            (number, line[:6000])
            for number, line in enumerate(lines, 1)
            if start <= number < start + count
        ]

        if not selected:

            raise ProjectError(
                f"Script line {start} is outside the source file."
            )

        return {
            "script_id": script["script_id"],
            "path": script["path"],
            "class_name": script["class_name"],
            "start_line": selected[0][0],
            "end_line": selected[-1][0],
            "total_lines": len(lines),
            "lines": selected
        }

    def search(self, project_id, query, limit=10):

        project = self._get(project_id)
        text = str(query or "").strip()

        if not text:

            raise ProjectError("Search query cannot be empty.")

        if len(text) > 200:

            raise ProjectError("Search query is limited to 200 characters.")

        max_results = min(30, max(1, int(limit or 10)))
        results = []
        current_script = ""
        needle = text.casefold()

        try:

            with Path(project["parsed_path"]).open(
                "r",
                encoding="utf-8",
                errors="replace"
            ) as stream:

                for line_number, raw_line in enumerate(stream, 1):

                    line = raw_line.rstrip("\r\n")
                    heading = SCRIPT_HEADER.match(line)

                    if heading:

                        current_script = heading.group(1)

                    match_at = line.casefold().find(needle)

                    if match_at < 0:

                        continue

                    start = max(0, match_at - 120)
                    end = min(len(line), match_at + len(text) + 240)
                    snippet = line[start:end]

                    if start:

                        snippet = "..." + snippet

                    if end < len(line):

                        snippet += "..."

                    results.append(
                        {
                            "line": line_number,
                            "path": current_script,
                            "text": snippet
                        }
                    )

                    if len(results) >= max_results:

                        break

        except OSError as error:

            raise ProjectError(
                f"Could not search project index: {error}"
            ) from error

        return results

    def read(self, project_id, start_line=1, max_lines=100):

        project = self._get(project_id)
        start = max(1, int(start_line or 1))
        count = min(200, max(1, int(max_lines or 100)))
        selected = []

        try:

            with Path(project["parsed_path"]).open(
                "r",
                encoding="utf-8",
                errors="replace"
            ) as stream:

                for line_number, raw_line in enumerate(stream, 1):

                    if line_number < start:

                        continue

                    selected.append(
                        (
                            line_number,
                            raw_line.rstrip("\r\n")[:6000]
                        )
                    )

                    if len(selected) >= count:

                        break

        except OSError as error:

            raise ProjectError(
                f"Could not read project index: {error}"
            ) from error

        if not selected:

            raise ProjectError(
                f"Start line {start} is past the end of the project index."
            )

        return selected

    def create_artifact(
        self,
        project_id,
        title,
        language,
        content,
        source_script_id=""
    ):

        self._get(project_id)
        safe_title = str(title or "").strip()[:160]
        source = str(content or "")
        normalized_language = str(language or "luau").lower()

        if not safe_title:

            raise ProjectError("Artifact title cannot be empty.")

        if not source.strip():

            raise ProjectError("Artifact code cannot be empty.")

        if len(source) > MAX_ARTIFACT_CHARS:

            raise ProjectError("Artifact code is limited to 2 million characters.")

        if normalized_language not in LANGUAGE_EXTENSIONS:

            normalized_language = "text"

        artifact = self.store.create_project_artifact(
            project_id,
            safe_title,
            normalized_language,
            source,
            source_script_id
        )

        if artifact is None:

            raise ProjectNotFound("Project script not found.")

        return self.public_artifact(artifact)

    def public_artifact(self, artifact):

        old_lines = (artifact.get("base_content") or "").splitlines()
        new_lines = (artifact.get("content") or "").splitlines()
        source_name = artifact.get("source_path") or "/dev/null"
        diff_lines = list(
            difflib.unified_diff(
                old_lines,
                new_lines,
                fromfile=source_name,
                tofile=artifact["title"],
                lineterm=""
            )
        )
        if len(diff_lines) > 20_000:

            diff_lines = diff_lines[:20_000]
            diff_lines.append("[diff preview truncated; download the full draft]")

        diff = "\n".join(diff_lines)

        if len(diff) > 200_000:

            diff = diff[:200_000] + "\n[diff preview truncated]"

        return {
            "id": artifact["id"],
            "project_id": artifact["project_id"],
            "title": artifact["title"],
            "language": artifact["language"],
            "source_script_id": artifact["source_script_id"],
            "source_path": artifact["source_path"],
            "status": artifact["status"],
            "diff": diff,
            "created_at": artifact["created_at"],
            "updated_at": artifact["updated_at"]
        }

    def artifacts(self, project_id):

        self._get(project_id)
        return [
            self.public_artifact(row)
            for row in self.store.list_project_artifacts(project_id)
        ]

    def decide_artifact(self, project_id, artifact_id, status):

        project = self._get(project_id)
        artifact = self.store.get_project_artifact(project_id, artifact_id)

        if artifact is None:

            raise ProjectNotFound("Project artifact not found.")

        if artifact["status"] != "pending":

            raise ProjectError("This project draft has already been reviewed.")

        if status == "rejected":

            result = self.store.decide_project_artifact(
                project_id,
                artifact_id,
                "rejected"
            )

            if result is None:

                raise ProjectError("This project draft has already been reviewed.")

            return self.public_artifact(result)

        if status != "approved":

            raise ProjectError("Review status must be approved or rejected.")

        extension = LANGUAGE_EXTENSIONS.get(artifact["language"], ".txt")
        output_dir = self._project_dir(project_id) / "artifacts"
        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = output_dir / f"{artifact_id}{extension}"
        temporary_path = output_path.with_suffix(
            output_path.suffix + ".tmp"
        )

        try:

            temporary_path.write_bytes(
                artifact["content"].encode("utf-8")
            )
            os.replace(temporary_path, output_path)
            result = self.store.decide_project_artifact(
                project_id,
                artifact_id,
                "approved",
                str(output_path)
            )

            if result is None:

                output_path.unlink(missing_ok=True)
                raise ProjectError(
                    "This project draft has already been reviewed."
                )

        except OSError as error:

            temporary_path.unlink(missing_ok=True)
            raise ProjectError(
                f"Could not export approved artifact: {error}"
            ) from error

        return self.public_artifact(result)

    def artifact_file(self, project_id, artifact_id):

        self._get(project_id)
        artifact = self.store.get_project_artifact(project_id, artifact_id)

        if artifact is None or artifact["status"] != "approved":

            raise ProjectNotFound("Approved project artifact not found.")

        output_path = Path(artifact["output_path"]).resolve()
        project_dir = self._project_dir(project_id)

        if project_dir not in output_path.parents or not output_path.is_file():

            raise ProjectNotFound("Approved project artifact not found.")

        extension = output_path.suffix
        filename = re.sub(
            r"[^A-Za-z0-9._-]+",
            "_",
            artifact["title"]
        ).strip("._") or "artifact"

        if not filename.lower().endswith(extension.lower()):

            filename += extension

        return output_path, filename

    def delete(self, project_id):

        project_dir = self._project_dir(project_id)

        if self.store.get_project(project_id) is None:

            raise ProjectNotFound("Roblox project not found.")

        self._script_find_cache = {
            key: value
            for key, value in self._script_find_cache.items()
            if key[0] != project_id
        }

        if not self.store.delete_project(project_id):

            raise ProjectNotFound("Roblox project not found.")

        if project_dir.exists():

            shutil.rmtree(project_dir)
