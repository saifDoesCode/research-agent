let reportMarkdown = "";

function toggleSidebar() {
    document.getElementById('sidebar').classList.toggle('open');
    document.getElementById('overlay').classList.toggle('open');
}

function handleKeyDown(e) {
    if (e.key === 'Enter') startResearch();
}

async function startResearch() {
    const topic = document.getElementById("topic-input").value.trim();
    const anthropicKey = document.getElementById("anthropic-key").value.trim();
    const tavilyKey = document.getElementById("tavily-key").value.trim();

    if (!topic) return;

    reportMarkdown = "";
    document.getElementById("progress-log").innerHTML = "";
    document.getElementById("report-output").innerHTML = "";
    document.getElementById("progress-card").style.display = "block";
    document.getElementById("report-card").style.display = "none";

    const input = document.getElementById("topic-input");
    input.disabled = true;
    input.placeholder = "Researching…";

    try {
        const response = await fetch("/research", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                topic,
                anthropic_key: anthropicKey,
                tavily_key: tavilyKey
            })
        });

        const reader = response.body.getReader();
        const decoder = new TextDecoder();

        while (true) {
            const { done, value } = await reader.read();
            if (done) break;

            const chunk = decoder.decode(value);
            for (const line of chunk.split("\n")) {
                if (!line.startsWith("data: ")) continue;
                const json = line.slice(6).trim();
                if (!json) continue;
                try { handleEvent(JSON.parse(json)); } catch { /* partial chunk */ }
            }
        }

    } catch (err) {
        addProgressItem(`❌ Error: ${err.message}`);
    } finally {
        input.disabled = false;
        input.placeholder = "Topic You Want To Research";
    }
}

function handleEvent(event) {
    if (event.type === "status")  addProgressItem(event.message);
    if (event.type === "report")  { reportMarkdown = event.content; displayReport(event.content); }
    if (event.type === "error")   addProgressItem(`❌ ${event.message}`);
}

function addProgressItem(message) {
    const log = document.getElementById("progress-log");
    const item = document.createElement("div");
    item.className = "progress-item";
    item.textContent = message;
    log.appendChild(item);
    item.scrollIntoView({ behavior: "smooth" });
}

function displayReport(markdown) {
    document.getElementById("report-card").style.display = "block";
    document.getElementById("report-output").innerHTML = renderMarkdown(markdown);
    document.getElementById("report-card").scrollIntoView({ behavior: "smooth" });
}

function renderMarkdown(text) {
    return text
        .replace(/^# (.+)$/gm,    "<h1>$1</h1>")
        .replace(/^## (.+)$/gm,   "<h2>$1</h2>")
        .replace(/^### (.+)$/gm,  "<h3>$1</h3>")
        .replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>")
        .replace(/\*(.+?)\*/g,    "<em>$1</em>")
        .replace(/^- (.+)$/gm,    "<li>$1</li>")
        .replace(/(<li>.*<\/li>)/s, "<ul>$1</ul>")
        .replace(/\[(.+?)\]\((.+?)\)/g, '<a href="$2" target="_blank">$1</a>')
        .replace(/^---$/gm,       "<hr>")
        .replace(/\n\n/g,         "</p><p>")
        .replace(/^(?!<[hup])/gm, "<p>");
}

function downloadReport() {
    if (!reportMarkdown) return;
    const topic = document.getElementById("topic-input").value.trim();
    const filename = topic.toLowerCase().replace(/\s+/g, "_") + "_report.md";
    const blob = new Blob([reportMarkdown], { type: "text/markdown" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = filename;
    a.click();
    URL.revokeObjectURL(url);
}
