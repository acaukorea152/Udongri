(() => {
  if ("serviceWorker" in navigator) {
    window.addEventListener("load", () => {
      navigator.serviceWorker.register("/service-worker.js", { scope: "/" }).catch((error) => {
        console.error("서비스 워커 등록 실패:", error);
      });
    });
  }

  const prompt = document.getElementById("install-prompt");
  if (!prompt) return;
  const dismissed = localStorage.getItem("udongri-install-dismissed") === "1";
  const installed = window.matchMedia("(display-mode: standalone)").matches || window.navigator.standalone;
  if (dismissed || installed) return;

  const installButton = document.getElementById("install-button");
  const help = document.getElementById("install-help");
  const isIOS = /iphone|ipad|ipod/i.test(navigator.userAgent);
  let installEvent;

  window.addEventListener("beforeinstallprompt", (event) => {
    event.preventDefault();
    installEvent = event;
    installButton.hidden = false;
  });

  if (isIOS) help.textContent = "Safari의 공유 버튼을 누른 뒤 ‘홈 화면에 추가’를 선택하세요.";
  prompt.hidden = false;

  installButton.addEventListener("click", async () => {
    if (!installEvent) return;
    installEvent.prompt();
    await installEvent.userChoice;
    installEvent = null;
    prompt.hidden = true;
  });

  document.getElementById("install-dismiss").addEventListener("click", () => {
    localStorage.setItem("udongri-install-dismissed", "1");
    prompt.hidden = true;
  });

  window.addEventListener("appinstalled", () => { prompt.hidden = true; });
})();
