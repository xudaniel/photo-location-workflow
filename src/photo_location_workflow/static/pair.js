const form = document.querySelector("#pair-form");
const message = document.querySelector("#pair-message");
const fragment = new URLSearchParams(location.hash.slice(1));
const auto = fragment.has("admin")
  ? { admin: fragment.get("admin") }
  : fragment.has("pair")
    ? { pair: fragment.get("pair") }
    : null;
// Pairing secrets stay out of request URLs, referrers and subsequent history.
history.replaceState(null, "", location.pathname);
async function connect(body) {
  form.querySelector("button").disabled = true;
  message.textContent = "正在连接 / Connecting…";
  try {
    const response = await fetch("/api/pair", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    const result = await response.json();
    if (!response.ok)
      throw new Error(result.error || "连接失败 / Connection failed");
    location.replace("/");
  } catch (error) {
    message.textContent = error.message;
    form.querySelector("button").disabled = false;
  }
}
form.addEventListener("submit", (event) => {
  event.preventDefault();
  connect({ code: form.elements.code.value.trim() });
});
if (auto) connect(auto);
