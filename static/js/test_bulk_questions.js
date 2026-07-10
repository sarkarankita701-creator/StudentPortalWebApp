document.addEventListener("DOMContentLoaded", function () {
  var textarea = document.getElementById("questions_json");
  var validateBtn = document.getElementById("validate-questions-btn");
  var validateResult = document.getElementById("validate-questions-result");
  var copyPromptBtn = document.getElementById("copy-questions-prompt-btn");
  if (!textarea) return;

  var PROMPT =
    "Generate multiple-choice questions for a student test as a single JSON object, following this exact " +
    "structure. Return ONLY the JSON, no explanation or markdown code fences.\n\n" +
    '{\n  "questions": [\n' +
    "    {\n" +
    '      "question_text": "...",\n' +
    '      "option_a": "...",\n' +
    '      "option_b": "...",\n' +
    '      "option_c": "...",\n' +
    '      "option_d": "...",\n' +
    '      "correct_option": "a",\n' +
    '      "marks": 1\n' +
    "    }\n" +
    "  ]\n}\n\n" +
    "Rules:\n" +
    "- Each question needs \"question_text\" and all four options (option_a, option_b, option_c, option_d) as non-empty strings.\n" +
    '- "correct_option" must be exactly one of "a", "b", "c", "d" (lowercase), matching the correct option.\n' +
    '- "marks" is optional (a positive integer; defaults to 1 if omitted).\n' +
    "- Include as many questions as needed in the \"questions\" array.\n\n" +
    "Topic / content to cover: [describe the topic and difficulty level you want questions on here]";

  function validateQuestions(text) {
    var data;
    try {
      data = JSON.parse(text);
    } catch (err) {
      return "Invalid JSON: " + err.message;
    }
    if (!data || typeof data !== "object" || !Array.isArray(data.questions)) {
      return 'JSON must be an object with a "questions" array, e.g. {"questions": [...]}.';
    }
    if (data.questions.length === 0) {
      return "At least one question is required.";
    }
    var required = ["question_text", "option_a", "option_b", "option_c", "option_d", "correct_option"];
    for (var i = 0; i < data.questions.length; i++) {
      var q = data.questions[i];
      var n = i + 1;
      if (!q || typeof q !== "object") {
        return "Question " + n + " must be an object.";
      }
      for (var j = 0; j < required.length; j++) {
        var key = required[j];
        if (typeof q[key] !== "string" || !q[key].trim()) {
          return 'Question ' + n + ' needs non-empty "' + key + '".';
        }
      }
      if (["a", "b", "c", "d"].indexOf(String(q.correct_option).toLowerCase()) === -1) {
        return 'Question ' + n + ' "correct_option" must be one of "a", "b", "c", "d".';
      }
      if ("marks" in q && (typeof q.marks !== "number" || q.marks <= 0 || Math.floor(q.marks) !== q.marks)) {
        return 'Question ' + n + ' "marks" must be a positive integer.';
      }
    }
    return null;
  }

  if (validateBtn) {
    validateBtn.addEventListener("click", function () {
      var error = validateQuestions(textarea.value.trim());
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
