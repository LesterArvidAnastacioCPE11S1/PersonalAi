import base64
import unittest

from io import BytesIO
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest.mock import patch

from docx import Document
from PIL import Image

from core.store import Store
from features.attachments import AttachmentService
from features.image_ocr import ImageOCRError
from models.openai_compat import OpenAICompatibleModel
from config import ToolsConfig
from features.tools.executor import run_tool


class AttachmentTests(unittest.TestCase):

    def setUp(self):
        self.temp = TemporaryDirectory()
        db_path = Path(self.temp.name) / "test.db"
        self.store = Store(db_path)
        self.conversation = self.store.create_conversation()
        config = SimpleNamespace(
            app=SimpleNamespace(db_path=str(db_path))
        )
        self.attachments = AttachmentService(config, self.store)

    def tearDown(self):
        self.temp.cleanup()

    def test_roblox_xml_source_is_searchable_on_demand(self):
        source = "x\n" * 50_050 + 'print("loaded")'
        data = (
            '<roblox version="4"><Item class="Script" referent="RBX0">'
            '<Properties><string name="Name">Main</string>'
            f'<ProtectedString name="Source">{source}</ProtectedString>'
            '<string name="Description">A property for hierarchy</string>'
            '</Properties></Item></roblox>'
        ).encode("utf-8")

        row, warning = self.attachments.save(
            self.conversation["id"],
            "place.rbxlx",
            data
        )

        self.assertIsNone(warning)
        self.assertEqual(row["kind"], "roblox")
        self.assertNotIn('print("loaded")', row["text"])
        prompt = self.attachments.prompt_text([row])
        self.assertIn(row["id"], prompt)
        self.assertNotIn('print("loaded")', prompt)

        result = run_tool(
            "attachments_search",
            {
                "query": 'print("loaded")',
                "attachment_id": row["id"]
            },
            ToolsConfig(),
            None,
            attachment_rows=[row]
        )
        self.assertTrue(result["ok"], result["error"])
        self.assertIn('print("loaded")', result["output"])

        result = run_tool(
            "attachments_search",
            {
                "query": "property for hierarchy",
                "attachment_id": row["id"]
            },
            ToolsConfig(),
            None,
            attachment_rows=[row]
        )
        self.assertTrue(result["ok"], result["error"])
        self.assertIn("Description", result["output"])

        result = run_tool(
            "attachments_read",
            {
                "attachment_id": row["id"],
                "start_line": 50_057,
                "max_lines": 1
            },
            ToolsConfig(),
            None,
            attachment_rows=[row]
        )
        self.assertTrue(result["ok"], result["error"])
        self.assertIn('print("loaded")', result["output"])

    def test_docx_table_text_is_extracted(self):
        buffer = BytesIO()
        document = Document()
        table = document.add_table(rows=1, cols=2)
        table.cell(0, 0).text = "Student"
        table.cell(0, 1).text = "Ada"
        document.save(buffer)

        row, warning = self.attachments.save(
            self.conversation["id"],
            "table.docx",
            buffer.getvalue()
        )

        self.assertIsNone(warning)
        self.assertIn("Student\tAda", row["text"])

    def test_image_ocr_is_saved_and_searchable(self):
        buffer = BytesIO()
        Image.new("RGB", (8, 8), color=(30, 100, 220)).save(
            buffer,
            format="PNG"
        )

        with patch(
            "features.attachments.extract_image_text",
            return_value="No Files were Selected"
        ):
            row, warning = self.attachments.save(
                self.conversation["id"],
                "upload-error.png",
                buffer.getvalue()
            )

        self.assertIsNone(warning)
        self.assertEqual(row["text"], "No Files were Selected")
        self.assertIn(
            "No Files were Selected",
            self.attachments.prompt_text([row])
        )
        self.assertIn(
            "No Files were Selected",
            self.attachments.image_ocr_text([row])
        )

        result = run_tool(
            "attachments_search",
            {
                "query": "No Files were Selected",
                "attachment_id": row["id"]
            },
            ToolsConfig(),
            None,
            attachment_rows=[row]
        )
        self.assertTrue(result["ok"], result["error"])
        self.assertIn("No Files were Selected", result["output"])

    def test_image_ocr_failure_is_reported_without_rejecting_upload(self):
        buffer = BytesIO()
        Image.new("RGB", (8, 8), color=(30, 100, 220)).save(
            buffer,
            format="PNG"
        )

        with patch(
            "features.attachments.extract_image_text",
            side_effect=ImageOCRError("OCR engine unavailable")
        ):
            row, warning = self.attachments.save(
                self.conversation["id"],
                "image.png",
                buffer.getvalue()
            )

        self.assertEqual(row["kind"], "image")
        self.assertEqual(row["text"], "")
        self.assertIn("OCR engine unavailable", warning)

    def test_supported_images_are_sent_as_vision_inputs(self):
        rows = []
        formats = (
            ("PNG", ".png"),
            ("JPEG", ".jpg"),
            ("WEBP", ".webp"),
            ("GIF", ".gif"),
            ("BMP", ".bmp")
        )

        with patch("features.attachments.extract_image_text", return_value=""):
            for image_format, extension in formats:
                buffer = BytesIO()
                Image.new("RGB", (8, 8), color=(30, 100, 220)).save(
                    buffer,
                    format=image_format
                )
                row, _ = self.attachments.save(
                    self.conversation["id"],
                    f"image{extension}",
                    buffer.getvalue()
                )
                rows.append(row)

        data_urls = self.attachments.image_data_urls(rows)

        self.assertEqual(len(data_urls), len(formats))
        self.assertTrue(all(url.startswith("data:image/") for url in data_urls))
        self.assertTrue(data_urls[3].startswith("data:image/png;base64,"))
        self.assertTrue(data_urls[4].startswith("data:image/png;base64,"))
        self.assertTrue(base64.b64decode(data_urls[0].split(",", 1)[1]))

        config = SimpleNamespace(
            model="default",
            vision=True,
            vision_model="moondream",
            big_context_model="",
            auto_big_context=False,
            temperature=0.2,
            top_p=1.0,
            max_tokens=500,
            stream=False
        )
        model = OpenAICompatibleModel(config)
        messages = [{
            "role": "user",
            "content": [
                {"type": "text", "text": "Describe this."},
                {
                    "type": "image_url",
                    "image_url": {"url": data_urls[0]}
                }
            ]
        }]

        self.assertEqual(
            model._payload(messages, False, None, None)["model"],
            "moondream"
        )

        with patch.object(
            model,
            "complete",
            return_value="Repeated numbering"
        ) as complete:
            result = model.analyze_images(
                data_urls[:1],
                "Why is the numbering repeated?",
                "1. First item\n1. Second item"
            )

        self.assertEqual(result, "Repeated numbering")
        analysis_messages = complete.call_args.args[0]
        analysis_text = analysis_messages[0]["content"][0]["text"]
        self.assertIn("1. First item", analysis_text)
        self.assertIn("Do not transcribe or paraphrase text or numbers", analysis_text)
        self.assertEqual(
            model._model_id(analysis_messages),
            "moondream"
        )

        final_messages = [{
            "role": "user",
            "content": (
                "Review this Luau code. [Attached files] "
                "No Files were Selected"
            )
        }]
        config.big_context_model = "personalai:bigctx"
        config.auto_big_context = True
        self.assertEqual(
            model._model_id(final_messages),
            "personalai:bigctx"
        )

    def test_vision_input_does_not_route_to_text_only_big_context_model(self):
        config = SimpleNamespace(
            model="personalai:main",
            vision=True,
            vision_model="",
            big_context_model="personalai:bigctx",
            auto_big_context=True,
            temperature=0.2,
            top_p=1.0,
            max_tokens=500,
            stream=False
        )
        model = OpenAICompatibleModel(config)
        messages = [{
            "role": "user",
            "content": [
                {"type": "text", "text": "Analyze this Roblox screenshot."},
                {
                    "type": "image_url",
                    "image_url": {"url": "data:image/png;base64,AA=="}
                }
            ]
        }]

        self.assertEqual(model._model_id(messages), "personalai:main")

    def test_dotfile_extensions_are_recognized(self):
        self.assertEqual(self.attachments._ext(".env"), ".env")
        self.assertEqual(self.attachments._ext(".gitignore"), ".gitignore")
        self.assertEqual(self.attachments._ext("Dockerfile"), ".dockerfile")


if __name__ == "__main__":
    unittest.main()
