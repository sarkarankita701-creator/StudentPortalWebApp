document.addEventListener("DOMContentLoaded", function () {
  var dataEl = document.getElementById("game-items-data");
  var stage = document.getElementById("game-stage");
  if (!dataEl || !stage) return;

  var items = JSON.parse(dataEl.textContent || "[]");
  var progressFill = document.getElementById("game-progress-fill");
  var progressLabel = document.getElementById("game-progress-label");
  var scoreScreen = document.getElementById("game-score-screen");
  var finalScoreEl = document.getElementById("game-final-score");
  var completeScoreInput = document.getElementById("complete-score");
  var completeTotalInput = document.getElementById("complete-total");

  var totalPoints = items.reduce(function (sum, item) { return sum + (item.points || 1); }, 0);
  var index = 0;
  var score = 0;

  function el(tag, className, text) {
    var node = document.createElement(tag);
    if (className) node.className = className;
    if (text !== undefined) node.textContent = text;
    return node;
  }

  function updateProgress() {
    var pct = items.length ? Math.round((index / items.length) * 100) : 0;
    progressFill.style.width = pct + "%";
    progressLabel.textContent = "Item " + Math.min(index + 1, items.length) + " of " + items.length;
  }

  function addContinueButton(onCorrect) {
    var continueBtn = el("button", "btn", "Continue");
    continueBtn.type = "button";
    continueBtn.style.marginTop = "0.8rem";
    continueBtn.addEventListener("click", function () { next(onCorrect); });
    stage.appendChild(continueBtn);
  }

  function finish() {
    stage.style.display = "none";
    progressFill.style.width = "100%";
    progressLabel.textContent = "Finished — " + items.length + " of " + items.length;
    finalScoreEl.textContent = score + " / " + totalPoints;
    completeScoreInput.value = score;
    completeTotalInput.value = totalPoints;
    scoreScreen.style.display = "";
  }

  function next(wasCorrect) {
    if (wasCorrect) score += (items[index].points || 1);
    index += 1;
    if (index >= items.length) {
      finish();
    } else {
      renderItem();
    }
  }

  function renderFlashcard(item) {
    stage.innerHTML = "";
    stage.appendChild(el("h3", "", item.front));
    var back = el("p", "page-sub", item.back);
    back.style.display = "none";
    stage.appendChild(back);

    var revealBtn = el("button", "btn secondary", "Reveal Answer");
    revealBtn.type = "button";
    stage.appendChild(revealBtn);

    var feedbackRow = el("div", "");
    feedbackRow.style.marginTop = "0.8rem";
    feedbackRow.style.display = "none";
    var gotItBtn = el("button", "btn small", "I knew it");
    gotItBtn.type = "button";
    var missedBtn = el("button", "btn small danger", "I missed it");
    missedBtn.type = "button";
    missedBtn.style.marginLeft = "0.5rem";
    feedbackRow.appendChild(gotItBtn);
    feedbackRow.appendChild(missedBtn);
    stage.appendChild(feedbackRow);

    revealBtn.addEventListener("click", function () {
      back.style.display = "";
      revealBtn.style.display = "none";
      feedbackRow.style.display = "";
    });
    gotItBtn.addEventListener("click", function () { next(true); });
    missedBtn.addEventListener("click", function () { next(false); });
  }

  function renderMcq(item) {
    stage.innerHTML = "";
    stage.appendChild(el("h3", "", item.question));
    var answered = false;

    item.options.forEach(function (option, i) {
      var label = el("label", "option-label");
      var input = document.createElement("input");
      input.type = "radio";
      input.name = "mcq-option";
      label.appendChild(input);
      label.appendChild(document.createTextNode(" " + option));
      stage.appendChild(label);

      input.addEventListener("change", function () {
        if (answered) return;
        answered = true;
        var correct = i === item.correct_index;
        label.style.borderColor = "var(--red-fg)";
        label.style.background = "var(--red-bg)";
        if (correct) {
          label.style.borderColor = "var(--green-fg)";
          label.style.background = "var(--green-bg)";
        } else {
          var labels = stage.querySelectorAll(".option-label");
          labels[item.correct_index].style.borderColor = "var(--green-fg)";
          labels[item.correct_index].style.background = "var(--green-bg)";
        }
        if (item.explanation) {
          stage.appendChild(el("p", "page-sub", item.explanation));
        }
        addContinueButton(correct);
      });
    });
  }

  function renderTrueFalse(item) {
    stage.innerHTML = "";
    stage.appendChild(el("h3", "", item.statement));
    var answered = false;
    var row = el("div", "");
    var trueBtn = el("button", "btn secondary", "True");
    var falseBtn = el("button", "btn secondary", "False");
    trueBtn.type = "button";
    falseBtn.type = "button";
    falseBtn.style.marginLeft = "0.5rem";
    row.appendChild(trueBtn);
    row.appendChild(falseBtn);
    stage.appendChild(row);

    function answer(choice, btn) {
      if (answered) return;
      answered = true;
      var correct = choice === item.answer;
      btn.style.borderColor = correct ? "var(--green-fg)" : "var(--red-fg)";
      btn.style.background = correct ? "var(--green-bg)" : "var(--red-bg)";
      addContinueButton(correct);
    }

    trueBtn.addEventListener("click", function () { answer(true, trueBtn); });
    falseBtn.addEventListener("click", function () { answer(false, falseBtn); });
  }

  function renderFillBlank(item) {
    stage.innerHTML = "";
    stage.appendChild(el("h3", "", item.text));
    var input = document.createElement("input");
    input.type = "text";
    input.placeholder = "Your answer";
    stage.appendChild(input);
    var submitBtn = el("button", "btn", "Submit");
    submitBtn.type = "button";
    submitBtn.style.marginLeft = "0.5rem";
    stage.appendChild(submitBtn);

    var answered = false;
    submitBtn.addEventListener("click", function () {
      if (answered) return;
      answered = true;
      var given = input.value.trim().toLowerCase();
      var accepted = [item.answer].concat(item.accepted_answers || []).map(function (a) { return a.toLowerCase(); });
      var correct = accepted.indexOf(given) !== -1;
      input.disabled = true;
      submitBtn.disabled = true;
      var feedback = el("p", correct ? "validate-ok" : "validate-error",
        correct ? "✓ Correct!" : ("✗ Correct answer: " + item.answer));
      stage.appendChild(feedback);
      addContinueButton(correct);
    });
  }

  function renderItem() {
    updateProgress();
    var item = items[index];
    if (item.type === "flashcard") renderFlashcard(item);
    else if (item.type === "mcq") renderMcq(item);
    else if (item.type === "true_false") renderTrueFalse(item);
    else if (item.type === "fill_blank") renderFillBlank(item);
  }

  if (items.length === 0) {
    stage.innerHTML = "<p>This game has no items yet.</p>";
  } else {
    renderItem();
  }
});
