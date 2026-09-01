// Progressive enhancement only: every action below also works without JS.
document.addEventListener("DOMContentLoaded", () => {
  // Submit a cart quantity change on blur so "Update" is optional.
  document.querySelectorAll(".qty-form input[type=number]").forEach((input) => {
    const initial = input.value;
    input.addEventListener("change", () => {
      if (input.value !== initial) input.form.requestSubmit();
    });
  });

  // Submit enhanced controls immediately while retaining their submit button.
  document.querySelectorAll("[data-auto-submit]").forEach((control) => {
    control.addEventListener("change", () => control.form.requestSubmit());
  });

  // Dismiss flash messages on click.
  document.querySelectorAll(".flash").forEach((flash) => {
    flash.addEventListener("click", () => flash.remove());
  });
});
