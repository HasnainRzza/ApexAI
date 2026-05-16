const ws = new WebSocket("ws://127.0.0.1:8765");

ws.onopen = () => {
    console.log("Connected to Proctoring Server");
};

ws.onclose = () => {
    console.log("Disconnected from Proctoring Server. Attempting to reconnect...");
    // Simple reconnect logic
    setTimeout(() => {
        window.location.reload();
    }, 5000);
};

function sendEvent(eventType) {
    if (ws.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify({ type: eventType, timestamp: Date.now() }));
        console.log(`Sent: ${eventType}`);
    }
}

window.addEventListener("blur", () => sendEvent("blur"));
window.addEventListener("focus", () => sendEvent("focus"));

document.addEventListener("visibilitychange", () => {
    if (document.visibilityState === "hidden") {
        sendEvent("hidden");
    } else {
        sendEvent("visible");
    }
});

document.addEventListener("fullscreenchange", () => {
    if (!document.fullscreenElement) {
        sendEvent("fullscreen_exit");
    } else {
        sendEvent("fullscreen_enter");
    }
});
