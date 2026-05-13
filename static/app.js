let reportMarkdown = "";

// Scale the title to span the full page width
function fitTitle() {
    const title = document.querySelector('.site-title');
    if (!title) return;
    title.style.fontSize = '10px';
    let size = 10;
    while (title.scrollWidth <= title.clientWidth && size < 600) {
        size++;
        title.style.fontSize = size + 'px';
    }
    title.style.fontSize = Math.max(10, size - 1) + 'px';
}

function toggleConfig() {
    const panel = document.getElementById('config-panel');
    const toggle = document.getElementById('config-toggle');
    panel.classList.toggle('hidden');
    toggle.classList.toggle('collapsed');
}

async function startResearch() {
    const topic = document.getElementById("topic-input").value.trim();
    const anthropicKey = document.getElementById("anthropic-key").value.trim();
    const tavily_key = document.getElementById("tavily-key").value.trim();

    if (!topic) {
        alert("Please enter a research topic.");
        return;
    }

    reportMarkdown = "";
    document.getElementById("progress-log").innerHTML = "";
    document.getElementById("report-output").innerHTML = "";
    document.getElementById("progress-card").style.display = "block";
    document.getElementById("report-card").style.display = "none";
    document.getElementById("research-btn").disabled = true;
    document.getElementById("research-btn").textContent = "Researching...";

    try {
        const response = await fetch("/research", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                topic: topic,
                anthropic_key: anthropicKey,
                tavily_key: tavily_key
            })
        });

        const reader = response.body.getReader();
        const decoder = new TextDecoder();

        while (true) {
            const { done, value } = await reader.read();
            if (done) break;

            const chunk = decoder.decode(value);
            const lines = chunk.split("\n");

            for (const line of lines) {
                if (!line.startsWith("data: ")) continue;

                const jsonString = line.replace("data: ", "");
                if (!jsonString.trim()) continue;

                try {
                    const event = JSON.parse(jsonString);
                    handleEvent(event);
                } catch {
                    // incomplete chunk, skip
                }
            }
        }

    } catch (error) {
        addProgressItem(`❌ Error: ${error.message}`);
    } finally {
        document.getElementById("research-btn").disabled = false;
        document.getElementById("research-btn").textContent = "Start Research";
    }
}

function handleEvent(event) {
    if (event.type === "status") {
        addProgressItem(event.message);
    }

    if (event.type === "report") {
        reportMarkdown = event.content;
        displayReport(event.content);
    }

    if (event.type === "error") {
        addProgressItem(`❌ ${event.message}`);
    }
}

function addProgressItem(message) {
    const progressLog = document.getElementById("progress-log");
    const item = document.createElement("div");
    item.className = "progress-item";
    item.textContent = message;
    progressLog.appendChild(item);
    item.scrollIntoView({ behavior: "smooth" });
}

function displayReport(markdown) {
    document.getElementById("report-card").style.display = "block";
    document.getElementById("report-output").innerHTML = renderMarkdown(markdown);
    document.getElementById("report-card").scrollIntoView({ behavior: "smooth" });
}

function renderMarkdown(text) {
    return text
        .replace(/^# (.+)$/gm, "<h1>$1</h1>")
        .replace(/^## (.+)$/gm, "<h2>$1</h2>")
        .replace(/^### (.+)$/gm, "<h3>$1</h3>")
        .replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>")
        .replace(/\*(.+?)\*/g, "<em>$1</em>")
        .replace(/^- (.+)$/gm, "<li>$1</li>")
        .replace(/(<li>.*<\/li>)/s, "<ul>$1</ul>")
        .replace(/\[(.+?)\]\((.+?)\)/g, '<a href="$2" target="_blank">$1</a>')
        .replace(/^---$/gm, "<hr>")
        .replace(/\n\n/g, "</p><p>")
        .replace(/^(?!<[h|u|l|p])/gm, "<p>")
}

function downloadReport() {
    if (!reportMarkdown) return;

    const topic = document.getElementById("topic-input").value.trim();
    const filename = topic.toLowerCase().replace(/\s+/g, "_") + "_report.md";
    const blob = new Blob([reportMarkdown], { type: "text/markdown" });
    const url = URL.createObjectURL(blob);

    const downloadLink = document.createElement("a");
    downloadLink.href = url;
    downloadLink.download = filename;
    downloadLink.click();

    URL.revokeObjectURL(url);
}

window.addEventListener('DOMContentLoaded', fitTitle);
window.addEventListener('resize', fitTitle);
