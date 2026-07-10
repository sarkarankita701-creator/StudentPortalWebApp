document.addEventListener("DOMContentLoaded", function () {
  var toggle = document.getElementById("content-type-toggle");
  var fieldLink = document.getElementById("field-link");
  var fieldStructured = document.getElementById("field-structured");
  var contentInput = document.getElementById("content_input");
  var hint = document.getElementById("structured-hint");
  var validateBtn = document.getElementById("validate-btn");
  var validateResult = document.getElementById("validate-result");
  var copyPromptBtn = document.getElementById("copy-prompt-btn");
  if (!toggle || !fieldLink || !fieldStructured) return;

  var HINTS = {
    json: 'Paste a JSON object like {"blocks": [{"type": "heading", "text": "..."}, {"type": "paragraph", "text": "..."}]}.',
    html: "Paste HTML (headings, paragraphs, lists, tables, links, images). Scripts and event handlers are stripped when saved.",
  };

  var PROMPTS = {
    json:
      "Generate content for a student notes page as a single JSON object, following this exact structure. " +
      "Return ONLY the JSON, no explanation or markdown code fences.\n\n" +
      '{\n  "blocks": [\n' +
      '    { "type": "heading", "level": 2, "text": "..." },\n' +
      '    { "type": "paragraph", "text": "..." },\n' +
      '    { "type": "list", "style": "bullet", "items": ["...", "..."] },\n' +
      '    { "type": "table", "headers": ["...", "..."], "rows": [["...", "..."]] },\n' +
      '    { "type": "qa", "question": "...", "answer": "..." },\n' +
      '    { "type": "code", "text": "..." },\n' +
      '    { "type": "image", "url": "https://...", "caption": "..." }\n' +
      "  ]\n}\n\n" +
      "Rules:\n" +
      '- "type" must be one of: heading, paragraph, list, table, qa, code, image.\n' +
      '- heading: "text" required, "level" optional (integer 1-4, default 2).\n' +
      '- list: "items" is a non-empty array of strings; "style" is "bullet" or "number".\n' +
      '- table: "headers" and "rows" are non-empty arrays; every row must have the same number of cells as "headers".\n' +
      '- qa: both "question" and "answer" are required.\n' +
      '- image: "url" must start with http:// or https://.\n' +
      "Only include the block types that actually fit the topic below — you don't need to use all of them.\n\n" +
      " ",
    html:
      "Generate content for a student notes page as clean HTML (just the content, no <html>/<head>/<body> wrapper). " +
      "Return ONLY the HTML, no explanation or markdown code fences.\n\n" +
      "Only use these tags: p, br, hr, h1, h2, h3, h4, strong, b, em, i, u, ul, ol, li, table, thead, tbody, tr, th, td, " +
      "blockquote, code, pre, a (with href), img (with src and alt), span, div.\n" +
      "Do not use <script>, inline event handlers (onclick, onload, etc.), <style>, or any tag/attribute not listed above " +
      "— they will be stripped when saved.\n\n" +
      " ",
  };

  function selectedContentType() {
    var checked = toggle.querySelector('input[name="content_type"]:checked');
    return checked ? checked.value : "link";
  }

  function updateVisibility() {
    var type = selectedContentType();
    if (type === "link") {
      fieldLink.style.display = "";
      fieldStructured.style.display = "none";
    } else {
      fieldLink.style.display = "none";
      fieldStructured.style.display = "";
      hint.textContent = HINTS[type] || "";
    }
    validateResult.textContent = "";
    validateResult.className = "";
  }

  toggle.querySelectorAll('input[name="content_type"]').forEach(function (radio) {
    radio.addEventListener("change", updateVisibility);
  });
  updateVisibility();

  var ALLOWED_BLOCK_TYPES = ["heading", "paragraph", "list", "table", "qa", "code", "image"];

  function validateBlocks(text) {
    var data;
    try {
      data = JSON.parse(text);
    } catch (err) {
      return "Invalid JSON: " + err.message;
    }
    if (!data || typeof data !== "object" || !Array.isArray(data.blocks)) {
      return 'JSON must be an object with a "blocks" array, e.g. {"blocks": [...]}.';
    }
    if (data.blocks.length === 0) {
      return "At least one block is required.";
    }
    for (var i = 0; i < data.blocks.length; i++) {
      var block = data.blocks[i];
      var n = i + 1;
      if (!block || typeof block !== "object" || !block.type) {
        return "Block " + n + " is missing a \"type\".";
      }
      if (ALLOWED_BLOCK_TYPES.indexOf(block.type) === -1) {
        return "Block " + n + ' has unknown type "' + block.type + '".';
      }
      switch (block.type) {
        case "heading":
        case "paragraph":
        case "code":
          if (typeof block.text !== "string" || !block.text.trim()) {
            return "Block " + n + " (" + block.type + ') needs non-empty "text".';
          }
          break;
        case "list":
          if (!Array.isArray(block.items) || block.items.length === 0) {
            return "Block " + n + ' (list) needs a non-empty "items" array.';
          }
          break;
        case "table":
          if (!Array.isArray(block.headers) || block.headers.length === 0 || !Array.isArray(block.rows) || block.rows.length === 0) {
            return "Block " + n + ' (table) needs non-empty "headers" and "rows" arrays.';
          }
          break;
        case "qa":
          if (!block.question || !block.answer) {
            return "Block " + n + ' (qa) needs both "question" and "answer".';
          }
          break;
        case "image":
          if (typeof block.url !== "string" || !/^https?:\/\//.test(block.url)) {
            return "Block " + n + ' (image) needs a "url" starting with http:// or https://.';
          }
          break;
      }
    }
    return null;
  }

  function validateHtml(text) {
    if (!text.trim()) return "Paste some HTML content first.";
    var doc = new DOMParser().parseFromString(text, "text/html");
    if (doc.querySelector("parsererror")) {
      return "That doesn't look like valid HTML.";
    }
    if (/<script[\s>]/i.test(text)) {
      return "Note: <script> tags will be removed when this is saved (not allowed in notes).";
    }
    return null;
  }

  if (validateBtn) {
    validateBtn.addEventListener("click", function () {
      var type = selectedContentType();
      var text = contentInput.value.trim();
      var error = type === "html" ? validateHtml(text) : validateBlocks(text);
      if (error) {
        validateResult.textContent = "✗ " + error;
        validateResult.className = "validate-error";
      } else {
        validateResult.textContent = "✓ Looks good.";
        validateResult.className = "validate-ok";
      }
    });
  }

  function copyText(text, onDone) {
    if (navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard.writeText(text).then(
        function () { onDone(true); },
        function () { onDone(false); }
      );
      return;
    }
    var ta = document.createElement("textarea");
    ta.value = text;
    ta.style.position = "fixed";
    ta.style.opacity = "0";
    document.body.appendChild(ta);
    ta.focus();
    ta.select();
    var ok = false;
    try {
      ok = document.execCommand("copy");
    } catch (err) {
      ok = false;
    }
    document.body.removeChild(ta);
    onDone(ok);
  }

  if (copyPromptBtn) {
    copyPromptBtn.addEventListener("click", function () {
      var type = selectedContentType();
      var prompt = PROMPTS[type] || PROMPTS.json;
      var originalLabel = copyPromptBtn.textContent;
      copyText(prompt, function (ok) {
        copyPromptBtn.textContent = ok ? "Copied!" : "Copy failed";
        setTimeout(function () {
          copyPromptBtn.textContent = originalLabel;
        }, 1500);
      });
    });
  }
});
