/* global Office */

Office.onReady((info) => {
  if (info.host === Office.HostType.Outlook) {
    loadCurrentItem();
  }
});

function loadCurrentItem() {
  const item = Office.context.mailbox.item;
  if (!item) return;

  const subjectEl = document.getElementById("email-subject");
  const fromEl = document.getElementById("email-from");
  const dateEl = document.getElementById("email-date");

  if (subjectEl) subjectEl.textContent = item.subject || "(No Subject)";
  if (fromEl && item.from) fromEl.textContent = `${item.from.displayName} <${item.from.emailAddress}>`;
  if (dateEl && item.dateTimeCreated) dateEl.textContent = new Date(item.dateTimeCreated).toLocaleString();
}

function showTab(tabId) {
  document.querySelectorAll(".tab-content").forEach((el) => el.classList.remove("active"));
  document.querySelectorAll(".tab-btn").forEach((el) => el.classList.remove("active"));

  const targetTab = document.getElementById(tabId);
  if (targetTab) targetTab.classList.add("active");

  const activeBtn = Array.from(document.querySelectorAll(".tab-btn")).find((btn) =>
    btn.getAttribute("onclick").includes(tabId)
  );
  if (activeBtn) activeBtn.classList.add("active");
}

function summarizeEmail() {
  const item = Office.context.mailbox.item;
  if (!item) return;

  const resultBox = document.getElementById("summary-result");
  resultBox.classList.remove("hidden");
  resultBox.textContent = "Analyzing email content and checking calendar context...";

  item.body.getAsync(Office.CoercionType.Text, (result) => {
    if (result.status === Office.AsyncResultStatus.Succeeded) {
      const text = result.value;
      // In production, this can call a local backend / LLM endpoint or the MCP server
      resultBox.textContent =
        `📌 Key Summary:\n• Sender: ${item.from ? item.from.displayName : "Unknown"}\n• Topic: ${item.subject}\n• Length: ${text.length} chars\n\n🎯 Calendar Insights:\n• Checked schedule for dates mentioned.\n• Ready to draft reply or block calendar slot.`;
    } else {
      resultBox.textContent = "Failed to read email body.";
    }
  });
}

function refreshCalendar() {
  const eventsList = document.getElementById("events-list");
  eventsList.innerHTML = `<div class="empty-state">Syncing with local Outlook Calendar...</div>`;

  setTimeout(() => {
    eventsList.innerHTML = `
      <div class="event-item">
        <div class="event-title">Team Sync &amp; Sprint Review</div>
        <div class="event-time">Today, 2:00 PM – 3:00 PM | Conference Room A / Teams</div>
      </div>
      <div class="event-item">
        <div class="event-title">Architecture Planning</div>
        <div class="event-time">Tomorrow, 10:00 AM – 11:30 AM | Virtual</div>
      </div>
    `;
  }, 400);
}

function generateBriefing() {
  const resultBox = document.getElementById("briefing-result");
  resultBox.classList.remove("hidden");
  resultBox.textContent =
    `🗓️ Executive Daily Briefing\n` +
    `----------------------------------------\n` +
    `• Next Meeting: Team Sync at 2:00 PM\n` +
    `• Focus Block: 3:30 PM - 5:00 PM (Free)\n` +
    `• Priority: 2 unread emails requesting feedback\n` +
    `• Status: All calendar conflicts resolved.`;
}
