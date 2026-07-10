document.addEventListener("DOMContentLoaded", function () {
  var textarea = document.getElementById("items_json");
  var validateBtn = document.getElementById("validate-items-btn");
  var validateResult = document.getElementById("validate-items-result");
  var copyPromptBtn = document.getElementById("copy-items-prompt-btn");
  if (!textarea) return;

  var PROMPT =
    "Generate revision game items for a student as a single JSON object, following this exact structure. " +
    "Return ONLY the JSON, no explanation or markdown code fences.\n\n" +
    '{\n  "items": [\n' +
    '    { "type": "flashcard", "front": "...", "back": "..." },\n' +
    '    { "type": "mcq", "question": "...", "options": ["...", "...", "..."], "correct_index": 0, "explanation": "..." },\n' +
    '    { "type": "true_false", "statement": "...", "answer": true },\n' +
    '    { "type": "fill_blank", "text": "...", "answer": "...", "accepted_answers": ["..."] }\n' +
    "  ]\n}\n\n" +
    "Rules:\n" +
    '- "type" must be one of: flashcard, mcq, true_false, fill_blank.\n' +
    '- flashcard: "front" and "back" are both required non-empty strings.\n' +
    '- mcq: "options" is an array of at least 2 non-empty strings; "correct_index" is the 0-based index of the correct option; "explanation" is optional.\n' +
    '- true_false: "answer" must be the boolean true or false (not a string).\n' +
    '- fill_blank: "answer" is the expected response; "accepted_answers" is an optional array of alternate acceptable answers.\n' +
    '- Every item may optionally include "points" (a positive integer, defaults to 1).\n' +
    "- Mix item types as you see fit for the topic below — you don't need to use all of them.\n\n" +
    "Topic / content to cover: [describe the topic and difficulty level you want items on here]";

  var ALLOWED_ITEM_TYPES = ["flashcard", "mcq", "true_false", "fill_blank"];

  function validateItems(text) {
    var data;
    try {
      data = JSON.parse(text);
    } catch (err) {
      return "Invalid JSON: " + err.message;
    }
    if (!data || typeof data !== "object" || !Array.isArray(data.items)) {
      return 'JSON must be an object with an "items" array, e.g. {"items": [...]}.';
    }
    if (data.items.length === 0) {
      return "At least one item is required.";
    }
    for (var i = 0; i < data.items.length; i++) {
      var item = data.items[i];
      var n = i + 1;
      if (!item || typeof item !== "object" || !item.type) {
        return "Item " + n + " is missing a \"type\".";
      }
      if (ALLOWED_ITEM_TYPES.indexOf(item.type) === -1) {
        return "Item " + n + ' has unknown type "' + item.type + '".';
      }
      if ("points" in item && (typeof item.points !== "number" || item.points <= 0 || Math.floor(item.points) !== item.points)) {
        return 'Item ' + n + ' "points" must be a positive integer.';
      }
      switch (item.type) {
        case "flashcard":
          if (typeof item.front !== "string" || !item.front.trim() || typeof item.back !== "string" || !item.back.trim()) {
            return "Item " + n + ' (flashcard) needs non-empty "front" and "back".';
          }
          break;
        case "mcq":
          if (typeof item.question !== "string" || !item.question.trim()) {
            return "Item " + n + ' (mcq) needs a non-empty "question".';
          }
          if (!Array.isArray(item.options) || item.options.length < 2) {
            return "Item " + n + ' (mcq) needs an "options" array with at least 2 entries.';
          }
          if (!item.options.every(function (o) { return typeof o === "string" && o.trim(); })) {
            return "Item " + n + " (mcq) options must all be non-empty strings.";
          }
          if (typeof item.correct_index !== "number" || item.correct_index < 0 || item.correct_index >= item.options.length) {
            return "Item " + n + ' (mcq) "correct_index" must be a valid index into "options".';
          }
          break;
        case "true_false":
          if (typeof item.statement !== "string" || !item.statement.trim()) {
            return "Item " + n + ' (true_false) needs a non-empty "statement".';
          }
          if (typeof item.answer !== "boolean") {
            return "Item " + n + ' (true_false) "answer" must be true or false.';
          }
          break;
        case "fill_blank":
          if (typeof item.text !== "string" || !item.text.trim()) {
            return "Item " + n + ' (fill_blank) needs a non-empty "text".';
          }
          if (typeof item.answer !== "string" || !item.answer.trim()) {
            return "Item " + n + ' (fill_blank) needs a non-empty "answer".';
          }
          break;
      }
    }
    return null;
  }

  if (validateBtn) {
    validateBtn.addEventListener("click", function () {
      var error = validateItems(textarea.value.trim());
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
      var originalLabel = copyPromptBtn.textContent;
      copyText(PROMPT, function (ok) {
        copyPromptBtn.textContent = ok ? "Copied!" : "Copy failed";
        setTimeout(function () {
          copyPromptBtn.textContent = originalLabel;
        }, 1500);
      });
    });
  }
});
