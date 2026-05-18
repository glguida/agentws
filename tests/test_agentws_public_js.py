# SPDX-License-Identifier: MIT

import json
import subprocess
import textwrap
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


class AgentwsPublicJsTest(unittest.TestCase):
    def run_node(self, script):
        result = subprocess.run(
            ["node", "-e", script],
            cwd=REPO_ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        if result.returncode != 0:
            self.fail(result.stderr or result.stdout)
        return result.stdout

    def test_chat_parser_keeps_markdown_h3_inside_assistant_message(self):
        transcript = textwrap.dedent(
            """
            ### Assistant

            # Document

            ### Details

            Body text

            [2026-05-18T10:00:00Z] codex turn completed
            """
        )
        script = JS_HARNESS + f"""
        const messages = parseTranscriptMessages({json.dumps(transcript)});
        assert(messages.length === 1, `expected one message, got ${{messages.length}}`);
        assert(messages[0].role === "assistant", messages[0].role);
        assert(messages[0].text.includes("### Details"), messages[0].text);
        """
        self.run_node(script)

    def test_chat_render_uses_signature_not_full_text_attribute(self):
        script = JS_HARNESS + """
        const html = renderChatMessage({ role: "assistant", title: "Assistant", text: "Hello" }, "0:assistant:Assistant");
        assert(html.includes("data-chat-sig="), html);
        assert(!html.includes("data-chat-text="), html);
        """
        self.run_node(script)


JS_HARNESS = r"""
const fs = require("fs");
const vm = require("vm");

function assert(condition, message) {
  if (!condition) throw new Error(message || "assertion failed");
}

function element() {
  return {
    addEventListener() {},
    classList: { add() {}, remove() {}, toggle() {} },
    closest() { return element(); },
    dataset: {},
    disabled: false,
    hidden: false,
    innerHTML: "",
    querySelector() { return null; },
    querySelectorAll() { return []; },
    style: {},
    textContent: "",
    title: ""
  };
}

const document = {
  createElement(name) {
    if (name === "template") {
      return {
        content: { firstElementChild: element() },
        set innerHTML(_value) {}
      };
    }
    return element();
  },
  querySelector() { return element(); },
  querySelectorAll() { return []; }
};

const context = {
  Array,
  Boolean,
  Date,
  Error,
  Map,
  Math,
  Number,
  RegExp,
  Set,
  String,
  clearInterval() {},
  clearTimeout() {},
  console,
  document,
  encodeURIComponent,
  fetch: async () => ({ ok: false, json: async () => ({ error: "stubbed" }) }),
  history: { replaceState() {} },
  location: { hash: "" },
  setInterval() { return 0; },
  setTimeout() { return 0; },
  window: { addEventListener() {} }
};

vm.createContext(context);
vm.runInContext(fs.readFileSync("template/tools/agentws-public/app.js", "utf8"), context);
const {
  parseTranscriptMessages,
  renderChatMessage
} = context;
"""


if __name__ == "__main__":
    unittest.main()
