let reportMarkdown = "";

(function () {
  const CONFIG = {
    width: 60, height: 60,
    radius: 18, coneHeight: 28,
    particleSpacing: 1.4, dotSize: 0.5,
    color: '221, 161, 94',
    rotationSpeed: 0.012, tiltX: 0.35, fov: 90,
  };

  const canvas = document.getElementById('particle-cone-btn');
  if (!canvas) return;
  const ctx = canvas.getContext('2d');
  canvas.width = CONFIG.width;
  canvas.height = CONFIG.height;

  function buildConePoints() {
    const pts = [], R = CONFIG.radius, H = CONFIG.coneHeight, STEP = CONFIG.particleSpacing, baseY = H / 2;
    for (let px = -R; px <= R; px += STEP)
      for (let pz = -R; pz <= R; pz += STEP)
        if (px*px + pz*pz <= R*R) pts.push({ x: px, y: baseY, z: pz });
    const slices = Math.ceil(H / STEP);
    for (let si = 0; si <= slices; si++) {
      const t = si / slices, y = baseY - t * H, r = R * (1 - t);
      const steps = Math.max(1, Math.round(2 * Math.PI * r / STEP));
      for (let j = 0; j < steps; j++) {
        const theta = (2 * Math.PI * j) / steps;
        pts.push({ x: r * Math.cos(theta), y, z: r * Math.sin(theta) });
      }
    }
    return pts;
  }

  const points = buildConePoints();
  let angleY = 0;

  const rotateX = (p, a) => ({ x: p.x, y: p.y * Math.cos(a) - p.z * Math.sin(a), z: p.y * Math.sin(a) + p.z * Math.cos(a) });
  const rotateY = (p, a) => ({ x: p.x * Math.cos(a) + p.z * Math.sin(a), y: p.y, z: -p.x * Math.sin(a) + p.z * Math.cos(a) });
  const project = (p) => {
    const z = p.z + CONFIG.fov;
    return { x: (p.x * CONFIG.fov) / z + CONFIG.width / 2, y: (p.y * CONFIG.fov) / z + CONFIG.height / 2, z: p.z };
  };

  function draw() {
    ctx.clearRect(0, 0, CONFIG.width, CONFIG.height);
    angleY += CONFIG.rotationSpeed;
    const projected = points.map(p => { let r = rotateX(p, CONFIG.tiltX); r = rotateY(r, angleY); return project(r); });
    projected.sort((a, b) => a.z - b.z);
    const R = CONFIG.radius;
    for (const p of projected) {
      const depth = (p.z + R + 40) / (R * 2 + 40);
      const alpha = 0.15 + depth * 0.85;
      const radius = CONFIG.dotSize * (0.4 + depth * 0.7);
      ctx.beginPath();
      ctx.arc(p.x, p.y, radius, 0, Math.PI * 2);
      ctx.fillStyle = `rgba(${CONFIG.color}, ${alpha})`;
      ctx.fill();
    }
    requestAnimationFrame(draw);
  }

  draw();
})();

function openModal(id) {
    document.getElementById(id).classList.add('open');
}

function closeModal(id) {
    document.getElementById(id).classList.remove('open');
}

function closeModalOutside(event, id) {
    if (event.target.id === id) closeModal(id);
}

function toggleSidebar() {
    document.getElementById('sidebar').classList.toggle('open');
    document.getElementById('overlay').classList.toggle('open');
}

function handleKeyDown(e) {
    if (e.key === 'Enter') startResearch();
}

async function startResearch() {
    const topic = document.getElementById("topic-input").value.trim();

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
            body: JSON.stringify({ topic })
        });

        if (response.status === 429) {
            document.getElementById("progress-card").style.display = "none";
            openModal("ratelimit-modal");
            return;
        }

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
