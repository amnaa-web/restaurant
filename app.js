const API = "";

const $ = (s) => document.querySelector(s);

async function api(p, o = {}) {
  const r = await fetch(API + p, {
    headers: {
      "Content-Type": "application/json"
    },
    ...o
  });

  if (!r.ok) {
    const error = await r.json().catch(() => ({
      detail: "Request failed"
    }));

    throw new Error(
      error.detail || "Request failed"
    );
  }

  return r.json();
}


function add(t, c) {
  const d = document.createElement("div");

  d.className = "msg " + c;
  d.textContent = t;

  $("#chatLog").appendChild(d);

  $("#chatLog").scrollTop =
    $("#chatLog").scrollHeight;
}


async function load() {
  try {

    const h = await api(
      "/api/health"
    );

    $("#status").textContent =
      "Backend online · " + h.ai_mode;


    const ops = await api(
      "/api/ops"
    );

    $("#workflowList").innerHTML =
      ops.automation_ideas
        .map(
          (x) => `
            <div class="item">
              <b>${x.title}</b>
              <div>${x.impact}</div>
              <small>${x.status}</small>
            </div>
          `
        )
        .join("");


    const rows = await api(
      "/api/reservations"
    );

    $("#bookingList").innerHTML =
      rows.length
        ? rows
            .map(
              (r) => `
                <div class="item">
                  <b>${r.guest_name}</b>
                  · party of ${r.party_size}

                  <div>
                    ${r.date}
                    at
                    ${r.time}
                  </div>
                </div>
              `
            )
            .join("")
        : "No reservations yet.";

  } catch (e) {

    $("#status").textContent =
      "Backend offline";

    console.error(
      "Load error:",
      e
    );
  }
}


$("#chatForm").onsubmit =
  async (e) => {

    e.preventDefault();

    const input =
      $("#chatInput");

    const m =
      input.value.trim();

    if (!m) {
      return;
    }

    add(
      m,
      "user"
    );

    input.value = "";

    $("#chatMeta").textContent =
      "Thinking...";

    try {

      const d = await api(
        "/api/chat",
        {
          method: "POST",

          body:
            JSON.stringify({
              message: m
            })
        }
      );

      add(
        d.reply,
        "bot"
      );

      $("#chatMeta").textContent =
        d.intent +
        " · " +
        d.source;

    } catch (e) {

      add(
        "Unable to process your request right now.",
        "bot"
      );

      $("#chatMeta").textContent =
        "Request failed";

      console.error(
        e
      );
    }
  };


$("#bookingForm").onsubmit =
  async (e) => {

    e.preventDefault();

    const form =
      e.currentTarget;

    const p =
      Object.fromEntries(
        new FormData(form)
      );

    p.party_size =
      Number(
        p.party_size
      );

    try {

      const d = await api(
        "/api/reservations",
        {
          method: "POST",

          body:
            JSON.stringify(p)
        }
      );

      $("#bookingResult").textContent =
        `Reservation #${d.id} confirmed for ${d.guest_name}`;

      form.reset();

      setDefaultDate();

      await load();

    } catch (e) {

      $("#bookingResult").textContent =
        "Reservation failed: " +
        e.message;

      console.error(
        e
      );
    }
  };


function setDefaultDate() {

  const dt =
    new Date();

  dt.setDate(
    dt.getDate() + 1
  );

  document.querySelector(
    '[name="date"]'
  ).value =
    dt
      .toISOString()
      .slice(
        0,
        10
      );
}


setDefaultDate();

load();
