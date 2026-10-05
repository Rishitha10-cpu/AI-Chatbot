const chatForm = document.getElementById("chat-form");
const messageInput = document.getElementById("message");
const chatBox = document.getElementById("chat-box");
const sendButton = chatForm.querySelector("button");
const botAvatar = "/static/images/robot.png";
function addMessage(text, sender) {
    const row = document.createElement("div");
    row.className = "message " + sender;
    if (sender === "bot") {
        const avatar = document.createElement("img");
        avatar.className = "avatar";
        avatar.src = botAvatar;
        avatar.alt = "Bot";
        row.appendChild(avatar);
    }
    const bubble = document.createElement("div");
    bubble.className = "bubble";
    bubble.textContent = text;
    row.appendChild(bubble);
    chatBox.appendChild(row);
    chatBox.scrollTop = chatBox.scrollHeight;
    return row;
}
function addTyping() {
    const row = document.createElement("div");
    row.className = "message bot";
    row.innerHTML =
        '<img class="avatar" src="' + botAvatar + '" alt="Bot">' +
        '<div class="bubble typing"><span></span><span></span><span></span></div>';
    chatBox.appendChild(row);
    chatBox.scrollTop = chatBox.scrollHeight;
    return row;
}
chatForm.addEventListener("submit", async function (event) {
    event.preventDefault();
    const message = messageInput.value.trim();
    if (message === "") {
        return;
    }
    addMessage(message, "user");
    messageInput.value = "";
    sendButton.disabled = true;
    const typing = addTyping();
    try {
        const response = await fetch("/chat", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({
                message: message
            })
        });
        const data = await response.json();
        typing.remove();
        addMessage(data.response, "bot");
    } catch (error) {
        typing.remove();
        addMessage("Something went wrong. Please try again.", "bot");
        console.error(error);
    }
    sendButton.disabled = false;
    messageInput.focus();
});
messageInput.focus();
chatBox.scrollTop = chatBox.scrollHeight;
