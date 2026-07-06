function initTestTimer(remainingSeconds, formId, displayId) {
  var display = document.getElementById(displayId);
  var form = document.getElementById(formId);
  var submitted = false;

  function render(seconds) {
    var m = Math.floor(seconds / 60);
    var s = seconds % 60;
    display.textContent = "Time remaining: " + m + ":" + (s < 10 ? "0" : "") + s;
  }

  render(remainingSeconds);

  var timer = setInterval(function () {
    remainingSeconds -= 1;
    if (remainingSeconds <= 0) {
      clearInterval(timer);
      render(0);
      if (!submitted) {
        submitted = true;
        form.submit();
      }
      return;
    }
    render(remainingSeconds);
  }, 1000);

  form.addEventListener("submit", function () {
    submitted = true;
    clearInterval(timer);
  });
}
