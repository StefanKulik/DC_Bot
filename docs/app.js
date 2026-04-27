const statusNode = document.querySelector("#status");
const contentNode = document.querySelector("#content");
const guildTemplate = document.querySelector("#guild-template");
const entryTemplate = document.querySelector("#entry-template");

const projectNameNode = document.querySelector("#project-name");
const projectTaglineNode = document.querySelector("#project-tagline");
const guildCountNode = document.querySelector("#guild-count");
const entryCountNode = document.querySelector("#entry-count");
const generatedAtNode = document.querySelector("#generated-at");

function formatDate(value) {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return "unbekannt";
  }

  return new Intl.DateTimeFormat("de-DE", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(date);
}

function createEntryNode(entry) {
  const fragment = entryTemplate.content.cloneNode(true);
  fragment.querySelector(".entry-category").textContent = entry.category || "Allgemein";
  fragment.querySelector(".entry-date").textContent = formatDate(entry.updatedAt || entry.createdAt);
  fragment.querySelector(".entry-title").textContent = entry.title;
  fragment.querySelector(".entry-description").textContent = entry.description;

  const link = fragment.querySelector(".entry-link");
  if (entry.linkUrl) {
    link.href = entry.linkUrl;
  } else {
    link.remove();
  }

  return fragment;
}

function createGuildNode(guild) {
  const fragment = guildTemplate.content.cloneNode(true);
  const card = fragment.querySelector(".guild-card");
  card.style.setProperty("--accent", guild.accentColor || "#1f7aec");

  fragment.querySelector(".guild-name").textContent = guild.name;
  fragment.querySelector(".guild-description").textContent = guild.description;

  const inviteLink = fragment.querySelector(".guild-link");
  if (guild.inviteUrl) {
    inviteLink.href = guild.inviteUrl;
  } else {
    inviteLink.remove();
  }

  const entryList = fragment.querySelector(".entry-list");
  guild.entries.forEach((entry) => {
    entryList.appendChild(createEntryNode(entry));
  });

  return fragment;
}

async function loadData() {
  try {
    const response = await fetch("./data/site-data.json", { cache: "no-store" });
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }

    const data = await response.json();
    projectNameNode.textContent = data.project?.name || "Discord Bot Showcase";
    projectTaglineNode.textContent = data.project?.tagline || "Inhalte aus der Bot-Datenbank";
    guildCountNode.textContent = String(data.totals?.guildCount ?? 0);
    entryCountNode.textContent = String(data.totals?.entryCount ?? 0);
    generatedAtNode.textContent = formatDate(data.generatedAt);

    contentNode.innerHTML = "";

    if (!data.guilds || data.guilds.length === 0) {
      statusNode.textContent = "Noch keine veroefentlichten Inhalte vorhanden.";
      return;
    }

    data.guilds.forEach((guild) => {
      contentNode.appendChild(createGuildNode(guild));
    });
    statusNode.textContent = "";
  } catch (error) {
    statusNode.textContent = "Die Exportdatei konnte nicht geladen werden.";
    console.error(error);
  }
}

loadData();
