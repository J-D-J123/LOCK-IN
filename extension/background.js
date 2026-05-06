// ── BLOCKED DOMAINS ─────────────────────────────────────────
const BLOCKED_DOMAINS = [
  'youtube.com',
  'instagram.com',
  'x.com',
  'twitter.com',
  'tiktok.com',
  'reddit.com',
  'facebook.com',
  'netflix.com',
  'twitch.tv',
  'snapchat.com',
  'pinterest.com',
  'tumblr.com',
];

const DEFAULT_DURATION_MINUTES = 30;

// ── BUILD BLOCKING RULES ─────────────────────────────────────
// One rule per domain — requestDomains handles all subdomains automatically
function buildRules() {
  return BLOCKED_DOMAINS.map((domain, i) => ({
    id: i + 1,
    priority: 1,
    action: {
      type: 'redirect',
      redirect: { extensionPath: '/blocked.html' },
    },
    condition: {
      requestDomains: [domain],
      resourceTypes: ['main_frame'],
    },
  }));
}

// ── LOCKDOWN ON ──────────────────────────────────────────────
async function startLockdown(durationMinutes) {
  const dur     = durationMinutes || DEFAULT_DURATION_MINUTES;
  const endTime = Date.now() + dur * 60 * 1000;

  await chrome.storage.local.set({ lockdownActive: true, lockdownEndTime: endTime });

  // Enable blocking rules
  const rules = buildRules();
  await chrome.declarativeNetRequest.updateDynamicRules({
    removeRuleIds: rules.map(r => r.id),
    addRules: rules,
  });

  // Redirect any currently open distracting tabs
  const tabs = await chrome.tabs.query({});
  for (const tab of tabs) {
    if (tab.url && BLOCKED_DOMAINS.some(d => tab.url.includes(d))) {
      chrome.tabs.update(tab.id, { url: chrome.runtime.getURL('blocked.html') });
    }
  }

  // Prevent new tabs being useful — redirect chrome://newtab to blocked page
  await chrome.storage.local.set({ blockNewTabs: true });

  // Alarm to auto-end lockdown
  chrome.alarms.create('lockdown_end',    { when: endTime });
  // Badge update every minute
  chrome.alarms.create('badge_tick', { periodInMinutes: 1 });

  updateBadge(endTime);
}

// ── LOCKDOWN OFF ─────────────────────────────────────────────
async function endLockdown() {
  await chrome.storage.local.set({ lockdownActive: false, lockdownEndTime: 0, blockNewTabs: false });

  const rules = buildRules();
  await chrome.declarativeNetRequest.updateDynamicRules({
    removeRuleIds: rules.map(r => r.id),
    addRules: [],
  });

  chrome.alarms.clear('lockdown_end');
  chrome.alarms.clear('badge_tick');
  chrome.action.setBadgeText({ text: '' });
}

// ── BADGE ────────────────────────────────────────────────────
function updateBadge(endTime) {
  const ms      = Math.max(0, endTime - Date.now());
  const minutes = Math.ceil(ms / 60000);
  if (minutes > 0) {
    chrome.action.setBadgeText({ text: minutes + 'm' });
    chrome.action.setBadgeBackgroundColor({ color: '#FF6B00' });
  } else {
    chrome.action.setBadgeText({ text: '' });
  }
}

// ── NEW TAB INTERCEPT ────────────────────────────────────────
// When lockdown is active, redirect new blank tabs to blocked page
chrome.tabs.onCreated.addListener(async (tab) => {
  const data = await chrome.storage.local.get('blockNewTabs');
  if (!data.blockNewTabs) return;

  // Only intercept true new tabs (about:blank / newtab), not extension pages or existing URLs
  const url = tab.pendingUrl || tab.url || '';
  if (url === 'chrome://newtab/' || url === '' || url === 'about:blank') {
    // Give the browser a moment to settle, then redirect
    setTimeout(() => {
      chrome.tabs.update(tab.id, { url: chrome.runtime.getURL('blocked.html') });
    }, 150);
  }
});

// ── MESSAGES ─────────────────────────────────────────────────
chrome.runtime.onMessage.addListener((msg, _sender, respond) => {
  if (msg.type === 'START_LOCKDOWN') {
    startLockdown(msg.durationMinutes).then(() => respond({ ok: true }));
    return true;
  }
  if (msg.type === 'END_LOCKDOWN') {
    endLockdown().then(() => respond({ ok: true }));
    return true;
  }
  if (msg.type === 'GET_STATUS') {
    chrome.storage.local.get(['lockdownActive', 'lockdownEndTime'], respond);
    return true;
  }
});

// ── ALARMS ───────────────────────────────────────────────────
chrome.alarms.onAlarm.addListener(async (alarm) => {
  if (alarm.name === 'lockdown_end') {
    await endLockdown();
  }
  if (alarm.name === 'badge_tick') {
    const data = await chrome.storage.local.get(['lockdownActive', 'lockdownEndTime']);
    if (data.lockdownActive) updateBadge(data.lockdownEndTime);
  }
});

// ── TOOLBAR CLICK → open detector tab ───────────────────────
chrome.action.onClicked.addListener(async () => {
  const url      = chrome.runtime.getURL('detector.html');
  const existing = await chrome.tabs.query({ url });
  if (existing.length > 0) {
    chrome.tabs.update(existing[0].id, { active: true });
    chrome.windows.update(existing[0].windowId, { focused: true });
  } else {
    chrome.tabs.create({ url });
  }
});

// ── RESTORE STATE ON BROWSER START ───────────────────────────
chrome.runtime.onStartup.addListener(async () => {
  const data = await chrome.storage.local.get(['lockdownActive', 'lockdownEndTime']);
  if (data.lockdownActive && data.lockdownEndTime > Date.now()) {
    const rules = buildRules();
    await chrome.declarativeNetRequest.updateDynamicRules({
      removeRuleIds: rules.map(r => r.id),
      addRules: rules,
    });
    chrome.alarms.create('lockdown_end',    { when: data.lockdownEndTime });
    chrome.alarms.create('badge_tick', { periodInMinutes: 1 });
    updateBadge(data.lockdownEndTime);
  } else if (data.lockdownActive) {
    // Lockdown expired while browser was closed
    await endLockdown();
  }
});
